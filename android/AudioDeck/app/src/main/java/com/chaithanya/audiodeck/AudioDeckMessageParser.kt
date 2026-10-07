package com.chaithanya.audiodeck

import org.json.JSONObject


object AudioDeckMessageParser {

    fun parse(
        message: String,
        currentState: AudioDeckState = AudioDeckStateHolder.state
    ): AudioDeckState? {

        return try {

            val json = JSONObject(message)

            when (json.optString("type")) {

                "state" -> {
                    AudioDeckStateHolder.clearPendingSeek()
                    val artworkStr = if (json.has("artwork") && !json.isNull("artwork")) {
                        json.optString("artwork").takeIf { it.isNotEmpty() && it != "null" }
                    } else {
                        null
                    }

                    currentState.copy(
                        connected = true,
                        player = json.optString("player", currentState.player),
                        title = json.optString("title", currentState.title),
                        artist = json.optString("artist", currentState.artist),
                        album = json.optString("album", currentState.album),
                        status = json.optString("status", currentState.status),
                        position = json.optDouble("position", 0.0).coerceAtLeast(0.0),
                        duration = json.optDouble("duration", 0.0).coerceAtLeast(0.0),
                        artwork = artworkStr,
                        trackId = currentState.trackId + 1
                    )
                }

                "track" -> {
                    AudioDeckStateHolder.clearPendingSeek()
                    val artworkStr = if (json.has("artwork") && !json.isNull("artwork")) {
                        json.optString("artwork").takeIf { it.isNotEmpty() && it != "null" }
                    } else {
                        null
                    }

                    currentState.copy(
                        connected = true,
                        player = json.optString("player", currentState.player),
                        title = json.optString("title", ""),
                        artist = json.optString("artist", ""),
                        album = json.optString("album", ""),
                        status = if (json.has("status")) json.optString("status", currentState.status) else currentState.status,
                        position = json.optDouble("position", 0.0).coerceAtLeast(0.0),
                        duration = json.optDouble("duration", 0.0).coerceAtLeast(0.0),
                        artwork = artworkStr,
                        trackId = currentState.trackId + 1
                    )
                }

                "playback" -> {
                    currentState.copy(
                        connected = true,
                        status = json.optString("status", currentState.status)
                    )
                }

                "position" -> {
                    val rawPos = json.optDouble("position", currentState.position).coerceAtLeast(0.0)
                    val rawDur = json.optDouble("duration", currentState.duration).coerceAtLeast(0.0)
                    val resolvedPos = AudioDeckStateHolder.filterIncomingPosition(rawPos)
                    currentState.copy(
                        connected = true,
                        position = resolvedPos,
                        duration = rawDur
                    )
                }

                "welcome" -> {
                    currentState.copy(
                        connected = true
                    )
                }

                else -> null
            }

        } catch (e: Exception) {

            e.printStackTrace()
            null
        }
    }
}