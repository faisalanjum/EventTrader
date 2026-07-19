from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_daily_apis import redact_error_text


def test_redact_error_text_removes_known_secrets_and_query_credentials():
    secret = "not-real"
    message = (
        "failed https://example.test/data?apiKey=not-real"
        "&symbol=AAPL token=another-secret"
    )

    redacted = redact_error_text(message, [secret])

    assert secret not in redacted
    assert "another-secret" not in redacted
    assert "symbol=AAPL" in redacted
    assert redacted.count("[REDACTED]") == 2
