import asyncio
from pathlib import Path

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
)
from winsdk.windows.storage.streams import DataReader


OUTPUT_FILE = Path("test_artwork.jpg")


async def main():

    manager = (
        await GlobalSystemMediaTransportControlsSessionManager
        .request_async()
    )

    sessions = manager.get_sessions()

    brave_session = None

    for session in sessions:
        try:
            if "Brave" in session.source_app_user_model_id:
                brave_session = session
                break
        except Exception:
            continue

    if brave_session is None:
        print("No Brave media session found.")
        return

    properties = (
        await brave_session.try_get_media_properties_async()
    )

    print("Title :", properties.title)
    print("Artist:", properties.artist)
    print("Album :", properties.album_title)

    thumbnail = properties.thumbnail

    if thumbnail is None:
        print("No artwork available.")
        return

    print("Thumbnail found.")

    stream = await thumbnail.open_read_async()

    print("Stream opened.")
    print("Size:", stream.size)

    # Create a WinRT DataReader for the stream.
    reader = DataReader(stream)

    size = int(stream.size)

    loaded = await reader.load_async(size)

    print("Bytes loaded:", loaded)

    data = bytearray(size)

    for i in range(size):
        data[i] = reader.read_byte()

    OUTPUT_FILE.write_bytes(data)

    reader.close()
    stream.close()

    print()
    print(f"Artwork saved to: {OUTPUT_FILE.resolve()}")
    print(f"Bytes written: {len(data)}")


if __name__ == "__main__":
    asyncio.run(main())