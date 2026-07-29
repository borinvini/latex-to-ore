# ORE Research Article — Requirements (offline reference)

Sources: Open Research Europe "Preparing a Research Article" (STM) guidelines,
captured 2026-07-28; plus requirements from a real ORE editorial pre-publication
check email (2026) — the latter reflects what the editorial office actually
enforces and sometimes goes beyond the public guidelines page.

## Section order
Authors (+ affiliations, corresponding author) → Title → Abstract → Keywords →
Plain Language Summary (recommended) → Main body → **Declarations block at the
end, before References**: Data Availability → Ethics and consent → Competing
Interests → Grant Information → Acknowledgments (optional) → References →
Figure legends (at end) → Tables (with legends, AFTER references).

## Manuscript rules
- Abstract: structured (Background / Methods / Results / Conclusions), NO citations,
  spell out abbreviations. Word limit: the public guideline says <=300 words; a 2026
  editorial email stated <=350. Keep to <=300 to be safe. Must accurately reflect
  the manuscript.
- Keywords: up to 8.
- Plain Language Summary: recommended, not required.
- Main body: flexible; standard = Introduction / Methods / Results / Conclusions-Discussion.
  <=15,000 words. Enough detail to reproduce. Proprietary software → cite an
  open-source equivalent; author-written code must be open-source-compatible.
- PREPRINT SELF-CITATION: ORE publishes your article as a preprint before peer
  review. The editorial office asks authors to CITE the preprint version of their
  own article in the manuscript. Add it to the references once the preprint DOI
  is known.

## Declarations (all go at the END, before References)
- Data Availability (MANDATORY, even if no data): title it "Data Availability".
  F1000/ORE Open Data policy — you must make freely available ALL data/materials
  supporting the results under an open licence (CC BY or CC0). This explicitly
  includes: the values behind means/SDs and other reported measures; the values
  used to build every graph/figure; points extracted from images for analysis;
  and variable descriptions (a data dictionary: e.g. age, sex, units). Data must
  have a DOI (or accession number), must NOT be embargoed, and must NOT be behind
  a login. If some data cannot be shared (ethics/privacy/security), state that and
  why. If the article type needs no data, state that.
  Required format:
  ```
  Underlying data
  Repository name: [title of project]. https://doi.org/XXXXX [Reference].
  This project contains the following underlying data:
  - [file name with extension] (description of the data in the file).
  - [file name] (description).

  Extended data
  Repository name: [title of project]. https://doi.org/XXXXX [Reference].
  This project contains the following extended data:
  - [file] (description).
  (or: "There is no extended data associated with this article.")

  Data are available under the terms of the Creative Commons Attribution 4.0
  International license (CC BY 4.0).   [or CC0 1.0 for a public-domain waiver]
  ```
- Ethics and consent: place a dedicated "Ethics and consent" section immediately
  AFTER the Data Availability statement. For human/animal-subjects work it must
  give the name of the ethics board, the approval number, and the type of consent
  obtained. If not applicable, state exactly: "Ethical approval and consent were
  not required."
- Competing Interests: MANDATORY, before references. If none: "No competing
  interests were disclosed". (Accepted articles sometimes head it "Conflict of
  interest" with "There is no conflict of interest to declare." — either heading
  is accepted; "Competing Interests" is the official term.)
- Grant Information: list ALL funders — Horizon 2020 / Horizon Europe / Euratom
  project ID + title, plus every other funder (name, grant number, grantee). It
  MUST match the funders declared in the submission system's FundRef/funding form
  — the editorial office cross-checks and will flag any funder present in the
  system but missing from the manuscript statement. No unrelated funding.
- Author Contributions: CRediT taxonomy — entered in the ORE submission web form,
  NOT required as a manuscript section.
- Acknowledgments: optional; NO grant funding listed here.
- Supplementary material: NOT accepted. Use extended data in an approved
  repository, cited in Data Availability.

## Authors block
- List authors with affiliations; affiliation superscript numbers must match the
  actual number of listed affiliations (a common rejection: superscript "4" when
  only 3 affiliations exist).
- Corresponding author details must appear AFTER the affiliations.

## References
- Any consistent style (numbered IEEE or author-date both accepted). URLs go as
  in-text hyperlinks, not as references. Datasets deposited elsewhere go in the
  reference list. Include the preprint self-citation (see above).

## Figures
- Provide figures as SEPARATE files, one per figure, in TIFF or JPEG, print
  quality: 300 dpi for colour, 600 dpi for greyscale. RGB or grayscale.
- REMOVE figures from the manuscript body — keep ONLY the figure legend. All
  figure legends collected at the END of the manuscript. Every figure/table must
  have a legend; concise title <=15 words; legend standalone.
- Every figure CITED in the text must actually be provided (a common rejection:
  citing "Figure 7" but not supplying it). Verify no cited figure is missing and
  no supplied figure is uncited.

## Tables
- Place tables together with their legends AFTER the References section — not
  in-between the body text. Use native Word tables (or Excel for large ones).

## Second deliverable — the data repository deposit
The manuscript is only half the submission. The data behind it is deposited
separately in an approved repository (e.g. figshare, Zenodo) under CC BY / CC0,
and its DOI is what goes into the Data Availability statement. See
`data-package-structure.md` for a recommended deposit layout. Note: not every
paper needs every folder — include only what applies.

## Eligibility
At least one author must be on an eligible EU-funded project and the article must
result from it.
