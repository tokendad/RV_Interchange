"""Provider-neutral transactional mail boundary for submission intake."""

from dataclasses import dataclass
from typing import Any, Protocol


class TemporaryMailError(RuntimeError):
    """A provider failure that may succeed after bounded backoff."""


class PermanentMailError(RuntimeError):
    """A provider failure that must not be retried automatically."""


@dataclass(frozen=True)
class TransactionalMessage:
    """Decrypted message data passed to a future authorized provider adapter."""

    message_id: str
    recipient: str
    template: str
    template_data: dict[str, Any]
    submission_id: str | None


class TransactionalMailer(Protocol):
    """The narrow delivery seam implemented by a future mail provider."""

    def send(self, message: TransactionalMessage) -> str | None:
        """Deliver one message and return an optional provider reference."""

