# CVPR 2026 Paper Explorer

Static explorer for CVPR 2026 accepted papers.

Live site: <https://gisbi-kim.github.io/cvpr2026-explorer/>

The app is modeled after `gisbi-kim/icra2026-explorer`: Apple Developer Docs-style layout, official acceptance statistics, charts, affiliation summaries, taxonomy trends, and a searchable paper list.

## Data

- Input: `data/cvpr2026_papers.json`
- Expected fields: `title`, `type`, `authors`, `institutions`, `abstract`
- `type` is normalized to one of `oral`, `highlight`, `poster`

## Build

```powershell
python scripts/build_affiliation_regions.py
python scripts/build_html.py
```

Output:

```text
output/cvpr2026_explorer.html
```

The root `index.html` redirects to `output/cvpr2026_explorer.html` for GitHub Pages.
The output is self-contained except for Chart.js, Three.js, and MathJax loaded from CDNs.

## Notes

- CVPR 2026 official statistics are embedded from the user-provided acceptance summary:
  - 16,092 submissions
  - 4,090 accepted papers
  - 25.42% acceptance rate
  - 1,717 Findings recommendations
- The phylogeny section is inspired by `https://gisbi-kim.github.io/cvml-paper-phylogeny/`.
- Topic distribution uses semantic labels in `classification/semantic_topics.json`, with a keyword fallback into a 4-level CV/ML taxonomy: `Phylum -> Class -> Order -> Genus`.
- Affiliation regions use manual correction rules, `classification/manual_other_aff_region_lookup.json`, and `classification/aff_region_table.json`. The numbers are exploratory, not official CVPR or institutional statistics.
