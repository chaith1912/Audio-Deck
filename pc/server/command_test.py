import asyncio
import json

import websockets


SERVER = "ws://127.0.0.1:8765"


async def main():

    print("Connecting to Audio Deck server...")

    async with websockets.connect(SERVER) as websocket:

        print("Connected.")

        # Receive welcome message
        welcome = await websocket.recv()

        print()
        print("Welcome:")
        print(welcome)

        # Send play/pause command
        command = {
            "type": "command",
            "action": "play_pause",
        }

        print()
        print("Sending command:")
        print(json.dumps(command))

        await websocket.send(
            json.dumps(command)
        )

        # Keep connection alive briefly
        await asyncio.sleep(1)

        print()
        print("Command sent successfully.")


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nStopped.")