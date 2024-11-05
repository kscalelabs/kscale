"""This script lets you easily set up a robot for teleoperation.

Example usage:

python -m kscale.web.teleop server
python -m kscale.web.teleop client --server-url http://localhost:8080 --join-room <room-id>
"""

import asyncio
import json
import logging
import sys
import uuid
from multiprocessing import Process, Queue
from queue import Empty, Full
from typing import Optional

import aiohttp
import click
import colorlogging
import cv2
from aiohttp import web
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaStreamTrack

from kscale.utils.cli import coro

logger = logging.getLogger(__name__)


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
        options = {"framerate": "30", "video_size": "640x480"}
        try:
            if sys.platform == "darwin":
                # MacOS
                player = MediaPlayer("default:none", format="avfoundation", options=options)
            elif sys.platform.startswith("linux"):
                # Linux
                player = MediaPlayer("/dev/video0", format="v4l2", options=options)
            elif sys.platform.startswith("win"):
                # Windows
                player = MediaPlayer(None, format="dshow", options=options)
            else:
                raise RuntimeError("Unsupported platform")

            if not player.video:
                raise RuntimeError("No video track available from webcam")
            logger.info("Successfully initialized webcam stream")
            return player
        except Exception as e:
            logger.error(f"Failed to initialize webcam: {e}")
            raise

    async def create_peer_connection(self) -> RTCPeerConnection:
        """Create and configure peer connection."""
        self.peer_connection = RTCPeerConnection()

        logger.debug("Adding ICE candidate event handler")

        @self.peer_connection.on("icecandidate")
        async def on_ice_candidate(candidate: Optional[RTCIceCandidate]) -> None:
            logger.debug(f"ICE candidate event: {candidate}")
            if candidate:
                await self.send_ice_candidate(candidate, is_offer=self.is_offerer)
            else:
                logger.debug("ICE gathering complete")

        @self.peer_connection.on("track")
        async def on_track(track: MediaStreamTrack) -> None:
            logger.debug(f"Track received: {track.kind}")
            if track.kind == "video":
                self.video_track = track
                asyncio.create_task(self.display_video())

        # Get media stream and add tracks
        player = await self.get_media_stream()
        if player.audio:
            self.peer_connection.addTrack(player.audio)
        if player.video:
            # Add original video track
            self.peer_connection.addTrack(player.video)
            logger.info("Adding video track")
            logger.info(f"Video track added to connection: {player.video}")
        else:
            logger.error("No video track found in media player")

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
        is_offer_param = "false" if self.is_offerer else "true"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.server_url}/ice-candidates/{self.room_id}", params={"isOffer": is_offer_param}
            ) as response:
                data = await response.json()
                for candidate_data in data.get("candidates", []):
                    candidate = candidate_data["candidate"]
                    candidate_obj = RTCIceCandidate(
                        sdpMid=candidate_data["sdpMid"],
                        sdpMLineIndex=candidate_data["sdpMLineIndex"],
                        candidate=candidate,
                    )
                    await self.peer_connection.addIceCandidate(candidate_obj)

    @staticmethod
    def display_frames(frame_queue: Queue) -> None:
        """Display frames from the queue."""
        logger.info("Starting display process")
        try:
            # Create window with a reasonable default size
            cv2.namedWindow("WebRTC Stream", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("WebRTC Stream", 1280, 720)  # Set to 720p size
            logger.info("Created OpenCV window")

            while True:
                logger.debug("Waiting for frame...")
                try:
                    img = frame_queue.get(timeout=0.1)  # 100ms timeout
                    if img is None:  # Exit signal
                        logger.info("Received exit signal")
                        break

                    cv2.imshow("WebRTC Stream", img)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        logger.info("Quit signal received")
                        break
                except Empty:
                    cv2.waitKey(1)
                    continue
        except Exception as e:
            logger.error(f"Error in display process: {e}")
            logger.exception("Full traceback:")
        finally:
            cv2.destroyAllWindows()
            logger.info("Display process finished")

    @staticmethod
    def record_frames(frame_queue: Queue) -> None:
        """Record frames from the queue."""
        logger.info("Starting recording process")
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter("output.avi", fourcc, 30.0, (640, 480))
        try:
            while True:
                if not frame_queue.empty():
                    img = frame_queue.get()
                    if img is None:  # Exit signal
                        break
                    out.write(img)
        finally:
            out.release()
        logger.info("Recording process finished")

    async def display_video(self) -> None:
        """Handle video processing based on client role."""
        if self.is_offerer:
            # Producer: Monitor webcam frames
            logger.info("Starting producer video monitoring")
            try:
                if not self.peer_connection:
                    raise RuntimeError("No peer connection available")

                senders = self.peer_connection.getSenders()
                video_sender = next((s for s in senders if s.track and s.track.kind == "video"), None)

                if not video_sender:
                    raise RuntimeError("No video sender found in peer connection")

                logger.info(f"Successfully configured video sender: {video_sender.track}")

                # Keep connection alive while monitoring frame stats
                while True:
                    await asyncio.sleep(5)
                    stats = await video_sender.getStats()
                    frames_sent = sum(s.framesSent for s in stats.values() if hasattr(s, "framesSent"))
                    logger.info(f"Frames sent in last 5s: {frames_sent}")

            except Exception as e:
                logger.error(f"Producer video error: {e}")
                raise
        else:
            # Consumer: Display received video
            logger.info("Starting display as consumer")
            if self.video_track is None:
                logger.error("No video track available!")
                return

            display_queue = Queue(maxsize=30)  # Limit queue size to prevent memory issues
            logger.debug("Created display queue")

            display_process = Process(target=self.display_frames, args=(display_queue,))
            logger.debug("Created display process")

            display_process.start()
            logger.info("Started display process")

            frame_count = 0
            try:
                while True:
                    try:
                        logger.debug("Consumer waiting for frame...")
                        frame = await self.video_track.recv()
                        frame_count += 1
                        logger.info(f"Consumer received frame #{frame_count}")
                        img = frame.to_ndarray(format="bgr24")
                        try:
                            display_queue.put_nowait(img)
                            logger.debug(f"Frame #{frame_count} added to display queue")
                        except Full:
                            logger.warning(f"Queue full, skipping frame #{frame_count}")
                            continue
                    except Exception as e:
                        logger.error(f"Error processing frame: {e}")
                        logger.exception("Full traceback:")
                        break
            finally:
                logger.info(f"Consumer processed total of {frame_count} frames")
                logger.info("Sending exit signal to display process")
                try:
                    display_queue.put(None, timeout=1.0)
                except Full:
                    logger.warning("Could not send exit signal, queue full")
                display_process.join(timeout=5.0)
                if display_process.is_alive():
                    logger.warning("Display process did not terminate, forcing...")
                    display_process.terminate()
                logger.info("Display finished")


class WebRTCSignalingServer:
    def __init__(self) -> None:
        self.rooms = {}  # room_id -> {offer, answer, offer_ice_candidates, answer_ice_candidates}
        self.app = web.Application()
        self.app.router.add_post("/offer", self.handle_offer)
        self.app.router.add_post("/answer", self.handle_answer)
        self.app.router.add_post("/ice-candidate", self.handle_ice_candidate)
        self.app.router.add_get("/answer/{room_id}", self.handle_answer_get)
        self.app.router.add_get("/ice-candidates/{room_id}", self.handle_ice_candidates)
        self.app.router.add_get("/offer/{room_id}", self.handle_get_offer)

    async def handle_offer(self, request: web.Request) -> web.Response:
        data = await request.json()
        room_id = data["roomId"]

        # Store offer in room
        if room_id not in self.rooms:
            self.rooms[room_id] = {
                "offer": data["offer"],
                "offer_ice_candidates": [],
                "answer_ice_candidates": [],
                "answer": None,
            }

        # Simply return success - don't create a peer connection
        return web.Response(status=204)

    async def handle_ice_candidate(self, request: web.Request) -> web.Response:
        data = await request.json()
        room_id = data["roomId"]
        is_offer = data.get("isOffer", True)
        if room_id in self.rooms:
            room = self.rooms[room_id]
            candidates_key = "offer_ice_candidates" if is_offer else "answer_ice_candidates"
            if candidates_key not in room:
                room[candidates_key] = []
            room[candidates_key].append(data["candidate"])
        return web.Response(status=204)

    async def handle_answer(self, request: web.Request) -> web.Response:
        """Handle POST request for answer."""
        data = await request.json()
        room_id = data["roomId"]
        if room_id in self.rooms:
            self.rooms[room_id]["answer"] = data["answer"]
        return web.Response(status=204)

    async def handle_ice_candidates(self, request: web.Request) -> web.Response:
        room_id = request.match_info["room_id"]
        is_offer = request.query.get("isOffer", "false").lower() == "true"
        if room_id in self.rooms:
            room = self.rooms[room_id]
            candidates_key = "answer_ice_candidates" if is_offer else "offer_ice_candidates"
            candidates = room.get(candidates_key, [])
            return web.Response(
                content_type="application/json",
                text=json.dumps({"candidates": candidates}),
            )
        else:
            return web.Response(
                content_type="application/json",
                text=json.dumps({"candidates": []}),
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
    """Runs a local signaling server, instead of using the public one."""
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
        logger.info("Connection established")
        # Start the producer video monitoring
        asyncio.create_task(client.display_video())
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
        logger.info("Connection established")
        # Start the consumer video display
        asyncio.create_task(client.display_video())

    logger.info("Getting ICE candidates")
    await client.get_ice_candidates()

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
