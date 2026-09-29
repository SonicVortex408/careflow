"""raw -> bronze -> silver -> gold, on Spark or DuckDB.

bronze/lab_results   all sources unified (CSV + JSONL), strings, partitioned by lab
silver/biomarkers    LOINC-coded SI values + quality flags, partitioned by panel
silver/proms         intake forms normalized to the PROM schema
gold/patient_features one row per patient: latest report, 9 markers wide, age/sex, PROMs
audit/quality        per-lab counts for every data-quality rule
audit/population_stats.json  per-marker log-scale statistics (feeds quality checks online)

Label -> LOINC mapping runs the shared normalizer over the *distinct* labels only
(a few thousand strings, typos included) and is broadcast back as a join table,
so the per-row work stays in the engine.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from bda_engine.config import Settings
from bda_engine.etl.engine import Engine
from polymarker_common.catalog import BIOMARKER_KEYS, load_catalog
from polymarker_common.normalizer import match_name
from polymarker_common.quality import IQR_K, Z_THRESHOLD


def _meta_tables(engine: Engine) -> None:
    catalog = load_catalog()
    engine.register_pandas(
        "marker_meta",
        pd.DataFrame(
            [
                {
                    "marker": k,
                    "loinc": m.loinc,
                    "panel": m.panel,
                    "unit_si": m.canonical_unit,
                    "ref_low": float(m.reference.low),
                    "ref_high": float(m.reference.high),
                    "plaus_low": float(m.plausible.low),
                    "plaus_high": float(m.plausible.high),
                    "log_ref_mid": float(m.log_stats()[0]),
                }
                for k, m in catalog.items()
            ]
        ),
    )
    engine.register_pandas(
        "unit_map",
        pd.DataFrame(
            [
                {"marker": k, "unit_clean": u, "factor": float(f)}
                for k, m in catalog.items()
                for u, f in m.units.items()
            ]
        ),
    )


def _unit_clean_sql(expr: str) -> str:
    inner = f"lower(trim(coalesce({expr}, '')))"
    for a, b in (("µ", "u"), ("μ", "u"), ("mcg", "ug"), (" ", ""), ("litre", "l"), ("liter", "l")):
        inner = f"replace({inner}, '{a}', '{b}')"
    return inner


def bronze(engine: Engine, s: Settings) -> None:
    raw = s.raw_dir
    engine.read_csv("raw_csv", str(raw / "lab_results" / "*" / "*.csv"))
    sources = ["SELECT {cols} FROM raw_csv"]
    if list((raw / "lab_results").glob("*/*.jsonl")):
        engine.read_lab_jsonl("raw_jsonl", str(raw / "lab_results" / "*" / "*.jsonl"))
        sources.append("SELECT {cols} FROM raw_jsonl")
    cols = ", ".join(
        f"CAST({c} AS VARCHAR) AS {c}" if engine.name == "duckdb" else f"CAST({c} AS STRING) AS {c}"
        for c in (
            "report_id",
            "patient_id",
            "lab_provider",
            "collected_at",
            "raw_label",
            "raw_value",
            "raw_unit",
            "raw_reference",
            "flag",
        )
    )
    engine.sql("bronze_lab", " UNION ALL ".join(q.format(cols=cols) for q in sources), persist=True)
    engine.write_parquet("bronze_lab", s.lake_dir / "bronze" / "lab_results", ["lab_provider"])


def silver_biomarkers(engine: Engine, s: Settings) -> dict:
    _meta_tables(engine)
    labels = engine.to_pandas("SELECT DISTINCT raw_label FROM bronze_lab")["raw_label"].fillna("")
    rows = []
    for label in labels:
        m = match_name(label)
        rows.append(
            {
                "raw_label": label,
                "marker": m.key if m else None,
                "label_confidence": float(m.confidence) if m else 0.0,
                "match_method": m.method if m else "unmapped",
            }
        )
    label_map = pd.DataFrame(rows)
    engine.register_pandas("label_map", label_map)

    num_text = engine.regex_replace_all("raw_value", "[^0-9.,]", "")
    engine.sql(
        "parsed",
        f"""
        SELECT b.report_id, b.patient_id, b.lab_provider, CAST(b.collected_at AS DATE) AS collected_at,
               b.raw_label, b.raw_value, b.raw_unit, b.raw_reference, b.flag,
               l.marker, l.label_confidence, l.match_method,
               NULLIF(regexp_extract(b.raw_value, '^ *([<>]=?)', 1), '') AS qualifier,
               TRY_CAST(replace({num_text}, ',', '.') AS DOUBLE) AS value_num,
               {_unit_clean_sql("b.raw_unit")} AS unit_clean
        FROM bronze_lab b JOIN label_map l ON b.raw_label = l.raw_label
        WHERE l.marker IS NOT NULL
    """,
        persist=True,
    )

    # Unit inference for missing/unknown units: choose the known unit whose
    # conversion lands in the plausible range closest to the reference midpoint.
    engine.sql(
        "unit_candidates",
        """
        SELECT p.report_id, p.raw_label, p.raw_value, p.unit_clean, u.factor,
               ROW_NUMBER() OVER (
                   PARTITION BY p.report_id, p.raw_label, p.raw_value, p.unit_clean
                   ORDER BY abs(ln(greatest(p.value_num * u.factor, 0.000001)) - m.log_ref_mid)
               ) AS rn
        FROM parsed p
        JOIN marker_meta m ON p.marker = m.marker
        JOIN unit_map u ON p.marker = u.marker
        LEFT JOIN unit_map k ON p.marker = k.marker AND p.unit_clean = k.unit_clean
        WHERE k.factor IS NULL AND p.value_num IS NOT NULL
          AND p.value_num * u.factor BETWEEN m.plaus_low AND m.plaus_high
    """,
    )
    engine.sql(
        "converted",
        """
        SELECT p.*, m.loinc, m.panel, m.unit_si, m.ref_low, m.ref_high, m.plaus_low, m.plaus_high,
               p.value_num * coalesce(k.factor, c.factor) AS value_si,
               k.factor IS NULL AS unit_inferred
        FROM parsed p
        JOIN marker_meta m ON p.marker = m.marker
        LEFT JOIN unit_map k ON p.marker = k.marker AND p.unit_clean = k.unit_clean
        LEFT JOIN (SELECT * FROM unit_candidates WHERE rn = 1) c
          ON p.report_id = c.report_id AND p.raw_label = c.raw_label
         AND p.raw_value = c.raw_value AND p.unit_clean = c.unit_clean
    """,
        persist=True,
    )

    q1 = engine.quantile("ln(value_si)", 0.25)
    q3 = engine.quantile("ln(value_si)", 0.75)
    engine.sql(
        "pop_stats",
        f"""
        SELECT marker, AVG(ln(value_si)) AS log_mean, STDDEV_SAMP(ln(value_si)) AS log_sd,
               {q1} AS log_q1, {q3} AS log_q3, COUNT(*) AS n
        FROM converted
        WHERE value_si IS NOT NULL AND value_si BETWEEN plaus_low AND plaus_high
        GROUP BY marker
    """,
        persist=True,
    )

    engine.sql(
        "flagged",
        f"""
        SELECT c.*,
               (c.value_si IS NULL) AS unparseable,
               (c.value_si IS NOT NULL AND NOT (c.value_si BETWEEN c.plaus_low AND c.plaus_high)) AS implausible,
               (ln(greatest(c.value_si, 0.000001)) - s.log_mean) / s.log_sd AS z_log,
               (ln(greatest(c.value_si, 0.000001)) < s.log_q1 - {IQR_K} * (s.log_q3 - s.log_q1)
                 OR ln(greatest(c.value_si, 0.000001)) > s.log_q3 + {IQR_K} * (s.log_q3 - s.log_q1)) AS iqr_outlier
        FROM converted c JOIN pop_stats s ON c.marker = s.marker
    """,
    )
    engine.sql(
        "flagged2",
        f"""
        SELECT f.*,
               ((f.implausible OR abs(f.z_log) > {Z_THRESHOLD}) AND (
                   f.value_si / 10 BETWEEN f.ref_low AND f.ref_high
                OR f.value_si / 100 BETWEEN f.ref_low AND f.ref_high
                OR f.value_si * 10 BETWEEN f.ref_low AND f.ref_high)) AS decimal_misread_suspect,
               ROW_NUMBER() OVER (
                   PARTITION BY f.report_id, f.marker
                   ORDER BY f.implausible, f.unparseable, f.label_confidence DESC, f.unit_inferred
               ) AS dup_rank
        FROM flagged f
    """,
        persist=True,
    )
    engine.sql(
        "silver_biomarkers",
        """
        SELECT report_id, patient_id, lab_provider, collected_at, marker, loinc, panel,
               value_si, unit_si, qualifier, label_confidence, match_method, unit_inferred,
               implausible, decimal_misread_suspect, z_log, iqr_outlier
        FROM flagged2 WHERE dup_rank = 1 AND NOT unparseable
    """,
        persist=True,
    )
    engine.write_parquet("silver_biomarkers", s.lake_dir / "silver" / "biomarkers", ["panel"])

    engine.sql(
        "audit_quality",
        f"""
        SELECT lab_provider,
               COUNT(*) AS rows_mapped,
               SUM(CASE WHEN match_method = 'fuzzy' THEN 1 ELSE 0 END) AS fuzzy_labels,
               SUM(CASE WHEN unparseable THEN 1 ELSE 0 END) AS unparseable_values,
               SUM(CASE WHEN unit_inferred THEN 1 ELSE 0 END) AS unit_inferred,
               SUM(CASE WHEN implausible THEN 1 ELSE 0 END) AS implausible,
               SUM(CASE WHEN decimal_misread_suspect THEN 1 ELSE 0 END) AS decimal_misread_suspect,
               SUM(CASE WHEN abs(z_log) > {Z_THRESHOLD} THEN 1 ELSE 0 END) AS zscore_outliers,
               SUM(CASE WHEN iqr_outlier THEN 1 ELSE 0 END) AS iqr_outliers,
               SUM(CASE WHEN dup_rank > 1 THEN 1 ELSE 0 END) AS duplicates_removed
        FROM flagged2 GROUP BY lab_provider ORDER BY lab_provider
    """,
    )
    audit = engine.to_pandas("SELECT * FROM audit_quality")
    unmapped = engine.to_pandas("""
        SELECT b.lab_provider, COUNT(*) AS unmapped_rows
        FROM bronze_lab b JOIN label_map l ON b.raw_label = l.raw_label
        WHERE l.marker IS NULL GROUP BY b.lab_provider
    """)
    audit = audit.merge(unmapped, on="lab_provider", how="left").fillna({"unmapped_rows": 0})
    stats = engine.to_pandas("SELECT * FROM pop_stats ORDER BY marker")
    return {
        "label_map": {
            "distinct_labels": int(len(label_map)),
            "mapped": int(label_map["marker"].notna().sum()),
            "fuzzy": int((label_map["match_method"] == "fuzzy").sum()),
        },
        "audit": audit,
        "population_stats": stats,
    }


_FOG_CASE = """CASE
    WHEN v IN ('never', 'not at all') THEN 'never'
    WHEN v IN ('rarely', 'seldom') THEN 'rarely'
    WHEN v IN ('sometimes', 'occasionally') THEN 'sometimes'
    WHEN v IN ('often', 'frequently', 'most days') THEN 'often'
    WHEN v IN ('always', 'constantly', 'every day') THEN 'always'
