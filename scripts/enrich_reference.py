#!/usr/bin/env python
"""enrich_reference.py BASE_TEMPLATE.docx OUT_ENRICHED.docx

Add-only enrichment of an ORE Word template's styles so that EVERY paragraph and
table style Pandoc's docx writer can emit is defined in the reference document.

Why: Pandoc's --reference-doc applies a style from the reference doc only when
the element's style *name* (styleId) already exists there. The stock ORE
template defines just a handful of styles (Title, Heading1/2, BodyText,
PlainTable1, ...). Every other element Pandoc emits (Compact, FirstParagraph,
Author, Abstract, Heading3, Table, FigureTable, captions, Bibliography, ...)
therefore falls back to Pandoc's built-in Calibri/black defaults instead of the
ORE look.

This script copies the template and inserts a minimal <w:style> definition for
each missing style, `basedOn` an appropriate style that DOES exist in the ORE
template, so the new style inherits the ORE design (Arial, blue headings, ORE
body spacing, ORE table borders). It never removes or alters the template's own
styles, so it is safe to run against any ORE template version or an
author-customised one, and it is idempotent (re-running adds nothing).

Deterministic, no LLM. Requires only the Python standard library.
"""

import re
import shutil
import sys
import zipfile

# Every paragraph/table style Pandoc's docx writer can emit, with the exact
# w:name Pandoc uses and the ORE template style each should inherit from.
# `base` must be a styleId that exists in the ORE template; a runtime fallback
# (Normal / TableNormal) covers the case where it does not.
#   (styleId, wtype, w:name, base_styleId)
PANDOC_STYLES = [
    # headings beyond H1/H2 inherit ORE's Heading2 look (Arial bold; ORE only
    # colours H1 blue, so H3+ stay black bold — matching the ORE design intent)
    ("Heading3", "paragraph", "heading 3", "Heading2"),
    ("Heading4", "paragraph", "heading 4", "Heading2"),
    ("Heading5", "paragraph", "heading 5", "Heading2"),
    ("Heading6", "paragraph", "heading 6", "Heading2"),
    ("Heading7", "paragraph", "heading 7", "Heading2"),
    ("Heading8", "paragraph", "heading 8", "Heading2"),
    ("Heading9", "paragraph", "heading 9", "Heading2"),
    ("TOCHeading", "paragraph", "TOC Heading", "Heading2"),
    # body-like paragraph styles inherit ORE BodyText
    ("Compact", "paragraph", "Compact", "BodyText"),
    ("FirstParagraph", "paragraph", "First Paragraph", "BodyText"),
    ("Abstract", "paragraph", "Abstract", "BodyText"),
    ("Author", "paragraph", "Author", "BodyText"),
    ("Date", "paragraph", "Date", "BodyText"),
    ("Subtitle", "paragraph", "Subtitle", "BodyText"),
    ("Bibliography", "paragraph", "Bibliography", "BodyText"),
    ("BlockText", "paragraph", "Block Text", "BodyText"),
    ("FootnoteText", "paragraph", "Footnote Text", "BodyText"),
    ("FootnoteBlockText", "paragraph", "Footnote Block Text", "BodyText"),
    ("Definition", "paragraph", "Definition", "BodyText"),
    ("DefinitionTerm", "paragraph", "Definition Term", "BodyText"),
    ("Caption", "paragraph", "Caption", "BodyText"),
    ("TableCaption", "paragraph", "Table Caption", "BodyText"),
    ("ImageCaption", "paragraph", "Image Caption", "BodyText"),
    ("Figure", "paragraph", "Figure", "BodyText"),
    ("CaptionedFigure", "paragraph", "Captioned Figure", "BodyText"),
    # label-style paragraphs inherit ORE Heading2 (bold)
    ("AbstractTitle", "paragraph", "Abstract Title", "Heading2"),
    # table styles inherit the ORE table look
    ("Table", "table", "Table", "PlainTable1"),
    # FigureTable is emitted by Pandoc for borderless figure/layout tables but is
    # NOT in Pandoc's default reference.docx, so it must be listed explicitly.
    ("FigureTable", "table", "Figure Table", "PlainTable1"),
]

# Runtime fallback bases if a mapped base is absent from this particular template.
FALLBACK_BASE = {"paragraph": "Normal", "table": "TableNormal"}

