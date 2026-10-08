package com.chaithanya.audiodeck

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.material3.Button
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.chaithanya.audiodeck.ui.theme.AudioDeckTheme
import android.graphics.BitmapFactory
import android.util.Base64
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.size
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.dp
import androidx.compose.material3.Slider
import androidx.compose.foundation.layout.fillMaxWidth
import kotlinx.coroutines.delay
import kotlin.math.abs

class MainActivity : ComponentActivity() {

    private lateinit var audioDeckWebSocket: AudioDeckWebSocket

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            AudioDeckTheme {
                AudioDeckScreen()
            }
        }

        audioDeckWebSocket = AudioDeckWebSocket(

            onMessage = { message ->

                Log.d(
                    "AudioDeck",
                    "Raw message: $message"
                )

                val state =
                    AudioDeckMessageParser.parse(message)

                if (state != null) {

                    Log.d(
                        "AudioDeck",
                        "Title: ${state.title}"
                    )

                    Log.d(
                        "AudioDeck",
                        "Artist: ${state.artist}"
                    )

                    Log.d(
                        "AudioDeck",
                        "Artwork received: ${state.artwork != null}"
                    )

                    runOnUiThread {
                        AudioDeckStateHolder.update(state)
                    }
                }
            },

            onConnected = {
                Log.d(
                    "AudioDeck",
                    "CONNECTED TO PC"
                )

                runOnUiThread {
                    AudioDeckStateHolder.setConnected(true)
                }
            },

            onDisconnected = {
                Log.d(
                    "AudioDeck",
                    "DISCONNECTED FROM PC"
                )

                runOnUiThread {
                    AudioDeckStateHolder.setConnected(false)
                }
            },

            onError = { error ->
                Log.e(
                    "AudioDeck",
                    "WebSocket error: $error"
                )
            }
        )
        AudioDeckCommandHolder.sendCommand = { action, position, level ->
            audioDeckWebSocket.sendCommand(action, position, level)
        }
        audioDeckWebSocket.connect(
            "10.138.245.32"
        )
    }

    override fun onDestroy() {

        AudioDeckCommandHolder.sendCommand = null

        audioDeckWebSocket.disconnect()

        super.onDestroy()
    }
}


object AudioDeckStateHolder {

    var state by mutableStateOf(
        AudioDeckState()
    )
        private set

    fun update(newState: AudioDeckState) {
        state = newState.copy(
            connected = true
        )
    }

    fun updatePosition(position: Double, duration: Double) {
        state = state.copy(
            position = position,
            duration = duration
        )
    }

    fun updatePlayback(status: String) {
        state = state.copy(
            status = status
        )
    }

    fun updateVolume(volume: Double) {
        state = state.copy(
            volume = volume
        )
    }

    fun setConnected(connected: Boolean) {
        state = state.copy(
            connected = connected
        )
    }
}
object AudioDeckCommandHolder {

    var sendCommand: ((String, Double?, Double?) -> Unit)? = null

    fun sendPlayPause() {
        sendCommand?.invoke("play_pause", null, null)
    }

    fun sendNext() {
        sendCommand?.invoke("next", null, null)
    }

    fun sendPrevious() {
        sendCommand?.invoke("previous", null, null)
    }

    fun sendSeek(position: Double) {
        sendCommand?.invoke("seek", position, null)
    }

    fun sendVolume(level: Double) {
        sendCommand?.invoke("volume", null, level)
    }
}
fun decodeArtwork(
    base64: String?
): androidx.compose.ui.graphics.ImageBitmap? {

    if (base64.isNullOrEmpty()) {
        return null
    }

    return try {

        val bytes = Base64.decode(
            base64,
            Base64.DEFAULT
        )

        BitmapFactory
            .decodeByteArray(
                bytes,
                0,
                bytes.size
            )
            ?.asImageBitmap()

    } catch (e: Exception) {

        Log.e(
            "AudioDeck",
            "Artwork decode failed",
            e
        )

        null
    }
}

