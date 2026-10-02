import json


PROTOCOL_VERSION = "1.0"


def track_message(state):
    return {
        "type": "track",
        "player": state["player"],
        "title": state["title"],
        "artist": state["artist"],
        "album": state["album"],
        "duration": state["duration"],
    }


def playback_message(state):
    return {
        "type": "playback",
        "status": state["status"],
    }


def position_message(state):
    return {
        "type": "position",
        "position": state["position"],
        "duration": state["duration"],
    }


def state_message(state):
    return {
        "type": "state",
        "player": state["player"],
        "title": state["title"],
        "artist": state["artist"],
        "album": state["album"],
        "status": state["status"],
        "position": state["position"],
        "duration": state["duration"],
    }


def welcome_message():
    return {
        "type": "welcome",
        "server": "AudioDeck",
        "version": PROTOCOL_VERSION,
    }


def parse_message(message):
    return json.loads(message)