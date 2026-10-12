import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from backend.connection_cache import ConnectionCache


class Connection:
    def __init__(self):
        self.closed = False
        self.broken = False
        self.pings = []

    def ping(self, reconnect):
        self.pings.append(reconnect)
        if self.broken:
            raise OSError('Disconnected')

    def close(self):
        self.closed = True


class ConnectionCacheTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def connect(self):
        connection = Connection()
        self.created.append(connection)
        return connection

    def test_reuses_only_released_connection(self):
        cache = ConnectionCache(self.connect)
        first = cache.acquire()
        second = cache.acquire()
        self.assertIsNot(first, second)
        cache.release(first)
        self.assertIs(cache.acquire(), first)
        self.assertEqual(first.pings, [False])

    def test_nested_checkout_does_not_wait_on_a_lease(self):
        cache = ConnectionCache(self.connect, size=1)
        first, second = cache.acquire(), cache.acquire()
        cache.release(first)
        cache.release(second)
        self.assertFalse(first.closed)
        self.assertTrue(second.closed)

    def test_broken_idle_connection_is_replaced(self):
        cache = ConnectionCache(self.connect)
        first = cache.acquire()
        first.broken = True
        cache.release(first)
        self.assertIsNot(cache.acquire(), first)
        self.assertTrue(first.closed)

    def test_expired_idle_connection_is_closed(self):
        cache = ConnectionCache(self.connect, idle_seconds=10)
        first = cache.acquire()
        with patch('backend.connection_cache.monotonic', return_value=100):
            cache.release(first)
        with patch('backend.connection_cache.monotonic', return_value=111):
            self.assertIsNot(cache.acquire(), first)
        self.assertTrue(first.closed)

    def test_disabled_cache_closes_released_connections(self):
        cache = ConnectionCache(self.connect, size=0)
        first = cache.acquire()
        cache.release(first)
        self.assertTrue(first.closed)
        self.assertIsNot(cache.acquire(), first)

    def test_close_does_not_close_borrowed_connections(self):
        cache = ConnectionCache(self.connect)
        leased = cache.acquire()
        idle = cache.acquire()
        cache.release(idle)
        cache.close()
        self.assertTrue(idle.closed)
        self.assertFalse(leased.closed)
        cache.release(leased)
        cache.close()
        self.assertTrue(leased.closed)

    def test_threads_never_share_a_leased_connection(self):
        cache = ConnectionCache(self.connect, size=2)
        barrier = Barrier(8)
        def borrow(_):
            connection = cache.acquire()
            barrier.wait(timeout=5)
            cache.release(connection)
            return connection
        with ThreadPoolExecutor(max_workers=8) as workers:
            connections = list(workers.map(borrow, range(8)))
        self.assertEqual(len({id(connection) for connection in connections}), 8)
        self.assertEqual(sum(connection.closed for connection in connections), 6)
        cache.close()


class TransactionTests(unittest.TestCase):
    def setUp(self):
        from backend import main
        self.main = main
        self.connection = Connection()
        self.connection.commit = unittest.mock.Mock()
        self.connection.rollback = unittest.mock.Mock()
        self.cache = ConnectionCache(lambda: self.connection)
        self.patcher = patch.object(main, 'connection_cache', self.cache)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.cache.close)

    def test_success_commits_before_reuse(self):
        with self.main.db():
            pass
        self.connection.commit.assert_called_once()
        self.assertIs(self.cache.acquire(), self.connection)

    def test_failed_operation_rolls_back(self):
        with self.assertRaises(ValueError):
            with self.main.db():
                raise ValueError('Invalid profile')
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_rollback_failure_discards_connection(self):
        self.connection.rollback.side_effect = OSError('Disconnected')
        with self.assertRaises(ValueError):
            with self.main.db():
                raise ValueError('Original failure')
        self.assertTrue(self.connection.closed)

    def test_interrupt_rolls_back(self):
        with self.assertRaises(KeyboardInterrupt):
            with self.main.db():
                raise KeyboardInterrupt()
        self.connection.rollback.assert_called_once()

    def test_transport_failure_is_not_retried_as_a_write(self):
        import pymysql
        self.connection.commit.side_effect = pymysql.err.OperationalError(2013, 'Lost connection')
        with self.assertRaises(pymysql.err.OperationalError):
            with self.main.db():
                pass
        self.connection.commit.assert_called_once()
        self.assertTrue(self.connection.closed)


if __name__ == '__main__':
    unittest.main()
