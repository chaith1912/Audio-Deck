import asyncio
import base64
import time

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus,
)
from winsdk.windows.storage.streams import DataReader


STATUS_NAMES = {
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING: "PLAYING",
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED: "PAUSED",
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.STOPPED: "STOPPED",
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.CLOSED: "CLOSED",
}


class MediaSessionReader:
    def __init__(self):
        self.manager = None

        # Local position tracking
        self.base_position = 0.0
        self.base_time = None
        self.last_status = None
        self.last_track = None

        # Artwork cache
        self.artwork_cache = None
        self.artwork_track = None

    async def initialize(self):
        self.manager = await (
            GlobalSystemMediaTransportControlsSessionManager.request_async()
        )

    async def get_brave_session(self):
        if self.manager is None:
            await self.initialize()

        sessions = self.manager.get_sessions()

        for session in sessions:
            try:
                source = session.source_app_user_model_id

                if "Brave" in source:
                    return session

            except Exception:
                continue

        return None

    async def get_artwork(self, thumbnail):
        """
        Extract artwork from Windows GSMTC thumbnail
        and return it as a Base64 string.
        """

        if thumbnail is None:
            return None

        try:
            stream = await thumbnail.open_read_async()

            size = int(stream.size)

            if size <= 0:
                stream.close()
                return None

            reader = DataReader(stream)

            loaded = await reader.load_async(size)

            data = bytearray(loaded)

            for i in range(loaded):
                data[i] = reader.read_byte()

            reader.close()
            stream.close()

            return base64.b64encode(data).decode("ascii")

        except Exception as e:
            print(f"[Artwork] Error: {e}")
            return None

    async def get_current_state(self):
        session = await self.get_brave_session()

        if session is None:
            return None

        properties = await session.try_get_media_properties_async()

        playback_info = session.get_playback_info()
        timeline = session.get_timeline_properties()

        title = properties.title or "Unknown"
        artist = properties.artist or "Unknown"
        album = properties.album_title or "Unknown"

        status = STATUS_NAMES.get(
            playback_info.playback_status,
            str(playback_info.playback_status),
        )

        duration = (
            timeline.end_time - timeline.start_time
        ).total_seconds()

        # Raw position reported by Windows.
        raw_position = timeline.position.total_seconds()

        track = (
            title,
            artist,
            album,
        )

        now = time.monotonic()

        # --------------------------------------------------
        # New track
        # --------------------------------------------------

        if track != self.last_track:

            self.last_track = track

            self.base_position = max(
                0.0,
                raw_position,
            )

            self.base_time = now

            # ----------------------------------------------
            # Load artwork only when the track changes
            # ----------------------------------------------

            self.artwork_cache = await self.get_artwork(
                properties.thumbnail
            )

            self.artwork_track = track

            if self.artwork_cache is not None:
                print("[Artwork] New artwork loaded.")
            else:
                print("[Artwork] No artwork available.")

        # --------------------------------------------------
        # Playback state changed
        # --------------------------------------------------

        elif status != self.last_status:

            if status == "PLAYING":

                # Resume from the last known position.
                self.base_time = now

            elif status != "PLAYING":

                # Freeze the position when paused/stopped.
                if self.base_time is not None:

                    self.base_position += (
                        now - self.base_time
                    )

                    self.base_position = min(
                        self.base_position,
                        duration,
                    )

                self.base_time = now

        # --------------------------------------------------
        # Calculate current position
        # --------------------------------------------------

        if status == "PLAYING":

            if self.base_time is None:
                self.base_time = now

            position = (
                self.base_position
                + (now - self.base_time)
            )

        else:

            position = self.base_position

        # --------------------------------------------------
        # Clamp position
        # --------------------------------------------------

        position = max(
            0.0,
            min(position, duration),
        )

        self.last_status = status

        return {
            "player": "Brave",
            "title": title,
            "artist": artist,
            "album": album,
            "status": status,
            "position": position,
            "duration": duration,
            "artwork": self.artwork_cache,
        }
    async def toggle_play_pause(self):
        session = await self.get_brave_session()

        if session is None:
            print("[Control] No Brave media session found.")
            return False
        
        try:
            await session.try_toggle_play_pause_async()
            print("[Control] Play/Pause toggled.")
            return True
        
        except Exception as e:
            print(f"[Control] Play/Pause failed: {e}")
            return False

    async def next_track(self):
        session = await self.get_brave_session()

        if session is None:
            print("[Control] No Brave media session found.")
            return False
        
        try:
            await session.try_skip_next_async()
            print("[Control] Skipped to next track.")
            return True
        
        except Exception as e:
            print(f"[Control] Next track failed: {e}")
            return False

    async def previous_track(self):
        session = await self.get_brave_session()

        if session is None:
            print("[Control] No Brave media session found.")
            return False
        
        try:
            await session.try_skip_previous_async()
            print("[Control] Skipped to previous track.")
            return True
        
        except Exception as e:
            print(f"[Control] Previous track failed: {e}")
            return False

async def test():

    reader = MediaSessionReader()

    while True:

        state = await reader.get_current_state()

        if state is None:

            print("No Brave media session found.")

        else:

            artwork_status = (
                "YES"
                if state["artwork"] is not None
                else "NO"
            )

            print(
                f"{state['status']:8} "
                f"{state['position']:7.2f} / "
                f"{state['duration']:.2f} "
                f"| Artwork: {artwork_status}"
            )

        await asyncio.sleep(1)


if __name__ == "__main__":

    try:
        asyncio.run(test())

    except KeyboardInterrupt:
        print("\nStopped.")

#test
async def test_control():
    reader = MediaSessionReader()

    await reader.initialize()

    print("Audio Deck control test")
    input("Press ENTER for next track...")

    result = await reader.next_track()

    print("Control successful." if result else "Control failed.")


if __name__ == "__main__":
    asyncio.run(test_control())