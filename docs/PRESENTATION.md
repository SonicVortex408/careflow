# PolyMarker Analytics — presentation outline

Slide-by-slide outline for the final presentation (Week 14). Figures live in
`evaluation/figures/`, UI screenshots in `docs/images/` (captured from a live
end-to-end run on the synthetic demo data).

1. **Problem.** Thyroid + micronutrient reports are hard to read; symptoms
   (fatigue, brain fog, hair loss) are rarely linked to the numbers.
   Reference ranges describe healthy people, not where symptoms start.
2. **Title & gist.** *PolyMarker Analytics: a scalable big-data architecture for
   multi-biomarker clustering, symptom correlation and functional-range
   discovery in unstructured health records.* Synthetic-data rule stated up front.
3. **Architecture.** Component diagram from `docs/ARCHITECTURE.md` §2: React →
   Express gateway → FastAPI + Celery + LangGraph → Neo4j / Redis / Mongo; offline
   bda_engine → versioned artifacts.
4. **Volume & Variety.** 50k patients, 0.5 M rows, 5 heterogeneous labs, 500
   PDFs (35 % scanned); bronze/silver/gold Parquet lake. (`README.md` 4-V table)
5. **ETL on Spark and DuckDB.** Same SQL, identical output; 8 s vs 68 s at this
   scale and why; data-quality reconciliation table (`REPORT.md` §2).
6. **OCR & normalization.** 97.7 % value accuracy overall, 93 % on scans; 78 %
   of wrong scanned values are flagged low-confidence; LOINC + SI conversion;
   names never extracted. (`REPORT.md` §3)
7. **Knowledge graph.** Evidence chains with source + evidence level; unverified
   links labelled. Neo4j browser screenshot + one chain.
8. **Clustering.** `figures/cluster_profiles.png`; honest silhouette (0.14);
   DBSCAN outliers are 3× more fatigued.
9. **Functional bands.** `figures/functional_bands_vs_truth.png`; edges within
   ~13 % of hidden thresholds, all inside lab ranges; **circularity caveat (R2)**.
10. **Risk + SHAP.** `figures/roc_curves.png`, `calibration.png`,
    `shap_fatigue_beeswarm.png`; AUROC 0.81 / 0.69 / 0.74, ECE ≈ 0.01.
11. **GraphRAG + guardrails.** Pipeline diagram (LLM never last); red-team 30/30,
    0/25 false positives; 500/500 summaries ≤ grade 8, 0 ungrounded numbers.
12. **Human in the loop.** `images/review-queue.png`, `images/clinician-review.png`:
    escalation-sorted queue, extracted values with confidence, audit trail,
    approve / edit / reject.
13. **Patient view.** `images/patient-dashboard.png`: gauges (lab vs functional
    range), radar, cohort map, symptom likelihood, evidence, appointment guide.
14. **Assistant.** `images/assistant.png`: grounded answer + disclaimer; red-flag
    escalation demo ("chest pain").
15. **Engineering quality.** 137 automated tests (+3 live-integration) across 6 projects, live Neo4j /
    Redis / Mongo in CI, Docker Compose, env-driven config.
16. **Limitations & next steps.** Synthetic data only; LLM path unevaluated
    without a key; OCR on real faxes/photos; LayoutLMv3 fine-tuning;
    de-identified real-world validation; clinician-configured escalation
    thresholds.
