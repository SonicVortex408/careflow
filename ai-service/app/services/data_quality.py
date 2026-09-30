"""Per-report data-quality checks, parameterised with cohort statistics from the
bda_engine ``population_stats`` artifact when available (catalog prior otherwise)."""

from __future__ import annotations

from app.services.interpretation import population_stats
from polymarker_common.normalizer import NormalizedResult
from polymarker_common.quality import QualityReport
from polymarker_common.quality import check_report as _check_report


def check_report(results: list[NormalizedResult], *, sex: str | None = None) -> QualityReport:
    return _check_report(results, sex=sex, population_stats=population_stats())
