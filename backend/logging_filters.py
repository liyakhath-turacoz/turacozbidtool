"""Keep WebSocket access tokens out of HTTP/server logs."""

import logging
import re


class TokenQueryFilter(logging.Filter):
    def filter(self, record):
        def redact(value):
            if isinstance(value, str):
                return re.sub(r"([?&]token=)[^&\s\"']+", r"\1[redacted]", value)
            return value

        record.msg = redact(record.msg)
        # Preserve Uvicorn's argument tuple for its access-log formatter.
        if isinstance(record.args, tuple):
            record.args = tuple(redact(value) for value in record.args)
        elif isinstance(record.args, dict):
            record.args = {key: redact(value) for key, value in record.args.items()}
        return True


def install_token_filters():
    for name in ("uvicorn.access", "uvicorn.error", "turacozbidtool"):
        target = logging.getLogger(name)
        if not any(isinstance(existing, TokenQueryFilter) for existing in target.filters):
            target.addFilter(TokenQueryFilter())
