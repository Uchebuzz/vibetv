package {{APP_ID}}

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient

/**
 * A full-screen WebView that runs the web app in ../web.
 *
 * During development `vibetv serve --open` relaunches this activity with
 * `--es url http://<your-laptop>:8765/` so edits live-reload on the TV.
 */
class MainActivity : Activity() {
    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WebView.setWebContentsDebuggingEnabled(true) // chrome://inspect from your laptop
        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.mediaPlaybackRequiresUserGesture = false
            settings.loadWithOverviewMode = true
            settings.useWideViewPort = true
            setBackgroundColor(0xFF000000.toInt())
            isFocusable = true
            isFocusableInTouchMode = true
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()
            addJavascriptInterface(NativeBridge(this@MainActivity), "VibeTVNative")
        }
        setContentView(webView)
        webView.requestFocus(View.FOCUS_DOWN)
        load(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        load(intent)
    }

    private fun load(intent: Intent?) {
        val url = intent?.getStringExtra("url")
        webView.loadUrl(if (url.isNullOrBlank()) ASSET_URL else url)
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            // Let the web app handle Back first (close a menu, leave the screensaver, ...).
            webView.evaluateJavascript("(window.TV && window.TV.back()) === true") { handled ->
                if (handled != "true") finish()
            }
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }

    companion object {
        const val ASSET_URL = "file:///android_asset/index.html"
    }
}
