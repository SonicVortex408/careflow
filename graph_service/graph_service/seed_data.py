"""Curated clinical knowledge for the PolyMarker graph.

Rules for this file:

* Every edge carries ``source`` (a key into SOURCES) and ``evidence_level``.
* ``evidence_level`` is one of EVIDENCE_LEVELS. Anything not backed by a
  guideline or an authoritative fact sheet is ``unverified`` and the connector
  reports it as such; the UI and the LLM prompt both surface that flag.
* Thresholds are in the catalog's canonical SI units.
* Nothing here is clinical guidance. The graph explains *why* a finding may be
  relevant to a symptom; it never produces a diagnosis.

Reference intervals and escalation thresholds are not duplicated here: they are
generated from ``polymarker_common`` so the graph and the normalizer agree.
"""

from __future__ import annotations

EVIDENCE_LEVELS = (
    "guideline",  # clinical practice guideline / WHO recommendation
    "authoritative_review",  # NIH ODS fact sheet or equivalent professional reference
    "observational",  # consistent observational literature, not causal
    "expert_consensus",
    "synthetic_derived",  # discovered by bda_engine on synthetic data
    "unverified",  # plausible hypothesis, not yet reviewed against literature
)
VERIFIED_LEVELS = {"guideline", "authoritative_review", "observational", "expert_consensus"}

SOURCES: dict[str, dict[str, str]] = {
    "who_ferritin_2020": {
        "title": "WHO guideline on use of ferritin concentrations to assess iron status in individuals and populations",
        "publisher": "World Health Organization",
        "year": "2020",
    },
    "nih_ods_vitd": {
        "title": "Vitamin D - Fact Sheet for Health Professionals",
        "publisher": "NIH Office of Dietary Supplements",
        "year": "2024",
    },
    "nih_ods_b12": {
        "title": "Vitamin B12 - Fact Sheet for Health Professionals",
        "publisher": "NIH Office of Dietary Supplements",
        "year": "2024",
    },
    "nih_ods_mg": {
        "title": "Magnesium - Fact Sheet for Health Professionals",
        "publisher": "NIH Office of Dietary Supplements",
        "year": "2022",
    },
    "nih_ods_zinc": {
        "title": "Zinc - Fact Sheet for Health Professionals",
        "publisher": "NIH Office of Dietary Supplements",
        "year": "2022",
    },
    "ata_aace_2012": {
        "title": "Clinical Practice Guidelines for Hypothyroidism in Adults (Garber et al., Thyroid 2012)",
        "publisher": "American Thyroid Association / AACE",
        "year": "2012",
    },
    "ata_patient": {
        "title": "Hypothyroidism patient information",
        "publisher": "American Thyroid Association",
        "year": "2024",
    },
    "curated_hypothesis": {
        "title": "Curated hypothesis pending literature review",
        "publisher": "PolyMarker Analytics project team",
        "year": "2026",
    },
    "bda_engine": {
        "title": "PolyMarker bda_engine discovery run on synthetic cohort",
        "publisher": "PolyMarker Analytics (synthetic data)",
        "year": "2026",
    },
}

CONDITIONS: dict[str, str] = {
    "iron_deficiency": "Low iron stores (iron deficiency)",
    "subclinical_hypothyroidism": "Subclinical hypothyroidism pattern",
    "hypothyroidism": "Underactive thyroid pattern",
    "hyperthyroidism": "Overactive thyroid pattern",
    "autoimmune_thyroiditis": "Thyroid autoimmunity (e.g. Hashimoto's thyroiditis)",
    "vitamin_d_deficiency": "Low vitamin D status",
    "b12_deficiency": "Low vitamin B12 status",
    "hypomagnesemia": "Low magnesium",
    "zinc_deficiency": "Low zinc status",
}

SYMPTOMS: dict[str, str] = {
    "fatigue": "Chronic fatigue",
    "brain_fog": "Brain fog",
    "hair_loss": "Hair loss",
}