END"""
_HAIR_CASE = """CASE
    WHEN v IN ('none', 'no') THEN 'none'
    WHEN v IN ('mild', 'a little') THEN 'mild'
    WHEN v IN ('moderate') THEN 'moderate'
    WHEN v IN ('severe', 'a lot') THEN 'severe'
END"""


def silver_proms(engine: Engine, s: Settings) -> None:
    engine.read_intake_jsonl("raw_intake", str(s.raw_dir / "intake" / "*.jsonl"))
    fog = _FOG_CASE.replace("v IN", "lower(trim(answers.brain_fog)) IN")
    hair = _HAIR_CASE.replace("v IN", "lower(trim(answers.hair_loss)) IN")
    engine.sql(
        "silver_proms",
        f"""
        SELECT report_id, patient_id,
               TRY_CAST(regexp_extract(answers.fatigue, '([0-9]+)', 1) AS INT) AS fatigue_severity,
               {fog} AS brain_fog_frequency,
               {hair} AS hair_loss
        FROM raw_intake
    """,
        persist=True,
    )
    engine.write_parquet("silver_proms", s.lake_dir / "silver" / "proms")


def gold(engine: Engine, s: Settings) -> None:
    engine.read_csv("raw_patients", str(s.raw_dir / "patients.csv"))
    pivots = ",\n".join(
        f"MAX(CASE WHEN marker = '{k}' AND NOT implausible THEN value_si END) AS {k}"
        for k in BIOMARKER_KEYS
    )
    flags = ",\n".join(
        f"MAX(CASE WHEN marker = '{k}' AND (unit_inferred OR decimal_misread_suspect OR label_confidence < 0.9) THEN 1 ELSE 0 END) AS {k}_low_quality"
        for k in BIOMARKER_KEYS
    )
    engine.sql(
        "report_wide",
        f"""
        SELECT report_id, patient_id, MIN(lab_provider) AS lab_provider, MIN(collected_at) AS collected_at,
               {pivots},
               {flags}
        FROM silver_biomarkers GROUP BY report_id, patient_id
    """,
    )
    engine.sql(
        "latest",
        """
        SELECT * FROM (
            SELECT r.*, ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY collected_at DESC, report_id DESC) AS rk,
                   COUNT(*) OVER (PARTITION BY patient_id) AS n_reports
            FROM report_wide r
        ) t WHERE rk = 1
    """,
    )
    engine.sql(
        "gold_features",
        """
        SELECT l.*, p.sex,
               CAST(year(l.collected_at) - CAST(p.birth_year AS INT) AS INT) AS age,
               pr.fatigue_severity, pr.brain_fog_frequency, pr.hair_loss
        FROM latest l
        JOIN raw_patients p ON l.patient_id = p.patient_id
        LEFT JOIN silver_proms pr ON l.report_id = pr.report_id
    """,
        persist=True,
    )
    engine.write_parquet("gold_features", s.lake_dir / "gold" / "patient_features")


def run_etl(engine: Engine, s: Settings) -> dict:
    timings = {}
    t0 = time.perf_counter()
    bronze(engine, s)
    timings["bronze_s"] = round(time.perf_counter() - t0, 2)
    t = time.perf_counter()
    result = silver_biomarkers(engine, s)
    timings["silver_biomarkers_s"] = round(time.perf_counter() - t, 2)
    t = time.perf_counter()
    silver_proms(engine, s)
    gold(engine, s)
    timings["gold_s"] = round(time.perf_counter() - t, 2)
    timings["total_s"] = round(time.perf_counter() - t0, 2)

    audit_dir = s.lake_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    result["audit"].to_csv(audit_dir / "quality_by_lab.csv", index=False)
    stats = {
        r["marker"]: {k: float(r[k]) for k in ("log_mean", "log_sd", "log_q1", "log_q3")}
        | {"n": int(r["n"])}
        for _, r in result["population_stats"].iterrows()
    }
    (audit_dir / "population_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    summary = {
        "engine": engine.name,
        "bronze_rows": engine.count("bronze_lab"),
        "silver_biomarker_rows": engine.count("silver_biomarkers"),
        "silver_prom_rows": engine.count("silver_proms"),
        "gold_patients": engine.count("gold_features"),
        "label_map": result["label_map"],
        "audit_totals": {
            c: int(result["audit"][c].sum()) for c in result["audit"].columns if c != "lab_provider"
        },
        "timings": timings,
    }
    (audit_dir / f"etl_summary_{engine.name}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def read_gold(s: Settings) -> pd.DataFrame:
    return pd.read_parquet(Path(s.lake_dir) / "gold" / "patient_features")
