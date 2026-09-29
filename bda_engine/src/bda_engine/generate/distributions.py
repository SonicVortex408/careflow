"""
Patient phenotype and biomarker/PROM sampling.

Design principle (mitigates ARCHITECTURE.md risk R2 -- "symptom
correlations are circular"): PROMs are drawn conditional on a latent
*phenotype*, not derived from the sampled biomarker values themselves.
Biomarkers are ALSO drawn conditional on the same phenotype,
independently. This means a marker and a PROM end up correlated only
through their shared phenotype (exactly like real disease), not
because one was computed from the other -- but it is still a modeling
choice made by this generator, and any downstream analysis "recovering"
a marker-symptom correlation is partly rediscovering this generator's
own rules. The generator parameters below (PHENOTYPES) are the
complete specification of that rule; keep them out of any model
training code, and document this as a validity threat in
evaluation/REPORT.md (Phase 4), not as a finding.

All values are sampled directly in each biomarker's *canonical* unit
(see reference/biomarkers.yaml) -- unit variation is applied later,
at render time, by converting canonical -> a randomly chosen source
unit for printing (see generate_synthetic_data.py).
"""

from dataclasses import dataclass

import numpy as np

from bda_engine.schemas.common import BiomarkerKey, PromItemCode


@dataclass(frozen=True)
class MarkerDist:
    """Lognormal in canonical units: draws are exp(N(mu, sigma)), which
    keeps every value positive and gives the right-skew real lab
    values actually have."""

    mu: float
    sigma: float


@dataclass(frozen=True)
class PromDist:
    """Value is drawn from a Beta(alpha, beta) distribution scaled to
    [scale_min, scale_max], then rounded to the nearest valid step (1
    for the fatigue NRS, 1 for the two ordinal scales -- both are
    integer-stepped)."""

    alpha: float
    beta: float
    scale_min: float
    scale_max: float


@dataclass(frozen=True)
class Phenotype:
    key: str
    weight: float  # relative prevalence in the synthetic population
    markers: dict[BiomarkerKey, MarkerDist]
    proms: dict[PromItemCode, PromDist]
    ferritin_sex_offset_log: float = 0.0  # applied to FERRITIN only, see below


# ---------------------------------------------------------------------
# Five latent phenotypes. Means (mu, in log-space) are chosen so that
# exp(mu) lands near clinically recognizable levels for each pattern;
# they are illustrative/plausible, not fit to any real dataset --
# labelled "derived from synthetic data" everywhere downstream per
# ARCHITECTURE.md's synthetic-data rule.
# ---------------------------------------------------------------------

def _m(mu, sigma):
    return MarkerDist(mu=mu, sigma=sigma)


def _p(alpha, beta, lo, hi):
    return PromDist(alpha=alpha, beta=beta, scale_min=lo, scale_max=hi)


