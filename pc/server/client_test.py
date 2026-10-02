import asyncio
import websockets


PC_IP = "127.0.0.1"
PORT = 8765


async def main():

    uri = f"ws://{PC_IP}:{PORT}"

    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:

        print("Connected!")
        print("Waiting for Audio Deck messages...")
        print()

        async for message in websocket:

            print(f"RECEIVED: {message}")


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print("\nClient stopped.")