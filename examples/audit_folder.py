"""Batch-audit a folder of PDFs and download any dispute paperwork.

Uploads every PDF in a directory, waits for the pipeline to settle, then saves
each dispute's PDF (evidence + a draft vendor email) into ./disputes/.

    export COSTCLAW_API_KEY=ck_...
    python examples/audit_folder.py ./freight-october
"""

import os
import sys
import time
from pathlib import Path

from costclaw import CostClawClient


def main() -> None:
    api_key = os.environ.get("COSTCLAW_API_KEY")
    if not api_key:
        sys.exit("set COSTCLAW_API_KEY")
    if len(sys.argv) < 2:
        sys.exit("usage: python examples/audit_folder.py <folder>")

    folder = Path(sys.argv[1])
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"no PDFs in {folder}")

    out = Path("disputes")
    out.mkdir(exist_ok=True)

    with CostClawClient(api_key) as cc:
        print(f"Uploading {len(pdfs)} file(s)…")
        for res in cc.upload_documents(list(pdfs)):
            print(f"  {res.filename}: {res.status}")

        # The audit runs asynchronously; poll disputes for a short while.
        print("Waiting for the audit to run…")
        seen: set = set()
        for _ in range(12):  # ~1 minute
            for disp in cc.list_disputes():
                if disp.id in seen:
                    continue
                seen.add(disp.id)
                dest = out / f"dispute-{disp.id[:8]}.pdf"
                cc.download_dispute(disp.id, dest=dest)
                amt = disp.disputed_amount
                print(f"  dispute {disp.id[:8]}  {amt} {disp.currency or ''}  → {dest}")
            time.sleep(5)

        if not seen:
            print("No disputes yet — check `list_issues()` for invoices awaiting a quote.")


if __name__ == "__main__":
    main()
