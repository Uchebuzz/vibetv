package {{APP_ID}}

import android.annotation.SuppressLint
import android.service.dreams.DreamService
import android.webkit.WebView
import android.webkit.WebViewClient

/** Screensaver (Daydream) that shows the web app with ?screensaver=1. */
class WebDreamService : DreamService() {
    private var webView: WebView? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        isInteractive = false
        isFullscreen = true
        isScreenBright = false
        val view = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            setBackgroundColor(0xFF000000.toInt())
            webViewClient = WebViewClient()
            loadUrl(MainActivity.ASSET_URL + "?screensaver=1")
        }
        webView = view
        setContentView(view)
    }

    override fun onDetachedFromWindow() {
        webView?.destroy()
        webView = null
        super.onDetachedFromWindow()
    }
}
