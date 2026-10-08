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
        "artwork": state["artwork"],
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


def volume_message(state):
    return {
        "type": "volume",
        "volume": state["volume"],
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
        "artwork": state["artwork"],
        "volume": state.get("volume", 1.0),
    }

def welcome_message():
    return {
        "type": "welcome",
        "server": "AudioDeck",
        "version": PROTOCOL_VERSION,
    }


def parse_message(message):
    return json.loads(message)

def command_message(action):
    return {
        "type": "command",
        "action": action,
    }

def parse_command(message):
    data = json.loads(message)

    if data.get("type") != "command":
        return None

    return {
        "action": data.get("action"),
        "position": data.get("position"),
        "level": data.get("level", data.get("volume")),
    }