"""Assemble the assignment report.

Run twice: the first pass produces the document, the PDF render tells us which
page each section landed on, and the second pass writes those numbers into the
table of contents.

    python build.py                 # pass 1, placeholder page numbers
    python build.py --pages pages.json
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import content_a
import content_b
import content_c
from docbuild import add_header_footer, add_page_border, new_document

OUT = pathlib.Path(__file__).resolve().parents[2] / "SmartCare_Software_Engineering_Report.docx"

SECTIONS = [
    ("s1", content_a.section1),
    ("s2", content_a.section2),
    ("s3", content_a.section3),
    ("s4", content_a.section4),
    ("s5", content_b.section5),
    ("s6", content_b.section6),
    ("s7", content_b.section7),
    ("s8", content_b.section8),
    ("s9", content_c.section9),
    ("s10", content_c.section10),
    ("s11", content_c.section11),
    ("s12", content_c.section12),
    ("s13", content_c.section13),
    ("s14", content_c.section14),
    ("s15", content_c.section15),
    ("s16", content_c.section16),
]


def build(pages):
    doc = new_document()
    add_header_footer(doc, "SmartCare — Healthcare Appointment Platform",
                      "CSA10 Software Engineering")
    add_page_border(doc)
    content_a.title_page(doc)
    doc.add_page_break()
    content_a.evidence_block(doc)
    content_a.toc(doc, pages)
    for _, fn in SECTIONS:
        fn(doc)
    doc.save(str(OUT))
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", help="JSON file mapping section key -> page number")
    args = ap.parse_args()
    pages = json.loads(pathlib.Path(args.pages).read_text()) if args.pages else {}
    path = build(pages)
    print("written", path, path.stat().st_size // 1024, "KB")