# Property overrides applied to styles that ALREADY exist in the ORE template
# (Title, Heading1, Heading2). The add-only enrichment above cannot fix these
# because it skips any style the template already defines; these patches set
# specific paragraph/run properties so the ORE output matches the house style:
#   - Title: centered, ORE blue (like the section headings), with breathing room.
#   - Heading1/Heading2: real space before AND after so headings do not jam into
#     the surrounding paragraphs. Heading3+ inherit this via `basedOn Heading2`.
# Values are twips (1 pt = 20 twips). ORE blue = 004494 (the template's Heading1
# colour). Applied by rewriting only the managed child elements, in OOXML schema
# order, and is idempotent (re-running reproduces the same result).
#   styleId: {spacing:(before,after), jc:val|None, color:val|None, drop_ind:bool}
#
# AbstractTitle is ADDED by the enrichment pass above (it is not in the stock ORE
# template); because enrich_styles_xml runs BEFORE apply_style_patches, the style
# exists by the time it is patched here. It is basedOn Heading2 (small bold), and
# this patch colours it ORE blue (004494) so the "Abstract" heading — and the
# "Keywords" heading that postprocess.py retypes to AbstractTitle — match the
# blue section headings, per ORE house style.
#
# BodyText gets a real space-after (120 twips = 6 pt) so consecutive body
# paragraphs are visibly separated — the stock template's BodyText has only
# before="14" (0.7 pt), which reads as no gap at all. FirstParagraph, Abstract,
# Bibliography, captions, etc. inherit this via `basedOn BodyText`. Compact
# (Pandoc's tight-list and table-cell paragraph style) is pinned back to 0/0 so
# list items and table cells stay tight instead of inheriting the 6 pt gap.
STYLE_PATCHES = {
    "Title":         {"spacing": ("240", "160"), "jc": "center", "color": "004494", "drop_ind": True},
    "Heading1":      {"spacing": ("240", "120"), "jc": None,     "color": None,     "drop_ind": False},
    "Heading2":      {"spacing": ("200", "80"),  "jc": None,     "color": None,     "drop_ind": False},
    "AbstractTitle": {"spacing": ("200", "80"),  "jc": None,     "color": "004494", "drop_ind": False},
    "BodyText":      {"spacing": ("0", "120"),   "jc": None,     "color": None,     "drop_ind": False},
    "Compact":       {"spacing": ("0", "0"),     "jc": None,     "color": None,     "drop_ind": False},
}

# The ORE body font size, in half-points (19 = 9.5 pt), matching the template's
# BodyText style. Pandoc emits list-item paragraphs with NO paragraph style, so
# they inherit Normal -> docDefaults, which the template leaves at 22 (11 pt) —
# visibly larger than the 9.5 pt body. Lowering the document default to the body
# size makes unstyled paragraphs (list items) match the surrounding text; every
# heading/title/body style sets its own explicit size, so they are unaffected.
DOC_DEFAULT_SZ = "19"


def _patch_ppr(inner, spacing, jc, drop_ind):
    """Rewrite a <w:pPr> inner string: set spacing, optionally set jc / drop ind.
    Managed elements are emitted in OOXML schema order (spacing, [ind], jc,
    ... outlineLvl). We only add jc together with drop_ind, so the surviving
    order is always spacing -> (kept ind) -> jc? No: jc is only used when ind is
    dropped, so the result is spacing -> jc -> <remaining> (outlineLvl), or
    spacing -> <remaining: ind, outlineLvl> when jc is unused -- both valid."""
    inner = re.sub(r'<w:spacing\b[^>]*/>', '', inner)
    inner = re.sub(r'<w:jc\b[^>]*/>', '', inner)
    if drop_ind:
        inner = re.sub(r'<w:ind\b[^>]*/>', '', inner)
    prefix = f'<w:spacing w:before="{spacing[0]}" w:after="{spacing[1]}"/>'
    if jc:
        prefix += f'<w:jc w:val="{jc}"/>'
    return prefix + inner


def _patch_rpr(inner, color):
    """Rewrite a <w:rPr> inner string: set colour. w:color precedes w:sz in the
    CT_RPr schema order, so insert it before the first <w:sz> (else append)."""
    inner = re.sub(r'<w:color\b[^>]*/>', '', inner)
    color_el = f'<w:color w:val="{color}"/>'
    if '<w:sz' in inner:
        return inner.replace('<w:sz', color_el + '<w:sz', 1)
    return inner + color_el


def _patch_one_style(block, patch):
    # paragraph properties
    m = re.search(r'<w:pPr>(.*?)</w:pPr>', block, re.S)
    new_ppr = '<w:pPr>' + _patch_ppr(m.group(1) if m else '',
                                     patch["spacing"], patch.get("jc"),
                                     patch.get("drop_ind", False)) + '</w:pPr>'
    if m:
        block = block[:m.start()] + new_ppr + block[m.end():]
    else:  # insert pPr before rPr, else before </w:style> (schema: pPr < rPr)
        if '<w:rPr>' in block:
            block = block.replace('<w:rPr>', new_ppr + '<w:rPr>', 1)
        else:
            block = block.replace('</w:style>', new_ppr + '</w:style>', 1)
    # run properties (colour only, when requested)
    if patch.get("color"):
        m = re.search(r'<w:rPr>(.*?)</w:rPr>', block, re.S)
        new_rpr = '<w:rPr>' + _patch_rpr(m.group(1) if m else '', patch["color"]) + '</w:rPr>'
        if m:
            block = block[:m.start()] + new_rpr + block[m.end():]
        else:  # rPr goes after pPr, before </w:style>
            block = block.replace('</w:style>', new_rpr + '</w:style>', 1)
    return block


