import 'dart:html' as html;

const _key = 'turacoz_session';

Future<String?> readSessionValue() async => html.window.sessionStorage[_key];

Future<void> writeSessionValue(String value) async {
  html.window.sessionStorage[_key] = value;
}

Future<void> clearSessionValue() async {
  html.window.sessionStorage.remove(_key);
}
