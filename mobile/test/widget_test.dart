// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import 'package:turacozbidtool/main.dart';

void main() {
  testWidgets('Turacoz Bid Tool launches unified login', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const TuracozBidToolApp());

    expect(find.text('Turacoz Bid Tool Login'), findsOneWidget);
    expect(find.text('Username'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('Admin'), findsNothing);
    expect(find.text('Buyer'), findsNothing);
    expect(find.text('Dealer'), findsNothing);
  });

  testWidgets('Failed backend login stays on real login screen', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const TuracozBidToolApp());
    await tester.enterText(find.byType(EditableText).at(0), 'buyer1');
    await tester.enterText(find.byType(EditableText).at(1), 'buyer1');
    await tester.pump();
    await tester.tap(find.text('Sign in'));
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(seconds: 1));
    });
    await tester.pump();

    expect(find.text('Turacoz Bid Tool Login'), findsOneWidget);
    expect(find.textContaining('Login failed'), findsOneWidget);
  });
}
