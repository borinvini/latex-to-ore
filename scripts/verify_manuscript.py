#!/usr/bin/env python
"""verify_manuscript.py MANUSCRIPT.docx [FIGURES_DIR]

Read ORE compliance back off the FINISHED manuscript, rather than trusting the
LaTeX that produced it. Every other check in this skill runs on the input .tex
(Phase 4 reviews it before conversion) or on style NAMES (verify_styles.py); this
script is the only one that inspects what actually landed in word/document.xml.

Why it exists: the conversion can silently violate ORE order. preprocess.pl
anchors citeproc's reference list with \\hypertarget{refs}{}; if that anchoring
fails, citeproc appends the references at the very END of the document -- after
the Figure Legends and Tables -- which is an ORE rejection and is invisible both
to a .tex review and to a style check.

Checks (FAIL = ORE compliance problem, WARN = author should look):
  1. Section order          ORE sequence, in the DOCX itself
  2. Declarations           the four mandatory ones, present and correctly placed
  3. Structured abstract    Background/Methods/Results/Conclusions, <=300 words,
                            no bracketed citations
  4. Reference list         non-empty and positioned before the Figure Legends
  5. Figure legends         all numbered; count cross-checked against FIGURES_DIR
  6. Tables                 every table in the Tables section has a numbered legend
  7. Leaked raw TeX         constructs Pandoc failed to convert
  8. Embedded images        ORE wants figures as separate files, not in the .docx
  9. ORE styling applied    the enriched reference doc really was used

Exits 1 if any check FAILs, so the skill surfaces the problem instead of shipping
a non-compliant package. Deterministic, standard library only.
"""

import os
import re
import sys
import zipfile

DOCXML = "word/document.xml"
STYLESXML = "word/styles.xml"

# Paragraph styles that mark a section heading.
HEADING_STYLES = re.compile(r"^(Heading\d|Title|AbstractTitle)$")

# ORE section sequence. (name, aliases, required)
# Aliases are matched casefolded against the whole heading text; ORE accepts a
# few heading variants (e.g. "Conflict of interest" for Competing Interests).
ORE_SECTIONS = [
    ("Abstract",              ["abstract"],                                        True),
    ("Keywords",              ["keywords", "key words"],                           False),
    ("Plain Language Summary", ["plain language summary"],                         False),
    ("Data Availability",     ["data availability", "data availability statement"], True),
    ("Ethics and consent",    ["ethics and consent", "ethics", "ethical approval",
                               "ethics and consent statement"],                    True),
    ("Competing Interests",   ["competing interests", "conflict of interest",
                               "competing interest", "conflicts of interest"],     True),
    ("Grant Information",     ["grant information", "funding", "grant info"],      True),
    ("Acknowledgments",       ["acknowledgments", "acknowledgements"],             False),
    ("References",            ["references", "bibliography"],                      True),
    ("Figure Legends",        ["figure legends", "figure legend"],                 False),
    ("Tables",                ["tables"],                                          False),
]

ABSTRACT_LABELS = ["background", "methods", "results", "conclusions"]

# Constructs that mean Pandoc left LaTeX in the output.
LEAKED_TEX = [
    (r"\\begin\{",     r"\begin{"),
    (r"\\end\{",       r"\end{"),
    (r"\\ref\{",       r"\ref{"),
    (r"\\cite\{",      r"\cite{"),
    (r"\\includegraphics", r"\includegraphics"),
    (r"\\resizebox",   r"\resizebox"),
    (r"\\textbf\{",    r"\textbf{"),
    (r"\\thanks\{",    r"\thanks{"),
]

ORE_BLUE = "004494"


class Report:
    """Collects PASS/WARN/FAIL lines; FAILs drive the exit code."""

    def __init__(self):
        self.fails = 0
        self.warns = 0

    def ok(self, msg):
        print(f"  PASS  {msg}")

    def warn(self, msg):
        self.warns += 1
        print(f"  WARN  {msg}")

    def fail(self, msg):
        self.fails += 1
        print(f"  FAIL  {msg}", file=sys.stderr)


def plain_text(fragment):
    """Visible text of an OOXML fragment, whitespace-collapsed."""
    text = "".join(re.findall(r"<w:t\b[^>]*>(.*?)</w:t>", fragment, re.S))
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


