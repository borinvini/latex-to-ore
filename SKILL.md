---
name: latex-to-ore
description: Use when converting a LaTeX paper into an Open Research Europe (ORE) submission package. Copies the LaTeX project, guides the author through ORE compliance (structured abstract, Data & Software Availability, Ethics, Competing Interests, Grant Information) by editing the LaTeX copy directly, then converts to a Word manuscript via Pandoc using an enriched reference template that matches the ORE house style, plus separate figures and a submission checklist.
---

# latex-to-ore

Converts a LaTeX paper into a complete Open Research Europe (ORE) submission
package. The workflow is **LaTeX-first**: the skill copies the whole project,
makes every ORE content change *in the LaTeX copy* (easier and reviewable than
editing a `.docx`), and only then converts to Word — using a reference template
enriched so Pandoc's output actually follows the ORE house style. Authoritative
ORE rules: `references/ore-guidelines.md`.

**Never edit the author's original project.** All work happens inside
`ore-submission/`. `$SKILLDIR` below = `~/.claude/skills/latex-to-ore`.

## Pipeline at a glance

```
Phase 0  Detect main .tex / .bib / figures; verify Pandoc; fetch ORE template
Phase 1  Copy the whole LaTeX project -> ore-submission/tex/   (still compiles)
Phase 2  ORE compliance Q&A (gather answers; don't write yet)
Phase 3  Inject answers INTO ore-submission/tex/main.tex:
           restructured abstract + declarations sections + move tables to end
Phase 4  Author reviews / edits ore-submission/tex/main.tex   (review gate)
Phase 5  Convert the edited .tex -> manuscript.docx (enriched ref + verify styles)
Phase 6  Figures, checklist, data-deposit reminder, summary
Phase 7  Verify the FINISHED .docx against ORE + the template   (approval gate)
Phase 8  After the author APPROVES the manuscript: delete the working tex copy
         and the templates; keep manuscript, figures, checklist
```

## Phase 0 — Detect & set up

1. Find the main `.tex` file: the one containing both `\documentclass` and
   `\begin{document}` (if several candidates exist, ask which is the main file).
2. Find the `.bib` file(s) from the paper's `\bibliography{...}` line — do not
   assume names. Note any `.bbl` (informational only; not used).
3. Determine where figures live, then **ask the author to confirm**:
   - Collect the path in every `\includegraphics[...]{PATH}` command (ignore
     commented-out lines); note the directory/directories they reference,
     resolved relative to the main `.tex`.
   - **Ask the author for the figures folder**, proposing the detected directory
     as default (e.g. "Your figures appear to be in `figs/` — is that correct?").
   - The `\includegraphics` paths stay the source of truth for which file is
     which figure; the confirmed folder is where to resolve bare filenames.
     Figures may live in `figs/`, `figures/`, `images/`, subfolders, or the
     project root — never assume.
   - Flag any referenced figure file that does not exist on disk.
4. Create `ore-submission/` in the paper directory if absent.
5. Verify Pandoc: `pandoc --version`. If missing, stop and ask the author to
   install it. (Phases 5–6 also need Python 3 for the styling scripts and, for
   figure conversion, Pillow + poppler `pdftocairo`.)
