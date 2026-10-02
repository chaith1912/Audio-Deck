import asyncio

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus,
)

STATUS_NAMES = {
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING: "PLAYING",
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.PAUSED: "PAUSED",
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.STOPPED: "STOPPED",
    GlobalSystemMediaTransportControlsSessionPlaybackStatus.CLOSED: "CLOSED",
}

def format_time(seconds):
    """Convert seconds to MM:SS."""

    if seconds is None:
        return "--:--"

    seconds = max(0, int(seconds))

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"

class MediaSessionReader:
    """Reads media information from the active Brave session."""

    def __init__(self):
        self.manager = None

    async def initialize(self):
        """Initialize Windows Media Session manager."""

        self.manager = await (
            GlobalSystemMediaTransportControlsSessionManager
            .request_async()
        )

    async def get_brave_session(self):
        """Find the Brave media session."""

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

    async def get_current_state(self):
        """Return the current Brave playback state."""

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

        position = timeline.position.total_seconds()

        duration = (
            timeline.end_time - timeline.start_time
        ).total_seconds()

        return {
            "player": "Brave",
            "title": title,
            "artist": artist,
            "album": album,
            "status": status,
            "position": position,
            "duration": duration,
        }

async def test():

    reader = MediaSessionReader()

    state = await reader.get_current_state()

    if state is None:
        print("No Brave media session found.")
        return

    print(state)


if __name__ == "__main__":
    asyncio.run(test())