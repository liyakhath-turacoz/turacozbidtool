import 'session_store_stub.dart'
    if (dart.library.html) 'session_store_web.dart';

Future<String?> readSavedSession() => readSessionValue();

Future<void> saveSession(String value) => writeSessionValue(value);

Future<void> clearSession() => clearSessionValue();
