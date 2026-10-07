import asyncio
import json

import websockets

from media_session import MediaSessionReader
from protocol import (
    welcome_message,
    state_message,
    track_message,
    playback_message,
    position_message,
    parse_command,
)

HOST = "0.0.0.0"
PORT = 8765

POSITION_INTERVAL = 1.0


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

        # Tell the client which protocol we're using.
        await websocket.send(
            json.dumps(welcome_message())
        )

        # Immediately send the current complete state.
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
        """
        Handle an Android WebSocket client.

        Supported commands:

        {
            "type": "command",
            "action": "play_pause"
        }

        {
            "type": "command",
            "action": "next"
        }

        {
            "type": "command",
            "action": "previous"
        }
        """

        await self.register_client(websocket)

        try:
            async for message in websocket:

                print(
                    f"[WebSocket] Received: {message}"
                )

                try:
                    command = parse_command(message)

                except Exception as e:
                    print(
                        f"[WebSocket] Invalid command: {e}"
                    )
                    continue

                if command is None:
                    continue

                command_type = command.get("action")

                print(
                    f"[WebSocket] Command: "
                    f"{command_type}"
                )

                # -----------------------------------
                # Play / Pause
                # -----------------------------------

                if command_type == "play_pause":

                    result = (
                        await self.media_reader
                        .toggle_play_pause()
                    )

                    if result:
                        print(
                            "[Control] "
                            "Play/Pause successful."
                        )

                    else:
                        print(
                            "[Control] "
                            "Play/Pause failed."
                        )

                # -----------------------------------
                # Next Track
                # -----------------------------------

                elif command_type == "next":

                    result = (
                        await self.media_reader
                        .next_track()
                    )

                    if result:
                        print(
                            "[Control] "
                            "Next track successful."
                        )

                    else:
                        print(
                            "[Control] "
                            "Next track failed."
                        )

                # -----------------------------------
                # Previous Track
                # -----------------------------------

                elif command_type == "previous":

                    result = (
                        await self.media_reader
                        .previous_track()
                    )

                    if result:
                        print(
                            "[Control] "
                            "Previous track successful."
                        )

                    else:
                        print(
                            "[Control] "
                            "Previous track failed."
                        )

                elif command_type == "seek":

                    position = command.get("position")

                    if position is None:
                        print("[Command] Seek position missing.")
                        continue

                    success = await self.media_reader.seek(float(position))

                    if success:
                        print(f"[Command] Seek executed: {position}s")
                        state = await self.media_reader.get_current_state()
                        if state is not None:
                            self.current_state = state
                            await self.send_to_all(position_message(state))
                    else:
                        print("[Command] Seek failed.")

                # -----------------------------------
                # Unknown Command
                # -----------------------------------

                else:

                    print(
                        f"[Control] Unknown command: "
                        f"{command_type}"
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
        # First state received.
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
        # Track changed.
        # ---------------------------------------

        if track != self.current_track:

            self.current_track = track

            await self.send_to_all(
                track_message(state)
            )

        # ---------------------------------------
        # Playback state changed.
        # ---------------------------------------

        if status != self.current_status:

            self.current_status = status

            await self.send_to_all(
                playback_message(state)
            )

        # Always keep the latest state internally.
        self.current_state = state

    async def media_monitor(self):
        while True:

            try:
                await self.update_media_state()

            except Exception as e:
                print(
                    f"[Media] Error: {e}"
                )

            await asyncio.sleep(
                POSITION_INTERVAL
            )

    async def position_monitor(self):
        """
        Sends periodic position synchronization.

        This is intentionally separate from
        track/playback events so the Android client
        can smoothly interpolate between
        synchronization points.
        """

        while True:

            try:

                if self.current_state is not None:

                    state = (
                        await self.media_reader
                        .get_current_state()
                    )

                    if state is not None:

                        self.current_state = state

                        await self.send_to_all(
                            position_message(state)
                        )

            except Exception as e:

                print(
                    f"[Position] Error: {e}"
                )

            await asyncio.sleep(
                POSITION_INTERVAL
            )

    async def start(self):

        await self.initialize()

        print()
        print("=" * 60)
        print("             AUDIO DECK SERVER")
        print("=" * 60)
        print()

        print(
            f"WebSocket: ws://0.0.0.0:{PORT}"
        )

        print(
            "Monitoring Brave..."
        )

        print(
            "Position synchronization enabled."
        )

        print(
            "Remote controls enabled:"
        )

        print(
            "  - Play/Pause"
        )

        print(
            "  - Next Track"
        )

        print(
            "  - Previous Track"
        )

        print(
            "Waiting for clients..."
        )

        print()

        print(
            "Press Ctrl+C to stop."
        )

        print()

        async with websockets.serve(
            self.handle_client,
            HOST,
            PORT,
        ):

            await asyncio.gather(
                self.media_monitor(),
                self.position_monitor(),
            )


async def main():

    server = AudioDeckWebSocketServer()

    await server.start()


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print(
            "Audio Deck server stopped."
        )