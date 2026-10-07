package com.chaithanya.audiodeck

import org.junit.Assert.*
import org.junit.Test

class AudioDeckMessageParserTest {

    @Test
    fun parse_stateMessage_populatesFullState() {
        val json = """
            {
                "type": "state",
                "player": "Brave",
                "title": "Song A",
                "artist": "Artist A",
                "album": "Album A",
                "status": "PLAYING",
                "position": 45.5,
                "duration": 200.0,
                "artwork": "base64data"
            }
        """.trimIndent()

        val state = AudioDeckMessageParser.parse(json, AudioDeckState())

        assertNotNull(state)
        assertEquals("Brave", state!!.player)
        assertEquals("Song A", state.title)
        assertEquals("Artist A", state.artist)
        assertEquals("Album A", state.album)
        assertEquals("PLAYING", state.status)
        assertEquals(45.5, state.position, 0.001)
        assertEquals(200.0, state.duration, 0.001)
        assertEquals("base64data", state.artwork)
        assertTrue(state.connected)
        assertEquals(1L, state.trackId)
    }

    @Test
    fun parse_trackMessage_resetsPositionToZeroAndIncrementsTrackId() {
        val initial = AudioDeckState(
            connected = true,
            player = "Brave",
            title = "Song A",
            artist = "Artist A",
            album = "Album A",
            status = "PLAYING",
            position = 95.0,
            duration = 200.0,
            trackId = 1L
        )

        val trackJson = """
            {
                "type": "track",
                "player": "Brave",
                "title": "Song B",
                "artist": "Artist B",
                "album": "Album B",
                "duration": 180.0,
                "artwork": null
            }
        """.trimIndent()

        val newState = AudioDeckMessageParser.parse(trackJson, initial)

        assertNotNull(newState)
        assertEquals("Song B", newState!!.title)
        assertEquals("Artist B", newState.artist)
        assertEquals("Album B", newState.album)
        assertEquals(180.0, newState.duration, 0.001)
        // CRITICAL: Position must immediately be reset to 0.0, never retaining Song A's 95.0!
        assertEquals(0.0, newState.position, 0.001)
        // Status should be preserved from current state
        assertEquals("PLAYING", newState.status)
        assertNull(newState.artwork)
        // Track ID must be incremented
        assertEquals(2L, newState.trackId)
    }

    @Test
    fun parse_positionMessage_updatesPositionWithoutAffectingTrackMetadata() {
        val current = AudioDeckState(
            connected = true,
            player = "Brave",
            title = "Song B",
            artist = "Artist B",
            album = "Album B",
            status = "PLAYING",
            position = 0.0,
            duration = 180.0,
            trackId = 2L
        )

        val posJson = """
            {
                "type": "position",
                "position": 12.5,
                "duration": 180.0
            }
        """.trimIndent()

        val updated = AudioDeckMessageParser.parse(posJson, current)

        assertNotNull(updated)
        assertEquals(12.5, updated!!.position, 0.001)
        assertEquals(180.0, updated.duration, 0.001)
        // Track metadata must be untouched
        assertEquals("Song B", updated.title)
        assertEquals("Artist B", updated.artist)
        assertEquals(2L, updated.trackId)
    }

    @Test
    fun parse_playbackMessage_updatesStatusOnly() {
        val current = AudioDeckState(
            connected = true,
            player = "Brave",
            title = "Song B",
            artist = "Artist B",
            status = "PLAYING",
            position = 30.0,
            duration = 180.0,
            trackId = 2L
        )

        val playbackJson = """
            {
                "type": "playback",
                "status": "PAUSED"
            }
        """.trimIndent()

        val updated = AudioDeckMessageParser.parse(playbackJson, current)

        assertNotNull(updated)
        assertEquals("PAUSED", updated!!.status)
        assertEquals(30.0, updated.position, 0.001)
        assertEquals("Song B", updated.title)
        assertEquals(2L, updated.trackId)
    }

    @Test
    fun parse_rapidTrackChanges_correctlyResetsEachTime() {
        var state = AudioDeckState(
            title = "Song 1",
            position = 50.0,
            duration = 100.0,
            trackId = 1L
        )

        // Rapid next 1
        state = AudioDeckMessageParser.parse(
            """{"type": "track", "title": "Song 2", "artist": "Artist 2", "duration": 150.0}""",
            state
        )!!
        assertEquals("Song 2", state.title)
        assertEquals(0.0, state.position, 0.001)
        assertEquals(2L, state.trackId)

        // Rapid next 2
        state = AudioDeckMessageParser.parse(
            """{"type": "track", "title": "Song 3", "artist": "Artist 3", "duration": 220.0}""",
            state
        )!!
        assertEquals("Song 3", state.title)
        assertEquals(0.0, state.position, 0.001)
        assertEquals(3L, state.trackId)

        // Rapid previous
        state = AudioDeckMessageParser.parse(
            """{"type": "track", "title": "Song 2", "artist": "Artist 2", "duration": 150.0}""",
            state
        )!!
        assertEquals("Song 2", state.title)
        assertEquals(0.0, state.position, 0.001)
        assertEquals(4L, state.trackId)
    }

    @Test
    fun parse_zeroOrInvalidDuration_safelyCoerced() {
        val json = """
            {
                "type": "track",
                "title": "Loading Song",
                "duration": -5.0,
                "position": -2.0
            }
        """.trimIndent()

        val state = AudioDeckMessageParser.parse(json, AudioDeckState())
        assertNotNull(state)
        assertEquals(0.0, state!!.duration, 0.001)
        assertEquals(0.0, state.position, 0.001)
    }

    @Test
    fun parse_unknownType_returnsNull() {
        val json = """{"type": "unknown_event"}"""
        val state = AudioDeckMessageParser.parse(json, AudioDeckState())
        assertNull(state)
    }
}
