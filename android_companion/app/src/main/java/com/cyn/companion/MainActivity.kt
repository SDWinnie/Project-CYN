package com.cyn.companion

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var etHostIp: EditText
    private lateinit var btnToggleService: Button
    private lateinit var tvStatus: TextView
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        prefs = getSharedPreferences("cyn_companion_prefs", Context.MODE_PRIVATE)

        webView = findViewById(R.id.webViewAvatar)
        etHostIp = findViewById(R.id.etHostIp)
        btnToggleService = findViewById(R.id.btnToggleService)
        tvStatus = findViewById(R.id.tvServiceStatus)

        val savedIp = prefs.getString("host_ip", "192.168.1.50") ?: "192.168.1.50"
        etHostIp.setText(savedIp)

        setupWebView()
        requestAppPermissions()

        btnToggleService.setOnClickListener {
            toggleService()
        }

        findViewById<Button>(R.id.btnReloadAvatar).setOnClickListener {
            val ip = etHostIp.text.toString().trim()
            prefs.edit().putString("host_ip", ip).apply()
            loadAvatarUrl(ip)
        }

        updateServiceUi()
        loadAvatarUrl(savedIp)
    }

    private fun setupWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = true
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            setRenderPriority(WebSettings.RenderPriority.HIGH)
        }
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null)
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                tvStatus.text = "Avatar 3D Stream Synchronized"
            }
        }
    }

    private fun loadAvatarUrl(ip: String) {
        val url = if (ip.startsWith("http://") || ip.startsWith("https://")) ip else "http://$ip:8080"
        tvStatus.text = "Loading Avatar from $url..."
        webView.loadUrl(url)
    }

    private fun toggleService() {
        val ip = etHostIp.text.toString().trim()
        prefs.edit().putString("host_ip", ip).apply()

        val serviceIntent = Intent(this, CynForegroundService::class.java)

        if (CynForegroundService.isRunning) {
            serviceIntent.action = CynForegroundService.ACTION_STOP
            startService(serviceIntent)
            Toast.makeText(this, "Stopping CYN Daemon...", Toast.LENGTH_SHORT).show()
        } else {
            val wsUrl = "ws://$ip:8080/ws/cyn"
            serviceIntent.action = CynForegroundService.ACTION_START
            serviceIntent.putExtra(CynForegroundService.EXTRA_HOST_URL, wsUrl)

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ContextCompat.startForegroundService(this, serviceIntent)
            } else {
                startService(serviceIntent)
            }
            Toast.makeText(this, "CYN Foreground Service Started!", Toast.LENGTH_SHORT).show()
        }

        webView.postDelayed({ updateServiceUi() }, 500)
    }

    private fun updateServiceUi() {
        if (CynForegroundService.isRunning) {
            btnToggleService.text = "STOP DAEMON SERVICE"
            btnToggleService.setBackgroundColor(0xFF882222.toInt())
            tvStatus.text = "Daemon: RUNNING (Sensors Streaming)"
        } else {
            btnToggleService.text = "START DAEMON SERVICE"
            btnToggleService.setBackgroundColor(0xFFFFCC00.toInt())
            tvStatus.text = "Daemon: STANDBY / DORMANT"
        }
    }

    private fun requestAppPermissions() {
        val perms = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                perms.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        if (perms.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, perms.toTypedArray(), 101)
        }
    }
}
