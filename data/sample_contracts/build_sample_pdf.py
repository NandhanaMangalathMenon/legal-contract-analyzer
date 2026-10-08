from __future__ import annotations

import string
import textwrap
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
TEXT = (ROOT / "sample_contract.txt").read_text(encoding="utf-8")


def build() -> Path:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    valid_chars = set(string.printable)
    for line in TEXT.splitlines():
        cleaned = "".join(c for c in line if c in valid_chars).strip()
        if not cleaned:
            pdf.multi_cell(0, 6, " ")
            continue
        for wrapped in textwrap.wrap(cleaned, width=80):
            pdf.cell(0, 6, text=wrapped, new_x="LMARGIN", new_y="NEXT")
    out = ROOT / "sample_contract.pdf"
    pdf.output(str(out))
    return out


if __name__ == "__main__":
    print(build())
