"""Combined code for the WebRTC Flask app with embedded client and HTML."""

import asyncio
import os
import threading
import uuid
from pathlib import Path
from types import TracebackType
from typing import Optional, Type

import aiohttp
import cv2
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaStreamTrack
from av import VideoFrame
from flask import Flask, Response, jsonify, render_template_string, request
from flask_cors import CORS

client_thread = None  # Move this to the module level


def create_app() -> Flask:
    app = Flask(__name__)

    CORS(app)

    # In-memory storage for offers, answers and ICE candidates
    connections = {}

    @app.route("/offer", methods=["POST"])
    def handle_offer() -> Response:
        """Handle incoming WebRTC offers."""
        data = request.get_json()
        room_id = data.get("roomId")
        offer = data.get("offer")

        if not room_id or not offer:
            return jsonify({"error": "Missing roomId or offer"}), 400

        if room_id not in connections:
            connections[room_id] = {}

        connections[room_id].update(
            {
                "offer": offer,
                "answer": None,
                "offerCandidates": [],
                "answerCandidates": [],
            }
        )

        return jsonify({"success": True})

    @app.route("/answer", methods=["POST"])
    def handle_answer() -> Response:
        """Handle incoming WebRTC answers."""
        data = request.get_json()
        room_id = data.get("roomId")
        answer = data.get("answer")

        if not room_id or not answer:
            return jsonify({"error": "Missing roomId or answer"}), 400

        if room_id not in connections:
            return jsonify({"error": "Room not found"}), 404

        connections[room_id]["answer"] = answer
        return jsonify({"success": True})

    @app.route("/offer/<room_id>", methods=["GET"])
    def get_offer(room_id: str) -> Response:
        """Retrieve the offer for a specific room."""
        if room_id not in connections:
            return jsonify({"error": "Room not found"}), 404

        return jsonify({"offer": connections[room_id]["offer"]})

    @app.route("/answer/<room_id>", methods=["GET"])
    def get_answer(room_id: str) -> Response:
        """Retrieve the answer for a specific room."""
        if room_id not in connections:
            return jsonify({"error": "Room not found"}), 404

        return jsonify({"answer": connections[room_id]["answer"]})

    @app.route("/ice-candidate", methods=["POST"])
    def handle_ice_candidate() -> Response:
        """Handle ICE candidates from both peers."""
        data = request.get_json()
        room_id = data.get("roomId")
        candidate = data.get("candidate")
        is_offer = data.get("isOffer", True)

        if not room_id or not candidate:
            return jsonify({"error": "Missing roomId or candidate"}), 400

        if room_id not in connections:
            return jsonify({"error": "Room not found"}), 404

        if is_offer:
            connections[room_id]["offerCandidates"].append(candidate)
        else:
            connections[room_id]["answerCandidates"].append(candidate)

        return jsonify({"success": True})

    @app.route("/ice-candidates/<room_id>", methods=["GET"])
    def get_ice_candidates(room_id: str) -> Response:
        """Retrieve ICE candidates for a specific room."""
        if room_id not in connections:
            return jsonify({"error": "Room not found"}), 404

        is_offer = request.args.get("isOffer", "true").lower() == "true"
        candidates = connections[room_id]["offerCandidates"] if is_offer else connections[room_id]["answerCandidates"]

        return jsonify({"candidates": candidates})

    @app.route("/clear/<room_id>", methods=["POST"])
    def clear_room(room_id: str) -> Response:
        """Clear all stored data for a specific room."""
        if room_id in connections:
            del connections[room_id]
        return jsonify({"success": True})

    @app.route("/")
    def index() -> str:
        """Serve the HTML page."""
        with open(Path(__file__).parent / "static" / "index.html", "r") as file:
            html_content = file.read()
        return render_template_string(html_content)

    class VideoTransformTrack(MediaStreamTrack):
        """Video stream transform track for SBS format."""

        kind = "video"

        def __init__(self, track: MediaStreamTrack) -> None:
            super().__init__()
            self.track = track

        async def recv(self) -> VideoFrame:
            frame = await self.track.recv()
            img = frame.to_ndarray(format="bgr24")

            # Convert to grayscale
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Convert back to BGR format (required for VideoFrame)
            gray_img_bgr = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)

            # Convert back to VideoFrame
            new_frame = VideoFrame.from_ndarray(gray_img_bgr, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base

            return new_frame

    class WebRTCClient:
        def __init__(self, server_url: str = "http://localhost:8080") -> None:
            """Initialize WebRTC client.

            Args:
                server_url: URL of the signaling server
            """
            self.server_url = server_url
            self.peer_connection: Optional[RTCPeerConnection] = None
            self.room_id = str(uuid.uuid4())
            self.is_disconnected = False
            self.session: Optional[aiohttp.ClientSession] = None

        async def __aenter__(self) -> "WebRTCClient":
            """Initialize client session."""
            self.session = aiohttp.ClientSession()
            return self

        async def __aexit__(
            self,
            _exc_type: Optional[Type[BaseException]],
            _exc_val: Optional[BaseException],
            _exc_tb: Optional[TracebackType],
        ) -> None:
            """Cleanup client session."""
            if self.session:
                await self.session.close()

        async def get_media_stream(self) -> MediaPlayer:
            """Get video/audio stream from webcam."""
            options = {"framerate": "30", "video_size": "640x480"}
            if hasattr(MediaPlayer, "_get_default_video_device"):
                # Windows
                player = MediaPlayer(
                    MediaPlayer._get_default_video_device(),
                    format="dshow",
                    options=options,
                )
            else:
                # Linux/Mac
                try:
                    player = MediaPlayer("default:none", format="avfoundation", options=options)
                except Exception:
                    player = MediaPlayer("0", format="avfoundation", options=options)
            return player

        async def create_peer_connection(self) -> RTCPeerConnection:
            """Create and configure peer connection."""
            self.peer_connection = RTCPeerConnection()

            @self.peer_connection.on("connectionstatechange")
            async def on_connection_state_change() -> None:
                print(f"Connection state changed to {self.peer_connection.connectionState}")
                if self.peer_connection.connectionState in [
                    "closed",
                    "failed",
                    "disconnected",
                ]:
                    await self.handle_disconnection()

            @self.peer_connection.on("icecandidate")
            async def on_ice_candidate(candidate: Optional[RTCIceCandidate]) -> None:
                if candidate:
                    await self.send_ice_candidate(candidate, is_offer=True)

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
            offer = await self.peer_connection.createOffer()
            await self.peer_connection.setLocalDescription(offer)

            await self.session.post(
                f"{self.server_url}/offer",
                json={
                    "roomId": self.room_id,
                    "offer": {"sdp": offer.sdp, "type": offer.type},
                },
            )

        async def send_ice_candidate(self, candidate: RTCIceCandidate, is_offer: bool) -> None:
            """Send ICE candidate to the signaling server."""
            await self.session.post(
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
            while True:
                async with self.session.get(f"{self.server_url}/answer/{self.room_id}") as response:
                    data = await response.json()
                    if data.get("answer"):
                        answer = RTCSessionDescription(sdp=data["answer"]["sdp"], type=data["answer"]["type"])
                        await self.peer_connection.setRemoteDescription(answer)
                        break
                await asyncio.sleep(1)

        async def get_ice_candidates(self) -> None:
            """Get ICE candidates from the server."""
            async with self.session.get(
                f"{self.server_url}/ice-candidates/{self.room_id}",
                params={"isOffer": "false"},
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

        async def handle_disconnection(self) -> None:
            """Handle peer disconnection."""
            print("Peer disconnected. Closing connection and preparing for a new room.")
            if self.peer_connection:
                await self.peer_connection.close()
            await self.session.post(f"{self.server_url}/clear/{self.room_id}")
            self.is_disconnected = True

    async def run_client() -> None:
        """Run the WebRTC client."""
        while True:
            async with WebRTCClient() as client:
                await client.create_peer_connection()
                await client.create_offer()
                print(f"Room ID: {client.room_id}")
                print("Waiting for peer to connect...")

                await client.wait_for_answer()
                await client.get_ice_candidates()

                # Wait until the peer connection is disconnected
                while not client.is_disconnected:
                    await asyncio.sleep(1)

                print("Creating a new room...")

    def start_client() -> None:
        """Start the client code in a new thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_client())

    def init_client() -> None:
        """Initialize the client when the Flask app starts."""
        global client_thread  # Use global instead of nonlocal
        if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            if client_thread is None or not client_thread.is_alive():
                client_thread = threading.Thread(target=start_client)
                client_thread.daemon = True
                client_thread.start()

    with app.app_context():
        init_client()

    return app


def main() -> None:
    app = create_app()
    app.run(debug=False, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
