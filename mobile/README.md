# Turacoz Bid Tool Mobile

Flutter app for buyers, dealers, and administrators. See the [project README](../README.md) for backend and database setup.

## Run

For the Android emulator, use `10.0.2.2` to reach the API on the host computer:

```sh
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

For a physical device, pass the computer's LAN address, such as `http://192.168.1.20:8000`. Flutter web can use `http://localhost:8000` when served on the same computer.

## Release build

```sh
flutter build apk --release --dart-define=API_BASE_URL=http://10.0.2.2:8000
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
```

On Windows, Android plugin builds may require Developer Mode for symlink support.
