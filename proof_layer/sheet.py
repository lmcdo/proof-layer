"""One-glance check sheet: a picture of the PDF page, number highlighted, for each figure that needs a look.

proof-layer report.pdf results.json --sheet check.html   (needs PyMuPDF: pip install "proof-layer[pdf]")
"""
from __future__ import annotations

import base64
import html


def _forms(value) -> list[str]:
    """How the number may be printed: 1,196 / 1196 / 5.1 ..."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return []
    forms = []
    f = abs(f)          # a loss is printed as (4,153) or with a dash, so look for the digits alone
    if f.is_integer():
        forms += [f"{int(f):,}", str(int(f))]
    forms += [f"{f:g}", str(abs(float(value))).rstrip('0').rstrip('.')]
    return list(dict.fromkeys(forms))


def _picture(pdf_path: str, page_no: int, value):
    """PNG (base64) of the band of the page around the number, number highlighted; None if not found."""
    import fitz
    with fitz.open(pdf_path) as pdf:
        if not 1 <= page_no <= len(pdf):
            return None
        page = pdf[page_no - 1]
        for form in _forms(value):
            hits = page.search_for(form)
            if hits:
                r = hits[0]
                page.add_highlight_annot(r)
                box = fitz.Rect(page.rect.x0, max(page.rect.y0, r.y0 - 70), page.rect.x1,
                                min(page.rect.y1, r.y1 + 70))
                return base64.b64encode(page.get_pixmap(clip=box, dpi=110).tobytes("png")).decode()
        return None


def write_sheet(pdf_path: str, items: list[dict], out_path: str) -> int:
    """items: dicts with word, name, value, shown, why, page. Returns how many cards were written."""
    cards = []
    for it in items:
        img = _picture(pdf_path, it["page"], it["value"]) if it.get("page") else None
        pic = (f'<img src="data:image/png;base64,{img}" alt="page {it["page"]}">' if img else
               '<p class="none">The number was not found on a page to show.</p>')
        where = f"page {it['page']}" if it.get("page") else "no page"
        cards.append(f'<section class="{it["word"].lower()}"><h2><b>{it["word"]}</b> '
                     f'{html.escape(str(it["name"]))} = {html.escape(str(it["shown"]))}</h2>'
                     f'<p>{html.escape(it["why"])} ({where})</p>{pic}</section>')
    doc = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           "<title>proof-layer check sheet</title><style>body{font:16px system-ui;max-width:900px;margin:auto;padding:16px}"
           "section{border:1px solid #8884;border-radius:8px;padding:8px 14px;margin:14px 0}"
           "section.wrong{border-color:#d33}section.check{border-color:#c90}img{max-width:100%}"
           "h2{font-size:1.05em}.none{color:#888}</style>"
           f"<h1>{len(cards)} figures to look at</h1><p>Each picture is the page, with the number highlighted.</p>"
           + "".join(cards))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return len(cards)
