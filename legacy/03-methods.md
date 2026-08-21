# The Lunar Green Revolution: methods

> Ported verbatim (minus GitBook markup) from `the-green-lunar-revolution-methods.md` in
> [Lunar_regolith_AWG](https://github.com/dr-richard-barker/Lunar_regolith_AWG).
> This is the original written record. The analysis that supersedes parts of it
> lives in `results/` and is reproducible from `scripts/`.

---

**Methods: Principal component analysis and deep learning clarifies hormonal**

The lunar regolith sample (GLDS-XXX) underwent statistical reanalysis using GAGE gene set enrichment correlation analysis. We applied Principal Component Pathways Correlation Analysis with the KEGG pathway library and examined changes to the ribosome and defense metabolism pathways using KEGG pathview.

Linear models compared all lunar locations, broadly grouped, against the regolith simulant to calculate differential expression using DESeq2. We correlated the DEG list with KEGG, GO, and Reactome to assess changes in metabolic and signaling processes related to plant hormone signaling.

Instead of separating the lunar locations or classifying the samples based on plant phenotype, we grouped all lunar samples into a "Broad Lunar" category. This approach allowed us to formulate the Broad Lunar Regolith model of terrestrial differentiation.