6. Ensure the base ORE Word template is at `ore-submission/ore-template.docx`.
   If missing, download it:

   ```sh
   curl -fsSL -o ore-submission/ore-template.docx \
     "https://openreseurope-files.f1000.com/resources/ORE_Article_Template.docx"
   unzip -l ore-submission/ore-template.docx | grep -q "word/document.xml" \
     && echo "ORE template OK" || echo "ORE template INVALID"
   ```

   If the download fails or is not a valid DOCX, delete any partial file and ask
   the author to download the ORE Article Template manually and place it there,
   then **pause** — Phase 5 depends on it. If a template is already present, use
   it as-is (don't overwrite an author-supplied one). This is the *base*
   template; Phase 5 enriches it before conversion.

## Phase 1 — Copy the LaTeX project

Copy the **whole** LaTeX project into `ore-submission/tex/` so the copy still
compiles and can be reviewed as a PDF. Include everything needed to build:
the main `.tex`, all `.bib` files, the document class / style files
(`.cls`, `.bst`), the figures folder, and any other referenced assets.

```sh
mkdir -p ore-submission/tex
# copy sources (adapt to the project's actual files/folders)
cp main.tex *.bib *.cls *.bst ore-submission/tex/ 2>/dev/null
cp -r figs ore-submission/tex/            # the confirmed figures folder
```

From here on, all content edits happen in `ore-submission/tex/main.tex`. The
original project root is never touched.

## Phase 2 — ORE compliance Q&A (gather answers)

Load `references/ore-guidelines.md` as the authoritative rule set. Read the
copied `.tex` to detect what already exists, and only prompt the author about
genuine gaps or decisions — don't ask about sections already present and
compliant. Gather (do not write into the `.tex` yet — that is Phase 3):

1. **Author/affiliation block** — confirm affiliation superscript numbers match
   the number of listed affiliations (a common rejection is a superscript with
   no matching affiliation), and that corresponding-author details appear AFTER
   the affiliations. Note whether affiliations are currently in `\thanks{...}`
   footnotes (typical for IEEEtran) — Phase 3 moves them inline after the names.
   Collect the EMAIL of every author (not just the corresponding author) and,
   when authors span more than one affiliation, which affiliation(s) each author
   belongs to (this drives the per-name superscripts in Phase 3).
2. **Structured abstract** — will be rewritten to Background / Methods / Results
   / Conclusions, no citations, abbreviations spelled out, <=300 words, accurately
   reflecting the manuscript. Draft it for the author to approve.
3. **Keywords** — up to 8; pull from `\IEEEkeywords` (or equivalent) if present.
4. **Plain Language Summary** — offer to draft one (recommended, not required).
5. **Drafting style rule (abstract + Plain Language Summary): NEVER use en
   dashes or em dashes** (`–` / `—`, or LaTeX `--` / `---`) in any prose this
   skill drafts. No parenthetical dashes ("severe weather – snow and ice – is"),
   no dash-joined ranges ("2018–2024"). Rephrase instead: use commas or
   "such as ..." for asides, parentheses where natural, and "2018 to 2024" /
   "between 2018 and 2024" for ranges. Hyphens inside compound words
   (ready-to-use) are fine. When reviewing an existing abstract/PLS, rewrite
   any dash constructions the same way.
6. **Section mapping** — confirm the body maps to Introduction / Methods /
   Results / Conclusions-Discussion. Don't silently rename the author's
   sections — ask before restructuring.
7. **Existing preprint — ASK EVERY TIME.** Ask the author outright: *"Do you
   already have a preprint version of this work (for example an arXiv, bioRxiv,
   SSRN, Zenodo, or institutional-repository posting)? ORE editors ask authors to
   cite it in the manuscript."* Do not infer the answer from the `.tex` — ask,
   even if a self-citation seems to be present already.
   - **If yes** — collect the preprint DOI or URL, plus enough metadata for a
     reference entry (authors, title, year, server/repository, arXiv ID if any).
     Check whether the `.bib` already has an entry for it and reuse that key;
     otherwise a new entry is added in Phase 3. Phase 3 then cites it in the
     **Introduction**.
   - **If no** — nothing to insert. Keep the standard to-do below.
8. **ORE preprint self-citation (always a to-do)** — ORE also publishes the
   article itself as a preprint before review and asks authors to cite that
   version. Its DOI does not exist until after submission, so record it as a
   checklist to-do regardless of the answer to item 7.

Declarations to gather (Phase 3 writes them at the END, before `\bibliography`,
in this order: Data Availability -> Ethics and consent -> Competing Interests ->
Grant Information -> Acknowledgments):

9. **Data Availability** — MANDATORY even with no new data. Follow the ORE Open
   Data policy and exact format in `references/ore-guidelines.md`: an
   **Underlying data** subsection ("Repository name: [title]. https://doi.org/XXXX
   [Reference]." + a bulleted list of every deposited file with a description),
   an **Extended data** subsection (or "There is no extended data associated with
   this article."), ending with the license sentence (CC BY 4.0 or CC0). The data
   must cover the values behind means/SDs, the values behind every figure, any
   points extracted from images, and variable descriptions; it needs a DOI and
   must not be embargoed or login-gated. **Flag any non-approved repository**
   (e.g. Kaggle) — ORE expects an approved repository (Zenodo/figshare/Dryad/OSF)
   with CC BY/CC0 and no login wall; recommend a Zenodo/figshare deposit and use
   that DOI. (See `data-package-structure.md` for the matching deposit.)
10. **Ethics and consent** — dedicated section immediately AFTER Data
    Availability. Human/animal subjects: give ethics-board name, approval number,
    consent type. If not applicable: "Ethical approval and consent were not
    required."
11. **Competing Interests** — mandatory. Default "No competing interests were
    disclosed" unless the author says otherwise (accepted variant: "Conflict of
    interest").
12. **Grant Information** — extract from `\thanks{...}`/acknowledgments; format
    as project ID + title + grantee for EVERY funder. Cross-check against the
    funders the author declares in the submission-system funding form (the
    editorial office flags any funder in the system but missing here). Ask the
    author to confirm the full funder list.
13. **Author Contributions** — collect a CRediT-taxonomy summary, but note it is
    entered in the ORE web form, NOT written into the manuscript.
14. **Acknowledgments** — optional; no grant funding here (that belongs only in
    Grant Information).

## Phase 3 — Inject content into the LaTeX copy

Write the Phase-2 answers directly into `ore-submission/tex/main.tex`. Keep the
file **compile-clean** (the author reviews it, optionally as a PDF). Do NOT
produce separate `.md` draft files — the `.tex` copy is the single source of
truth.

1. **Abstract** — replace the contents of the `abstract` environment with the
   structured version (bold inline labels `\textbf{Background:}` … through
   `\textbf{Conclusions:}`), citations stripped, abbreviations spelled out,
   <=300 words.
2. **Declarations** — insert the gathered declaration sections immediately
   BEFORE the `\bibliography{...}` line, in ORE order (Data Availability ->
   Ethics and consent -> Competing Interests -> Grant Information ->
   Acknowledgments). If the paper already has a Data Availability section, edit
   it into the ORE format in place rather than duplicating it.
3. **Plain Language Summary** — if the author opted in, add it after the keywords
   block.
4. **Author & affiliation block (no `\thanks` footnotes)** — ORE shows the
   affiliations, all author emails, and the corresponding author as plain lines
   right after the author NAMES, not as footnotes. Rewrite the IEEEtran author
   block with each line separated by `\\`. Include the email of EVERY author
   (not just the corresponding author). There are two layouts:

   **Single shared affiliation** — no superscripts:

   ```latex
   \title{Clean Title On One Line}
   \author{First Last, Second Author, and Third Author \\
   Affiliation, City, Country \\
   Emails: a@domain, b@domain, c@domain \\
   Corresponding author: a@domain}
   ```

   **Multiple affiliations** — put a superscript number after each name with
   `\textsuperscript{}` (comma-separated when an author belongs to several), and
   prefix each affiliation line with the matching `\textsuperscript{}`. Pandoc
   renders `\textsuperscript{}` as a real superscript in the DOCX, and IEEEtran
   does the same in the review PDF:

   ```latex
   \author{First Last\textsuperscript{1}, Second Author\textsuperscript{2}, and Third Author\textsuperscript{1,2} \\
   \textsuperscript{1}First Affiliation, City, Country \\
   \textsuperscript{2}Second Affiliation, City, Country \\
   Emails: a@domain, b@domain, c@domain \\
   Corresponding author: a@domain}
   ```

   The number of distinct affiliation superscripts MUST equal the number of
   affiliation lines (a superscript with no matching affiliation is a common ORE
   rejection — see Phase 2). Delete the `\thanks{...}` blocks (funding already
   lives in Grant Information; affiliations, emails, and corresponding author
   move into `\author` as above). Also strip any `\\` inside `\title{}` — Pandoc
   concatenates across it, joining the words on either side (e.g. "for\\Railway"
   → "forRailway").

   Why `\\` and not `\and`: IEEEtran honours `\\` as real line breaks, so the
   review PDF typesets the author block cleanly. Pandoc, however, DROPS `\\`
   inside `\author{}` (mashing the lines onto one line) and instead renders each
   `\and`-separated chunk as its own ORE "Author" line. `preprocess.pl` (Phase 5)
   bridges this by converting `\\`→`\and` inside `\author{}` on the throwaway
   conversion copy only — so the same author-facing `.tex` yields BOTH a clean
   review PDF and a clean DOCX (names / affiliation / corresponding author on
   separate lines, before the abstract, no footnotes).
5. **Preprint citation in the Introduction** — only if the author answered YES to
   Phase 2 item 7. Add a `@misc`/`@article` entry for the preprint to the copied
   `.bib` (skip if a usable entry already exists) with its DOI or URL, then add
   this sentence as the LAST paragraph of the Introduction, citing that key:

   ```latex
   A previous version of this work was made available as a preprint~\cite{KEY}.
   The present article includes revisions made during the Open Research Europe
   publication process.
   ```

   Keep the wording; adapt only the key. It must land in the Introduction (the
   `\section{Introduction}` body, or the paper's equivalent opening section as
   mapped in Phase 2 item 6), not in the declarations. Do not add it if the author
   said they have no preprint.
6. **Move tables after the references** — ORE requires tables (with legends) in a
   dedicated section AFTER the references. Run the bundled script on the
   author-facing copy (it still has a real `\bibliography` line, so the copy
   keeps compiling):

   ```sh
   perl "$SKILLDIR/scripts/tables.pl" ore-submission/tex/main.tex
   ```

   It relocates every active `\begin{table}...\end{table}` / `table*` block,
   preserving captions/labels, into a new `\section*{Tables}` placed right after
   `\bibliography`. (Commented-out tables are left alone.) Figure legends are
   handled later, at conversion, and land BEFORE this Tables section — see
   Phase 5 — giving the ORE order References -> Figure Legends -> Tables.

## Phase 4 — Author review gate

Tell the author the ORE content is now in `ore-submission/tex/main.tex`: the
restructured abstract, the declaration sections, the preprint sentence in the
Introduction (if they have a preprint), and the relocated Tables section. Invite
them to review/edit it directly (and optionally compile it to a
PDF to eyeball). **Pause for their confirmation** before converting. Anything
they change in the `.tex` flows straight through the conversion.

## Phase 5 — Convert to DOCX (fidelity-aware)

This is a proven mechanical recipe — apply it as-is; do not improvise alternative
Pandoc flags. It uses five bundled scripts and a bundled CSL file:

- `scripts/enrich_reference.py` — builds a reference `.docx` that defines EVERY
  paragraph/table style Pandoc emits, matched to the ORE look (see "Why the
  enriched reference" below). Run it against the base template each time.
- `scripts/preprocess.pl` — strips constructs Pandoc's LaTeX reader chokes on and
  anchors the reference list (see its list below).
- `scripts/figures.pl` — strips figure images and relocates figure legends,
  placing them before the Tables section.
- `scripts/postprocess.py` — OOXML fixups Pandoc + the reference doc cannot
  express: numbers body equations, numbers figure legends and tables, adds
  spacing between tables, and retypes the Keywords heading (see "What
  postprocess.py does" below). Runs on the finished `manuscript.docx`.
- `scripts/verify_styles.py` — fails if any style used in the output is undefined
  in the enriched reference (the orphan-style guard).
- `assets/ieee.csl` — bundled IEEE CSL so citeproc works offline. Its
  `<bibliography>` has NO `second-field-align="flush"`, so each reference reads
  `[n] Text` with a single space (the flush variant put `[n]` in its own column
  with a wide tab gap); the citation-number carries a trailing-space suffix.

### Sequence (adapt bib names to the paper; run from the paper directory)

```sh
SKILLDIR=~/.claude/skills/latex-to-ore

# 1. Build the enriched reference doc from the base ORE template (idempotent).
python "$SKILLDIR/scripts/enrich_reference.py" \
  ore-submission/ore-template.docx ore-submission/ore-reference-enriched.docx

# 2. Work on a THROWAWAY copy of the edited author .tex — never convert the
#    author-facing copy in place.
cp ore-submission/tex/main.tex _ore_work.tex
perl "$SKILLDIR/scripts/preprocess.pl" _ore_work.tex
perl "$SKILLDIR/scripts/figures.pl"    _ore_work.tex

# 3. Convert with the ENRICHED reference doc (not the bare template).
pandoc _ore_work.tex --from=latex --to=docx --citeproc \
  --bibliography=IEEEabrv.bib \
  --bibliography=references.bib \
  --csl="$SKILLDIR/assets/ieee.csl" \
  --reference-doc=ore-submission/ore-reference-enriched.docx \
  --resource-path=ore-submission/tex \
  --output=ore-submission/manuscript.docx
rm _ore_work.tex

# 4. OOXML fixups on the finished DOCX (equation/figure/table numbering, table
#    spacing, Keywords heading). Idempotent; safe to re-run.
python "$SKILLDIR/scripts/postprocess.py" ore-submission/manuscript.docx

# 5. Guard: every paragraph/table style used must be defined in the reference.
python "$SKILLDIR/scripts/verify_styles.py" \
  ore-submission/manuscript.docx ore-submission/ore-reference-enriched.docx
```

- `--bibliography` filenames are per-paper — use the actual names from the
  `\bibliography{...}` line. `--resource-path` points at the copied project so
  any residual asset resolves; `figures.pl` strips images anyway.
- Reference path: citeproc + CSL, **not** inlining the `.bbl`. Inlining `.bbl`
  breaks in-text numbering (blank instead of `[n]`) and yields an unnumbered
  list; citeproc + `--bibliography`/`--csl` is the only proven-correct path.
- **If `verify_styles.py` fails**, it names each orphan style. Add a derivation
  for it to `enrich_reference.py` (`PANDOC_STYLES`), rebuild the enriched
  reference, and reconvert. Do not ship a doc with orphan styles.

### Why the enriched reference (the fidelity fix)

Pandoc's `--reference-doc` applies a style only when the element's style *name*
already exists in the reference doc. The stock ORE template defines just a few
styles (`Title`, `Heading1/2`, `BodyText`, `PlainTable1`, …), so everything else
Pandoc emits (`Compact`, `FirstParagraph`, `Author`, `Abstract`, `Heading3`,
`Table`, `FigureTable`, captions, `Bibliography`, …) falls back to Pandoc's
Calibri/black defaults — which is why an un-enriched conversion ignores the ORE
blue headings, fonts, spacing, and table style. `enrich_reference.py` adds a
definition for each missing style, `basedOn` an existing ORE style, so it
inherits the ORE design (Arial blue headings, Cambria body, ORE table borders).
It is add-only and idempotent, so it is safe against any template version.

`enrich_reference.py` also carries a small `STYLE_PATCHES` map that OVERRIDES a
few properties on styles the template already defines (or that the enrichment
pass just added): the `Title` is made centered + ORE blue (`004494`, matching the
section headings) with breathing room; `Heading1`/`Heading2` get real `spacing`
before AND after so headings don't jam into the surrounding paragraphs
(`Heading3`/`Heading4` are patched separately — see "Heading hierarchy" below,
and `Heading5+` inherit from `Heading4`); `AbstractTitle` is coloured
ORE blue so the "Abstract" heading — and the "Keywords" heading `postprocess.py`
retypes to `AbstractTitle` — match the blue section headings; `BodyText` gets a
real space-after (6 pt) so consecutive body paragraphs are visibly separated
(the stock template's near-zero spacing makes paragraphs sit flush), while
`Compact` — Pandoc's tight-list / table-cell paragraph style — is pinned to 0/0
so lists and table cells stay tight. (`AbstractTitle` and `Compact` are
add-enriched first, so they exist by the time the patch runs.) The patcher rewrites
only the managed child elements, in OOXML schema order, and is idempotent. To
change the title colour/alignment or the heading spacing, edit `STYLE_PATCHES`
(values are twips; 1 pt = 20 twips) and rebuild the enriched reference.

### Heading hierarchy

The stock ORE template defines only TWO heading levels, so any paper with
`\subsubsection` needs level 3 supplied by this skill. Previously `Heading3` was
enriched as a bare `basedOn Heading2` with no overrides, which made a
`\subsubsection` typographically IDENTICAL to a `\subsection` in the DOCX.
`STYLE_PATCHES` now gives each level its own look, staying inside the ORE design
language (Arial throughout, black below level 1, progressive left indent):

| LaTeX | Style | Look |
|---|---|---|
| `\section` | `Heading1` | Arial bold, ORE blue `004494`, 10.5 pt (template) |
| `\subsection` | `Heading2` | Arial bold, black, 9 pt, indent 100 (template) |
| `\subsubsection` | `Heading3` | Arial **bold italic**, black, 9 pt, indent 220 |
| `\paragraph` (+deeper) | `Heading4`+ | Arial *italic*, not bold, 9 pt, indent 340 |

Bold → bold-italic → italic is the conventional academic step-down: each level
reads as subordinate without adding a font or colour ORE does not use. The
patcher supports `ind`, `bold`, and `italic` keys alongside `spacing`/`jc`/
`color`; `bold: False` emits an explicit `w:val="0"` because merely omitting
`<w:b/>` would NOT cancel the bold inherited through `basedOn`. If a future ORE
template ships its own level-3 style, the enrichment pass leaves it alone (it
never overwrites a style the template defines) — adjust `STYLE_PATCHES` to match.

Separately, `patch_doc_defaults` lowers the document-default run size to the ORE
body size (`DOC_DEFAULT_SZ`, 19 half-pt = 9.5 pt). Pandoc emits list-item
paragraphs with NO paragraph style, so they inherit `Normal` → `docDefaults`,
which the stock template leaves at 22 (11 pt) — visibly larger than the 9.5 pt
body. Every heading/title/body style sets its own explicit size, so only the
unstyled paragraphs (list items) are affected, and they now match the body.

### What `preprocess.pl` does (extend for new papers' macros)

1. Strips `\makeatletter...\makeatother` blocks (e.g. `\@startsection`
   redefinitions Pandoc leaks as literal glue text on headings).
2. Deletes the `\bibliographystyle{...}` line.
3. **Replaces** the `\bibliography{...}` line with `\section*{References}` +
   `\hypertarget{refs}{}` — the `\hypertarget` anchors citeproc's reference list
   at that point (Pandoc turns it into a `#refs` Div; without it citeproc appends
   references at the very end, AFTER the Figure Legends/Tables, breaking ORE
   order), and the `\section*{References}` gives the list a proper ORE heading
   (citeproc emits none). Order becomes References -> Figure Legends -> Tables.
4. Converts the `IEEEkeywords` environment to `\section*{Keywords}` + the keyword
   list, so the keywords get a heading (`postprocess.py` then retypes that
   heading to `AbstractTitle` to match the abstract). Without it the keywords
   render as a bare, unlabelled paragraph.
5. Strips `\begin{IEEEbiographynophoto}...\end{IEEEbiographynophoto}` blocks.
6. `\IEEEPARstart{X}{ext}` -> `Xext`.
7. Removes `\bstctlcite{...}`, `\balance`, `\IEEEpeerreviewmaketitle`.
8. Unwraps `\hlyellow{}`/`\hlgreen{}`/`\hlpink{}`/`\hlred{}`/`\review{}` to inner
   text.
9. Converts `\\` -> `\and` inside `\author{}` so the affiliation/corresponding
   author lines survive as separate ORE "Author" lines (Pandoc drops `\\` there).
   See Phase 3 step 4.
10. **De-stars floats**: `table*` -> `table`, `figure*` -> `figure`. The star only
    requests a two-column-spanning float and is meaningless for the single-column
    DOCX — but Pandoc's LaTeX reader fails to associate the `\caption` inside a
    `table*` with the table, so a starred table converts WITHOUT its caption (and
    is therefore not numbered, which ALSO breaks the in-text `\ref` to it).
    Dropping the star restores the caption.
11. **Unwraps `\resizebox{W}{H}{ ... }` and `\rotatebox[..]{angle}{ ... }`** to
    their inner content (a self-recursive `$nested` regex matches the balanced
    brace group). IEEE papers routinely wrap wide tables in
    `\resizebox{\columnwidth}{!}{ \begin{tabular} ... }` and rotate header cells
    with `\rotatebox{90}{...}`; Pandoc does not look inside `\resizebox`, so the
    tabular becomes an unparsed argument and the whole table (caption included) is
    dropped. Removing the wrappers exposes the plain tabular for conversion.
12. **Demotes thousands-separated inline math to plain text**: `$5{,}915$` ->
    `5,915`, `$245{,}000$` -> `245,000`. IEEE authors write these in math mode so
    LaTeX kerns the separator, but Pandoc converts them to OMML and Word then
    typesets the comma as a math punctuation operator, inserting a space after it
    ("5, 915"). They are not equations, so unwrapping the `$...$` and dropping the
    `{}` braces yields a normally spaced number. The pattern is deliberately
    narrow — 1 to 3 digits followed by one or more `{,}` + exactly-3-digit groups,
    and nothing else between the `$` — so any inline math carrying real operators
    or symbols is left alone.

If a new paper uses other custom macros Pandoc chokes on, add a numbered step to
`scripts/preprocess.pl` (regex strip or unwrap) rather than hand-editing the
`.tex` copy.

### What `postprocess.py` does (OOXML fixups on the finished DOCX)

Runs on `manuscript.docx` after Pandoc, for ORE house-style requirements that
Pandoc + the reference doc cannot express. Deterministic and idempotent:

1. **Keywords heading** — retypes the `Keywords` Heading1 (from preprocess step 4)
   to the `AbstractTitle` style, so it matches the blue "Abstract" heading.
2. **Equation numbers** — Pandoc/texmath DROPS LaTeX equation numbers. Every
   DISPLAY equation in the body (an `<m:oMathPara>` NOT inside a `<w:tbl>`) gets a
   right-aligned `(N)` via a centre tab + right tab, so the equation stays centred
   and the number sits at the right margin like the ORE template. Numbers that
   Pandoc rendered as math inside table cells (e.g. `$38{,}551{,}161$`) are NOT
   equations and are left alone — the script masks table blocks before numbering.
3. **Figure legends** — Pandoc wraps every figure in a layout table: a no-image
   figure becomes an empty `<w:tbl>` + caption paragraph (harmless), but a
   subfigure figure becomes a real multi-column `<w:tbl>` with each subcaption
   trapped in a cell (reads as a stray boxed table). The whole "Figure Legends"
   section is ORE legends with no genuine data tables, so ALL its `FigureTable`
   scaffolding is stripped (keeping the caption paragraphs), then each
   `ImageCaption` paragraph is prefixed with a bold `Figure N. ` in document order.
4. **Tables** — each table's caption is MOVED to AFTER its `<w:tbl>` (Pandoc emits
   it before), prefixed with a bold `Table N. ` in document order, and given
   spacing (small before, larger after) so consecutive tables are separated. Data
   tables are not nested, so the caption/table swap is a safe non-greedy match.

Figure/table numbers follow the same document order Pandoc uses to number the
in-text `Figure N`/`Table N` cross-references, so legends stay consistent with the
body. **Subfigure caveat:** Pandoc counts each `\label` — including subfigure
sub-labels — as its own figure, so a paper with subfigures shows more numbered
legends than distinct figures (e.g. a two-panel "Figure 7" becomes legends 7, 8, 9
and the body refs match). This is Pandoc's cross-reference numbering; flag it for
author review rather than trying to re-group.

### Figure legends (handled by `figures.pl`)

Every `\includegraphics` line is stripped and each figure's caption/label is
relocated into a `\section*{Figure Legends}` block. If a `\section*{Tables}`
section exists (Phase 3), the legends are inserted immediately before it;
otherwise before `\end{document}`. `\label{}` is moved (not duplicated) so
`\ref{fig:...}` cross-references still resolve. Zero images are embedded —
PDF-sourced figures embed as raw bytes Word cannot rasterize, and ORE wants
figures as separate files anyway (Phase 6). The `Figure N. ` legend numbering is
added later by `postprocess.py`, not here.

### Known limitations — flag to the author

- **Piecewise/matrix math:** `cases`/`matrix` environments usually convert to
  native OOXML but may render flattened (the piecewise brace collapsed onto one
  line) rather than as raw TeX. Surface it as an author-review item; do not
  auto-fix it. (If a construct DID leak as raw TeX, add an unwrap step to
  `preprocess.pl` instead.)
- **Subfigure numbering:** with subfigures, Pandoc numbers each sub-label as its
  own figure, so both the body refs and the numbered legends count more "figures"
  than there are panels (see `postprocess.py` above). Consistent between body and
  legends, but differs from the review PDF's `7a`/`7b` scheme — flag for review.

## Phase 6 — Package assembly

1. Confirm `ore-submission/manuscript.docx` was written and `verify_styles.py`
   passed.
2. **Verify figure completeness** — cross-check every in-text figure citation
   (`\ref{fig:...}` / "Figure N") against the figure environments that exist.
   Flag any figure cited but not provided, and any figure provided but never
   cited (ORE rejects both).
3. **Ask the author how to handle figure files** — (a) **keep as-is** (copy
   originals unchanged), (b) **convert to JPEG**, or (c) **convert to TIFF** (ORE
   print quality: 300 dpi colour / 600 dpi greyscale, auto-detected). For each
   **cited** figure, take its source path from the `\includegraphics{PATH}`
   command (resolved against `ore-submission/tex/`) — do NOT assume a `figs/`
   folder.
   - **Keep as-is:** copy to `ore-submission/figures/FigureN` (same extension),
     renamed in citation order (subfigures `Figure1a`, `Figure1b`). Flag any not
     already TIFF/JPEG at print quality.
   - **Convert:** run the bundled converter per figure —
     ```sh
     python "$SKILLDIR/scripts/convert_figure.py" "<source path>" \
       "ore-submission/figures/FigureN" <jpeg|tiff>
     ```
     It rasterizes PDF/EPS via poppler `pdftocairo` and writes JPEG/TIFF at
     300/600 dpi with DPI embedded (needs Pillow; `pdftocairo` for vector
     sources). On a missing-dependency exit (2), fall back to keep-as-is for that
     figure and tell the author what to install (`pip install Pillow`; poppler).
4. **Tables** — already relocated to a "Tables" section after the references by
   Phase 3 / conversion. Legends and the References -> Figure Legends -> Tables
   ordering are verified mechanically in Phase 7; do not hand-wave them here.
5. Copy `references/ore-checklist-template.md` to
   `ore-submission/SUBMISSION-CHECKLIST.md`, filling `{{PAPER_TITLE}}` and
   `{{DATE}}`, marking each item done / needs-input / N/A based on what the run
   produced.
6. **Data deposit** — remind the author the underlying data must be deposited in
   an approved repository (Zenodo/figshare, CC BY/CC0) and its DOI added to the
   Data Availability statement. Point to `references/data-package-structure.md`;
   offer to scaffold an empty deposit folder.
7. Print a summary: package contents and remaining author to-dos — the
   equation-review flag (cases/matrix math may show as raw TeX), any figures
   flagged for re-export, the ORE preprint self-citation to add later (and, if
   the author has an existing preprint, confirmation that it is cited in the
   Introduction with its final DOI), the funder
   cross-check, the data-deposit DOI, and any Phase 2 items left as "needs your
   input".

## Phase 7 — Verify the manuscript & get approval

Everything up to here checked the *inputs*: Phase 4 reviewed the `.tex` before
conversion, and `verify_styles.py` checked style NAMES. This phase checks the
**deliverable itself** — what actually landed in `manuscript.docx` — and is the
gate that Phase 8's deletion depends on. Do not skip it.

1. **Run the compliance verifier** on the finished package:

   ```sh
   python "$SKILLDIR/scripts/verify_manuscript.py" \
     ore-submission/manuscript.docx ore-submission/figures
   ```

   It reads `word/document.xml` and checks: ORE section order, the four
   mandatory declarations, the structured abstract (labels, <=300 words, no
   citations), that the reference list exists and sits BEFORE the figure legends,
   that every figure legend and table legend is numbered, that no raw LaTeX
   leaked, that no images are embedded, and that the enriched reference doc was
   really applied. It exits non-zero on any compliance failure.

   The order check matters most: if `preprocess.pl`'s `\hypertarget{refs}{}`
   anchor fails to take, citeproc appends the references at the very END —
   after the Figure Legends and Tables — which breaks ORE order invisibly. A
   `.tex` review cannot catch this; only reading the DOCX can.

2. **On FAIL, fix and reconvert — do not ship it.** Each failure names its
   cause: a missing declaration goes back to Phase 3, leaked LaTeX needs a new
   rule in `preprocess.pl`, missing numbering means `postprocess.py` did not
   run, and a missing ORE blue means the conversion did not use the enriched
   reference. Re-run Phase 5, then verify again. Report WARNs to the author
   rather than acting on them alone (subfigures legitimately inflate the legend
   count).

3. **Visual check against the ORE template** — the scripts verify structure and
   style *names*; they cannot see spacing or colour drift. Render/inspect
   `manuscript.docx` and compare against `ore-submission/ore-template.docx`:
   heading colour and hierarchy, body font and size, the abstract and keywords
   blocks, table borders, and the equation numbering alignment. Report what you
   compared and anything that looked off.

4. **Present the manuscript for approval and PAUSE.** Show the verifier output,
   the visual findings, and the outstanding checklist items, then ask the author
   to review `ore-submission/manuscript.docx` and confirm it is final. Phase 8
   deletes the LaTeX working copy, so do not proceed on anything less than an
   explicit approval.

## Phase 8 — Cleanup (only after the author approves the manuscript)

Once the author has reviewed `ore-submission/manuscript.docx` and **explicitly
says it is approved/final**, remove the intermediate build material so the
package contains only what is submitted.

**Ask first, then delete.** Do not run this on your own initiative, and never as
part of Phase 7 — if the author has not said the manuscript is approved, stop and
ask. If they want to keep the LaTeX copy, skip this phase entirely.

Delete:

- `ore-submission/tex/` — the *copied* LaTeX working folder created in Phase 1.
- `ore-submission/ore-template.docx` — the downloaded base ORE template.
- `ore-submission/ore-reference-enriched.docx` — the generated reference doc.
- Any stray `_ore_work.tex` left in the paper directory.

Keep:

- `ore-submission/manuscript.docx`
- `ore-submission/figures/`
- `ore-submission/SUBMISSION-CHECKLIST.md` — **never delete the checklist**; it
  carries the author's remaining to-dos.

<EXTREMELY-IMPORTANT>
Delete ONLY inside `ore-submission/`. The author's original `.tex`, `.bib`,
`.cls`, `.bst`, and figure files in the paper directory (and anywhere else) are
NEVER touched — Phase 1 copied them, so the copy is disposable but the originals
are not. Verify each path you delete starts with `ore-submission/` before
running the command. If a path is ambiguous, ask instead of deleting.
</EXTREMELY-IMPORTANT>

```sh
# from the paper directory; verify these paths first
rm -rf ore-submission/tex
rm -f  ore-submission/ore-template.docx ore-submission/ore-reference-enriched.docx
rm -f  _ore_work.tex
```

Then list what remains in `ore-submission/` so the author can confirm the final
package. Note that re-running the conversion later would require re-doing
Phases 1–5 (the template re-downloads automatically; the LaTeX copy does not).
