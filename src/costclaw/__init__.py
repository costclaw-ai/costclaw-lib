"""CostClaw — Python client for the freight-invoice audit API.

    from costclaw import CostClawClient

    with CostClawClient("ck_...") as cc:
        cc.upload_document("invoice.pdf")
        for d in cc.list_disputes():
            print(d.id, d.state, d.disputed_amount, d.currency)
"""

from __future__ import annotations

from ._version import __version__
from .client import DEFAULT_BASE_URL, CostClawClient
from .errors import (
    APIError,
    AuthenticationError,
    CostClawError,
    NotFoundError,
    PermissionDeniedError,
)
from .models import Dispute, Document, Issue, Quote, QuoteInvoice, UploadResult

__all__ = [
    "CostClawClient",
    "DEFAULT_BASE_URL",
    "CostClawError",
    "APIError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "Document",
    "UploadResult",
    "Quote",
    "QuoteInvoice",
    "Issue",
    "Dispute",
    "__version__",
]
