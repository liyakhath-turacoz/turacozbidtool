String? _sessionValue;

Future<String?> readSessionValue() async => _sessionValue;

Future<void> writeSessionValue(String value) async {
  _sessionValue = value;
}

Future<void> clearSessionValue() async {
  _sessionValue = null;
}
