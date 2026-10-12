"""Reuse idle connections without sharing transactions between threads."""

from contextlib import suppress
from queue import Empty, Full, LifoQueue
from time import monotonic


class ConnectionCache:
    def __init__(self, connect, size=16, idle_seconds=120):
        self.connect = connect
        self.size = size
        self.idle_seconds = idle_seconds
        self.idle = LifoQueue(maxsize=max(size, 1))

    @staticmethod
    def discard(connection):
        with suppress(Exception):
            connection.close()

    def acquire(self):
        if self.size:
            while True:
                try:
                    released_at, connection = self.idle.get_nowait()
                except Empty:
                    break
                if monotonic() - released_at > self.idle_seconds:
                    self.discard(connection)
                    continue
                try:
                    # Never reconnect inside an existing transaction.
                    connection.ping(reconnect=False)
                except Exception:
                    self.discard(connection)
                    continue
                return connection
        # Nested repository reads must not wait on their own leased connection.
        return self.connect()

    def release(self, connection):
        if self.size:
            try:
                self.idle.put_nowait((monotonic(), connection))
                return
            except Full:
                pass
        self.discard(connection)

    def close(self):
        while True:
            try:
                _, connection = self.idle.get_nowait()
            except Empty:
                return
            self.discard(connection)
