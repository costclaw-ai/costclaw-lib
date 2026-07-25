"""Lightweight typed views over the API's JSON.

Each model exposes the common fields as attributes and keeps the full server
payload on ``.raw`` — so new API fields are always reachable even before this
library models them explicitly."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Document:
    id: str
    kind: Optional[str] = None  # quote | invoice | booking | unknown
    status: Optional[str] = None
    original_filename: Optional[str] = None
    received_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Document:
        return cls(
            id=str(d.get("id")),
            kind=d.get("kind"),
            status=d.get("status"),
            original_filename=d.get("original_filename"),
            received_at=d.get("received_at"),
            raw=d,
        )


@dataclass
class UploadResult:
    filename: Optional[str]
    status: str  # accepted | duplicate | rejected
    document_id: Optional[str] = None
    reason: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> UploadResult:
        return cls(
            filename=d.get("filename"),
            status=str(d.get("status")),
            document_id=d.get("document_id"),
            reason=d.get("reason"),
            raw=d,
        )


@dataclass
class Quote:
    id: str
    original_filename: Optional[str] = None
    vendor: Optional[str] = None
    quote_reference: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Quote:
        return cls(
            id=str(d.get("id")),
            original_filename=d.get("original_filename"),
            vendor=d.get("vendor"),
            quote_reference=d.get("quote_reference"),
            raw=d,
        )


@dataclass
class QuoteInvoice:
    id: str
    original_filename: Optional[str] = None
    status: Optional[str] = None
    invoice_number: Optional[str] = None
    dispute_id: Optional[str] = None
    dispute_state: Optional[str] = None
    disputed_minor_units: Optional[int] = None
    currency: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> QuoteInvoice:
        return cls(
            id=str(d.get("id")),
            original_filename=d.get("original_filename"),
            status=d.get("status"),
            invoice_number=d.get("invoice_number"),
            dispute_id=d.get("dispute_id"),
            dispute_state=d.get("dispute_state"),
            disputed_minor_units=d.get("disputed_minor_units"),
            currency=d.get("currency"),
            raw=d,
        )


@dataclass
class Issue:
    id: str
    kind: Optional[str] = None  # unmatched_invoice | low_confidence_match
    status: Optional[str] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None
    document_id: Optional[str] = None
    original_filename: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Issue:
        return cls(
            id=str(d.get("id")),
            kind=d.get("kind"),
            status=d.get("status"),
            reason=d.get("reason"),
            confidence=d.get("confidence"),
            document_id=d.get("document_id"),
            original_filename=d.get("original_filename"),
            raw=d,
        )


@dataclass
class Dispute:
    id: str
    state: Optional[str] = None
    disputed_minor_units: Optional[int] = None
    currency: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def disputed_amount(self) -> Optional[float]:
        """Disputed amount in major units (e.g. dollars), or None if unknown."""
        if self.disputed_minor_units is None:
            return None
        return self.disputed_minor_units / 100.0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Dispute:
        return cls(
            id=str(d.get("id")),
            state=d.get("state"),
            disputed_minor_units=d.get("disputed_minor_units"),
            currency=d.get("currency"),
            raw=d,
        )
