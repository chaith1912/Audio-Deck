package com.chaithanya.audiodeck

data class AudioDeckState(
    val connected: Boolean = false,
    val player: String = "",
    val title: String = "",
    val artist: String = "",
    val album: String = "",
    val status: String = "UNKNOWN",
    val position: Double = 0.0,
    val duration: Double = 0.0,
    val artwork: String? = null
)