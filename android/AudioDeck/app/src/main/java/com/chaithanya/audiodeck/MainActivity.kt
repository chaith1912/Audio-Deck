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


@Composable
fun AudioDeckScreen() {

    val state = AudioDeckStateHolder.state

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

        Text(
            text = if (state.artwork != null) {
                "ARTWORK RECEIVED"
            } else {
                "NO ARTWORK"
            }
        )
    }
}