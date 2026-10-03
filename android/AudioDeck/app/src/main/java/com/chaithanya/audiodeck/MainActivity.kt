package com.chaithanya.audiodeck

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
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

        audioDeckWebSocket.connect(
            "10.138.245.32"
        )
    }

    override fun onDestroy() {
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

    fun setConnected(connected: Boolean) {
        state = state.copy(
            connected = connected
        )
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

    val state = AudioDeckStateHolder.state

    val artwork = decodeArtwork(
        state.artwork
    )

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
                modifier = Modifier.size(250.dp)
            )

        } else {

            Text(
                text = "NO ARTWORK"
            )
        }
    }
}