PHENOTYPES: dict[str, Phenotype] = {
    "euthyroid_healthy": Phenotype(
        key="euthyroid_healthy",
        weight=0.45,
        markers={
            BiomarkerKey.TSH: _m(np.log(1.8), 0.35),
            BiomarkerKey.FT3: _m(np.log(4.8), 0.15),
            BiomarkerKey.FT4: _m(np.log(15.0), 0.15),
            BiomarkerKey.ANTI_TPO: _m(np.log(8.0), 0.6),
            BiomarkerKey.VIT_D_25OH: _m(np.log(80.0), 0.3),
            BiomarkerKey.VIT_B12: _m(np.log(350.0), 0.3),
            BiomarkerKey.FERRITIN: _m(np.log(90.0), 0.5),
            BiomarkerKey.MAGNESIUM: _m(np.log(0.85), 0.1),
            BiomarkerKey.ZINC: _m(np.log(14.0), 0.15),
        },
        proms={
            PromItemCode.FATIGUE_SEVERITY: _p(2.0, 6.0, 1, 10),
            PromItemCode.BRAIN_FOG_FREQUENCY: _p(1.5, 6.0, 0, 4),
            PromItemCode.HAIR_LOSS: _p(1.5, 7.0, 0, 4),
        },
    ),
    "subclinical_hypothyroid": Phenotype(
        key="subclinical_hypothyroid",
        weight=0.15,
        markers={
            BiomarkerKey.TSH: _m(np.log(6.5), 0.3),
            BiomarkerKey.FT3: _m(np.log(4.2), 0.15),
            BiomarkerKey.FT4: _m(np.log(13.0), 0.15),
            BiomarkerKey.ANTI_TPO: _m(np.log(25.0), 0.9),
            BiomarkerKey.VIT_D_25OH: _m(np.log(60.0), 0.35),
            BiomarkerKey.VIT_B12: _m(np.log(320.0), 0.3),
            BiomarkerKey.FERRITIN: _m(np.log(70.0), 0.5),
            BiomarkerKey.MAGNESIUM: _m(np.log(0.82), 0.1),
            BiomarkerKey.ZINC: _m(np.log(13.0), 0.15),
        },
        proms={
            PromItemCode.FATIGUE_SEVERITY: _p(4.0, 4.5, 1, 10),
            PromItemCode.BRAIN_FOG_FREQUENCY: _p(3.0, 4.0, 0, 4),
            PromItemCode.HAIR_LOSS: _p(2.5, 4.5, 0, 4),
        },
    ),
    "overt_hypothyroid_autoimmune": Phenotype(
        key="overt_hypothyroid_autoimmune",
        weight=0.10,
        markers={
            BiomarkerKey.TSH: _m(np.log(18.0), 0.4),
            BiomarkerKey.FT3: _m(np.log(3.2), 0.2),
            BiomarkerKey.FT4: _m(np.log(8.5), 0.2),
            BiomarkerKey.ANTI_TPO: _m(np.log(180.0), 0.8),
            BiomarkerKey.VIT_D_25OH: _m(np.log(45.0), 0.35),
            BiomarkerKey.VIT_B12: _m(np.log(280.0), 0.35),
            BiomarkerKey.FERRITIN: _m(np.log(55.0), 0.55),
            BiomarkerKey.MAGNESIUM: _m(np.log(0.78), 0.12),
            BiomarkerKey.ZINC: _m(np.log(11.5), 0.18),
        },
        proms={
            PromItemCode.FATIGUE_SEVERITY: _p(6.0, 3.0, 1, 10),
            PromItemCode.BRAIN_FOG_FREQUENCY: _p(4.5, 2.5, 0, 4),
            PromItemCode.HAIR_LOSS: _p(4.0, 3.0, 0, 4),
        },
    ),
    "hyperthyroid": Phenotype(
        key="hyperthyroid",
        weight=0.08,
        markers={
            BiomarkerKey.TSH: _m(np.log(0.05), 0.5),
            BiomarkerKey.FT3: _m(np.log(9.5), 0.25),
            BiomarkerKey.FT4: _m(np.log(32.0), 0.25),
            BiomarkerKey.ANTI_TPO: _m(np.log(40.0), 0.9),
            BiomarkerKey.VIT_D_25OH: _m(np.log(65.0), 0.3),
            BiomarkerKey.VIT_B12: _m(np.log(340.0), 0.3),
            BiomarkerKey.FERRITIN: _m(np.log(85.0), 0.5),
            BiomarkerKey.MAGNESIUM: _m(np.log(0.83), 0.1),
            BiomarkerKey.ZINC: _m(np.log(13.5), 0.15),
        },
        proms={
            PromItemCode.FATIGUE_SEVERITY: _p(5.0, 4.0, 1, 10),
            PromItemCode.BRAIN_FOG_FREQUENCY: _p(3.0, 4.5, 0, 4),
            PromItemCode.HAIR_LOSS: _p(3.0, 4.5, 0, 4),
        },
    ),
    "micronutrient_deficient": Phenotype(
        key="micronutrient_deficient",
        weight=0.22,
        markers={
            BiomarkerKey.TSH: _m(np.log(2.2), 0.35),
            BiomarkerKey.FT3: _m(np.log(4.5), 0.18),
            BiomarkerKey.FT4: _m(np.log(14.0), 0.18),
            BiomarkerKey.ANTI_TPO: _m(np.log(10.0), 0.6),
            BiomarkerKey.VIT_D_25OH: _m(np.log(28.0), 0.4),
            BiomarkerKey.VIT_B12: _m(np.log(140.0), 0.35),
            BiomarkerKey.FERRITIN: _m(np.log(18.0), 0.5),
            BiomarkerKey.MAGNESIUM: _m(np.log(0.70), 0.1),
            BiomarkerKey.ZINC: _m(np.log(9.5), 0.18),
        },
        proms={
            PromItemCode.FATIGUE_SEVERITY: _p(5.5, 3.5, 1, 10),
            PromItemCode.BRAIN_FOG_FREQUENCY: _p(3.5, 3.5, 0, 4),
            PromItemCode.HAIR_LOSS: _p(4.5, 2.5, 0, 4),
        },
    ),
}

# Ferritin runs lower in menstruating-age females across all phenotypes
# (a real, well-established physiological effect, applied as a log-space
# offset on top of the phenotype's own FERRITIN distribution).
FERRITIN_FEMALE_LOG_OFFSET = -0.55


def sample_phenotype(rng: np.random.Generator) -> Phenotype:
    keys = list(PHENOTYPES.keys())
    weights = np.array([PHENOTYPES[k].weight for k in keys])
    weights = weights / weights.sum()
    return PHENOTYPES[rng.choice(keys, p=weights)]


def sample_markers(
    phenotype: Phenotype, sex: str, rng: np.random.Generator
) -> dict[BiomarkerKey, float]:
    """Returns every biomarker's value in its CANONICAL unit. Missingness
    (not every report has all 9) is applied by the caller, not here --
    this always returns the full panel."""

    values = {}
    for key, dist in phenotype.markers.items():
        mu = dist.mu
        if key == BiomarkerKey.FERRITIN and sex == "female":
            mu += FERRITIN_FEMALE_LOG_OFFSET
        values[key] = float(np.exp(rng.normal(mu, dist.sigma)))
    return values


def sample_proms(phenotype: Phenotype, rng: np.random.Generator) -> dict[PromItemCode, float]:
    values = {}
    for item_code, dist in phenotype.proms.items():
        raw = rng.beta(dist.alpha, dist.beta)
        scaled = dist.scale_min + raw * (dist.scale_max - dist.scale_min)
        values[item_code] = float(round(scaled))
    return values


def sample_demographics(rng: np.random.Generator) -> tuple[float, str]:
    age = float(np.clip(rng.normal(45, 16), 18, 90))
    sex = rng.choice(["male", "female"])
    return round(age, 1), sex
