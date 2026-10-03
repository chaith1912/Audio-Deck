from protocol import (
    track_message,
    playback_message,
    position_message,
    state_message,
    welcome_message,
)


state = {
    "player": "Brave",
    "title": "Test Song",
    "artist": "Test Artist",
    "album": "Test Album",
    "status": "PLAYING",
    "position": 10.5,
    "duration": 200.0,
    "artwork": None,
}

print("TRACK")
print(track_message(state))

print("\nPLAYBACK")
print(playback_message(state))

print("\nPOSITION")
print(position_message(state))

print("\nSTATE")
print(state_message(state))

print("\nWELCOME")
print(welcome_message())