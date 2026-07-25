"""Quickstart: upload a PDF, then list what CostClaw found.

    export COSTCLAW_API_KEY=ck_...
    python examples/quickstart.py path/to/invoice.pdf
"""

import os
import sys

from costclaw import CostClawClient


def main() -> None:
    api_key = os.environ.get("COSTCLAW_API_KEY")
    if not api_key:
        sys.exit("set COSTCLAW_API_KEY (create one under Settings → Developer → API keys)")
    path = sys.argv[1] if len(sys.argv) > 1 else None

    with CostClawClient(api_key) as cc:
        if path:
            r = cc.upload_document(path)
            print(f"uploaded {r.filename}: {r.status} ({r.document_id or r.reason})")

        print("\nDocuments:")
        for d in cc.list_documents():
            print(f"  {d.kind or '?':8}  {d.status or '':12}  {d.original_filename}")

        print("\nIssues (invoices with no confident quote match):")
        for i in cc.list_issues():
            print(f"  {i.original_filename}: {i.reason}")

        print("\nDisputes:")
        for disp in cc.list_disputes():
            amt = disp.disputed_amount
            print(f"  {disp.id[:8]}  {disp.state}  {amt} {disp.currency or ''}")


if __name__ == "__main__":
    main()
