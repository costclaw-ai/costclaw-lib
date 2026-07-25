# costclaw — Python client for CostClaw

[![PyPI](https://img.shields.io/pypi/v/costclaw.svg)](https://pypi.org/project/costclaw/)
[![Python versions](https://img.shields.io/pypi/pyversions/costclaw.svg)](https://pypi.org/project/costclaw/)
[![License: MIT](https://img.shields.io/pypi/l/costclaw.svg)](./LICENSE)

Official Python client for the [CostClaw](https://costclaw.ai) freight-invoice
audit API. Upload quotes and invoices, and CostClaw converts them, matches
invoice ↔ booking ↔ quote, flags overcharges, and drafts disputes — this library
lets you drive all of it from Python with an API key.

The API is the **only** thing this library touches: your data stays in your
CostClaw project, reached with a per-project API key. Nothing about the
CostClaw internals is required or exposed.

## Install

```bash
pip install costclaw
```

Requires Python 3.9+. The only dependency is [`httpx`](https://www.python-httpx.org/).

## Authenticate

Create an API key in the app under **Settings → Developer → API keys**. The
key's **role** decides what it can do:

| Role | Can |
|------|-----|
| `read_only` | list/read documents, issues, disputes; download PDFs |
| `read_write` | the above **+ upload** documents |
| `admin` | the above **+ delete / clear** documents |

Keep keys out of source — read them from the environment:

```python
import os
from costclaw import CostClawClient

client = CostClawClient(os.environ["COSTCLAW_API_KEY"])
```

By default the client talks to the CostClaw staging API. Point it elsewhere with
`base_url=` or the `COSTCLAW_BASE_URL` environment variable:

```python
client = CostClawClient(api_key, base_url="https://api.costclaw.ai")
```

## Quick start

```python
from costclaw import CostClawClient

with CostClawClient("ck_...") as cc:
    # upload a PDF — kicks off classify → extract → match → audit
    result = cc.upload_document("invoice-4471.pdf")
    print(result.status)          # "accepted" | "duplicate" | "rejected"

    # what's in the project?
    for doc in cc.list_documents():
        print(doc.kind, doc.status, doc.original_filename)

    # invoices we couldn't confidently match to a quote yet
    for issue in cc.list_issues():
        print(issue.original_filename, "→", issue.reason)

    # overcharges we found, with the disputed amount
    for d in cc.list_disputes():
        print(d.id, d.state, d.disputed_amount, d.currency)
        cc.download_dispute(d.id, dest=f"dispute-{d.id[:8]}.pdf")
```

`with ...` closes the underlying HTTP connection for you; without it, call
`client.close()` when done.

## API reference

Every call runs against the single project your API key is scoped to.

### Documents

```python
cc.list_documents() -> list[Document]
cc.get_document(document_id) -> Document
cc.upload_document(file, *, filename=None) -> UploadResult      # read_write
cc.upload_documents([file, ...]) -> list[UploadResult]          # read_write
cc.download_document(document_id, dest=None) -> bytes
cc.delete_document(document_id) -> None                          # admin
cc.clear_documents() -> int                                      # admin, returns count
```

`file` may be a path (`str`/`Path`), raw `bytes` (pass `filename=`), or an open
binary file. Re-uploading identical content returns `status="duplicate"`
(dedup by content hash), so retries are safe.

### Reconciliation

```python
cc.list_quotes() -> list[Quote]
cc.invoices_for_quote(quote_id) -> list[QuoteInvoice]   # invoices billed against a quote
```

### Issues

```python
cc.list_issues(status="open") -> list[Issue]            # "open" | "resolved" | "dismissed"
```

An **Issue** is an invoice that couldn't be matched to a quote with high
confidence — usually because the quote hasn't been uploaded yet, or the match
needs a human to confirm.

### Disputes

```python
cc.list_disputes() -> list[Dispute]
cc.get_dispute(dispute_id) -> Dispute
cc.download_dispute(dispute_id, dest=None) -> bytes     # PDF: evidence + draft email
```

`Dispute.disputed_amount` gives the amount in major units (e.g. dollars);
`Dispute.disputed_minor_units` is the exact integer (cents). Full server detail —
findings and the draft vendor email — is always on `.raw`.

## Models

Each model exposes common fields as attributes and keeps the full JSON payload
on `.raw`, so new API fields are reachable even before this library names them:

```python
doc = cc.list_documents()[0]
doc.kind, doc.status, doc.original_filename   # typed attributes
doc.raw                                        # the complete server dict
```

## Errors

All errors derive from `CostClawError`. HTTP failures raise a subclass with
`.status_code` and `.detail`:

```python
from costclaw import AuthenticationError, PermissionDeniedError, NotFoundError, APIError

try:
    cc.clear_documents()
except PermissionDeniedError:
    print("this key isn't an admin key")
except AuthenticationError:
    print("bad or revoked API key")
```

| Exception | HTTP |
|-----------|------|
| `AuthenticationError` | 401 |
| `PermissionDeniedError` | 403 |
| `NotFoundError` | 404 |
| `APIError` | other 4xx/5xx |

## Examples

Runnable scripts in [`examples/`](./examples):

- [`quickstart.py`](./examples/quickstart.py) — upload a file and print documents/issues/disputes.
- [`audit_folder.py`](./examples/audit_folder.py) — upload a whole folder and save every dispute PDF.

## Prefer an AI agent?

CostClaw also exposes these same actions over the **Model Context Protocol** —
add the MCP server to Claude Code or Cursor and drive uploads/audits in plain
language. See the Developer tab in the app.

## License

MIT — see [LICENSE](./LICENSE).
