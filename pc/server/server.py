import asyncio

from media_session import MediaSessionReader


class AudioDeckServer:

    def __init__(self):
        self.media_reader = MediaSessionReader()

        self.current_state = None

        self.current_track = None
        self.current_status = None

    async def initialize(self):

        print("Initializing Audio Deck...")

        await self.media_reader.initialize()

        print("Media session initialized.")

    async def update_state(self):

        state = await self.media_reader.get_current_state()

        if state is None:
            return None

        track = (
            state["title"],
            state["artist"],
            state["album"],
        )

        status = state["status"]

        event = None

        # -----------------------------------------
        # New track
        # -----------------------------------------

        if track != self.current_track:

            self.current_track = track

            event = "TRACK_CHANGED"

        # -----------------------------------------
        # Playback state changed
        # -----------------------------------------

        elif status != self.current_status:

            event = "PLAYBACK_CHANGED"

        # -----------------------------------------
        # Update stored state
        # -----------------------------------------

        self.current_state = state
        self.current_status = status

        return event

    def display_state(self, event):

        if self.current_state is None:
            return

        state = self.current_state

        print()
        print("=" * 60)
        print(f"                 {event}")
        print("=" * 60)

        print(f"Player   : {state['player']}")
        print(f"Title    : {state['title']}")
        print(f"Artist   : {state['artist']}")
        print(f"Album    : {state['album']}")
        print(f"Status   : {state['status']}")

        print(
            f"Position : "
            f"{state['position']:.1f}s / "
            f"{state['duration']:.1f}s"
        )

        print("=" * 60)

    async def run(self):

        await self.initialize()

        print()
        print("Audio Deck server is running.")
        print("Monitoring Brave...")
        print("Press Ctrl+C to stop.")

        while True:

            try:

                event = await self.update_state()

                if event is not None:
                    self.display_state(event)

            except Exception as e:

                print(f"[Audio Deck] Error: {e}")

            await asyncio.sleep(1)


async def main():

    server = AudioDeckServer()

    await server.run()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("Audio Deck server stopped.")