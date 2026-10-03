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
                        artwork = json.optString("artwork", null)
                    )
                }

                "track" -> {

                    AudioDeckState(
                        connected = true,
                        player = json.optString("player"),
                        title = json.optString("title"),
                        artist = json.optString("artist"),
                        album = json.optString("album"),
                        duration = json.optDouble("duration", 0.0),
                        artwork = json.optString("artwork", null)
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