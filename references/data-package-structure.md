# Recommended data-repository deposit structure

The manuscript's Data Availability statement must point (via DOI) to a data
deposit in an approved open repository (figshare, Zenodo, etc.) under CC BY or
CC0. This file describes a recommended layout, generalized from a real accepted
ORE submission. **Not every paper needs every folder — include only what
applies** (e.g. a purely theoretical paper may have only figure_data + a README).

```
<dataset>/
  README.md               # describes the dataset, folder structure, and how each
                          #   figure/table maps to its data files; states the license
  License.txt             # full text/summary of the open license (CC BY 4.0 or CC0)
  requirements.txt        # (if code included) deps to reproduce, e.g. Python packages
  raw_*/                  # raw, unaveraged data (e.g. raw_realizations/*.csv.gz)
  source_tables/          # tabular source data behind the paper's tables (CSV)
  figure_data/            # the exact values used to plot EACH figure (CSV per figure)
  figures/                # the figure image files themselves (TIFF/JPEG, print quality)
  metadata/
    data_dictionary.csv   # column -> description + unit for every data column
    *_metadata.csv        # per-figure metadata (parameters, provenance)
    *_manifest.csv        # mapping from each paper figure/table to its data files
  code/                   # (optional) notebooks/scripts to regenerate figures from data
```

## Why each piece exists (ORE Open Data policy)
ORE requires you to share everything needed to replicate the findings, specifically:
- the values behind means, standard deviations, and other reported measures
  → `summary_statistics.csv`, `source_tables/`
- the values used to build every graph/figure → `figure_data/` (one file per figure)
- points extracted from images for analysis → include the extracted values as CSV
- variable descriptions → `metadata/data_dictionary.csv`

## README.md should contain
- One-line description of the dataset.
- Folder-structure list (what each folder holds).
- For each figure/table: which data file(s) generate it and the key parameters.
- Column definitions (or a pointer to `data_dictionary.csv`).
- A license statement.

## Licensing
State the license in README.md AND License.txt. Use CC BY 4.0 (attribution) or
CC0 1.0 (public-domain waiver). The Data Availability statement in the manuscript
must end with the matching license sentence.

## The DOI
Deposit first, get the DOI from the repository landing page, then put that DOI in
the manuscript's Data Availability statement. Data must not be embargoed or
login-gated.
