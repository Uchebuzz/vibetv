package {{APP_ID}}

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import android.provider.Settings
import android.util.Base64
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream

/** Exposed to JavaScript as `window.VibeTVNative` (wrapped as `TV.native` by tv.js). */
class NativeBridge(private val activity: Activity) {

    /** JSON array of launchable apps: [{package, label, banner?}] sorted by label. */
    @JavascriptInterface
    fun apps(): String {
        val pm = activity.packageManager
        val seen = mutableSetOf<String>()
        val result = mutableListOf<JSONObject>()
        for (category in listOf(Intent.CATEGORY_LEANBACK_LAUNCHER, Intent.CATEGORY_LAUNCHER)) {
            val query = Intent(Intent.ACTION_MAIN).addCategory(category)
            for (info in pm.queryIntentActivities(query, 0)) {
                val pkg = info.activityInfo.packageName
                if (pkg == activity.packageName || !seen.add(pkg)) continue
                val app = JSONObject()
                    .put("package", pkg)
                    .put("label", info.loadLabel(pm).toString())
                val banner = info.activityInfo.loadBanner(pm)
                    ?: info.activityInfo.applicationInfo.loadBanner(pm)
                if (banner != null) app.put("banner", toDataUrl(banner))
                result.add(app)
            }
        }
        result.sortBy { it.getString("label").lowercase() }
        return JSONArray(result).toString()
    }

    @JavascriptInterface
    fun launch(pkg: String): Boolean {
        val pm = activity.packageManager
        val intent = pm.getLeanbackLaunchIntentForPackage(pkg) ?: pm.getLaunchIntentForPackage(pkg) ?: return false
        activity.runOnUiThread { activity.startActivity(intent) }
        return true
    }

    @JavascriptInterface
    fun openSettings() {
        activity.runOnUiThread { activity.startActivity(Intent(Settings.ACTION_SETTINGS)) }
    }

    @JavascriptInterface
    fun exit() {
        activity.runOnUiThread { activity.finish() }
    }

    private fun toDataUrl(drawable: Drawable): String {
        val w = drawable.intrinsicWidth.takeIf { it > 0 } ?: 320
        val h = drawable.intrinsicHeight.takeIf { it > 0 } ?: 180
        val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, w, h)
        drawable.draw(canvas)
        val out = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
        bitmap.recycle()
        return "data:image/png;base64," + Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
    }
}
