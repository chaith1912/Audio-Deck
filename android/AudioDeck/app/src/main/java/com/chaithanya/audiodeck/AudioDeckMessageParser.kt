package com.chaithanya.audiodeck

import org.json.JSONObject


object AudioDeckMessageParser {

    fun parse(message: String): AudioDeckState? {

        return try {

            val json = JSONObject(message)

            when (json.optString("type")) {

                "state" -> {

                    AudioDeckState(
                        connected = true,
                        player = json.optString("player"),
                        title = json.optString("title"),
                        artist = json.optString("artist"),
                        album = json.optString("album"),
                        status = json.optString("status"),
                        position = json.optDouble("position", 0.0),
                        duration = json.optDouble("duration", 0.0),
                        artwork = if (json.has("artwork") && !json.isNull("artwork")) json.getString("artwork") else null,
                        volume = json.optDouble("volume", 1.0)
                    )
                }

                "track" -> {

                    val currentState = AudioDeckStateHolder.state
                    currentState.copy(
                        connected = true,
                        player = json.optString("player", currentState.player),
                        title = json.optString("title", currentState.title),
                        artist = json.optString("artist", currentState.artist),
                        album = json.optString("album", currentState.album),
                        duration = json.optDouble("duration", currentState.duration),
                        artwork = if (json.has("artwork") && !json.isNull("artwork")) json.getString("artwork") else null
                    )
                }

                "playback" -> {

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

                "volume" -> {

                    val currentState = AudioDeckStateHolder.state
                    currentState.copy(
                        volume = json.optDouble("volume", currentState.volume)
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