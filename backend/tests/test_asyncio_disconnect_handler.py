from types import SimpleNamespace

from backend.main import make_asyncio_exception_handler


class WindowsConnectionReset(ConnectionResetError):
    @property
    def winerror(self):
        return 10054


def test_ignores_only_windows_transport_cleanup_peer_reset():
    delegated = []

    def previous(loop, context):
        delegated.append(context)

    def _call_connection_lost():
        pass

    context = {
        "message": "Exception in callback ProactorBasePipeTransport._call_connection_lost(None)",
        "exception": WindowsConnectionReset("connection reset by peer"),
        "handle": SimpleNamespace(_callback=_call_connection_lost),
    }

    make_asyncio_exception_handler(previous, platform_name="nt")(None, context)

    assert delegated == []


def test_delegates_other_errors_to_previous_handler():
    delegated = []

    def previous(loop, context):
        delegated.append(context)

    context = {"message": "application callback failed", "exception": RuntimeError("failure")}
    make_asyncio_exception_handler(previous, platform_name="nt")(None, context)

    assert delegated == [context]


def test_does_not_suppress_peer_reset_outside_windows():
    delegated = []

    def previous(loop, context):
        delegated.append(context)

    def _call_connection_lost():
        pass

    context = {
        "message": "Exception in callback _call_connection_lost",
        "exception": WindowsConnectionReset("connection reset by peer"),
        "handle": SimpleNamespace(_callback=_call_connection_lost),
    }
    make_asyncio_exception_handler(previous, platform_name="posix")(None, context)

    assert delegated == [context]
