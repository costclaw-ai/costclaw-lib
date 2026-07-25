"""Synchronous CostClaw API client."""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO, Any, List, Optional, Union

import httpx

from ._version import __version__
from .errors import (
    APIError,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
)
from .models import Dispute, Document, Issue, Quote, QuoteInvoice, UploadResult

#: Default API base URL. Override with ``base_url=`` or ``COSTCLAW_BASE_URL``.
DEFAULT_BASE_URL = "https://api-46801476993.us-west1.run.app"

FileInput = Union[str, Path, bytes, IO[bytes]]


class CostClawClient:
    """Talk to the CostClaw API with an API key.

    Create a key in the app under **Settings → Developer → API keys**. The key's
    role decides what you can do: ``read_only`` reads, ``read_write`` also
    uploads, ``admin`` also deletes/clears. Every call runs against the single
    project the key is scoped to.

    Example::

        from costclaw import CostClawClient

        with CostClawClient("ck_...") as cc:
            cc.upload_document("invoice.pdf")
            for d in cc.list_disputes():
                print(d.id, d.state, d.disputed_amount, d.currency)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required (create one under Settings → Developer)")
        base = (base_url or os.environ.get("COSTCLAW_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.base_url = base
        self._http = httpx.Client(
            base_url=base,
            headers={
                "X-API-Key": api_key,
                "User-Agent": "costclaw-python/" + __version__,
            },
            timeout=timeout,
            transport=transport,
        )

    # -- lifecycle ----------------------------------------------------------

    def __enter__(self) -> CostClawClient:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def __repr__(self) -> str:
        return f"CostClawClient(base_url={self.base_url!r})"

    # -- plumbing -----------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        resp = self._http.request(method, path, **kwargs)
        if resp.status_code >= 400:
            detail: Optional[str]
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("error")
            except Exception:
                detail = resp.text or None
            code = resp.status_code
            if code == 401:
                raise AuthenticationError(code, detail)
            if code == 403:
                raise PermissionDeniedError(code, detail)
            if code == 404:
                raise NotFoundError(code, detail)
            raise APIError(code, detail)
        return resp

    # -- documents ----------------------------------------------------------

    def list_documents(self) -> List[Document]:
        """Every document in the project."""
        data = self._request("GET", "/v1/documents").json()
        return [Document.from_dict(d) for d in data]

    def get_document(self, document_id: str) -> Document:
        return Document.from_dict(self._request("GET", "/v1/documents/" + document_id).json())

    def upload_document(
        self, file: FileInput, *, filename: Optional[str] = None
    ) -> UploadResult:
        """Upload one PDF and start the audit pipeline.

        ``file`` may be a path (str/Path), raw ``bytes``, or an open binary
        file. Requires a ``read_write`` (or ``admin``) key. Re-uploading the
        same content returns ``status="duplicate"`` (dedup by content hash)."""
        name, data = _read_file(file, filename)
        files = {"files": (name, data, "application/pdf")}
        body = self._request("POST", "/v1/documents", files=files).json()
        results = body.get("results", [])
        if not results:
            raise APIError(500, "upload returned no result")
        return UploadResult.from_dict(results[0])

    def upload_documents(
        self, files: List[FileInput]
    ) -> List[UploadResult]:
        """Upload several PDFs in one request; one result per file."""
        multipart = []
        for f in files:
            name, data = _read_file(f, None)
            multipart.append(("files", (name, data, "application/pdf")))
        body = self._request("POST", "/v1/documents", files=multipart).json()
        return [UploadResult.from_dict(r) for r in body.get("results", [])]

    def download_document(
        self, document_id: str, dest: Optional[Union[str, Path]] = None
    ) -> bytes:
        """Return the original PDF bytes; also write them to ``dest`` if given."""
        content = self._request("GET", "/v1/documents/" + document_id + "/download").content
        if dest is not None:
            Path(dest).write_bytes(content)
        return content

    def delete_document(self, document_id: str) -> None:
        """Delete one document and its derived data (admin key)."""
        self._request("DELETE", "/v1/documents/" + document_id)

    def clear_documents(self) -> int:
        """Delete ALL documents in the project (admin key). Returns the count.

        Irreversible — this is the programmatic 'reset the project' button."""
        return int(self._request("POST", "/v1/documents/clear").json().get("cleared", 0))

    # -- reconciliation: quotes and their invoices --------------------------

    def list_quotes(self) -> List[Quote]:
        return [Quote.from_dict(q) for q in self._request("GET", "/v1/quotes").json()]

    def invoices_for_quote(self, quote_id: str) -> List[QuoteInvoice]:
        """Invoices billed against a quote, with dispute status."""
        data = self._request("GET", "/v1/quotes/" + quote_id + "/invoices").json()
        return [QuoteInvoice.from_dict(i) for i in data]

    # -- issues -------------------------------------------------------------

    def list_issues(self, status: str = "open") -> List[Issue]:
        """Invoices that couldn't be matched to a quote with high confidence.

        ``status``: ``open`` (default), ``resolved``, or ``dismissed``."""
        data = self._request("GET", "/v1/issues", params={"status": status}).json()
        return [Issue.from_dict(i) for i in data]

    # -- disputes -----------------------------------------------------------

    def list_disputes(self) -> List[Dispute]:
        return [Dispute.from_dict(d) for d in self._request("GET", "/v1/disputes").json()]

    def get_dispute(self, dispute_id: str) -> Dispute:
        """Full dispute detail (findings and the draft vendor email are on ``.raw``)."""
        return Dispute.from_dict(self._request("GET", "/v1/disputes/" + dispute_id).json())

    def download_dispute(
        self, dispute_id: str, dest: Optional[Union[str, Path]] = None
    ) -> bytes:
        """The dispute PDF (evidence table + draft vendor email). Writes to
        ``dest`` if given; always returns the bytes."""
        content = self._request("GET", "/v1/disputes/" + dispute_id + "/download").content
        if dest is not None:
            Path(dest).write_bytes(content)
        return content


def _read_file(file: FileInput, filename: Optional[str]):
    """Normalise a path / bytes / file-object into (filename, bytes)."""
    if isinstance(file, (str, Path)):
        path = Path(file)
        return filename or path.name, path.read_bytes()
    if isinstance(file, bytes):
        if not filename:
            raise ValueError("filename is required when uploading raw bytes")
        return filename, file
    # assume a binary file-like object
    data = file.read()
    name = filename or getattr(file, "name", None)
    if name:
        name = Path(str(name)).name
    else:
        raise ValueError("filename is required for this file object")
    return name, data
