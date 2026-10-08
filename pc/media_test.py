import asyncio
from datetime import timedelta

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
    """Convert seconds into MM:SS."""
    if seconds is None:
        return "--:--"

    seconds = max(0, int(seconds))

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


async def get_brave_session(manager):
    """Find the active Brave media session."""

    sessions = manager.get_sessions()

    for session in sessions:
        try:
            source = session.source_app_user_model_id

            if "Brave" in source:
                return session

        except Exception:
            continue

    return None


async def read_session(session):
    """Read metadata, playback state and timeline."""

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
        "title": title,
        "artist": artist,
        "album": album,
        "status": status,
        "position": position,
        "duration": duration,
    }


async def main():

    manager = await (
        GlobalSystemMediaTransportControlsSessionManager
        .request_async()
    )

    print("=" * 60)
    print("             AUDIO DECK - BRAVE MONITOR")
    print("=" * 60)

    print("\nMonitoring Brave...")
    print("Press Ctrl+C to stop.\n")

    previous_track = None
    previous_status = None

    while True:

        try:
            session = await get_brave_session(manager)

            if session is None:

                if previous_status != "NO_SESSION":
                    print("[Audio Deck] Brave media session not found.")

                previous_status = "NO_SESSION"

                await asyncio.sleep(1)
                continue

            data = await read_session(session)

            current_track = (
                data["title"],
                data["artist"],
                data["album"],
            )

            # Detect a new track
            if current_track != previous_track:

                print("\n" + "=" * 60)
                print("                  NOW PLAYING")
                print("=" * 60)

                print(f"Title    : {data['title']}")
                print(f"Artist   : {data['artist']}")
                print(f"Album    : {data['album']}")

                print(
                    f"Position : "
                    f"{format_time(data['position'])} / "
                    f"{format_time(data['duration'])}"
                )

                print(f"Status   : {data['status']}")

                print("=" * 60)

                previous_track = current_track
                previous_status = data["status"]

            # Detect play/pause/stop changes
            elif data["status"] != previous_status:

                print(
                    f"[Audio Deck] "
                    f"{data['status']} — "
                    f"{format_time(data['position'])} / "
                    f"{format_time(data['duration'])}"
                )

                previous_status = data["status"]

        except Exception as e:

            print(f"[Audio Deck] Error: {e}")

        await asyncio.sleep(1)

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n\nAudio Deck stopped.")