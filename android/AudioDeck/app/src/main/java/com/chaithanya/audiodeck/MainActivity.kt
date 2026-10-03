package com.chaithanya.audiodeck

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.chaithanya.audiodeck.ui.theme.AudioDeckTheme

class MainActivity : ComponentActivity() {

    private lateinit var audioDeckWebSocket: AudioDeckWebSocket

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

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
                        "Status: ${state.status}"
                    )

                    Log.d(
                        "AudioDeck",
                        "Position: ${state.position}"
                    )

                    Log.d(
                        "AudioDeck",
                        "Artwork received: ${state.artwork != null}"
                    )
                }
            },

            onConnected = {
                Log.d(
                    "AudioDeck",
                    "CONNECTED TO PC"
                )
            },

            onDisconnected = {
                Log.d(
                    "AudioDeck",
                    "DISCONNECTED FROM PC"
                )
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

        setContent {
            AudioDeckTheme {
                ConnectionScreen()
            }
        }
    }

    override fun onDestroy() {
        audioDeckWebSocket.disconnect()
        super.onDestroy()
    }
}

@Composable
fun ConnectionScreen() {

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(text = "AUDIO DECK")
        Text(text = "Connecting to PC...")
    }
}