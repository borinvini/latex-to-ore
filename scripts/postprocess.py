#!/usr/bin/env python
"""postprocess.py MANUSCRIPT.docx

In-place OOXML fixups applied to the Pandoc-produced manuscript, for the few ORE
house-style requirements that Pandoc + the reference doc cannot express:

  2. Keywords heading  -> retype the "Keywords" Heading1 (emitted because
     preprocess.pl turns \\begin{IEEEkeywords} into \\section*{Keywords}) to the
     "Abstract Title" style, so it matches the blue "Abstract" heading.
  4. Equation numbers  -> Pandoc/texmath drops LaTeX equation numbers. Every
     DISPLAY equation in the body (an <m:oMathPara> NOT inside a table) is given a
     right-aligned "(N)" using a centre tab + right tab, so the equation stays
     centred and the number sits at the right margin like the ORE template, plus
     space above and below (EQ_SPACING) so it is set off from the surrounding text.
     Numbers rendered inside table cells (e.g. "$38{,}551{,}161$") are NOT
     equations and are left untouched.
  7. Figure legends    -> First UNWRAP the layout tables Pandoc wraps every figure
     in: a figure with no image becomes an empty <w:tbl> + caption paragraph
     (harmless), but a subfigure figure becomes a real multi-column <w:tbl> with
     each subcaption trapped in a cell — which reads as a stray boxed table. The
     Figure-Legends section is layout-table-free ORE content, so ALL its FigureTable
     scaffolding is stripped, lifting every caption paragraph out. THEN prefix each
     ImageCaption paragraph with a bold "Figure N. " in document order.
  8. Tables            -> Move each table's caption to AFTER its <w:tbl> (Pandoc
     emits it before), prefix it with a bold "Table N. " in document order, and add
     space around it so consecutive tables are visually separated.

Figure/table numbers follow the same document order Pandoc uses to number the
in-text "Figure N"/"Table N" cross-references, so legends and body stay
consistent. (Pandoc counts each \\label — including subfigure sub-labels — as a
figure, so a paper with subfigures may show more numbered legends than distinct
figures; that is Pandoc's cross-reference numbering, and the legends match it.)

Deterministic, no LLM. Requires only the Python standard library. Idempotent
guards keep re-runs from double-numbering.
"""

import re
import shutil
import sys
import zipfile

DOCXML = "word/document.xml"

# Space above and below each numbered display equation (twips; 1 pt = 20 twips).
EQ_SPACING = '<w:spacing w:before="120" w:after="120"/>'


def tab_positions(x):
    """Centre and right tab stops (twips) from the section page size/margins."""
    W = 12240  # US-letter default
    m = re.search(r'<w:pgSz\b[^>]*\bw:w="(\d+)"', x)
    if m:
        W = int(m.group(1))
    L = R = 1440
    mm = re.search(r'<w:pgMar\b[^>]*/>', x)
    if mm:
        ml = re.search(r'w:left="(\d+)"', mm.group(0))
        mr = re.search(r'w:right="(\d+)"', mm.group(0))
        if ml:
            L = int(ml.group(1))
        if mr:
            R = int(mr.group(1))
    tw = W - L - R
    return tw // 2, tw


def plain_text(p):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", p)).strip()


def bold_prefix_run(text):
    return (f'<w:r><w:rPr><w:b/></w:rPr>'
            f'<w:t xml:space="preserve">{text}</w:t></w:r>')


def retype_keywords(x):
    """Item 2: Heading1 whose text is exactly 'Keywords' -> AbstractTitle."""
    def repl(m):
        p = m.group(0)
        if 'w:val="Heading1"' in p and plain_text(p) == "Keywords":
            p = p.replace('w:val="Heading1"', 'w:val="AbstractTitle"', 1)
        return p
    return re.sub(r"<w:p\b.*?</w:p>", repl, x, flags=re.S)


