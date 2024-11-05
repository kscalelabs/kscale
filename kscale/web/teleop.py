"""Client code for WebRTC video/audio streaming.

To set up a local peer-to-peer WebRTC connection:

1. Start the signaling server in one terminal:

   python -m kscale.web.teleop server

2. Start the first peer (sender) in another terminal:

   python -m kscale.web.teleop client

   - Note the Room ID that is printed

3. Start the second peer (receiver) in a third terminal:

   python -m kscale.web.teleop client --join-room <ROOM_ID>

The sender's webcam feed will be displayed on the receiver's screen.
"""

import asyncio
import json
import logging
import sys
import uuid
from typing import Optional

import aiohttp
import click
import colorlogging
import cv2
import numpy as np
from aiohttp import web
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaStreamTrack
from av import VideoFrame

from kscale.utils.cli import coro

logger = logging.getLogger(__name__)


class VideoTransformTrack(MediaStreamTrack):
    """Video stream transform track for SBS format."""

    kind = "video"

    def __init__(self, track: MediaStreamTrack) -> None:
        super().__init__()
        self.track = track

    async def recv(self) -> VideoFrame:
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        # Create side-by-side duplicate
        sbs_img = np.hstack([img, img])

        # Convert back to VideoFrame
        new_frame = VideoFrame.from_ndarray(sbs_img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base

        return new_frame


class WebRTCClient:
    def __init__(self, server_url: str = "http://localhost:8080", room_id: Optional[str] = None) -> None:
        """Initialize WebRTC client.

        Args:
            server_url: URL of the signaling server
            room_id: Room ID to join. If None, creates a new room.
        """
        self.server_url = server_url
        self.peer_connection: Optional[RTCPeerConnection] = None
        self.room_id = room_id or str(uuid.uuid4())
        self.is_offerer = room_id is None
        self.video_track: Optional[MediaStreamTrack] = None

    async def get_media_stream(self) -> MediaPlayer:
        """Get video/audio stream from webcam."""
        options = {
            "framerate": "30",
            "video_size": "640x480",
        }

        if hasattr(MediaPlayer, "_get_default_video_device"):
            # Windows
            options["input_format"] = "yuyv422"  # Windows-specific format
            player = MediaPlayer(
                MediaPlayer._get_default_video_device(),
                format="dshow",
                options=options,
            )
        else:
            # Linux/Mac
            # For Mac, we use "default" instead of "0:none" and specify video device
            player = MediaPlayer(
                "default:none" if sys.platform == "darwin" else "0:none",
                format="avfoundation",
                options={
                    **options,
                    "video_device_index": "0",  # Use the default camera
                },
            )
        return player

    async def create_peer_connection(self) -> RTCPeerConnection:
        """Create and configure peer connection."""
        self.peer_connection = RTCPeerConnection()

        @self.peer_connection.on("icecandidate")
        async def on_ice_candidate(candidate: RTCIceCandidate) -> None:
            if candidate:
                await self.send_ice_candidate(candidate, is_offer=True)

        @self.peer_connection.on("track")
        async def on_track(track: MediaStreamTrack) -> None:
            if track.kind == "video":
                self.video_track = track
                asyncio.create_task(self.display_video())

        # Get media stream and add tracks
        player = await self.get_media_stream()
        if player.audio:
            self.peer_connection.addTrack(player.audio)
        if player.video:
            # Add transformed video track instead of original
            transformed_track = VideoTransformTrack(player.video)
            self.peer_connection.addTrack(transformed_track)

        return self.peer_connection

    async def create_offer(self) -> None:
        """Create and send offer to the signaling server."""
        # Create offer
        offer = await self.peer_connection.createOffer()
        await self.peer_connection.setLocalDescription(offer)

        # Send offer to signaling server
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.server_url}/offer",
                json={"roomId": self.room_id, "offer": {"sdp": offer.sdp, "type": offer.type}},
            )

    async def send_ice_candidate(self, candidate: RTCIceCandidate, is_offer: bool) -> None:
        """Send ICE candidate to the signaling server."""
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.server_url}/ice-candidate",
                json={
                    "roomId": self.room_id,
                    "candidate": {
                        "candidate": candidate.candidate,
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex,
                    },
                    "isOffer": is_offer,
                },
            )

    async def wait_for_answer(self) -> None:
        """Poll the server for an answer."""
        logger.info("Waiting for answer...")
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(f"{self.server_url}/answer/{self.room_id}") as response:
                    data = await response.json()
                    if data.get("answer"):
                        logger.info("Answer received")
                        answer = RTCSessionDescription(sdp=data["answer"]["sdp"], type=data["answer"]["type"])
                        await self.peer_connection.setRemoteDescription(answer)
                        break
                    logger.debug("No answer yet, retrying...")
                    await asyncio.sleep(1)

    async def get_ice_candidates(self) -> None:
        """Get ICE candidates from the server."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.server_url}/ice-candidates/{self.room_id}", params={"isOffer": "false"}
            ) as response:
                data = await response.json()
                for candidate_data in data.get("candidates", []):
                    # Parse the candidate string
                    candidate = candidate_data["candidate"]
                    parts = candidate.split()

                    # Example candidate string:
                    # candidate:1 1 UDP 2113937151 192.168.1.1 54400 typ host
                    if len(parts) >= 8:
                        candidate_obj = RTCIceCandidate(
                            component=int(parts[1]),
                            foundation=parts[0].split(":")[1],
                            protocol=parts[2].lower(),
                            priority=int(parts[3]),
                            ip=parts[4],
                            port=int(parts[5]),
                            type=parts[7],
                            sdpMid=candidate_data["sdpMid"],
                            sdpMLineIndex=candidate_data["sdpMLineIndex"],
                        )
                        await self.peer_connection.addIceCandidate(candidate_obj)

    async def display_video(self) -> None:
        """Log the received video frames to a file."""
        logger.info("Starting video logging")

        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter("output.avi", fourcc, 30.0, (640, 480))

        while True:
            try:
                logger.debug("Waiting for next frame...")
                frame = await self.video_track.recv()
                logger.debug("Received frame")
                img = frame.to_ndarray(format="bgr24")
                logger.debug(f"Converted frame to numpy array: shape={img.shape}")

                # Write the frame to the file
                out.write(img)

            except Exception as e:
                logger.error(f"Error logging video: {e}")
                logger.exception("Full traceback:")
                break

        logger.info("Closing video logging")
        out.release()


class WebRTCSignalingServer:
    def __init__(self) -> None:
        self.rooms = {}  # Dict to store room_id -> connection info
        self.app = web.Application()
        self.app.router.add_post("/offer", self.handle_offer)
        self.app.router.add_post("/answer", self.handle_answer)
        self.app.router.add_post("/ice-candidate", self.handle_ice_candidate)
        self.app.router.add_get("/answer/{room_id}", self.handle_answer_get)
        self.app.router.add_get("/ice-candidates/{room_id}", self.handle_ice_candidates)
        self.app.router.add_get("/offer/{room_id}", self.handle_get_offer)
        self.rooms = {}  # Will store room_id -> {offer, answer, ice_candidates}

    async def handle_offer(self, request: web.Request) -> web.Response:
        data = await request.json()
        room_id = data["roomId"]

        # Store offer in room
        if room_id not in self.rooms:
            self.rooms[room_id] = {"offer": data["offer"], "ice_candidates": [], "answer": None}

        # Simply return success - don't create a peer connection
        return web.Response(status=204)

    async def handle_ice_candidate(self, request: web.Request) -> web.Response:
        data = await request.json()
        room_id = data["roomId"]
        if room_id in self.rooms:
            if "ice_candidates" not in self.rooms[room_id]:
                self.rooms[room_id]["ice_candidates"] = []
            self.rooms[room_id]["ice_candidates"].append(data["candidate"])
        return web.Response(status=204)

    async def handle_answer(self, request: web.Request) -> web.Response:
        """Handle POST request for answer."""
        data = await request.json()
        room_id = data["roomId"]
        if room_id in self.rooms:
            self.rooms[room_id]["answer"] = data["answer"]
        return web.Response(status=204)

    async def handle_ice_candidates(self, request: web.Request) -> web.Response:
        return web.Response(
            content_type="application/json",
            text=json.dumps({"candidates": self.rooms[request.match_info["room_id"]]["ice_candidates"]}),
        )

    async def handle_get_offer(self, request: web.Request) -> web.Response:
        """Handle GET request for offer."""
        room_id = request.match_info["room_id"]
        if room_id in self.rooms:
            offer = self.rooms[room_id].get("offer")
            if offer:
                return web.Response(content_type="application/json", text=json.dumps({"offer": offer}))
        return web.Response(content_type="application/json", text=json.dumps({"offer": None}))

    async def handle_answer_get(self, request: web.Request) -> web.Response:
        """Handle GET request for answer."""
        room_id = request.match_info["room_id"]
        if room_id in self.rooms:
            answer = self.rooms[room_id].get("answer")
            if answer:
                return web.Response(content_type="application/json", text=json.dumps({"answer": answer}))
        return web.Response(content_type="application/json", text=json.dumps({"answer": None}))

    def run(self) -> None:
        """Run the signaling server."""
        web.run_app(self.app, host="0.0.0.0", port=8080)


@click.group()
def cli() -> None:
    """K-Scale WebRTC CLI tool."""
    pass


@cli.command()
def server() -> None:
    """Run the WebRTC server."""
    server = WebRTCSignalingServer()
    server.run()


@cli.command()
@click.option("--server-url", default="http://localhost:8080")
@click.option("--join-room", help="Room ID to join as receiver")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@coro
async def client(server_url: str, join_room: Optional[str], debug: bool) -> None:
    """Run the WebRTC client.

    If --join-room is provided, joins as receiver.
    Otherwise, creates a new room as sender.
    """
    colorlogging.configure(level=logging.DEBUG if debug else logging.INFO)

    client = WebRTCClient(server_url, room_id=join_room)

    if client.is_offerer:
        logger.info("Creating new room as sender")
        logger.info("Room ID: %s", client.room_id)
        logger.debug("Creating peer connection...")
        await client.create_peer_connection()
        logger.debug("Creating and sending offer...")
        await client.create_offer()
        logger.debug("Waiting for answer...")
        await client.wait_for_answer()
    else:
        logger.info(f"Joining room {join_room} as receiver")
        logger.debug("Creating peer connection...")
        await client.create_peer_connection()

        # Get the offer from the server first
        async with aiohttp.ClientSession() as session:
            logger.debug("Getting offer from server...")
            async with session.get(f"{server_url}/offer/{join_room}") as response:
                data = await response.json()
                if not data.get("offer"):
                    logger.error("No offer found for room")
                    return

                logger.debug("Setting remote description...")
                offer = RTCSessionDescription(sdp=data["offer"]["sdp"], type=data["offer"]["type"])
                await client.peer_connection.setRemoteDescription(offer)

                logger.debug("Creating and setting local answer...")
                answer = await client.peer_connection.createAnswer()
                await client.peer_connection.setLocalDescription(answer)

                logger.debug("Sending answer to server...")
                await session.post(
                    f"{server_url}/answer",
                    json={"roomId": join_room, "answer": {"sdp": answer.sdp, "type": answer.type}},
                )

    logger.info("Getting ICE candidates")
    await client.get_ice_candidates()

    logger.info("Connection established")

    try:
        await asyncio.Future()
    finally:
        logger.info("Closing connection")
        if client.peer_connection:
            await client.peer_connection.close()
    logger.info("Connection closed")


if __name__ == "__main__":
    # python -m kscale.web.teleop
    cli()
