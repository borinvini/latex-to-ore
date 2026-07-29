# latex-to-ore

A [Claude Code](https://claude.com/claude-code) skill that turns a LaTeX paper
into a complete, submission-ready package for
[Open Research Europe (ORE)](https://open-research-europe.ec.europa.eu/).

## Why this exists

ORE is an open-access publishing venue with a **Word-only** submission route and
a long list of house rules: a structured abstract, mandatory declaration
sections in a fixed order, tables moved after the references, figures as
separate print-quality files, a specific author/affiliation layout, and a strict
open-data policy. Getting a LaTeX manuscript through that gauntlet by hand is
tedious and easy to get wrong — most ORE desk rejections are formatting and
declaration problems, not science problems.

Naively running `pandoc paper.tex -o paper.docx` does not work. The output loses
equation numbers, drops captions on `table*` floats, silently deletes tables
wrapped in `\resizebox`, mashes the author block onto one line, appends the
reference list in the wrong place, and — because Pandoc only applies a style
that already exists in the reference document — renders almost everything in
Calibri black instead of the ORE house style.

This skill encodes the fixes for all of that as a repeatable pipeline.

## The approach: LaTeX-first

Every ORE content change is made **in a copy of your LaTeX project**, not in a
`.docx`. That means you can read the diff, compile the copy to a PDF to check
it, and edit it like normal LaTeX before anything is converted. Word conversion
is the last step, and it is mechanical.

Two guarantees:

- **Your original project is never modified.** Everything happens inside a new
  `ore-submission/` folder.
- **Nothing is deleted without your approval.** Cleanup is a separate final
  phase you have to explicitly authorise.

## Pipeline

```
Phase 0  Detect main .tex / .bib / figures · verify Pandoc · fetch ORE template
   |
Phase 1  Copy the whole LaTeX project -> ore-submission/tex/   (still compiles)
   |
Phase 2  ORE compliance Q&A — abstract, keywords, plain language summary,
   |     Data Availability, Ethics, Competing Interests, Grant Information
   |
Phase 3  Inject the answers INTO ore-submission/tex/main.tex:
   |     structured abstract · declaration sections · author block rewrite ·
   |     tables relocated after the references
   |
Phase 4  ==== REVIEW GATE ====  you read/edit the .tex; nothing proceeds
   |                            until you confirm
   |
Phase 5  Convert .tex -> manuscript.docx
   |     enrich reference template · preprocess · strip & relocate figure
   |     legends · pandoc + citeproc · OOXML fixups · style verification
   |
Phase 6  Package: figures at print DPI · submission checklist ·
   |     data-deposit reminder · completeness report
   |
Phase 7  ==== CLEANUP GATE ====  only after you approve the manuscript:
         delete the working copy and templates, keep the deliverables
```

### What you get

```
ore-submission/
├── manuscript.docx            # ORE-styled Word manuscript
├── figures/
│   ├── Figure1.tif
│   └── Figure2.tif            # renamed in citation order, 300/600 dpi
└── SUBMISSION-CHECKLIST.md    # per-item status + your remaining to-dos
```

## Install

The skill reads its own bundled scripts from a fixed path, so **the directory
name must be `latex-to-ore`**.

```sh
git clone https://github.com/<you>/latex-to-ore.git ~/.claude/skills/latex-to-ore
```

Windows (PowerShell):

```powershell
git clone https://github.com/<you>/latex-to-ore.git "$env:USERPROFILE\.claude\skills\latex-to-ore"
```

Restart Claude Code (or start a new session) and the skill is available.

### Prerequisites

| Tool | Needed for | Install |
|---|---|---|
| **Pandoc** | LaTeX → DOCX conversion (Phase 5) | [pandoc.org/installing](https://pandoc.org/installing.html) |
| **Perl** | `preprocess.pl`, `figures.pl`, `tables.pl` | preinstalled on macOS/Linux; [Strawberry Perl](https://strawberryperl.com/) on Windows |
| **Python 3** | styling and packaging scripts | [python.org](https://www.python.org/) |
| **Pillow** | figure conversion (Phase 6) | `pip install Pillow` |
| **poppler** (`pdftocairo`) | rasterizing PDF/EPS figures | `brew install poppler` · `apt install poppler-utils` · [Windows builds](https://github.com/oschwartz10612/poppler-windows) |
| A LaTeX distribution | *optional* — only to compile the review PDF at Phase 4 | TeX Live / MiKTeX |

Only Pandoc and Perl are hard requirements. Pillow and poppler are needed only
if you ask the skill to convert figures; without them it falls back to copying
your figure files unchanged.

## Usage

Run Claude Code from the directory containing your paper and just ask:

```
> convert my paper to an ORE submission
```

Other phrasings that trigger it:

```
> I want to submit this to Open Research Europe — prepare the package
> turn main.tex into an ORE manuscript
```

You can also invoke it explicitly with `/latex-to-ore`.

### What the session looks like

```
you  > convert this paper for Open Research Europe

     Found main.tex (\documentclass{IEEEtran}) and references.bib.
     Your figures appear to be in figs/ — is that correct?

you  > yes

     Pandoc 3.1.11 OK. Downloaded the ORE Article Template.
     Copied the project to ore-submission/tex/.

     A few ORE requirements to settle:
     1. Structured abstract — here is a draft rewritten as
        Background / Methods / Results / Conclusions (287 words) ...
     2. Data Availability is mandatory even with no new data. Where is your
        underlying data deposited?

you  > it's on Kaggle

     ORE requires an approved repository (Zenodo / figshare / Dryad / OSF)
     with CC BY or CC0 and no login wall — Kaggle will be flagged. I
     recommend a Zenodo deposit; I can scaffold the folder structure.
     ...

     [Phase 4] ore-submission/tex/main.tex now has the restructured
     abstract, the five declaration sections, and the Tables section moved
     after the references. Review or edit it, then tell me to continue.

you  > looks good, convert it

     ✓ manuscript.docx written · style verification passed (0 orphan styles)
     ✓ 6 figures → ore-submission/figures/ as 600 dpi TIFF
     ✓ SUBMISSION-CHECKLIST.md written

     Remaining to-dos:
     - Deposit data on Zenodo and add the DOI to Data Availability
     - Review Equation (4): the piecewise brace may have flattened
     - Add your preprint self-citation once ORE assigns the DOI
```

### Resuming

Each phase leaves its state on disk, so you can stop after the review gate and
come back later — point a new session at the same paper directory and ask it to
continue from `ore-submission/`.

## What it handles for you

**Compliance**
- Structured abstract (Background / Methods / Results / Conclusions, ≤300 words,
  no citations, abbreviations expanded)
- The five declaration sections in ORE's required order: Data Availability →
  Ethics and consent → Competing Interests → Grant Information →
  Acknowledgments
- Author block rewritten to ORE's layout — affiliations, all author emails and
  the corresponding author as plain lines after the names, with superscripts
  validated against the affiliation count (a common rejection cause), and
  `\thanks{}` footnotes removed
- Open-data policy check, including flagging non-approved repositories
- Cross-check that every figure is both cited and provided
- CRediT author contributions collected (they go in ORE's web form, not the
  manuscript)

**Conversion fidelity**
- An *enriched* reference document that defines every style Pandoc emits, so the
  output actually inherits the ORE look instead of Pandoc's Calibri defaults
- Equation numbers restored (Pandoc drops them) as right-aligned `(N)`
- Figure legends relocated to a "Figure Legends" section and numbered; images
  stripped, since ORE wants figures as separate files
- Table captions moved below their tables and numbered; `table*` de-starred so
  captions survive; `\resizebox`/`\rotatebox` wrappers unwrapped so wide tables
  are not silently dropped
- Reference list anchored in the right position, giving the ORE section order
  References → Figure Legends → Tables
- A style-verification guard that fails the build if any style in the output is
  undefined in the reference document

**Packaging**
- Figures rasterized to ORE print quality — 300 dpi colour / 600 dpi greyscale,
  auto-detected — and renamed in citation order
- A filled-in submission checklist with per-item status

## Known limitations

- **Subfigures:** Pandoc counts each `\label` as a separate figure, so a
  two-panel figure produces more numbered legends than there are panels. Body
  references and legends stay consistent with each other, but differ from the
  review PDF's `7a`/`7b` scheme. Flagged for your review rather than auto-fixed.
- **Piecewise / matrix math:** `cases` and `matrix` environments usually convert
  to native OOXML but may render flattened. Flagged for review.
- Tested primarily against **IEEEtran** papers. Other document classes work, but
  unusual custom macros may need a new strip/unwrap rule (see below).

## Repository layout

```
SKILL.md                              the skill itself — the full pipeline
assets/ieee.csl                       bundled IEEE CSL (offline citeproc)
references/ore-guidelines.md          authoritative ORE rules
references/ore-checklist-template.md  submission checklist template
references/data-package-structure.md  how to structure the data deposit
scripts/enrich_reference.py           builds the ORE-styled reference .docx
scripts/preprocess.pl                 strips LaTeX constructs Pandoc chokes on
scripts/figures.pl                    strips images, relocates figure legends
scripts/tables.pl                     moves tables after the references
scripts/postprocess.py                OOXML fixups on the finished .docx
scripts/verify_styles.py              orphan-style guard
scripts/convert_figure.py             figure → 300/600 dpi TIFF/JPEG
```

## Extending

If a paper uses a custom macro Pandoc mishandles, add a numbered rule to
`scripts/preprocess.pl` rather than hand-editing the converted `.tex` — that
keeps the pipeline reproducible for the next paper.

If `verify_styles.py` reports an orphan style, add a derivation for it to
`PANDOC_STYLES` in `scripts/enrich_reference.py`, rebuild the enriched
reference, and reconvert. Visual tweaks (title colour, heading spacing) live in
`STYLE_PATCHES` in the same file.

Issues and pull requests welcome — especially conversion fixes for document
classes beyond IEEEtran.

## License

MIT — see [LICENSE](LICENSE).

`assets/ieee.csl` is third-party content under CC BY-SA 3.0 and the ORE Word
template is downloaded at run time rather than bundled; see
[NOTICE.md](NOTICE.md).

*Not affiliated with or endorsed by Open Research Europe, the European
Commission, or F1000 Research. Always check the
[current ORE author guidelines](https://open-research-europe.ec.europa.eu/for-authors/article-guidelines)
before submitting.*
