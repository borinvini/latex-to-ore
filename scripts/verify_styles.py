#!/usr/bin/env python
"""verify_styles.py MANUSCRIPT.docx ENRICHED_REFERENCE.docx

Guard against the orphan-style bug: a paragraph or table style that the produced
manuscript USES but the enriched reference doc does NOT define. Such a style
silently falls back to Pandoc's built-in Calibri/black defaults instead of the
ORE look — exactly the failure this skill's enriched-reference step exists to
prevent.

Checks: every w:pStyle (paragraph) and w:tblStyle (table) value referenced in
the manuscript's word/document.xml must be defined as a w:styleId in the
enriched reference doc's word/styles.xml. Character run styles (w:rStyle) are
out of scope — they are inline and not the block-level fidelity problem, and
Pandoc supplies their definitions in the output itself.

Prints each orphan with its occurrence count and a fix hint, and exits non-zero
if any orphan is found, so the skill surfaces the problem rather than shipping a
mis-styled document. Deterministic, standard library only.
"""

import re
import sys
import zipfile
from collections import Counter


def used_block_styles(document_xml):
    """Return Counter of styleId -> count for paragraph and table styles used."""
    counts = Counter()
    for m in re.finditer(r'<w:(?:pStyle|tblStyle)\b[^>]*w:val="([^"]*)"', document_xml):
        counts[m.group(1)] += 1
    return counts


def defined_style_ids(styles_xml):
    return set(re.findall(r'w:styleId="([^"]*)"', styles_xml))


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: verify_styles.py MANUSCRIPT.docx ENRICHED_REFERENCE.docx")
    manuscript, reference = sys.argv[1], sys.argv[2]

    with zipfile.ZipFile(manuscript) as z:
        document_xml = z.read("word/document.xml").decode("utf-8")
    with zipfile.ZipFile(reference) as z:
        styles_xml = z.read("word/styles.xml").decode("utf-8")

    used = used_block_styles(document_xml)
    defined = defined_style_ids(styles_xml)

    orphans = {sid: n for sid, n in used.items() if sid not in defined}

    if not orphans:
        print(
            f"verify_styles.py: OK - all {len(used)} paragraph/table styles used "
            f"in {manuscript} are defined in the reference doc."
        )
        return 0

    print(
        f"verify_styles.py: FAIL - {len(orphans)} style(s) used in {manuscript} "
        f"are NOT defined in {reference} and fell back to Pandoc defaults:",
        file=sys.stderr,
    )
    for sid, n in sorted(orphans.items(), key=lambda kv: -kv[1]):
        print(f"  - {sid}  ({n} occurrence(s))", file=sys.stderr)
    print(
        "  Fix: add a derivation for each style above to "
        "scripts/enrich_reference.py (PANDOC_STYLES), then rebuild the enriched "
        "reference doc and reconvert.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