def number_equations(x, center, right):
    """Item 4: number display equations that are NOT inside a table."""
    # Mask table blocks so their in-cell math is never treated as an equation.
    tbls = []

    def mask(m):
        tbls.append(m.group(0))
        return f"@@ORE_TBL_{len(tbls) - 1}@@"

    masked = re.sub(r"<w:tbl>.*?</w:tbl>", mask, x, flags=re.S)

    tabs = (f'<w:tabs><w:tab w:val="center" w:pos="{center}"/>'
            f'<w:tab w:val="right" w:pos="{right}"/></w:tabs>')
    count = [0]

    def repl(m):
        p = m.group(0)
        if "<m:oMathPara" not in p:
            return p
        if "@@ORE_EQ@@" in p:  # already numbered (idempotent guard marker)
            return p
        om = re.search(r"<m:oMath>.*?</m:oMath>", p, re.S)
        if not om:
            return p
        count[0] += 1
        omath = om.group(0)
        bookmarks = "".join(re.findall(r"<w:bookmark(?:Start|End)\b[^>]*/>", p))
        pm = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
        ppr = pm.group(0) if pm else '<w:pPr><w:pStyle w:val="BodyText"/></w:pPr>'
        # Insert tab stops (centre + right for the number) and spacing above/below,
        # in OOXML schema order pStyle -> tabs -> spacing. Drop any existing spacing
        # first so we never emit two <w:spacing> or one out of order.
        ppr = re.sub(r"<w:spacing\b[^>]*/>", "", ppr)
        insert = tabs + EQ_SPACING
        if "<w:pStyle" in ppr:
            ppr = re.sub(r"(<w:pStyle\b[^>]*/>)", r"\1" + insert, ppr, count=1)
        else:
            ppr = ppr.replace("<w:pPr>", "<w:pPr>" + insert, 1)
        pstart = re.match(r"<w:p\b[^>]*>", p).group(0)
        body = (f'<w:r><w:tab/></w:r>{omath}<w:r><w:tab/></w:r>'
                f'<w:r><!--@@ORE_EQ@@--><w:t xml:space="preserve">({count[0]})</w:t></w:r>')
        return f"{pstart}{ppr}{bookmarks}{body}</w:p>"

    masked = re.sub(r"<w:p\b.*?</w:p>", repl, masked, flags=re.S)
    for i, t in enumerate(tbls):
        masked = masked.replace(f"@@ORE_TBL_{i}@@", t)
    return masked, count[0]


def unwrap_figure_tables(x):
    """Item 7 (part 1): strip every layout table Pandoc wraps figures in, within
    the Figure-Legends section only. Pandoc renders a no-image figure as an empty
    <w:tbl> + caption paragraph, and a subfigure figure as a real multi-column
    <w:tbl> with each subcaption in a cell. That whole section is ORE figure
    legends (no genuine data tables), so removing all table scaffolding — while
    KEEPING the <w:p> caption paragraphs and bookmarks — lifts every caption out to
    top level so they all read as plain paragraphs. Bounded from the Figure-Legends
    heading to the Tables heading; only table-structural tags are removed, so the
    Tables heading paragraph (up to which the region runs) is unaffected."""
    a = x.find(">Figure Legends</w:t>")
    if a < 0:
        return x
    b = x.find(">Tables</w:t>")
    if b < 0:
        b = len(x)
    region = x[a:b]
    region = re.sub(r"<w:tblPr>.*?</w:tblPr>", "", region, flags=re.S)
    region = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", "", region, flags=re.S)
    region = re.sub(r"<w:tblGrid\s*/>", "", region)
    region = re.sub(r"<w:trPr>.*?</w:trPr>", "", region, flags=re.S)
    region = re.sub(r"<w:tcPr>.*?</w:tcPr>", "", region, flags=re.S)
    region = re.sub(r"<w:tcPr\s*/>", "", region)
    region = re.sub(r"</?w:tbl>|<w:tr\b[^>]*>|</w:tr>|<w:tc\b[^>]*>|</w:tc>", "", region)
    return x[:a] + region + x[b:]