# Threshold nodes: (id, biomarker, op, value, label)
THRESHOLDS: list[dict] = [
    {
        "id": "ferritin_lt_15",
        "biomarker": "FERRITIN",
        "op": "<",
        "value": 15.0,
        "label": "Ferritin below 15 ug/L",
    },
    {
        "id": "ferritin_lt_30",
        "biomarker": "FERRITIN",
        "op": "<",
        "value": 30.0,
        "label": "Ferritin below 30 ug/L",
    },
    {
        "id": "tsh_gt_4",
        "biomarker": "TSH",
        "op": ">",
        "value": 4.0,
        "label": "TSH above the reference interval",
    },
    {
        "id": "tsh_gt_10",
        "biomarker": "TSH",
        "op": ">",
        "value": 10.0,
        "label": "TSH above 10 mIU/L",
    },
    {
        "id": "tsh_lt_0_4",
        "biomarker": "TSH",
        "op": "<",
        "value": 0.4,
        "label": "TSH below the reference interval",
    },
    {
        "id": "ft4_lt_10",
        "biomarker": "FT4",
        "op": "<",
        "value": 10.0,
        "label": "Free T4 below the reference interval",
    },
    {
        "id": "ft4_gt_23",
        "biomarker": "FT4",
        "op": ">",
        "value": 23.0,
        "label": "Free T4 above the reference interval",
    },
    {
        "id": "ft3_lt_3_1",
        "biomarker": "FT3",
        "op": "<",
        "value": 3.1,
        "label": "Free T3 below the reference interval",
    },
    {
        "id": "tpo_gt_35",
        "biomarker": "TPOAB",
        "op": ">",
        "value": 35.0,
        "label": "Anti-TPO above assay cut-off",
    },
    {
        "id": "vitd_lt_30",
        "biomarker": "VITD",
        "op": "<",
        "value": 30.0,
        "label": "25-OH vitamin D below 30 nmol/L",
    },
    {
        "id": "vitd_lt_50",
        "biomarker": "VITD",
        "op": "<",
        "value": 50.0,
        "label": "25-OH vitamin D below 50 nmol/L",
    },
    {
        "id": "b12_lt_148",
        "biomarker": "B12",
        "op": "<",
        "value": 148.0,
        "label": "Vitamin B12 below 148 pmol/L",
    },
    {
        "id": "mg_lt_0_7",
        "biomarker": "MG",
        "op": "<",
        "value": 0.7,
        "label": "Magnesium below 0.70 mmol/L",
    },
    {
        "id": "zinc_lt_9_2",
        "biomarker": "ZINC",
        "op": "<",
        "value": 9.2,
        "label": "Zinc below 9.2 umol/L",
    },
]

# (threshold id) -[INDICATES | AMPLIFIES]-> (condition)
THRESHOLD_EDGES: list[dict] = [
    {
        "from": "ferritin_lt_15",
        "type": "INDICATES",
        "to": "iron_deficiency",
        "source": "who_ferritin_2020",
        "evidence_level": "guideline",
        "note": "WHO: ferritin <15 ug/L indicates iron deficiency in apparently healthy adults.",
    },
    {
        "from": "ferritin_lt_30",
        "type": "INDICATES",
        "to": "iron_deficiency",
        "source": "who_ferritin_2020",
        "evidence_level": "expert_consensus",
        "note": "Higher cut-offs are used when inflammation may be present.",
    },
    {
        "from": "ferritin_lt_30",
        "type": "AMPLIFIES",
        "to": "subclinical_hypothyroidism",
        "source": "curated_hypothesis",
        "evidence_level": "unverified",
        "note": "Low iron stores may compound fatigue attributed to borderline thyroid function.",
    },
    {
        "from": "tsh_gt_4",
        "type": "INDICATES",
        "to": "subclinical_hypothyroidism",
        "source": "ata_aace_2012",
        "evidence_level": "guideline",
        "note": "Raised TSH with free T4 in range is the laboratory definition of subclinical hypothyroidism.",
        "requires": {"biomarker": "FT4", "within_reference": True},
    },
    {
        "from": "tsh_gt_10",
        "type": "INDICATES",
        "to": "hypothyroidism",
        "source": "ata_aace_2012",
        "evidence_level": "guideline",
        "note": "TSH above 10 mIU/L is generally considered clinically significant.",
    },
    {
        "from": "ft4_lt_10",
        "type": "INDICATES",
        "to": "hypothyroidism",
        "source": "ata_aace_2012",
        "evidence_level": "guideline",
        "note": "Low free T4 with raised TSH indicates overt hypothyroidism.",
        "requires": {"biomarker": "TSH", "above": 4.0},
    },
    {
        "from": "tsh_lt_0_4",
        "type": "INDICATES",
        "to": "hyperthyroidism",
        "source": "ata_patient",
        "evidence_level": "authoritative_review",
        "note": "A low TSH can reflect an overactive thyroid and needs clinical context.",
    },
    {
        "from": "ft4_gt_23",
        "type": "INDICATES",
        "to": "hyperthyroidism",
        "source": "ata_patient",
        "evidence_level": "authoritative_review",
        "note": "Raised free T4 is consistent with an overactive thyroid.",
    },
    {
        "from": "tpo_gt_35",
        "type": "INDICATES",
        "to": "autoimmune_thyroiditis",
        "source": "ata_aace_2012",
        "evidence_level": "guideline",
        "note": "TPO antibodies mark autoimmune thyroid disease and predict progression of subclinical hypothyroidism.",
    },
    {
        "from": "tpo_gt_35",
        "type": "AMPLIFIES",
        "to": "subclinical_hypothyroidism",
        "source": "ata_aace_2012",
        "evidence_level": "guideline",
        "note": "Positive antibodies raise the likelihood that a raised TSH progresses.",
    },
    {
        "from": "vitd_lt_30",
        "type": "INDICATES",
        "to": "vitamin_d_deficiency",
        "source": "nih_ods_vitd",
        "evidence_level": "authoritative_review",
        "note": "NIH ODS: levels below 30 nmol/L are associated with deficiency.",
    },
    {
        "from": "vitd_lt_50",
        "type": "INDICATES",
        "to": "vitamin_d_deficiency",
        "source": "nih_ods_vitd",
        "evidence_level": "authoritative_review",
        "note": "NIH ODS: 30-50 nmol/L is generally considered inadequate for bone and overall health.",
    },
    {
        "from": "b12_lt_148",
        "type": "INDICATES",
        "to": "b12_deficiency",
        "source": "nih_ods_b12",
        "evidence_level": "authoritative_review",
        "note": "Serum B12 below ~148 pmol/L (200 pg/mL) is commonly used to indicate deficiency.",
    },
    {
        "from": "mg_lt_0_7",
        "type": "INDICATES",
        "to": "hypomagnesemia",
        "source": "nih_ods_mg",
        "evidence_level": "authoritative_review",
        "note": "Serum magnesium below the reference interval; serum levels poorly reflect total body stores.",
    },
    {
        "from": "zinc_lt_9_2",
        "type": "INDICATES",
        "to": "zinc_deficiency",
        "source": "nih_ods_zinc",
        "evidence_level": "unverified",
        "note": "Serum zinc is an imperfect marker of zinc status.",
    },
    {
        "from": "ft3_lt_3_1",
        "type": "AMPLIFIES",
        "to": "hypothyroidism",
        "source": "curated_hypothesis",
        "evidence_level": "unverified",
        "note": "Low free T3 in isolation is non-specific (e.g. illness, low intake).",
    },
]

