# Turacoz Bid Tool Mobile

Flutter app for buyers, dealers, and admin users. See the [project README](../README.md) for backend and database setup.

For Android Emulator, use `10.0.2.2` to reach the API on the host computer:

```sh
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

For a physical device, pass the computer's LAN address, such as `http://192.168.1.20:8000`. Flutter web can use `http://localhost:8000` when served on the same computer.

Export actions download a CSV in Flutter web. On native mobile they copy the CSV contents to the clipboard.

Location search uses the shared API geocoder. **Use my location** requests browser/device permission; Android declares coarse/fine location permissions. Radius coverage is drawn in meters from the shop pin. Flutter web keeps logins per tab. Native session storage remains local to the app installation.

WebSocket request snapshots update competing offers and open offer dialogs directly. Finalized requests show the winning price and terms to participants; only the buyer and winner receive contacts and private bid chat. New awards charge no commission. Either participant can report the other, and admin can inspect the linked conversation. Duration limits are under **Platform Rules & Settings**.

On Windows, plugin builds need Developer Mode/symlink support. The current source passes Dart type analysis with existing lint warnings; native Android execution and a rebuilt APK have not been verified for these changes.

The release Flutter web build passed browser checks for separate accounts, live competing offers, dashboard counts, open dialogs, immediate winning contacts and private chat in both directions. See [MOBILE_WEB_E2E_RESULTS.md](../MOBILE_WEB_E2E_RESULTS.md). Run `python backend\scripts\e2e_bidding.py --suite mobile` from the project root while the API and release web build on port 5180 are running.

Build an APK:

```sh
flutter build apk --release --dart-define=API_BASE_URL=http://10.0.2.2:8000
```
