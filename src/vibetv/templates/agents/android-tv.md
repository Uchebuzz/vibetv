
## This project: Android TV / Google TV / Fire TV app

- **The UI is the web app in `web/`.** That's where nearly all changes go. The Kotlin in `app/` is a thin
  full-screen WebView shell; only touch it for native features.
- Live reload on the TV (fastest loop):
  1. `vibetv deploy` once to install the shell app (or install the APK built by GitHub Actions: `vibetv install app-debug.apk`).
  2. `vibetv serve --open`: the app on the TV now loads `web/` from this machine and reloads on every save.
- Native bridge (Android only, `TV.native` is `null` elsewhere, so always guard):
  `TV.native.apps()` → `[{package, label, banner}]`, `TV.native.launch(pkg)`, `TV.native.openSettings()`, `TV.native.exit()`.
  Add new bridge methods in `app/src/main/java/.../NativeBridge.kt` with `@JavascriptInterface`.
- **Custom launcher:** uncomment the HOME intent-filter in `AndroidManifest.xml`, redeploy, then
  `vibetv launcher set {{APP_ID}}`. Undo: `vibetv tweak revert custom-launcher`.
- **Custom screensaver:** `WebDreamService` renders `web/index.html?screensaver=1`. Activate with
  `vibetv screensaver set {{APP_ID}}/.WebDreamService`. Detect it in JS via `TV.params.has('screensaver')`.
- Remote debugging: `chrome://inspect` on your laptop shows the TV's WebView (WebContents debugging is on).
- Building needs JDK 17 + Android SDK + Gradle 8.9+ locally (`gradle wrapper` once to create `./gradlew`).
  No SDK? Push to GitHub: `.github/workflows/build-apk.yml` builds the APK as a downloadable artifact.
- Package name / app id: `{{APP_ID}}`.