# (condition) -[PRESENTS_WITH]-> (symptom)
PRESENTS_WITH: list[dict] = [
    {
        "from": "iron_deficiency",
        "to": "fatigue",
        "source": "who_ferritin_2020",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "iron_deficiency",
        "to": "hair_loss",
        "source": "curated_hypothesis",
        "evidence_level": "unverified",
    },
    {
        "from": "iron_deficiency",
        "to": "brain_fog",
        "source": "curated_hypothesis",
        "evidence_level": "unverified",
    },
    {
        "from": "hypothyroidism",
        "to": "fatigue",
        "source": "ata_patient",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "hypothyroidism",
        "to": "brain_fog",
        "source": "ata_patient",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "hypothyroidism",
        "to": "hair_loss",
        "source": "ata_patient",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "subclinical_hypothyroidism",
        "to": "fatigue",
        "source": "ata_aace_2012",
        "evidence_level": "observational",
    },
    {
        "from": "subclinical_hypothyroidism",
        "to": "brain_fog",
        "source": "curated_hypothesis",
        "evidence_level": "unverified",
    },
    {
        "from": "hyperthyroidism",
        "to": "fatigue",
        "source": "ata_patient",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "hyperthyroidism",
        "to": "hair_loss",
        "source": "ata_patient",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "autoimmune_thyroiditis",
        "to": "fatigue",
        "source": "curated_hypothesis",
        "evidence_level": "unverified",
    },
    {
        "from": "vitamin_d_deficiency",
        "to": "fatigue",
        "source": "curated_hypothesis",
        "evidence_level": "unverified",
    },
    {
        "from": "b12_deficiency",
        "to": "fatigue",
        "source": "nih_ods_b12",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "b12_deficiency",
        "to": "brain_fog",
        "source": "nih_ods_b12",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "hypomagnesemia",
        "to": "fatigue",
        "source": "nih_ods_mg",
        "evidence_level": "authoritative_review",
    },
    {
        "from": "zinc_deficiency",
        "to": "hair_loss",
        "source": "nih_ods_zinc",
        "evidence_level": "authoritative_review",
    },
]

# Biomarker -[CORRELATES_WITH]- Biomarker, curated (model-derived ones are added from artifacts)
BIOMARKER_CORRELATIONS: list[dict] = [
    {
        "from": "TSH",
        "to": "FT4",
        "direction": "inverse",
        "source": "ata_aace_2012",
        "evidence_level": "guideline",
    },
    {
        "from": "TPOAB",
        "to": "TSH",
        "direction": "positive",
        "source": "ata_aace_2012",
        "evidence_level": "observational",
    },
]
