# Code and data for "Recurrence and verifiability of safety recommendations in Nepal's aircraft accident investigation reports, 2012–2025"

This repository contains the coded dataset and analysis code for the paper. Every number, table and figure in the paper can be reproduced from `Supplementary_Data_S1.xlsx` using the three scripts below.

**Authors:** Prabhat Ghimire, Shristi Rimal, Sijal Shahi, Bishwo Dahal (School of Engineering, Pokhara University, Nepal)
**Contact:** prabhatghimire7@gmail.com
**Source reports:** Ministry of Culture, Tourism and Civil Aviation (MoCTCA), Government of Nepal, Aircraft Accident Investigation page: <https://tourism.gov.np/category/Aircraft-Accident-Investigation/?page=1>

---

## Contents

| File | Purpose | Paper section |
|---|---|---|
| `Supplementary_Data_S1.xlsx` | Coded dataset: all 269 recommendations (verbatim text and every coding decision), accident coverage list, recurrence chains (`Chain_members` sheet), similarity pairs and evidence assessment | Sections 2–3 |
| `coding_rules.py` | Re-applies the written coding rules to the verbatim texts and checks that they reproduce every coded variable (addressee category and level, actor specificity, directive force, type of action, timeframe, CAAN role, system level). The 43 manual type-of-action decisions and 6 CAAN-role overrides are listed in the script. | Section 2.3, Table 3 |
| `reproduce_analysis.py` | Recomputes every statistic in the paper and checks each against the value printed in the manuscript (92 checks). Writes all values to `results.json`. | Sections 3.1–3.6, Tables 1, 4, 5 |
| `make_figures.py` | Draws Figures 1–3 (PNG at 300 dpi and vector PDF; Times New Roman, 5–8 pt). | Figures 1–3 |
| `requirements.txt` | Python dependencies | — |
| `extraction/` | Working scripts used to build the dataset from the report PDFs (for transparency only; see below) | Section 2.2 |

---

## How to run

```bash
pip install -r requirements.txt

python coding_rules.py        Supplementary_Data_S1.xlsx            # prints agreement for each variable
python reproduce_analysis.py  Supplementary_Data_S1.xlsx            # ~1 minute; prints PASS/FAIL for each value
python make_figures.py        Supplementary_Data_S1.xlsx figures/   # writes Figures 1–3 to figures/
```

**Expected output**

- `coding_rules.py`: `All coded variables reproduced.`
- `reproduce_analysis.py`: `92 of 92 values in the paper reproduced.`

### Tested environment

Python 3.13, pandas 3.0.5, numpy 2.5.3, scipy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.1, matplotlib 3.11.2, openpyxl 3.1.5.

Random seeds are fixed (permutation tests: 1; cluster bootstrap: 7), so results are identical on every run. Other library versions may change the last decimal place of the GEE estimates.

---

## Methods implemented in `reproduce_analysis.py`

| Analysis | Details |
|---|---|
| Descriptive counts and shares | Table 4; Sections 3.1–3.3 |
| Kendall's tau | Report-level trend in the number and framing of recommendations against accident date |
| Chi-square tests by period | Permutation p-values (5,000 permutations); descriptive, reported in the dataset |
| GEE logistic models | Exchangeable working correlation, clustered by report; accident date as a continuous variable in years, centred on 2018; each model fitted with and without report 9N-AME |
| Cluster bootstrap | Change in shares from 2012–16 to 2022–25; 10,000 resamples of reports within each period |
| Recurrence measures | Strict and broad reissue shares; report-level reissue events; results with 9N-AME excluded |
| Similarity screen and recall check | TF-IDF cosine similarity on unigrams and bigrams, English stop words removed, sublinear term frequency |
| State versus other addressees | Fisher's exact test and GEE |
| Recurrence by system level | Chi-square test |

---

## `extraction/`: how the dataset was built

These scripts extracted the recommendation text from the report PDFs. They are included for transparency. **They are not needed to reproduce the analysis** and will not run unchanged on another computer, because they use fixed file paths and the line positions of each report's recommendations section.

1. **Convert PDFs to text** with `pdftotext -layout` (Poppler).
2. **Locate and cut the recommendations section** of each report: `01_locate_sections.py`, then `02_cut_recommendation_sections.py` (also strips page headers and footers).
3. **Split each section into individual recommendations**: `03_parse_recommendations.py`. It records each recommendation's number, the addressee heading it falls under, and whether it is interim or final.
4. **Assign IDs, accident dates and thematic tags, and compute all cross-report similarity pairs**: `04_themes_and_similarity.py`.

### Manual corrections

After parsing, 13 records were corrected by hand against the PDFs:

- **Addressees assigned** (6): the heading did not name one. Records 9N-ABO-01 to -03, 9N-AJZ-01 and -02, 9N-AMS-02.
- **Page headers removed** (3): captured inside the recommendation text. Records 9N-AKY-04, S2-AGU-02, 9N-ALS-02.
- **Truncated text completed** (4): the parser had cut them short. Records 9N-ABO-04, 9N-ABB-01, 9N-ABB-02 and the 9N-AHH interim recommendation.

### Verification

Every extracted recommendation was checked against its source report: each consecutive six-word sequence was confirmed to occur in the report text.

### What is not generated by code

Recurrence chains and the strict or broad status of each chain member were decided by reading the texts (Section 2.4 of the paper). They are recorded in the `Chain_members` sheet of `Supplementary_Data_S1.xlsx`, not produced by any script.

---

## Citation

If you use these data or code, please cite the paper and this repository:

> Ghimire, P., Rimal, S., Shahi, S., & Dahal, B. (2026). *Recurrence and verifiability of safety recommendations in Nepal's aircraft accident investigation reports, 2012–2025.* 

## Licence

[Add licence, e.g. CC BY 4.0 for the data and MIT for the code.] The source investigation reports are public documents of the Government of Nepal (MoCTCA).