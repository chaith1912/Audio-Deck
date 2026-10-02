import asyncio
import json

import websockets

from media_session import MediaSessionReader
from protocol import (
    state_message,
    track_message,
    playback_message,
    position_message,
    welcome_message,
)


HOST = "0.0.0.0"
PORT = 8765


class AudioDeckWebSocketServer:

    def __init__(self):
        self.media_reader = MediaSessionReader()
        self.clients = set()

        self.current_state = None
        self.current_track = None
        self.current_status = None

    async def initialize(self):
        print("Initializing Audio Deck...")

        await self.media_reader.initialize()

        print("Media session initialized.")

    async def register_client(self, websocket):
        self.clients.add(websocket)

        print(
            f"[WebSocket] Client connected: "
            f"{websocket.remote_address}"
        )

        # Send welcome message
        await websocket.send(
            json.dumps(welcome_message())
        )

        # Immediately send current state
        if self.current_state is not None:

            await websocket.send(
                json.dumps(
                    state_message(self.current_state)
                )
            )

    async def unregister_client(self, websocket):

        self.clients.discard(websocket)

        print(
            f"[WebSocket] Client disconnected: "
            f"{websocket.remote_address}"
        )

    async def send_to_all(self, message):

        if not self.clients:
            return

        data = json.dumps(message)

        disconnected = set()

        for client in self.clients:

            try:
                await client.send(data)

            except Exception:
                disconnected.add(client)

        for client in disconnected:
            self.clients.discard(client)

    async def handle_client(self, websocket):

        await self.register_client(websocket)

        try:

            async for message in websocket:

                print(
                    f"[WebSocket] Received: {message}"
                )

        except websockets.exceptions.ConnectionClosed:
            pass

        finally:

            await self.unregister_client(websocket)

    async def update_media_state(self):

        state = await self.media_reader.get_current_state()

        if state is None:
            return

        track = (
            state["title"],
            state["artist"],
            state["album"],
        )

        status = state["status"]

        # ---------------------------------------
        # First state
        # ---------------------------------------

        if self.current_state is None:

            self.current_state = state
            self.current_track = track
            self.current_status = status

            await self.send_to_all(
                state_message(state)
            )

            return

        # ---------------------------------------
        # Track changed
        # ---------------------------------------

        if track != self.current_track:

            self.current_track = track

            await self.send_to_all(
                track_message(state)
            )

        # ---------------------------------------
        # Playback changed
        # ---------------------------------------

        if status != self.current_status:

            self.current_status = status

            await self.send_to_all(
                playback_message(state)
            )

        # ---------------------------------------
        # Update current state
        # ---------------------------------------

        self.current_state = state

    async def media_monitor(self):

        while True:

            try:

                await self.update_media_state()

            except Exception as e:

                print(
                    f"[Media] Error: {e}"
                )

            await asyncio.sleep(1)

    async def start(self):

        await self.initialize()

        print()
        print("=" * 60)
        print("             AUDIO DECK SERVER")
        print("=" * 60)
        print()
        print(f"WebSocket: ws://0.0.0.0:{PORT}")
        print("Monitoring Brave...")
        print("Waiting for clients...")
        print()
        print("Press Ctrl+C to stop.")
        print()

        async with websockets.serve(
            self.handle_client,
            HOST,
            PORT,
        ):

            await self.media_monitor()


async def main():

    server = AudioDeckWebSocketServer()

    await server.start()


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("Audio Deck server stopped.")