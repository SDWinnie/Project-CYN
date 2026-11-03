package com.cyn.companion

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.BatteryManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import kotlin.math.abs
import kotlin.math.sqrt

class CynForegroundService : LifecycleService(), SensorEventListener {

    companion object {
        const val TAG = "CynService"
        const val CHANNEL_ID = "cyn_companion_service_channel"
        const val NOTIFICATION_ID = 7001
        const val ACTION_START = "ACTION_START_CYN_SERVICE"
        const val ACTION_STOP = "ACTION_STOP_CYN_SERVICE"
        const val EXTRA_HOST_URL = "EXTRA_HOST_URL"

        var isRunning: Boolean = false
            private set
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var wakeLock: PowerManager.WakeLock? = null

    private lateinit var sensorManager: SensorManager
    private var accelerometer: Sensor? = null
    private var lastAccMagnitude = 0f
    private var lastShakeTime = 0L

    private var okHttpClient: OkHttpClient? = null
    private var webSocket: WebSocket? = null
    private var targetHostUrl: String = "ws://192.168.1.50:8080/ws/cyn"

    private val batteryReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == Intent.ACTION_BATTERY_CHANGED) {
                val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
                val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
                if (level >= 0 && scale > 0) {
                    val batteryFraction = level / scale.toFloat()
                    if (batteryFraction < 0.20f) {
                        sendMobileTelemetry(acceleration = 0f, battery = batteryFraction)
                    }
                }
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "Creating CYN Companion Foreground Service...")
        createNotificationChannel()

        // Acquire partial wake lock to keep background connection active
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "CYN::ServiceWakeLock").apply {
            setReferenceCounted(false)
            acquire(24 * 60 * 60 * 1000L) // 24 hours max safe timeout
        }

        // Initialize motion sensors
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        accelerometer?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }

        // Register battery monitor
        registerReceiver(batteryReceiver, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        val action = intent?.action

        if (action == ACTION_STOP) {
            stopForegroundService()
            return START_NOT_STICKY
        }

        intent?.getStringExtra(EXTRA_HOST_URL)?.let {
            if (it.isNotBlank()) targetHostUrl = it
        }

        startForeground(NOTIFICATION_ID, buildForegroundNotification("Active & Connected to $targetHostUrl"))
        isRunning = true

        initWebSocket()

        return START_STICKY
    }

    private fun initWebSocket() {
        serviceScope.launch {
            if (okHttpClient == null) {
                okHttpClient = OkHttpClient.Builder()
                    .readTimeout(0, TimeUnit.MILLISECONDS)
                    .pingInterval(15, TimeUnit.SECONDS)
                    .build()
            }

            connectWebSocket()
        }
    }

    private fun connectWebSocket() {
        try {
            val fullUrl = if (targetHostUrl.contains("client=")) targetHostUrl
                else if (targetHostUrl.contains("?")) "$targetHostUrl&client=android"
                else "$targetHostUrl?client=android"
            val request = Request.Builder().url(fullUrl).build()
            webSocket = okHttpClient?.newWebSocket(request, object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    Log.i(TAG, "CYN WebSocket Connected: $fullUrl")
                    updateNotification("WebSocket Conduit Connected to Host")
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    // Forward received message broadcast to MainActivity if visible
                    val broadcastIntent = Intent("com.cyn.companion.EVENT").apply {
                        putExtra("cyn_payload", text)
                    }
                    sendBroadcast(broadcastIntent)
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    Log.w(TAG, "WebSocket failure: ${t.message}. Reconnecting in 5s...")
                    updateNotification("Disconnected. Retrying conduit in 5s...")
                    serviceScope.launch {
                        delay(5000)
                        if (isRunning) connectWebSocket()
                    }
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    Log.i(TAG, "WebSocket closed: $reason")
                }
            })
        } catch (e: Exception) {
            Log.e(TAG, "WebSocket connect error: ${e.message}")
        }
    }

    fun sendMobileTelemetry(acceleration: Float, battery: Float) {
        val payload = JSONObject().apply {
            put("type", "mobile_telemetry")
            put("acceleration", acceleration)
            put("battery", battery)
            put("orientation", "portrait")
        }
        webSocket?.send(payload.toString())
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event?.sensor?.type == Sensor.TYPE_ACCELEROMETER) {
            val x = event.values[0]
            val y = event.values[1]
            val z = event.values[2]
            val magnitude = sqrt((x * x + y * y + z * z).toDouble()).toFloat()

            val delta = abs(magnitude - lastAccMagnitude)
            lastAccMagnitude = magnitude

            val now = System.currentTimeMillis()
            // Sudden acceleration spike > 20 m/s^2 triggers shake telemetry hook
            if (delta > 20.0f && now - lastShakeTime > 4000L) {
                lastShakeTime = now
                Log.i(TAG, "Sudden motion turbulence detected: delta=$delta")
                sendMobileTelemetry(acceleration = delta, battery = 1.0f)
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "CYN Companion Background Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Persistent background telemetry and sensor stream for CYN"
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildForegroundNotification(statusText: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("PROJECT CYN // Absolute Solver Daemon")
            .setContentText(statusText)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateNotification(statusText: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, buildForegroundNotification(statusText))
    }

    private fun stopForegroundService() {
        isRunning = false
        try {
            sensorManager.unregisterListener(this)
            unregisterReceiver(batteryReceiver)
            wakeLock?.let { if (it.isHeld) it.release() }
            webSocket?.close(1000, "Service stopped")
            serviceScope.cancel()
        } catch (e: Exception) {
            Log.w(TAG, "Error cleaning up service: ${e.message}")
        }
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        stopForegroundService()
        super.onDestroy()
    }
}