def paragraphs(document_xml):
    """[(pos, styleId, text)] for every <w:p>, in document order."""
    out = []
    for m in re.finditer(r"<w:p\b.*?</w:p>", document_xml, re.S):
        block = m.group(0)
        sm = re.search(r'<w:pStyle\b[^>]*w:val="([^"]*)"', block)
        out.append((m.start(), sm.group(1) if sm else "", plain_text(block)))
    return out


def find_sections(paras):
    """{canonical name: position} for each ORE heading found in the document."""
    found = {}
    for pos, style, text in paras:
        if not HEADING_STYLES.match(style):
            continue
        key = text.casefold().rstrip(":.").strip()
        for name, aliases, _ in ORE_SECTIONS:
            if name in found:
                continue
            if key in aliases:
                found[name] = pos
                break
    return found


def check_order(found, rep):
    """Check 1+2: mandatory sections present, and all present ones in ORE order."""
    for name, _, required in ORE_SECTIONS:
        if required and name not in found:
            rep.fail(f"required ORE section missing from the manuscript: {name}")

    present = [n for n, _, _ in ORE_SECTIONS if n in found]
    actual = sorted(present, key=lambda n: found[n])
    if actual == present:
        if present:
            rep.ok(f"section order is ORE-compliant: {' -> '.join(present)}")
    else:
        rep.fail("sections are OUT OF ORE ORDER")
        print(f"        expected: {' -> '.join(present)}", file=sys.stderr)
        print(f"        actual:   {' -> '.join(actual)}", file=sys.stderr)


def check_abstract(paras, found, rep):
    """Check 3: structured abstract, word limit, no citations."""
    if "Abstract" not in found:
        return
    start = found["Abstract"]
    later = [p for p in found.values() if p > start]
    end = min(later) if later else float("inf")
    body = " ".join(t for pos, _, t in paras if start < pos < end and t)

    missing = [l for l in ABSTRACT_LABELS if l not in body.casefold()]
    if missing:
        rep.fail("abstract is not structured; missing label(s): "
                 + ", ".join(w.capitalize() for w in missing))
    else:
        rep.ok("abstract is structured (Background / Methods / Results / Conclusions)")

    words = len(body.split())
    if words > 300:
        rep.warn(f"abstract is {words} words; ORE's limit is 300")
    elif words:
        rep.ok(f"abstract length {words} words (limit 300)")

    if re.search(r"\[\d+\]", body):
        rep.warn("abstract appears to contain a bracketed citation; ORE forbids "
                 "citations in the abstract")


def check_references(paras, found, rep):
    """Check 4: the reference list exists and sits before the figure legends."""
    entries = [pos for pos, style, _ in paras if style == "Bibliography"]
    if not entries:
        rep.fail("no Bibliography paragraphs found -- citeproc produced no "
                 "reference list (check the --bibliography/--csl arguments)")
        return
    n = len(entries)
    rep.ok(f"reference list present ({n} entr{'y' if n == 1 else 'ies'})")

    for later in ("Figure Legends", "Tables"):
        if later in found and max(entries) > found[later]:
            rep.fail(f"the reference list runs PAST the '{later}' section -- "
                     "citeproc appended it at the end of the document; the "
                     "\\hypertarget{refs}{} anchor from preprocess.pl did not take")
            return
    rep.ok("reference list is positioned before the Figure Legends / Tables")


def check_figures(document_xml, found, figures_dir, rep):
    """Check 5: every legend numbered; count matches the exported figure files."""
    if "Figure Legends" not in found:
        rep.warn("no 'Figure Legends' section -- expected unless the paper has "
                 "no figures")
        return
    tail = document_xml[found["Figure Legends"]:]
    if "Tables" in found and found["Tables"] > found["Figure Legends"]:
        tail = document_xml[found["Figure Legends"]:found["Tables"]]

    numbered = re.findall(r"<w:t[^>]*>Figure (\d+)\.\s*</w:t>", tail)
    captions = len(re.findall(r'<w:pStyle\b[^>]*w:val="ImageCaption"', tail))
    if not numbered:
        rep.fail("no numbered figure legends found -- postprocess.py did not run "
                 "or found no ImageCaption paragraphs")
        return
    if captions > len(numbered):
        rep.fail(f"{captions} figure legend(s) but only {len(numbered)} numbered")
    else:
        rep.ok(f"{len(numbered)} figure legend(s), all numbered")

    if figures_dir:
        if not os.path.isdir(figures_dir):
            rep.warn(f"figures directory not found: {figures_dir}")
            return
        files = [f for f in sorted(os.listdir(figures_dir))
                 if not f.startswith(".")]
        if len(files) != len(numbered):
            rep.warn(f"{len(numbered)} figure legend(s) but {len(files)} file(s) "
                     f"in {figures_dir} -- ORE rejects a figure that is cited but "
                     "not supplied (subfigures legitimately inflate the legend "
                     "count; confirm by eye)")
        else:
            rep.ok(f"figure legends match the {len(files)} exported file(s)")


