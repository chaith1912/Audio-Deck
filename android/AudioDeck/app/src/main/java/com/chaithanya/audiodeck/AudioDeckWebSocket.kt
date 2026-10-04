package com.chaithanya.audiodeck

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener

class AudioDeckWebSocket(
    private val onMessage: (String) -> Unit,
    private val onConnected: () -> Unit,
    private val onDisconnected: () -> Unit,
    private val onError: (String) -> Unit
) {

    private val client = OkHttpClient()

    private var webSocket: WebSocket? = null

    fun connect(serverIp: String) {

        val url = "ws://$serverIp:8765"

        val request = Request.Builder()
            .url(url)
            .build()

        webSocket = client.newWebSocket(
            request,
            object : WebSocketListener() {

                override fun onOpen(
                    webSocket: WebSocket,
                    response: Response
                ) {
                    onConnected()
                }

                override fun onMessage(
                    webSocket: WebSocket,
                    text: String
                ) {
                    onMessage(text)
                }

                override fun onClosing(
                    webSocket: WebSocket,
                    code: Int,
                    reason: String
                ) {
                    webSocket.close(1000, null)
                    onDisconnected()
                }

                override fun onClosed(
                    webSocket: WebSocket,
                    code: Int,
                    reason: String
                ) {
                    onDisconnected()
                }

                override fun onFailure(
                    webSocket: WebSocket,
                    t: Throwable,
                    response: Response?
                ) {
                    onError(
                        t.message ?: "WebSocket connection failed"
                    )
                }
            }
        )
    }

    fun disconnect() {
        webSocket?.close(1000, "Client closing")
        webSocket = null
    }

    fun sendCommand(action: String, position: Double? = null) {

        val message = if (position != null) {
            """
        {
            "type": "command",
            "action": "$action",
            "position": $position
        }
        """.trimIndent()
        } else {
            """
        {
            "type": "command",
            "action": "$action"
        }
        """.trimIndent()
        }

        webSocket?.send(message)
    }
}