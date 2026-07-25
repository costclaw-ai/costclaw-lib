"""Client tests against a mocked API (no network) via httpx.MockTransport."""

from __future__ import annotations

import httpx
import pytest

from costclaw import (
    AuthenticationError,
    CostClawClient,
    NotFoundError,
    PermissionDeniedError,
)


def make_client(handler) -> CostClawClient:
    return CostClawClient(
        "ck_test", base_url="https://api.test", transport=httpx.MockTransport(handler)
    )


def test_api_key_required():
    with pytest.raises(ValueError):
        CostClawClient("")


def test_sends_api_key_header():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["key"] = req.headers.get("x-api-key")
        seen["ua"] = req.headers.get("user-agent")
        return httpx.Response(200, json=[])

    make_client(handler).list_documents()
    assert seen["key"] == "ck_test"
    assert seen["ua"].startswith("costclaw-python/")


def test_list_documents_parses_models():
    def handler(req):
        assert req.url.path == "/v1/documents"
        return httpx.Response(
            200,
            json=[
                {"id": "d1", "kind": "invoice", "status": "classified",
                 "original_filename": "inv.pdf", "received_at": "2026-07-24T00:00:00Z"}
            ],
        )

    docs = make_client(handler).list_documents()
    assert len(docs) == 1
    assert docs[0].id == "d1" and docs[0].kind == "invoice"
    assert docs[0].raw["status"] == "classified"


def test_upload_document_multipart_and_result():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST" and req.url.path == "/v1/documents"
        assert b'name="files"' in req.content
        assert b"%PDF" in req.content
        return httpx.Response(
            202,
            json={"results": [{"filename": "a.pdf", "status": "accepted", "document_id": "d9"}]},
        )

    res = make_client(handler).upload_document(b"%PDF-1.4 ...", filename="a.pdf")
    assert res.accepted and res.document_id == "d9"


def test_upload_bytes_requires_filename():
    with pytest.raises(ValueError):
        make_client(lambda r: httpx.Response(202, json={"results": []})).upload_document(b"x")


def test_download_document_writes_dest(tmp_path):
    def handler(req):
        assert req.url.path == "/v1/documents/d1/download"
        return httpx.Response(200, content=b"%PDF-bytes")

    dest = tmp_path / "out.pdf"
    data = make_client(handler).download_document("d1", dest=dest)
    assert data == b"%PDF-bytes" and dest.read_bytes() == b"%PDF-bytes"


def test_clear_documents_returns_count():
    def handler(req):
        assert req.method == "POST" and req.url.path == "/v1/documents/clear"
        return httpx.Response(200, json={"cleared": 7})

    assert make_client(handler).clear_documents() == 7


def test_quote_invoices():
    def handler(req):
        assert req.url.path == "/v1/quotes/q1/invoices"
        return httpx.Response(200, json=[{"id": "i1", "invoice_number": "INV-9",
                                          "dispute_state": "open"}])

    invs = make_client(handler).invoices_for_quote("q1")
    assert invs[0].invoice_number == "INV-9"


def test_list_issues_passes_status():
    def handler(req):
        assert req.url.params.get("status") == "resolved"
        return httpx.Response(200, json=[])

    make_client(handler).list_issues(status="resolved")


def test_dispute_amount_helper():
    def handler(req):
        return httpx.Response(200, json=[{"id": "x", "state": "open",
                                          "disputed_minor_units": 5000, "currency": "USD"}])

    d = make_client(handler).list_disputes()[0]
    assert d.disputed_amount == 50.0 and d.currency == "USD"


@pytest.mark.parametrize(
    "code,exc",
    [(401, AuthenticationError), (403, PermissionDeniedError), (404, NotFoundError)],
)
def test_error_mapping(code, exc):
    def handler(req):
        return httpx.Response(code, json={"detail": "nope"})

    with pytest.raises(exc) as ei:
        make_client(handler).list_documents()
    assert ei.value.status_code == code and ei.value.detail == "nope"


def test_context_manager_closes():
    c = make_client(lambda r: httpx.Response(200, json=[]))
    with c as cc:
        cc.list_documents()
    assert c._http.is_closed
