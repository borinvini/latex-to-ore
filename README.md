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
tedious and easy to get wrong.

Naively running `pandoc paper.tex -o paper.docx` does not work. The output loses
equation numbers, drops captions on `table*` floats, silently deletes tables
wrapped in `\resizebox`, mashes the author block onto one line, appends the
reference list in the wrong place, and — because Pandoc only applies a style
that already exists in the reference document — renders almost everything in
Calibri black instead of the ORE house style.

This skill encodes the fixes for all of that as a repeatable pipeline, and it
covers **every rule in the ORE Research Article guidelines** — see
[ORE compliance coverage](#ore-compliance-coverage) for the requirement-by-requirement
mapping.

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
Phase 7  Verify the finished .docx: ORE compliance read back off the Word
   |     file · visual check against the template
   |     ==== APPROVAL GATE ====  you review manuscript.docx and confirm
   |
Phase 8  ==== CLEANUP ====  only after you approve the manuscript:
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
git clone https://github.com/borinvini/latex-to-ore.git ~/.claude/skills/latex-to-ore
```

Windows (PowerShell):

```powershell
git clone https://github.com/borinvini/latex-to-ore.git "$env:USERPROFILE\.claude\skills\latex-to-ore"
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

## ORE compliance coverage

**The skill implements the ORE Research Article guidelines in full.** The rules
are not scattered through the code — they are written down as a single
authoritative reference, [`references/ore-guidelines.md`](references/ore-guidelines.md),
which the skill loads at Phase 2 and works through item by item. That file is
transcribed from the public *Preparing a Research Article* guidelines **plus** the
requirements from a real ORE editorial pre-publication check, which in a few
places go beyond what the public page states.

Every requirement in that reference is covered by the pipeline. Nothing is left
to the model's memory of what ORE wants:

| ORE requirement | How the skill satisfies it |
|---|---|
| **Section order** — authors → title → abstract → keywords → PLS → body → declarations → references → figure legends → tables | Enforced structurally: Phase 3 injects the declarations before `\bibliography`, `tables.pl` moves tables after the references, and `figures.pl` places the legends between them |
| **Structured abstract** — Background / Methods / Results / Conclusions, ≤300 words, no citations, abbreviations expanded | Drafted for your approval in Phase 2, written into the `.tex` in Phase 3 |
| **Keywords** — up to 8 | Pulled from `\IEEEkeywords` (or equivalent), trimmed to 8, given a proper ORE-styled heading |
| **Plain Language Summary** — recommended | Offered and drafted on request; placed after the keywords |
| **Main body** — standard IMRaD, ≤15,000 words | Section mapping confirmed with you; never silently renamed |
| **Preprint self-citation** | Recorded as an explicit to-do on the checklist (the DOI does not exist until after submission) |
| **Data Availability** — mandatory even with no data | Written in ORE's exact required format: *Underlying data* + *Extended data* subsections, per-file descriptions, DOI, closing CC BY 4.0 / CC0 licence sentence |
| **Open Data policy** — values behind means/SDs and every figure, points extracted from images, data dictionary; DOI required; no embargo, no login wall | Walked through in Phase 2; non-approved repositories (e.g. Kaggle) are flagged with a Zenodo/figshare/Dryad/OSF recommendation |
| **Ethics and consent** — dedicated section immediately after Data Availability | Board name, approval number and consent type collected; otherwise the exact required "Ethical approval and consent were not required." |
| **Competing Interests** — mandatory | Defaults to "No competing interests were disclosed" unless you say otherwise |
| **Grant Information** — every funder, project ID + title + grantee | Extracted from `\thanks{}`/acknowledgments, then cross-checked with you against the funders you declare in the submission form (the editorial office flags mismatches) |
| **Author Contributions** — CRediT | Collected, and you are told explicitly it goes in the web form, *not* the manuscript |
| **Acknowledgments** — optional, no funding | Kept optional; funding is routed to Grant Information only |
| **Supplementary material** — not accepted | Never produced; extended data is directed to the repository deposit instead |
| **Authors block** — affiliations listed, superscripts matching the affiliation count, corresponding author after the affiliations | Author block rewritten to ORE's layout with every author's email; superscript count validated against the affiliation count (a common rejection); `\thanks{}` footnotes removed |
| **References** — consistent style, datasets in the reference list | IEEE numbered style via the bundled CSL and citeproc |
| **Figures** — separate files, TIFF/JPEG, 300 dpi colour / 600 dpi greyscale, removed from the body, legends collected at the end, every figure both cited and supplied | Images stripped from the manuscript, legends collected and numbered, files exported at the right DPI in citation order, and a cited-vs-supplied cross-check run in both directions |
| **Tables** — native Word tables with legends, after the references | Relocated by `tables.pl`, converted as real Word tables, captions moved below and numbered |
| **Data repository deposit** — the second half of the submission | Reminded, with a recommended deposit layout in [`references/data-package-structure.md`](references/data-package-structure.md); the folder can be scaffolded for you |
| **Eligibility** — EU-funded project | Surfaced on the checklist; this one is yours to confirm |

Anything that cannot be settled automatically — a missing data DOI, an unclear
funder list, the preprint citation — is not quietly skipped. It lands in
`SUBMISSION-CHECKLIST.md` marked **needs your input**, so the package always
tells you exactly what is outstanding.

And the compliance is **checked against the deliverable, not just applied to the
input**. Phase 7 runs `verify_manuscript.py`, which reads `word/document.xml`
back out of the finished `.docx` and re-asserts ORE section order, the mandatory
declarations, the structured abstract, reference-list placement, figure and
table legend numbering, and that the ORE styling was really applied. It exits
non-zero on any failure, so a non-compliant package stops the pipeline instead
of reaching the submission form.

If ORE updates its guidelines, edit `references/ore-guidelines.md`: it is the
single place the rules live, and the pipeline follows it.

## Conversion fidelity

Beyond the content rules, the skill fixes what Pandoc gets wrong on the way to
Word:

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

## Known limitations

These are cosmetic conversion artefacts, not compliance gaps — each one is
flagged for your review rather than silently shipped:

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
scripts/verify_manuscript.py          reads ORE compliance back off the .docx
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
