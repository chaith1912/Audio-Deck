# AUDIO DECK — MASTER IMPLEMENTATION PLAN

> **Author**: Senior Software Architect (Claude Opus) — Analysis completed 2026-10-05
> **Executor**: Gemini inside Antigravity
> **Branch**: `antigravity-dev`
> **Status**: READY FOR EXECUTION

---

## TABLE OF CONTENTS

1. [Repository Analysis](#1-repository-analysis)
2. [Architecture Map](#2-architecture-map)
3. [Existing Code Inventory](#3-existing-code-inventory)
4. [Gap Analysis](#4-gap-analysis)
5. [Phase 7.6.5 — Position Synchronization](#phase-765--position-synchronization)
6. [Phase 7.7 — Volume Control](#phase-77--volume-control)
7. [Phase 7.8 — Control Synchronization](#phase-78--control-synchronization)
8. [Phase 7.9 — Control Error Handling](#phase-79--control-error-handling)
9. [Phase 8 — Functional UI](#phase-8--functional-ui)
10. [Phase 9 — Reliability](#phase-9--reliability)
11. [Phase 10 — Performance](#phase-10--performance)
12. [Phase 11 — Packaging + E2E Testing](#phase-11--packaging--e2e-testing)
13. [Execution Model](#13-execution-model)
14. [Stop Conditions](#14-stop-conditions)

---

## 1. REPOSITORY ANALYSIS

### Current State

The Audio Deck project is a **PC-to-Android audio display** that reads media state from **Brave Browser** via the **Windows Global System Media Transport Controls** (GSMTC) and sends that state to an Android phone over WebSocket.

### What Works Today

| Feature | PC (Python) | Android (Kotlin) | Status |
|---|---|---|---|
| Media session detection | ✅ `media_session.py` | — | Working |
| Track metadata (title/artist/album) | ✅ | ✅ Displayed | Working |
| Play/Pause state detection | ✅ | ✅ Parsed | Working |
| Artwork extraction + Base64 transport | ✅ | ✅ Decoded + displayed | Working |
| Position tracking (local interpolation) | ✅ `MediaSessionReader` | ❌ No interpolation | Partial |
| Position broadcast (1s interval) | ✅ `position_monitor()` | ⚠️ Received but not used for slider sync | Partial |
| Play/Pause command (Android → PC) | ✅ `toggle_play_pause()` | ✅ `sendPlayPause()` | Working |
| Next/Previous commands | ✅ | ✅ | Working |
| Seek command | ✅ `seek()` | ✅ `sendSeek()` | Working |
| Volume control | ❌ | ❌ | Missing |
| Command acknowledgment / error feedback | ❌ | ❌ | Missing |
| Connection reliability / auto-reconnect | ❌ | ❌ | Missing |
| Proper seek-bar synchronization | ❌ | ❌ | Missing |

### What Needs Fixing

1. **Position sync is one-way and the slider doesn't track it** — The Android slider (`seekPosition`) is a local `remember` state that is never updated from incoming `position` messages.
2. **`AudioDeckMessageParser` ignores `playback` and `position` message types** — It only handles `state` and `track`, so playback changes and position updates received from the server are silently discarded.
3. **No volume control** anywhere in the stack.
4. **No command acknowledgment** — Commands are fire-and-forget; the Android client has no idea if a command succeeded or failed.
5. **No auto-reconnect** — If the WebSocket drops, the Android client stays disconnected forever.
6. **Hardcoded server IP** — `"10.138.245.32"` is hardcoded in `MainActivity.kt`.

---

## 2. ARCHITECTURE MAP

```text
┌─────────────────────────────────────────────────────────────────┐
│                        WINDOWS PC                               │
│                                                                 │
│  Brave Browser                                                  │
│       │                                                         │
│       ▼                                                         │
│  Windows GSMTC (Media Session API)                              │
│       │                                                         │
│       ▼                                                         │
│  MediaSessionReader  (media_session.py)                         │
│   • get_current_state() → dict                                  │
│   • toggle_play_pause() / next / previous / seek                │
│   • get_artwork() → Base64                                      │
│   • Local position interpolation                                │
│       │                                                         │
│       ▼                                                         │
│  AudioDeckWebSocketServer  (websocket_server.py)                │
│   • WebSocket server on 0.0.0.0:8765                            │
│   • media_monitor() — detects track/playback changes            │
│   • position_monitor() — broadcasts position every 1s           │
│   • handle_client() — receives commands from Android            │
│   • Protocol messages defined in protocol.py                    │
│       │                                                         │
│       │  WebSocket (JSON)                                       │
│       ▼                                                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
└─────────────────────────────────────────────────────────────────┘
                            │
                       WiFi / LAN
                            │
┌─────────────────────────────────────────────────────────────────┐
│                      ANDROID PHONE                              │
│                                                                 │
│  AudioDeckWebSocket  (AudioDeckWebSocket.kt)                    │
│   • OkHttp WebSocket client                                     │
│   • connect() / disconnect() / sendCommand()                    │
│       │                                                         │
│       ▼                                                         │
│  AudioDeckMessageParser  (AudioDeckMessageParser.kt)            │
│   • Parses: "state", "track"                                    │
│   • MISSING: "playback", "position", "welcome"                  │
│       │                                                         │
│       ▼                                                         │
│  AudioDeckStateHolder  (MainActivity.kt)                        │
│   • Compose mutableStateOf(AudioDeckState)                      │
│       │                                                         │
│       ▼                                                         │
│  AudioDeckScreen  (MainActivity.kt)                             │
│   • Title, Artist, Artwork, Slider, Buttons                     │
│   • Slider NOT synced to server position                        │
│                                                                 │
│  AudioDeckCommandHolder  (MainActivity.kt)                      │
│   • sendPlayPause / sendNext / sendPrevious / sendSeek          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. EXISTING CODE INVENTORY

### PC Side (`pc/server/`)

| File | Purpose | Lines | Key Classes/Functions |
|---|---|---|---|
| `protocol.py` | Protocol message builders | ~70 | `track_message()`, `playback_message()`, `position_message()`, `state_message()`, `welcome_message()`, `command_message()`, `parse_command()` |
| `media_session.py` | Windows GSMTC reader | ~250 | `MediaSessionReader` — `initialize()`, `get_brave_session()`, `get_artwork()`, `get_current_state()`, `toggle_play_pause()`, `next_track()`, `previous_track()`, `seek()` |
| `server.py` | Standalone server (no WebSocket) | ~110 | `AudioDeckServer` — `update_state()`, `display_state()`, `run()` |
| `websocket_server.py` | Main WebSocket server | ~300 | `AudioDeckWebSocketServer` — `register_client()`, `unregister_client()`, `send_to_all()`, `handle_client()`, `update_media_state()`, `media_monitor()`, `position_monitor()`, `start()` |
| `protocol_test.py` | Protocol message test | ~35 | Script |
| `client_test.py` | WebSocket client test | ~30 | Script |
| `command_test.py` | Command send test | ~40 | Script |
| `artwork_test.py` | Artwork extraction test | ~65 | Script |

### Android Side (`android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/`)

| File | Purpose | Key Elements |
|---|---|---|
| `AudioDeckState.kt` | Data model | `data class AudioDeckState(connected, player, title, artist, album, status, position, duration, artwork)` |
| `AudioDeckMessageParser.kt` | JSON parser | Handles `"state"` and `"track"` types only |
| `AudioDeckWebSocket.kt` | OkHttp WebSocket client | `connect()`, `disconnect()`, `sendCommand()` |
| `MainActivity.kt` | Activity + UI | `AudioDeckStateHolder`, `AudioDeckCommandHolder`, `AudioDeckScreen()` composable, `decodeArtwork()` |

### Protocol Messages (Current)

**Server → Client:**
| Type | Fields | When Sent |
|---|---|---|
| `welcome` | `server`, `version` | On client connect |
| `state` | `player`, `title`, `artist`, `album`, `status`, `position`, `duration`, `artwork` | First state + on new client |
| `track` | `player`, `title`, `artist`, `album`, `duration`, `artwork` | Track changes |
| `playback` | `status` | Play/pause state changes |
| `position` | `position`, `duration` | Every 1s |

**Client → Server:**
| Type | Fields | When Sent |
|---|---|---|
| `command` | `action` = `"play_pause"` / `"next"` / `"previous"` | Button press |
| `command` | `action` = `"seek"`, `position` = float | Slider release |

---

## 4. GAP ANALYSIS

> [!IMPORTANT]
> These are the gaps that the implementation phases will close, in order.

| Gap | Phase |
|---|---|
| Android slider doesn't track position messages | **7.6.5** |
| `AudioDeckMessageParser` ignores `playback` and `position` types | **7.6.5** |
| No volume control (PC read + set, protocol, Android UI) | **7.7** |
| No command acknowledgment from server to client | **7.8** |
| Slider doesn't distinguish "user dragging" from "server update" | **7.8** |
| No error response when a command fails | **7.9** |
| No error UI on Android | **7.9** |
| UI is bare-bones dev-stage (no proper layout, no formatting) | **8** |
| No auto-reconnect on WebSocket drop | **9** |
| Hardcoded server IP | **9** |
| No heartbeat/ping-pong | **9** |
| Artwork decoded on every recomposition (partial — `remember` key exists but not fully optimized) | **10** |
| No debounce on seek commands | **10** |
| Position updates sent even when paused (wasteful) | **10** |
| No build scripts / packaging / end-to-end test suite | **11** |

---

## PHASE 7.6.5 — Position Synchronization

### Objective

Make the Android seek bar (Slider) reflect the actual playback position reported by the PC server, so the user sees a moving progress bar that tracks the current song position in real time.

### Current Code to Inspect

| File | What to look at |
|---|---|
| [protocol.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/protocol.py) | `position_message()` — sends `position` and `duration` |
| [websocket_server.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/websocket_server.py) | `position_monitor()` — broadcasts position every 1s |
| [AudioDeckMessageParser.kt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/AudioDeckMessageParser.kt) | Only handles `"state"` and `"track"` — ignores `"playback"` and `"position"` |
| [AudioDeckState.kt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/AudioDeckState.kt) | Data class with `position` and `duration` fields |
| [MainActivity.kt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/MainActivity.kt) | `AudioDeckScreen()` — `seekPosition` is local state, never updated from server |

### Files to Modify

1. `android/.../AudioDeckMessageParser.kt`
2. `android/.../MainActivity.kt` (specifically `AudioDeckStateHolder` and `AudioDeckScreen`)

### Files to Create

None.

### Functions/Classes Involved

| Component | Change |
|---|---|
| `AudioDeckMessageParser.parse()` | Add handling for `"playback"` and `"position"` message types |
| `AudioDeckStateHolder.update()` | Ensure partial updates (playback-only, position-only) merge into existing state rather than replacing it |
| `AudioDeckStateHolder` | Add new method `updatePosition(position: Double, duration: Double)` and `updatePlayback(status: String)` |
| `AudioDeckScreen()` | Sync `seekPosition` from `state.position` when user is NOT dragging the slider |

### Data/State Flow

```text
PC position_monitor()
    → sends: {"type":"position","position":42.5,"duration":210.0}
    → every 1 second

Android AudioDeckWebSocket.onMessage()
    → AudioDeckMessageParser.parse()
        → NOW handles "position" type
        → Calls AudioDeckStateHolder.updatePosition(42.5, 210.0)
    → AudioDeckStateHolder.state.position = 42.5
    → AudioDeckScreen() Slider value = state.position (when not dragging)
```

### Protocol Changes

**None.** The server already sends `position` messages. The Android client just doesn't process them.

### Android Changes

1. **`AudioDeckMessageParser.kt`** — Add two new `when` branches:

   ```kotlin
   "playback" -> {
       // Return a partial state update with only status changed
       val currentState = AudioDeckStateHolder.state
       currentState.copy(
           status = json.optString("status", currentState.status)
       )
   }

   "position" -> {
       val currentState = AudioDeckStateHolder.state
       currentState.copy(
           position = json.optDouble("position", currentState.position),
           duration = json.optDouble("duration", currentState.duration)
       )
   }
   ```

2. **`MainActivity.kt` — `AudioDeckScreen()`** — Add an `isSeeking` state to prevent server position updates from fighting user drag:

   ```kotlin
   var isSeeking by remember { mutableStateOf(false) }

   // When not seeking, track server position
   LaunchedEffect(state.position) {
       if (!isSeeking) {
           seekPosition = state.position.toFloat()
       }
   }
   ```

   Update the Slider:
   ```kotlin
   Slider(
       value = seekPosition,
       onValueChange = { value ->
           isSeeking = true
           seekPosition = value
       },
       onValueChangeFinished = {
           AudioDeckCommandHolder.sendSeek(seekPosition.toDouble())
           isSeeking = false
       },
       valueRange = 0f..maxOf(state.duration.toFloat(), 0.001f),
       ...
   )
   ```

### Python/Windows Changes

**None.** The PC side is already correctly implemented for this phase.

### UI Changes

The Slider will now move in sync with actual playback. No visual layout changes.

### Implementation Steps

1. Open `AudioDeckMessageParser.kt`
2. Add `"playback"` case that merges `status` into current state
3. Add `"position"` case that merges `position` and `duration` into current state
4. Open `MainActivity.kt`
5. Add `isSeeking` boolean state to `AudioDeckScreen()`
6. Add `LaunchedEffect(state.position)` to sync slider when not seeking
7. Modify `Slider.onValueChange` to set `isSeeking = true`
8. Modify `Slider.onValueChangeFinished` to set `isSeeking = false` after sending seek
9. Guard `valueRange` against `0f..0f` (when duration is 0)

### Build/Test Procedure

1. Build the Android project: `./gradlew assembleDebug` from `android/AudioDeck/`
2. Verify no compilation errors
3. Start the PC WebSocket server: `python server/websocket_server.py` from `pc/`
4. Play a song in Brave
5. Launch the Android app — verify:
   - Slider moves to match the current position
   - Slider updates approximately every 1 second
   - Dragging the slider does NOT get interrupted by server updates
   - Releasing the slider sends a seek command
   - After seeking, the slider resumes tracking the server position

### Acceptance Criteria

- [ ] `AudioDeckMessageParser` handles `"playback"`, `"position"`, `"state"`, and `"track"` message types
- [ ] Slider visually tracks playback position in real-time (~1s updates)
- [ ] User can drag the slider without it snapping back during drag
- [ ] After releasing the slider, seek command is sent and slider resumes server tracking
- [ ] Play/pause state changes from the server are reflected in `AudioDeckState.status`
- [ ] Android project compiles without errors

### Failure Conditions

- Slider jumps erratically between user drag position and server position
- `"position"` messages are still being silently discarded
- App crashes when receiving a `"playback"` message
- `valueRange` becomes `0f..0f` causing a crash or divide-by-zero

### Required Git Commit Message

```
feat: implement position synchronization
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- The Android app builds successfully
- Position sync has been manually verified with a live playback session
- Commit has been created on `antigravity-dev`

---

## PHASE 7.7 — Volume Control

### Objective

Add system volume reading and control on the PC side, add volume to the protocol, and add a volume slider to the Android UI.

### Current Code to Inspect

| File | What to look at |
|---|---|
| [media_session.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/media_session.py) | No volume functionality exists |
| [protocol.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/protocol.py) | No volume in any message |
| [websocket_server.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/websocket_server.py) | `handle_client()` — no volume command handling |
| [requirements.txt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/requirements.txt) | `websockets==17.1`, `winsdk==1.0.0b10` |

### Files to Modify

1. `pc/requirements.txt` — add `pycaw` dependency
2. `pc/server/media_session.py` — add volume read/set methods
3. `pc/server/protocol.py` — add volume message + volume command
4. `pc/server/websocket_server.py` — broadcast volume + handle volume command
5. `android/.../AudioDeckState.kt` — add `volume` field
6. `android/.../AudioDeckMessageParser.kt` — handle `"volume"` message type
7. `android/.../MainActivity.kt` — add volume slider to UI + volume command sender

### Files to Create

None. (Optionally a `pc/server/volume_test.py` for manual testing.)

### Functions/Classes Involved

**PC Side:**
| Component | Change |
|---|---|
| `MediaSessionReader` | Add `get_volume() -> float` (0.0–1.0) and `set_volume(level: float) -> bool` using `pycaw` / Windows Core Audio API |
| `protocol.py` | Add `volume_message(state)` → `{"type": "volume", "volume": 0.75}` |
| `protocol.py` | Update `state_message(state)` to include `"volume"` field |
| `protocol.py` | Update `parse_command()` to handle `"volume"` action with `"level"` field |
| `AudioDeckWebSocketServer` | Add volume to `update_media_state()` — detect volume changes |
| `AudioDeckWebSocketServer.handle_client()` | Add `"volume"` command handling |

**Android Side:**
| Component | Change |
|---|---|
| `AudioDeckState` | Add `val volume: Double = 1.0` |
| `AudioDeckMessageParser.parse()` | Handle `"volume"` type → merge volume into state |
| `AudioDeckStateHolder` | Add `updateVolume(volume: Double)` |
| `AudioDeckCommandHolder` | Add `sendVolume(level: Double)` |
| `AudioDeckScreen()` | Add volume Slider |

### Data/State Flow

```text
PC Volume Read:
    pycaw / IAudioEndpointVolume → get_volume() → float (0.0–1.0)
    → included in state_message on connect
    → volume_message broadcast when volume changes

PC Volume Set:
    Android sends: {"type":"command","action":"volume","level":0.5}
    → parse_command() extracts action="volume", level=0.5
    → MediaSessionReader.set_volume(0.5)
    → IAudioEndpointVolume.SetMasterVolumeLevelScalar(0.5)
```

### Protocol Changes

**New message: Server → Client:**
```json
{"type": "volume", "volume": 0.75}
```

**Updated message: Server → Client (state):**
```json
{"type": "state", ..., "volume": 0.75}
```

**New command: Client → Server:**
```json
{"type": "command", "action": "volume", "level": 0.5}
```

### Android Changes

1. Add `volume` field to `AudioDeckState`
2. Parse `"volume"` messages in `AudioDeckMessageParser`
3. Add volume slider to `AudioDeckScreen()` with `isSeeking` pattern (same as position)
4. Add `sendVolume()` to `AudioDeckCommandHolder`

### Python/Windows Changes

1. **Add `pycaw` to `requirements.txt`** — `pycaw` provides access to Windows Core Audio API
2. **`media_session.py`** — Add volume methods using `pycaw`:
   ```python
   from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
   from comtypes import CLSCTX_ALL

   def get_volume(self):
       devices = AudioUtilities.GetSpeakers()
       interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
       volume = interface.QueryInterface(IAudioEndpointVolume)
       return volume.GetMasterVolumeLevelScalar()

   def set_volume(self, level):
       # level: 0.0 to 1.0
       devices = AudioUtilities.GetSpeakers()
       interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
       volume = interface.QueryInterface(IAudioEndpointVolume)
       volume.SetMasterVolumeLevelScalar(level, None)
   ```
3. **`protocol.py`** — Add `volume_message()`, update `state_message()`, update `parse_command()`
4. **`websocket_server.py`** — Add volume tracking to `update_media_state()`, handle `"volume"` command in `handle_client()`

### UI Changes

A volume slider beneath the seek bar. Horizontal slider, 0%–100% range.

### Implementation Steps

1. Add `pycaw` to `requirements.txt`
2. Install: `pip install -r requirements.txt`
3. Add `get_volume()` and `set_volume()` to `MediaSessionReader`
4. Add `volume_message()` to `protocol.py`
5. Update `state_message()` to include volume
6. Update `parse_command()` to extract `level` for volume commands
7. Add volume change detection to `update_media_state()` in `websocket_server.py`
8. Add `"volume"` command handler to `handle_client()`
9. Include volume in `get_current_state()` return dict
10. Add `volume` field to `AudioDeckState.kt`
11. Handle `"volume"` type in `AudioDeckMessageParser.kt`
12. Add volume slider and `sendVolume()` to Android UI
13. Add `sendVolume()` to `AudioDeckCommandHolder`

### Build/Test Procedure

1. **PC**: Install pycaw → `pip install pycaw`
2. **PC**: Run server → verify volume is printed/logged on startup
3. **PC**: Verify `state_message` includes `"volume"` field
4. **Android**: Build → `./gradlew assembleDebug`
5. **Manual test**:
   - Connect Android to PC server
   - Verify volume slider shows current system volume
   - Drag volume slider on Android → PC system volume changes
   - Change volume on PC (physical keys) → Android slider updates

### Acceptance Criteria

- [ ] `pycaw` is in `requirements.txt` and installs cleanly
- [ ] `get_volume()` returns system volume as float 0.0–1.0
- [ ] `set_volume()` changes system volume
- [ ] `state_message` includes `volume` field
- [ ] Standalone `volume_message` is sent when volume changes
- [ ] Android parses volume messages
- [ ] Volume slider on Android reflects system volume
- [ ] Dragging Android volume slider changes PC volume
- [ ] Existing position sync from Phase 7.6.5 still works
- [ ] Both PC and Android compile/build without errors

### Failure Conditions

- `pycaw` fails to import or initialize (COM/audio device issues)
- Volume slider fights between user drag and server updates (same bug pattern as position)
- Changing volume crashes the PC server
- Volume command is sent but PC doesn't execute it

### Required Git Commit Message

```
feat: add volume controls
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- Volume control verified end-to-end
- Position sync (Phase 7.6.5) confirmed still working
- Commit created on `antigravity-dev`

---

## PHASE 7.8 — Control Synchronization

### Objective

After any command is executed (play/pause, next, previous, seek, volume), the server must send back a **confirmation message** to the requesting client with the updated state, ensuring the Android UI is immediately synchronized without waiting for the next polling cycle.

### Current Code to Inspect

| File | What to look at |
|---|---|
| [websocket_server.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/websocket_server.py) | `handle_client()` — commands are fire-and-forget, no response sent |
| [protocol.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/protocol.py) | No acknowledgment message type exists |

### Files to Modify

1. `pc/server/protocol.py` — add `ack_message()` function
2. `pc/server/websocket_server.py` — send ack after each command
3. `android/.../AudioDeckMessageParser.kt` — handle `"ack"` message type
4. `android/.../MainActivity.kt` — update state immediately on ack

### Files to Create

None.

### Functions/Classes Involved

| Component | Change |
|---|---|
| `protocol.py` | Add `ack_message(action, success, state)` |
| `AudioDeckWebSocketServer.handle_client()` | After each command execution, read fresh state, send `ack_message` back to the requesting client only |
| `AudioDeckMessageParser.parse()` | Add `"ack"` case |
| `AudioDeckStateHolder` | Ack triggers a full state update |

### Data/State Flow

```text
Android sends: {"type":"command","action":"play_pause"}
    ↓
PC handle_client():
    → toggle_play_pause() → success=True
    → read fresh state via get_current_state()
    → send to THIS client only:
      {"type":"ack","action":"play_pause","success":true,
       "status":"PAUSED","position":42.5,"duration":210.0,"volume":0.75}
    ↓
Android AudioDeckMessageParser:
    → "ack" case → merge into state immediately
```

### Protocol Changes

**New message: Server → Client (unicast to requesting client only):**
```json
{
    "type": "ack",
    "action": "play_pause",
    "success": true,
    "status": "PAUSED",
    "position": 42.5,
    "duration": 210.0,
    "volume": 0.75
}
```

### Android Changes

1. `AudioDeckMessageParser` — add `"ack"` handler that extracts fields and merges into `AudioDeckState`
2. On ack receipt, immediately update playback status and position in `AudioDeckStateHolder`

### Python/Windows Changes

1. **`protocol.py`** — Add:
   ```python
   def ack_message(action, success, state=None):
       msg = {
           "type": "ack",
           "action": action,
           "success": success,
       }
       if state is not None:
           msg["status"] = state.get("status")
           msg["position"] = state.get("position")
           msg["duration"] = state.get("duration")
           msg["volume"] = state.get("volume")
       return msg
   ```

2. **`websocket_server.py`** — After each command in `handle_client()`, send ack:
   ```python
   if command_type == "play_pause":
       result = await self.media_reader.toggle_play_pause()
       # Refresh state
       state = await self.media_reader.get_current_state()
       await websocket.send(json.dumps(ack_message("play_pause", result, state)))
   ```
   Apply same pattern for `next`, `previous`, `seek`, `volume`.

### UI Changes

None in this phase. The ack is consumed by the state holder, not rendered as a separate UI element.

### Implementation Steps

1. Add `ack_message()` to `protocol.py`
2. Import `ack_message` in `websocket_server.py`
3. In `handle_client()`, after each command (`play_pause`, `next`, `previous`, `seek`, `volume`), fetch fresh state and send ack to the requesting `websocket` (not `send_to_all`)
4. Add `"ack"` case to `AudioDeckMessageParser.kt`
5. On `"ack"` receipt, call `AudioDeckStateHolder.update()` with merged state

### Build/Test Procedure

1. **PC**: `python server/websocket_server.py` — verify server starts
2. **PC**: Use `command_test.py` (modified to listen for response) — verify ack is received
3. **Android**: Build → `./gradlew assembleDebug`
4. **Manual test**:
   - Press Play/Pause on Android → verify UI immediately reflects the change (not delayed 1s)
   - Press Next → verify track info updates instantly
   - Seek → verify position updates instantly after release
   - Change volume → verify volume slider settles immediately

### Acceptance Criteria

- [ ] Server sends `ack` message after every command
- [ ] Ack is sent only to the requesting client (unicast)
- [ ] Ack contains the post-command state (status, position, duration, volume)
- [ ] Android parses `ack` messages correctly
- [ ] UI reflects command results immediately (< 100ms after ack receipt)
- [ ] All previous phases still work
- [ ] Both PC and Android build without errors

### Failure Conditions

- Ack message is sent to all clients instead of just the requesting one
- Ack state is stale (read before command takes effect)
- `get_current_state()` after command throws an exception
- The parser crashes on `"ack"` type

### Required Git Commit Message

```
feat: synchronize playback controls
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- Ack-based synchronization verified for all command types
- Commit created on `antigravity-dev`

---

## PHASE 7.9 — Control Error Handling

### Objective

When a command fails on the PC side, send a structured error response to the Android client and display a transient error indicator in the UI.

### Current Code to Inspect

| File | What to look at |
|---|---|
| [websocket_server.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/websocket_server.py) | `handle_client()` — prints failures to console but doesn't tell the client |
| [media_session.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/media_session.py) | Control methods return `False` on failure |
| [protocol.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/protocol.py) | `ack_message` from Phase 7.8 already has `success` field |

### Files to Modify

1. `pc/server/protocol.py` — add `error_message()` or extend `ack_message` with `error` field
2. `pc/server/websocket_server.py` — send error ack when command fails
3. `android/.../AudioDeckState.kt` — add `error` field
4. `android/.../AudioDeckMessageParser.kt` — extract error from ack
5. `android/.../MainActivity.kt` — show error Snackbar/Toast

### Files to Create

None.

### Functions/Classes Involved

| Component | Change |
|---|---|
| `ack_message()` | Add optional `error` string field: `"error": "No Brave session found"` |
| `handle_client()` | When `result == False`, include error string in ack |
| `AudioDeckState` | Add `val error: String? = null` |
| `AudioDeckMessageParser` | Extract `error` from ack when `success == false` |
| `AudioDeckScreen()` | Show transient error (auto-dismiss after 3 seconds) |

### Data/State Flow

```text
Android sends: {"type":"command","action":"play_pause"}
    ↓
PC:
    → toggle_play_pause() → returns False
    → send to client:
      {"type":"ack","action":"play_pause","success":false,
       "error":"No Brave media session found"}
    ↓
Android:
    → Parses ack → success=false, error="No Brave media session found"
    → Sets state.error = "No Brave media session found"
    → UI shows error toast/snackbar
    → After 3s, error auto-clears
```

### Protocol Changes

**Updated ack message (failure case):**
```json
{
    "type": "ack",
    "action": "play_pause",
    "success": false,
    "error": "No Brave media session found"
}
```

### Android Changes

1. Add `val error: String? = null` to `AudioDeckState`
2. In `AudioDeckMessageParser`, when ack has `success == false`, extract `"error"` string
3. In `AudioDeckScreen()`, show error with `LaunchedEffect` that auto-clears after 3 seconds
4. Add `clearError()` to `AudioDeckStateHolder`

### Python/Windows Changes

1. Update `ack_message()` to accept optional `error` parameter
2. In `handle_client()`, when a command returns `False`, include descriptive error:
   - `"No Brave media session found"` — when session is None
   - `"Play/Pause failed"` / `"Seek failed"` etc. — when API call fails
3. Wrap command execution in try/except, include exception message as error string

### UI Changes

A transient error indicator — text or snackbar at the bottom of the screen that appears when a command fails and auto-dismisses after 3 seconds.

### Implementation Steps

1. Update `ack_message()` in `protocol.py` to include optional `error` string
2. Update all command handlers in `handle_client()` to send error ack on failure
3. Add `error` field to `AudioDeckState.kt`
4. Update `AudioDeckMessageParser.kt` to extract `error` from ack
5. Add error display to `AudioDeckScreen()` with auto-dismiss
6. Add `clearError()` to `AudioDeckStateHolder`

### Build/Test Procedure

1. **PC**: Start server with no media playing in Brave
2. **Android**: Press Play/Pause → should see error indicator
3. **PC**: Start playing media
4. **Android**: Press Play/Pause → should work normally, no error
5. **Android**: Verify error auto-dismisses after ~3 seconds
6. Verify all previous phases still work

### Acceptance Criteria

- [ ] Failed commands produce an ack with `success: false` and `error` string
- [ ] Android displays the error message transiently
- [ ] Error auto-clears after approximately 3 seconds
- [ ] Successful commands still produce normal acks (no error field or `error: null`)
- [ ] All previous phases still work
- [ ] Both sides build without errors

### Failure Conditions

- Error message doesn't get cleared, persisting forever
- Error display breaks the layout
- Error handling interferes with successful command flow
- PC server crashes when generating error ack

### Required Git Commit Message

```
feat: add control error handling
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- Error handling verified for failure and success paths
- Commit created on `antigravity-dev`

---

## PHASE 8 — Functional UI

### Objective

Transform the bare-bones developer UI into a functional, well-structured media player display. This is NOT the cyberpunk UI — this is a clean, readable, properly laid-out functional interface.

### Current Code to Inspect

| File | What to look at |
|---|---|
| [MainActivity.kt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/MainActivity.kt) | `AudioDeckScreen()` — bare Column with unstyled Text and default Buttons |
| [AndroidManifest.xml](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/AndroidManifest.xml) | `screenOrientation="landscape"` — the app is landscape |

### Files to Modify

1. `android/.../MainActivity.kt` — completely rewrite `AudioDeckScreen()` composable
2. `android/.../ui/theme/Color.kt` — define proper color palette
3. `android/.../ui/theme/Theme.kt` — update theme
4. `android/.../ui/theme/Type.kt` — define typography

### Files to Create

None. Keep everything within existing file structure.

### Functions/Classes Involved

| Component | Change |
|---|---|
| `AudioDeckScreen()` | Full rewrite of layout — landscape media player |
| `Color.kt` | Define dark theme color palette |
| `Theme.kt` | Force dark theme |
| `Type.kt` | Clean readable typography |

### UI Changes

> [!IMPORTANT]
> This is the **functional** UI, not the cyberpunk skin. Keep it clean, modern, and dark-themed.

**Layout (landscape orientation):**

```text
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   ┌─────────┐    Title                                               │
│   │         │    Artist                    [⏮] [⏯] [⏭]             │
│   │ ARTWORK │    Album                                               │
│   │         │                                                        │
│   └─────────┘    ──●──────────────────── 1:42 / 4:30                │
│                  🔊 ──────●──────────── 75%                          │
│                                                                      │
│                  ● CONNECTED                                         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Requirements:**
- Dark background (near-black)
- Artwork displayed prominently (not 50dp — make it ~120-160dp)
- Title: large, bold, white
- Artist: medium, secondary color (light gray)
- Album: small, tertiary color (dim gray)
- Position formatted as `MM:SS / MM:SS`
- Control buttons: icon-style (use Unicode or Material Icons)
- Volume slider: smaller, below the seek bar
- Connection status: small green dot + "CONNECTED" or red dot + "DISCONNECTED"
- Error message: shown as an overlay text at the bottom, semi-transparent background
- Keep screen on while connected (`FLAG_KEEP_SCREEN_ON`)

### Implementation Steps

1. Update `Color.kt` with a dark theme palette
2. Update `Theme.kt` to force dark theme
3. Update `Type.kt` with clean typography
4. Rewrite `AudioDeckScreen()` with proper layout:
   - `Row` layout (landscape): artwork on left, metadata + controls on right
   - Format position as `MM:SS`
   - Style control buttons (use Material Icons via `Icons.Filled`)
   - Add volume slider
   - Add connection status indicator
   - Add error display overlay
5. Add `FLAG_KEEP_SCREEN_ON` in `MainActivity.onCreate()`
6. Add `Icons` dependency if not present (check `build.gradle.kts` for `material-icons-extended`)

### Build/Test Procedure

1. **Android**: `./gradlew assembleDebug` — verify compilation
2. **Install on device** — verify landscape layout
3. **Connect to PC server** — verify:
   - Artwork displays at proper size
   - Title/Artist/Album are readable
   - Position shows as MM:SS / MM:SS
   - Slider tracks position
   - Control buttons work
   - Volume slider works
   - Connection status shows correctly
   - Screen stays on while connected
   - Error messages appear as overlay

### Acceptance Criteria

- [ ] Dark-themed UI renders correctly in landscape
- [ ] Artwork is prominently displayed (~120-160dp)
- [ ] Track metadata is clearly readable with proper hierarchy
- [ ] Position is formatted as MM:SS / MM:SS
- [ ] Control buttons are icon-style (not text buttons)
- [ ] Volume slider is visible and functional
- [ ] Connection status indicator works
- [ ] Error overlay appears and auto-dismisses
- [ ] Screen stays on while connected
- [ ] All functionality from previous phases works through the new UI
- [ ] Android project builds without errors

### Failure Conditions

- Layout overflows on smaller screens
- Controls are too small to tap reliably
- Text is unreadable against the background
- Previous functionality regresses (slider sync, volume, commands, errors)
- Layout doesn't adapt if artwork is unavailable

### Required Git Commit Message

```
feat: implement functional audio deck UI
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- UI has been visually verified on a device
- All previous functionality confirmed working through new UI
- Commit created on `antigravity-dev`

---

## PHASE 9 — Reliability

### Objective

Make the WebSocket connection resilient: auto-reconnect on drop, server discovery, heartbeat, and connection state management.

### Current Code to Inspect

| File | What to look at |
|---|---|
| [AudioDeckWebSocket.kt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/AudioDeckWebSocket.kt) | `onFailure()` — just calls `onError()`, no reconnect attempt. Hardcoded IP. |
| [websocket_server.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/websocket_server.py) | No heartbeat/ping. `send_to_all()` silently removes dead clients. |
| [MainActivity.kt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/MainActivity.kt) | Hardcoded IP: `audioDeckWebSocket.connect("10.138.245.32")` |

### Files to Modify

1. `android/.../AudioDeckWebSocket.kt` — add auto-reconnect with exponential backoff
2. `android/.../MainActivity.kt` — configurable server IP (settings or input field)
3. `pc/server/websocket_server.py` — add ping/pong heartbeat

### Files to Create

None.

### Functions/Classes Involved

| Component | Change |
|---|---|
| `AudioDeckWebSocket` | Add reconnect logic with exponential backoff (1s, 2s, 4s, 8s, max 30s) |
| `AudioDeckWebSocket.onFailure()` | Trigger reconnect instead of just reporting error |
| `AudioDeckWebSocket.onClosed()` | Trigger reconnect for unexpected closures |
| `AudioDeckWebSocket` | Add `isReconnecting` state |
| `MainActivity` | Allow user to input/change server IP |
| `AudioDeckStateHolder` | Add `isReconnecting` state |
| `AudioDeckWebSocketServer` | Add WebSocket ping interval configuration |

### Data/State Flow

```text
Connection drops:
    → onFailure() / onClosed() fires
    → Set state to DISCONNECTED + RECONNECTING
    → Wait backoff period
    → Attempt reconnect
    → If success → set CONNECTED, reset backoff
    → If fail → double backoff, retry
    → Max backoff: 30 seconds
    → Max retries: unlimited (until manual disconnect)
```

### Protocol Changes

**None.** WebSocket ping/pong is a transport-level feature, not an application protocol change.

### Android Changes

1. **`AudioDeckWebSocket.kt`** — Add:
   - `private var shouldReconnect = true`
   - `private var reconnectDelay = 1000L` (ms)
   - `private val maxReconnectDelay = 30_000L`
   - `private var serverIp: String = ""`
   - `private val reconnectHandler = Handler(Looper.getMainLooper())`
   - In `onFailure()` and `onClosed()`: schedule reconnect if `shouldReconnect`
   - `scheduleReconnect()` — doubles delay each attempt, caps at max
   - On successful `onOpen()`: reset `reconnectDelay = 1000L`
   - `disconnect()` sets `shouldReconnect = false` first

2. **`MainActivity.kt`** — Add server IP input:
   - When disconnected and not reconnecting, show a `TextField` for IP input
   - Save IP to `SharedPreferences`
   - Load saved IP on startup (default to empty, requiring user input on first launch)

3. **`AudioDeckState.kt`** — Add `val isReconnecting: Boolean = false`

### Python/Windows Changes

1. **`websocket_server.py`** — Add ping interval to `websockets.serve()`:
   ```python
   async with websockets.serve(
       self.handle_client,
       HOST,
       PORT,
       ping_interval=20,   # Send ping every 20s
       ping_timeout=10,    # Disconnect if no pong in 10s
   ):
   ```

### UI Changes

- Connection status shows three states: `CONNECTED`, `DISCONNECTED`, `RECONNECTING...`
- When disconnected (not reconnecting), show an IP input field
- Reconnection indicator (e.g., pulsing dot or text)

### Implementation Steps

1. Add ping configuration to `websockets.serve()` on PC side
2. Refactor `AudioDeckWebSocket.kt` to support auto-reconnect:
   - Store server IP as class field
   - Add reconnect scheduling with exponential backoff
   - Reset backoff on successful connection
   - Stop reconnecting on explicit `disconnect()`
3. Add `isReconnecting` field to `AudioDeckState.kt`
4. Update `AudioDeckStateHolder` to manage reconnecting state
5. Add IP input to `MainActivity` / `AudioDeckScreen()` when disconnected
6. Add `SharedPreferences` for persisting server IP
7. Update connection status display for three states

### Build/Test Procedure

1. **PC**: Start server → verify ping logs appear
2. **Android**: Build and install
3. **Test auto-reconnect**:
   - Connect successfully
   - Kill the PC server → Android shows DISCONNECTED → RECONNECTING
   - Restart PC server → Android auto-connects
   - Verify backoff increases (check logs)
4. **Test IP persistence**:
   - Enter IP → connect → close app → reopen → IP should be pre-filled
5. **Test explicit disconnect**:
   - Connect → press back / close app → should NOT keep reconnecting in background
6. Verify all previous phases still work

### Acceptance Criteria

- [ ] Auto-reconnect activates when connection drops
- [ ] Exponential backoff: 1s → 2s → 4s → 8s → ... → 30s max
- [ ] Backoff resets on successful reconnection
- [ ] UI shows CONNECTED / DISCONNECTED / RECONNECTING states
- [ ] Server IP is configurable (not hardcoded)
- [ ] Server IP persists across app restarts
- [ ] PC server uses ping/pong to detect dead clients
- [ ] Explicit disconnect stops reconnection attempts
- [ ] All previous phases still work
- [ ] Both sides build without errors

### Failure Conditions

- Reconnect loop runs on the UI thread, freezing the app
- Reconnect fires too rapidly (no backoff)
- Reconnect continues after explicit disconnect
- SharedPreferences read/write causes ANR
- PC ping/pong misconfigured, disconnecting healthy clients

### Required Git Commit Message

```
feat: improve connection reliability
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- Reconnect behavior verified through multiple disconnect/reconnect cycles
- Commit created on `antigravity-dev`

---

## PHASE 10 — Performance

### Objective

Optimize data transfer, reduce unnecessary processing, and ensure smooth UI performance.

### Current Code to Inspect

| File | What to look at |
|---|---|
| [websocket_server.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/websocket_server.py) | `position_monitor()` sends updates even when paused |
| [media_session.py](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/pc/server/media_session.py) | `get_artwork()` returns full Base64 every time in `get_current_state()` (cached at reader level, but still transported) |
| [MainActivity.kt](file:///c:/Users/Chaithanya%20R%20Rao/Desktop/AudioDeck/android/AudioDeck/app/src/main/java/com/chaithanya/audiodeck/MainActivity.kt) | `decodeArtwork()` — already uses `remember(state.artwork)`, but could be more robust |

### Files to Modify

1. `pc/server/websocket_server.py` — optimize position broadcasting
2. `pc/server/protocol.py` — separate artwork from position/playback updates
3. `android/.../AudioDeckWebSocket.kt` — add seek command debouncing
4. `android/.../MainActivity.kt` — ensure artwork bitmap is properly cached

### Files to Create

None.

### Functions/Classes Involved

| Component | Change |
|---|---|
| `position_monitor()` | Skip position broadcasts when status is PAUSED or STOPPED |
| `update_media_state()` | Don't include artwork in position messages (it's already never included, but verify) |
| `track_message()` | Ensure artwork is ONLY sent with track changes |
| `AudioDeckWebSocket.sendCommand()` | Add debouncing for rapid seek commands (ignore seeks within 100ms of each other) |
| `AudioDeckScreen()` | Ensure Slider recomposition is minimized |

### Data/State Flow

```text
Position Optimization:
    position_monitor():
        if status == "PAUSED" or status == "STOPPED":
            skip (don't send position)
        else:
            send position_message

Seek Debounce:
    User drags slider rapidly:
        → Only the LAST seek command is sent (debounce 100-200ms)
        → Avoids flooding the WebSocket with intermediate positions

Artwork Optimization:
    Verify: artwork (Base64, potentially 100KB+) is ONLY sent in:
        - state_message (initial connection)
        - track_message (track change)
    NEVER in:
        - position_message ✓ (already correct)
        - playback_message ✓ (already correct)
        - volume_message ✓ (already correct)
        - ack_message → verify it doesn't include artwork
```

### Protocol Changes

**None.** This is behavioral optimization, not protocol restructuring.

### Android Changes

1. **Seek debounce** in `AudioDeckCommandHolder` or `AudioDeckScreen`:
   ```kotlin
   private var seekJob: Job? = null

   fun sendSeekDebounced(position: Double, scope: CoroutineScope) {
       seekJob?.cancel()
       seekJob = scope.launch {
           delay(150) // 150ms debounce
           sendCommand?.invoke("seek", position)
       }
   }
   ```

2. **Verify artwork caching** — `remember(state.artwork)` is correct, but ensure the key is stable (same Base64 string produces same bitmap, no re-decode).

### Python/Windows Changes

1. **`websocket_server.py` — `position_monitor()`**:
   ```python
   async def position_monitor(self):
       while True:
           try:
               if (self.current_state is not None
                   and self.current_status == "PLAYING"):
                   # Only send position when actively playing
                   state = await self.media_reader.get_current_state()
                   if state is not None:
                       self.current_state = state
                       await self.send_to_all(position_message(state))
           except Exception as e:
               print(f"[Position] Error: {e}")
           await asyncio.sleep(POSITION_INTERVAL)
   ```

2. **Verify `ack_message()` doesn't include artwork** — it shouldn't (from Phase 7.8), but confirm.

### UI Changes

None. This phase is entirely behavioral.

### Implementation Steps

1. Modify `position_monitor()` to skip broadcasts when paused/stopped
2. Verify artwork is not sent in ack messages
3. Add seek debouncing on Android side
4. Verify artwork bitmap caching in Compose
5. Profile and verify reduced WebSocket message volume

### Build/Test Procedure

1. **PC**: Start server, pause playback → verify no position messages are sent (check logs)
2. **PC**: Resume playback → verify position messages resume
3. **Android**: Build and install
4. **Test seek debounce**:
   - Rapidly drag the seek slider back and forth
   - Check PC server logs — should show only 1-2 seek commands, not dozens
5. **Test artwork**:
   - Change tracks multiple times
   - Verify artwork loads correctly each time
   - Verify no OOM or performance degradation
6. Verify all previous phases still work

### Acceptance Criteria

- [ ] Position messages stop when playback is paused/stopped
- [ ] Position messages resume when playback resumes
- [ ] Seek commands are debounced (no rapid-fire flooding)
- [ ] Artwork is only transferred during `state` and `track` messages
- [ ] Ack messages do not contain artwork
- [ ] UI performance is smooth (no jank during slider updates)
- [ ] All previous phases still work
- [ ] Both sides build without errors

### Failure Conditions

- Position messages never resume after unpausing
- Debounce is too aggressive (user's final seek position is dropped)
- Artwork stops appearing after optimization
- Status comparison uses wrong value (e.g., comparing to `"Paused"` instead of `"PAUSED"`)

### Required Git Commit Message

```
perf: optimize audio deck performance
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- Performance optimizations verified with logging
- Commit created on `antigravity-dev`

---

## PHASE 11 — Packaging + E2E Testing

### Objective

Create proper build scripts, test harness, documentation, and verify the complete system end-to-end. Prepare for deployment.

### Current Code to Inspect

All files — this is a full-system verification phase.

### Files to Modify

1. `README.md` — comprehensive update
2. `pc/server/websocket_server.py` — add `--port` CLI argument
3. `.gitignore` — verify completeness

### Files to Create

1. `pc/server/test_protocol.py` — automated protocol unit tests (rename/expand from `protocol_test.py`)
2. `pc/server/test_e2e.py` — end-to-end WebSocket test script
3. `pc/run_server.py` — entry point script with argument parsing
4. `TESTING.md` — test checklist document

### Functions/Classes Involved

| Component | Change |
|---|---|
| `websocket_server.py` | Add argparse for `--host` and `--port` |
| `run_server.py` | Clean entry point that imports and runs the server |
| `test_protocol.py` | Unit tests for all protocol message builders |
| `test_e2e.py` | Automated WebSocket connection test |

### Data/State Flow

No new data flow. This phase validates existing flows.

### Protocol Changes

**None.**

### Android Changes

None functionally. Optionally update `versionName` in `build.gradle.kts` to `"1.1"` or similar.

### Python/Windows Changes

1. **`run_server.py`** — Clean entry point:
   ```python
   import argparse
   import asyncio
   import sys
   sys.path.insert(0, "server")
   from websocket_server import AudioDeckWebSocketServer

   def main():
       parser = argparse.ArgumentParser(description="Audio Deck Server")
       parser.add_argument("--host", default="0.0.0.0")
       parser.add_argument("--port", type=int, default=8765)
       args = parser.parse_args()

       server = AudioDeckWebSocketServer(host=args.host, port=args.port)
       asyncio.run(server.start())

   if __name__ == "__main__":
       main()
   ```

2. **`websocket_server.py`** — Accept host/port as constructor parameters (with defaults matching current hardcoded values).

3. **`test_protocol.py`** — Automated unit tests:
   ```python
   # Test all message builders produce valid JSON with expected fields
   # Test parse_command handles all action types
   # Test edge cases: empty strings, None values, zero durations
   ```

4. **`test_e2e.py`** — End-to-end test:
   ```python
   # Connect to running server
   # Verify welcome message received
   # Send play_pause command
   # Verify ack received
   # Verify position messages are periodic
   # Disconnect and verify clean shutdown
   ```

### UI Changes

None.

### Implementation Steps

1. Refactor `websocket_server.py` to accept configurable host/port
2. Create `pc/run_server.py` with argparse
3. Create `pc/server/test_protocol.py` with unit tests for every protocol function
4. Create `pc/server/test_e2e.py` with connection + command tests
5. Update `README.md`:
   - Updated architecture diagram
   - Complete feature list
   - Setup instructions for both PC and Android
   - Protocol documentation
   - Test instructions
6. Create `TESTING.md` with manual test checklist
7. Verify `.gitignore` covers all generated files
8. Run all tests

### Build/Test Procedure

1. **Run protocol tests**: `python server/test_protocol.py` — all pass
2. **Start server**: `python run_server.py --port 8765`
3. **Run E2E tests**: `python server/test_e2e.py` — all pass
4. **Android**: `./gradlew assembleDebug` — builds successfully
5. **Full manual E2E test** (follow `TESTING.md` checklist):
   - [ ] PC server starts cleanly
   - [ ] Android connects
   - [ ] Track info displays
   - [ ] Artwork displays
   - [ ] Position slider tracks playback
   - [ ] Play/Pause command works
   - [ ] Next/Previous commands work
   - [ ] Seek works
   - [ ] Volume control works
   - [ ] Command acknowledgments are received
   - [ ] Error handling works (kill Brave → command fails → error shown)
   - [ ] Auto-reconnect works (kill server → restart → client reconnects)
   - [ ] Position stops updating when paused
   - [ ] Seek debouncing works

### Acceptance Criteria

- [ ] `run_server.py` starts the server with `--host` and `--port` arguments
- [ ] `test_protocol.py` contains unit tests for all protocol functions — all pass
- [ ] `test_e2e.py` connects, receives welcome, sends command, receives ack — all pass
- [ ] `README.md` is comprehensive and accurate
- [ ] `TESTING.md` contains the complete manual test checklist
- [ ] Android APK builds successfully
- [ ] Full manual E2E test passes all items
- [ ] `.gitignore` is complete
- [ ] All previous phases confirmed working
- [ ] No regressions detected

### Failure Conditions

- Any test fails
- Any previous phase regresses
- README instructions produce errors when followed
- Server doesn't accept CLI arguments properly

### Required Git Commit Message

```
chore: finalize packaging and e2e testing
```

### Conditions Before Moving to Next Phase

- All acceptance criteria pass
- Full E2E test completed successfully
- Commit created on `antigravity-dev`
- **THIS IS THE FINAL PHASE — FREEZE**

---

## 13. EXECUTION MODEL

```text
┌──────────────────────────────────────┐
│         BEFORE FIRST PHASE           │
│                                      │
│  git checkout -b antigravity-dev     │
│                                      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         FOR EACH PHASE:              │
│                                      │
│  1. Read the phase specification     │
│  2. Inspect all listed current code  │
│  3. Implement the changes            │
│  4. Build (PC: python, Android: gradle)│
│  5. Test (automated + manual)        │
│  6. If tests fail → FIX → RETEST    │
│  7. Commit with specified message    │
│  8. Report:                          │
│     PHASE COMPLETE                   │
│     Tests passed: [list]             │
│     Files changed: [list]            │
│     Commit created: [message]        │
│     Commit hash: [hash]             │
│     Ready for next phase             │
│                                      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│       AFTER PHASE 11:                │
│                                      │
│  ██████████████████████████████████  │
│  ██                              ██  │
│  ██        F R E E Z E           ██  │
│  ██                              ██  │
│  ██  DO NOT START CYBERPUNK UI   ██  │
│  ██                              ██  │
│  ██████████████████████████████████  │
│                                      │
│  Wait for owner to create the        │
│  Cyberpunk UI workflow/branch.       │
│                                      │
└──────────────────────────────────────┘
```

### Phase Order (Strict)

| Order | Phase | Commit Message |
|---|---|---|
| 1 | 7.6.5 Position Synchronization | `feat: implement position synchronization` |
| 2 | 7.7 Volume Control | `feat: add volume controls` |
| 3 | 7.8 Control Synchronization | `feat: synchronize playback controls` |
| 4 | 7.9 Control Error Handling | `feat: add control error handling` |
| 5 | 8 Functional UI | `feat: implement functional audio deck UI` |
| 6 | 9 Reliability | `feat: improve connection reliability` |
| 7 | 10 Performance | `perf: optimize audio deck performance` |
| 8 | 11 Packaging + E2E Testing | `chore: finalize packaging and e2e testing` |

### Rules

- **ONE phase at a time.** Never implement two phases simultaneously.
- **Test before commit.** Never commit code that doesn't build/pass.
- **Fix before advancing.** If a phase breaks, fix it before moving on.
- **Report after each phase.** Every phase ends with the completion report.
- **No mute/unmute.** Do not introduce mute/unmute functionality anywhere.
- **No cyberpunk UI.** Phase 8 is a clean functional UI, not a themed skin.

---

## 14. STOP CONDITIONS

> [!CAUTION]
> Gemini MUST STOP and request human review if ANY of the following occur:

| Condition | Action |
|---|---|
| Existing working functionality would need to be removed | **STOP** — request approval |
| Existing architecture must be fundamentally rewritten | **STOP** — request approval |
| A protocol-breaking change is required | **STOP** — request approval |
| A test cannot be made to pass | **STOP** — report the failure |
| A requirement is ambiguous | **STOP** — ask for clarification |
| Implementation would affect a completed phase | **STOP** — report the risk |
| A destructive refactor is proposed | **STOP** — request approval |
| Uncertain about correct behavior | **STOP** — ask, don't guess |

---

> [!IMPORTANT]
> **EXCLUSIONS**: Mute/Unmute is NOT part of this project. Do not introduce it. Do not plan for it. Do not add a mute button, mute field, or mute state anywhere.

---

*End of Master Implementation Plan*
*Prepared for Gemini execution on branch `antigravity-dev`*