def apply_style_patches(styles_xml):
    patched = []
    for style_id, patch in STYLE_PATCHES.items():
        pat = re.compile(r'(<w:style\b[^>]*w:styleId="' + re.escape(style_id) + r'".*?</w:style>)', re.S)
        m = pat.search(styles_xml)
        if not m:
            continue  # template lacks this style; nothing to patch
        styles_xml = styles_xml[:m.start()] + _patch_one_style(m.group(1), patch) + styles_xml[m.end():]
        patched.append(style_id)
    return styles_xml, patched


def patch_doc_defaults(styles_xml):
    """Set the document-default run size (w:docDefaults/w:rPrDefault) to the ORE
    body size so unstyled paragraphs (Pandoc list items) match the body. Rewrites
    w:sz/w:szCs inside the docDefaults block only; if absent, inserts them into
    the default rPr. Idempotent. Returns (xml, changed)."""
    m = re.search(r'<w:docDefaults>.*?</w:docDefaults>', styles_xml, re.S)
    if not m:
        return styles_xml, False
    block = m.group(0)
    new = block
    for tag in ("w:sz", "w:szCs"):
        if re.search(r'<' + tag + r'\b[^>]*/>', new):
            new = re.sub(r'<' + tag + r'\b[^>]*/>',
                         f'<{tag} w:val="{DOC_DEFAULT_SZ}"/>', new)
        else:
            # insert into the default run properties (w:rPrDefault/w:rPr)
            new = re.sub(r'(<w:rPrDefault>\s*<w:rPr>)',
                         r'\1' + f'<{tag} w:val="{DOC_DEFAULT_SZ}"/>', new, count=1)
    if new == block:
        return styles_xml, False
    return styles_xml[:m.start()] + new + styles_xml[m.end():], True


def existing_style_ids(styles_xml):
    return set(re.findall(r'w:styleId="([^"]*)"', styles_xml))


def build_style_element(style_id, wtype, name, base):
    return (
        f'<w:style w:type="{wtype}" w:styleId="{style_id}">'
        f'<w:name w:val="{name}"/>'
        f'<w:basedOn w:val="{base}"/>'
        f'<w:qFormat/>'
        f'</w:style>'
    )


def enrich_styles_xml(styles_xml):
    present = existing_style_ids(styles_xml)
    additions = []
    added_ids = []
    for style_id, wtype, name, base in PANDOC_STYLES:
        if style_id in present:
            continue  # never touch a style the template already defines
        chosen_base = base if base in present else FALLBACK_BASE[wtype]
        additions.append(build_style_element(style_id, wtype, name, chosen_base))
        added_ids.append(style_id)
    if not additions:
        return styles_xml, added_ids
    injected = "".join(additions)
    if "</w:styles>" not in styles_xml:
        raise SystemExit("styles.xml has no </w:styles> close tag; unexpected format")
    styles_xml = styles_xml.replace("</w:styles>", injected + "</w:styles>", 1)
    return styles_xml, added_ids


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: enrich_reference.py BASE_TEMPLATE.docx OUT_ENRICHED.docx")
    base_path, out_path = sys.argv[1], sys.argv[2]

    with zipfile.ZipFile(base_path) as zin:
        names = zin.namelist()
        if "word/styles.xml" not in names:
            sys.exit(f"{base_path} is not a valid .docx (no word/styles.xml)")
        styles_xml = zin.read("word/styles.xml").decode("utf-8")
        enriched, added = enrich_styles_xml(styles_xml)
        enriched, patched = apply_style_patches(enriched)
        enriched, dd_patched = patch_doc_defaults(enriched)

        # Rewrite the zip: copy every entry unchanged except word/styles.xml.
        # (Write to a temp then move, so out_path == base_path is safe too.)
        tmp_path = out_path + ".tmp"
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/styles.xml":
                    data = enriched.encode("utf-8")
                zout.writestr(item, data)
    shutil.move(tmp_path, out_path)

    if added:
        print(f"enrich_reference.py: added {len(added)} style(s): {', '.join(added)}")
    else:
        print("enrich_reference.py: no styles added (already enriched)")
    if patched:
        print(f"enrich_reference.py: patched {len(patched)} ORE style(s): {', '.join(patched)}")
    if dd_patched:
        print(f"enrich_reference.py: set document-default run size to {DOC_DEFAULT_SZ} half-pt (body size)")


if __name__ == "__main__":
    main()