@Composable
fun AudioDeckScreen() {

    var seekPosition by remember { mutableFloatStateOf(0f) }
    var isSeeking by remember { mutableStateOf(false) }
    var pendingSeekTarget by remember { mutableStateOf<Double?>(null) }

    var volumePosition by remember { mutableFloatStateOf(1f) }
    var isChangingVolume by remember { mutableStateOf(false) }
    var pendingVolumeTarget by remember { mutableStateOf<Double?>(null) }

    val state = AudioDeckStateHolder.state

    LaunchedEffect(state.title) {
        pendingSeekTarget = null
    }

    LaunchedEffect(pendingSeekTarget) {
        if (pendingSeekTarget != null) {
            delay(1500)
            pendingSeekTarget = null
        }
    }

    LaunchedEffect(pendingVolumeTarget) {
        if (pendingVolumeTarget != null) {
            delay(1500)
            pendingVolumeTarget = null
        }
    }

    LaunchedEffect(state.position) {
        if (!isSeeking) {
            val target = pendingSeekTarget
            if (target != null) {
                if (abs(state.position - target) < 3.0) {
                    seekPosition = state.position.toFloat()
                    pendingSeekTarget = null
                }
            } else {
                seekPosition = state.position.toFloat()
            }
        }
    }

    LaunchedEffect(state.volume) {
        if (!isChangingVolume) {
            val target = pendingVolumeTarget
            if (target != null) {
                if (abs(state.volume - target) < 0.05) {
                    volumePosition = state.volume.toFloat()
                    pendingVolumeTarget = null
                }
            } else {
                volumePosition = state.volume.toFloat()
            }
        }
    }

    val artwork = remember(state.artwork) {
        decodeArtwork(state.artwork)
    }

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {

        Text(
            text = "AUDIO DECK"
        )

        Text(
            text = if (state.connected) {
                "CONNECTED"
            } else {
                "DISCONNECTED"
            }
        )

        Text(
            text = state.title
        )

        Text(
            text = state.artist
        )

        if (artwork != null) {

            Image(
                bitmap = artwork,
                contentDescription = "Album artwork",
                modifier = Modifier.size(50.dp)
            )

        } else {

            Text(
                text = "NO ARTWORK"
            )
        }

        val maxDuration = maxOf(state.duration.toFloat(), 0.001f)

        Slider(
            value = seekPosition.coerceIn(0f, maxDuration),
            onValueChange = { value ->
                isSeeking = true
                seekPosition = value
            },
            onValueChangeFinished = {
                val target = seekPosition.toDouble()
                pendingSeekTarget = target
                AudioDeckCommandHolder.sendSeek(target)
                isSeeking = false
            },
            valueRange = 0f..maxDuration,
            modifier = Modifier.fillMaxWidth(0.8f)
        )

        Text(
            text = "VOLUME: ${(volumePosition * 100).toInt()}%"
        )

        Slider(
            value = volumePosition.coerceIn(0f, 1f),
            onValueChange = { value ->
                isChangingVolume = true
                volumePosition = value
            },
            onValueChangeFinished = {
                val target = volumePosition.toDouble()
                pendingVolumeTarget = target
                AudioDeckCommandHolder.sendVolume(target)
                isChangingVolume = false
            },
            valueRange = 0f..1f,
            modifier = Modifier.fillMaxWidth(0.8f)
        )

        Button(
            onClick = {
                AudioDeckCommandHolder.sendPlayPause()
            }
        ) {
            Text("PLAY / PAUSE")
        }
        Button(
            onClick = {
                AudioDeckCommandHolder.sendNext()
            }
        ) {
            Text("NEXT")
        }
        Button(
            onClick = {
                AudioDeckCommandHolder.sendPrevious()
            }
        ) {
            Text("PREVIOUS")
        }
    }
}