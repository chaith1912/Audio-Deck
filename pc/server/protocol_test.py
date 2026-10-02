from protocol import (
    track_message,
    playback_message,
    position_message,
    state_message,
    welcome_message,
)


state = {
    "player": "Brave",
    "title": "Kaamaatchi",
    "artist": "Sunder Chandran",
    "album": "Kaamaatchi",
    "status": "PLAYING",
    "position": 37.2,
    "duration": 172.0,
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