def number_figure_legends(x):
    """Item 7 (part 2): prefix each ImageCaption paragraph in the Figure-Legends
    section with a bold 'Figure N. ' in document order."""
    anchor = x.find(">Figure Legends</w:t>")
    if anchor < 0:
        return x, 0
    head, tail = x[:anchor], x[anchor:]
    count = [0]

    def repl(m):
        p = m.group(0)
        if 'w:val="ImageCaption"' not in p or "@@ORE_NUM@@" in p:
            return p
        count[0] += 1
        run = "<!--@@ORE_NUM@@-->" + bold_prefix_run(f"Figure {count[0]}. ")
        return re.sub(r"(</w:pPr>)", r"\1" + run, p, count=1)

    tail = re.sub(r"<w:p\b.*?</w:p>", repl, tail, flags=re.S)
    return head + tail, count[0]


def restructure_tables(x):
    """Items 1/2/8: in the Tables section, move each caption to AFTER its table,
    prefix it with a bold 'Table N. ', and set spacing (small before, larger after)
    so consecutive tables are separated. Pandoc emits '<w:p TableCaption> then
    <w:tbl>'; this swaps them. Data tables are not nested, so the non-greedy
    <w:tbl>...</w:tbl> match is safe. Idempotent: after the swap the caption follows
    its table, so the caption-before-table pattern no longer matches."""
    anchor = x.find(">Tables</w:t>")
    if anchor < 0:
        return x, 0
    head, tail = x[:anchor], x[anchor:]
    count = [0]

    def repl(m):
        cap, sep, tbl = m.group("cap"), m.group("sep"), m.group("tbl")
        count[0] += 1
        run = "<!--@@ORE_NUM@@-->" + bold_prefix_run(f"Table {count[0]}. ")
        cap = re.sub(r"(</w:pPr>)", r"\1" + run, cap, count=1)
        spacing = '<w:spacing w:before="60" w:after="240"/>'
        if re.search(r"<w:spacing\b[^>]*/>", cap):
            cap = re.sub(r"<w:spacing\b[^>]*/>", spacing, cap, count=1)
        else:  # w:pStyle may be written "...TableCaption"/> or with a space before />
            cap = re.sub(r'(<w:pStyle w:val="TableCaption"[^>]*/>)', r"\1" + spacing, cap, count=1)
        return tbl + sep + cap  # table first, caption after

    pat = re.compile(
        r"(?P<cap><w:p\b(?:(?!</w:p>).)*?TableCaption(?:(?!</w:p>).)*?</w:p>)"
        r"(?P<sep>\s*)(?P<tbl><w:tbl>.*?</w:tbl>)", re.S)
    tail = pat.sub(repl, tail)
    return head + tail, count[0]


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: postprocess.py MANUSCRIPT.docx")
    path = sys.argv[1]
    with zipfile.ZipFile(path) as zin:
        if DOCXML not in zin.namelist():
            sys.exit(f"{path} is not a valid .docx (no {DOCXML})")
        x = zin.read(DOCXML).decode("utf-8")
        names = zin.infolist()
        data = {i.filename: zin.read(i.filename) for i in names}

    center, right = tab_positions(x)
    x = retype_keywords(x)
    x, n_eq = number_equations(x, center, right)
    x = unwrap_figure_tables(x)
    x, n_fig = number_figure_legends(x)
    x, n_tab = restructure_tables(x)

    data[DOCXML] = x.encode("utf-8")
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for i in names:
            zout.writestr(i, data[i.filename])
    shutil.move(tmp, path)

    print(f"postprocess.py: numbered {n_eq} equation(s), {n_fig} figure "
          f"legend(s), {n_tab} table(s); Keywords heading retyped")


if __name__ == "__main__":
    main()
