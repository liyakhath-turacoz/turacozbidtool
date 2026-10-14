import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend import main


class FakeCursor:
    def __init__(self):
        self.queries = []
        self._one = None
        self._all = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        normalized = " ".join(query.split()).lower()
        self.queries.append((normalized, params or []))
        if "select b.id, b.dealer_id, br.id as request_id" in normalized:
            self._one = {
                "id": "bid-id",
                "dealer_id": "dealer-id",
                "request_id": "request-id",
                "buyer_id": "buyer-id",
                "product": "Example product",
            }
        elif "select id, description from reports" in normalized:
            self._one = None
        elif "from users u" in normalized and "r.name='admin'" in normalized:
            self._all = []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self.fake_cursor


class ReportFlowTests(unittest.TestCase):
    def setUp(self):
        self.connection = FakeConnection()
        self.database = patch("backend.main.db", return_value=self.connection)
        self.database.start()
        self.addCleanup(self.database.stop)

    def test_buyer_report_is_linked_to_the_winning_dealer(self):
        report_id = main.ReportRepository().create_report(
            "buyer-id", main.ReportIn(bid_id="bid-id", reason="Quality concern")
        )
        report_insert = next(params for query, params in self.connection.fake_cursor.queries
                             if query.startswith("insert into reports "))
        self.assertTrue(report_id)
        self.assertEqual(report_insert[1:5], ["buyer-id", "dealer-id", "bid-id", "Quality concern"])

    def test_dealer_report_is_linked_to_the_buyer(self):
        main.ReportRepository().create_report(
            "dealer-id", main.ReportIn(bid_id="bid-id", reason="Payment issue")
        )
        report_insert = next(params for query, params in self.connection.fake_cursor.queries
                             if query.startswith("insert into reports "))
        self.assertEqual(report_insert[1:5], ["dealer-id", "buyer-id", "bid-id", "Payment issue"])

    def test_unrelated_account_cannot_report_the_bid(self):
        with self.assertRaises(HTTPException) as error:
            main.ReportRepository().create_report(
                "other-user", main.ReportIn(bid_id="bid-id", reason="Other")
            )
        self.assertEqual(error.exception.status_code, 403)
        self.assertFalse(any(query.startswith("insert into reports ")
                             for query, _ in self.connection.fake_cursor.queries))


if __name__ == "__main__":
    unittest.main()
