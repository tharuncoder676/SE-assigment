"""Measured originality analysis of the assignment report.

This does three things that can be checked by anyone with the repository:

1. Shingle overlap against the source material we were given (the assignment
   brief). Text is normalised, split into overlapping 8-word shingles, and the
   proportion of report shingles that also appear in the brief is reported.
   Eight words is the window most similarity tools treat as a match.
2. Internal self-similarity: repeated 8-word shingles inside the report, which
   is what flags padding and copy-pasted paragraphs.
3. A composition breakdown by content type, because quoted tool output, our
   own code listings and the bibliography are matched by similarity checkers
   but are not plagiarism.

Usage:  python originality.py
"""
import collections
import json
import pathlib
import re
import sys

import docx

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORT = ROOT / "SmartCare_Software_Engineering_Report.docx"
SOURCES = ROOT / "docs" / "sources"      # every document that was supplied to us
N = 8


def normalise(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def shingles(words, n=N):
    return [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]


def iter_blocks(document):
    """Yield (kind, text) for every paragraph and table cell in order."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    def classify(par):
        fonts = {r.font.name for r in par.runs if r.font.name}
        if fonts and fonts <= {"Consolas"}:
            return "code"
        if par.style.name == "List Number":
            return "reference"
        return "prose"

    # Section 17 reports these very statistics, so measuring it would make the
    # figures self-referential. Everything from its heading onwards is skipped,
    # and the report says so.
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            par = Paragraph(child, document)
            if par.text.strip().startswith("17.  Originality and Similarity"):
                return
            if par.text.strip():
                yield classify(par), par.text
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        yield "table", cell.text


def main():
    doc = docx.Document(str(REPORT))
    blocks = list(iter_blocks(doc))

    buckets = collections.Counter()
    prose_words = []
    all_words = []
    for kind, text in blocks:
        words = normalise(text).split()
        buckets[kind] += len(words)
        all_words.extend(words)
        if kind == "prose":
            prose_words.extend(words)

    total = sum(buckets.values())

    # -- 1. overlap with every source document supplied to us -------------
    prose_shingles = shingles(prose_words)
    per_source, brief_set = {}, set()
    for src in sorted(SOURCES.glob("*.txt")):
        words = normalise(src.read_text(encoding="utf-8", errors="replace")).split()
        source_set = set(shingles(words))
        brief_set |= source_set
        hits = [s for s in prose_shingles if s in source_set]
        per_source[src.stem] = {
            "source_words": len(words),
            "matched_shingles": len(hits),
            "overlap_percent": round(100.0 * len(hits) / max(1, len(prose_shingles)), 3),
        }
    matched = [s for s in prose_shingles if s in brief_set]
    brief_overlap = 100.0 * len(matched) / max(1, len(prose_shingles))

    # -- 2. internal self-similarity --------------------------------------
    counts = collections.Counter(prose_shingles)
    repeated = sum(c - 1 for c in counts.values() if c > 1)
    self_sim = 100.0 * repeated / max(1, len(prose_shingles))

    # -- 3. longest verbatim run taken from the brief ----------------------
    longest, run = 0, 0
    for s in prose_shingles:
        run = run + 1 if s in brief_set else 0
        longest = max(longest, run)
    longest_words = longest + N - 1 if longest else 0

    report = {
        "total_words": total,
        "composition": {k: {"words": v, "percent": round(100.0 * v / total, 1)}
                        for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])},
        "prose_words": len(prose_words),
        "shingle_size": N,
        "prose_shingles": len(prose_shingles),
        "per_source": per_source,
        "combined_source_overlap_percent": round(brief_overlap, 3),
        "matched_shingles": len(matched),
        "longest_verbatim_run_words": longest_words,
        "internal_self_similarity_percent": round(self_sim, 2),
        "sample_matches": sorted(set(matched))[:12],
    }
    print(json.dumps(report, indent=2))
    (ROOT / "docs" / "originality-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    sys.exit(0 if main() else 0)