def check_tables(document_xml, found, rep):
    """Check 6: every table in the Tables section carries a numbered legend."""
    if "Tables" not in found:
        rep.warn("no 'Tables' section -- expected unless the paper has no tables")
        return
    tail = document_xml[found["Tables"]:]
    tables = len(re.findall(r"<w:tbl>", tail))
    numbered = re.findall(r"<w:t[^>]*>Table (\d+)\.\s*</w:t>", tail)
    if tables == 0:
        rep.warn("'Tables' section contains no Word tables")
    elif len(numbered) < tables:
        rep.fail(f"{tables} table(s) in the Tables section but only "
                 f"{len(numbered)} numbered legend(s); ORE requires a legend on "
                 "every table")
    else:
        rep.ok(f"{tables} table(s), each with a numbered legend")


def check_leaked_tex(document_xml, rep):
    """Check 7: LaTeX that Pandoc failed to convert and dumped as text."""
    body = plain_text(document_xml)
    hits = [literal for pattern, literal in LEAKED_TEX
            if re.search(pattern, body)]
    if hits:
        rep.fail("raw LaTeX leaked into the manuscript text: " + ", ".join(hits))
        print("        Fix: add a strip/unwrap rule to scripts/preprocess.pl, "
              "then reconvert.", file=sys.stderr)
    else:
        rep.ok("no raw LaTeX leaked into the text")


def check_media(archive, rep):
    """Check 8: ORE wants figures as separate files, not embedded."""
    media = [n for n in archive.namelist() if n.startswith("word/media/")]
    if media:
        rep.warn(f"{len(media)} image(s) embedded in the .docx; ORE expects "
                 "figures as separate files and the body free of images")
    else:
        rep.ok("no images embedded (figures ship as separate files)")


def check_styling(archive, rep):
    """Check 9: the enriched ORE reference doc really was applied."""
    if STYLESXML not in archive.namelist():
        rep.fail(f"no {STYLESXML} in the manuscript")
        return
    styles = archive.read(STYLESXML).decode("utf-8", "replace")
    if ORE_BLUE.casefold() in styles.casefold():
        rep.ok("ORE house styling applied (ORE blue present in styles.xml)")
    else:
        rep.fail("ORE blue (#004494) not found in styles.xml -- the manuscript "
                 "was probably converted WITHOUT the enriched reference doc; "
                 "rebuild it with enrich_reference.py and reconvert")


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: verify_manuscript.py MANUSCRIPT.docx [FIGURES_DIR]")
    path = sys.argv[1]
    figures_dir = sys.argv[2] if len(sys.argv) == 3 else None

    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        sys.exit(f"cannot open {path}: {exc}")

    with archive:
        if DOCXML not in archive.namelist():
            sys.exit(f"{path} is not a valid .docx (no {DOCXML})")
        document_xml = archive.read(DOCXML).decode("utf-8", "replace")

        print(f"verify_manuscript.py: checking {path}")
        rep = Report()
        paras = paragraphs(document_xml)
        found = find_sections(paras)

        check_order(found, rep)
        check_abstract(paras, found, rep)
        check_references(paras, found, rep)
        check_figures(document_xml, found, figures_dir, rep)
        check_tables(document_xml, found, rep)
        check_leaked_tex(document_xml, rep)
        check_media(archive, rep)
        check_styling(archive, rep)

    if rep.fails:
        print(f"\nverify_manuscript.py: FAIL - {rep.fails} compliance problem(s), "
              f"{rep.warns} warning(s). Fix and reconvert before submitting.",
              file=sys.stderr)
        return 1
    print(f"\nverify_manuscript.py: OK - 0 compliance problems, "
          f"{rep.warns} warning(s) for author review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
