"""
Sanity checks on the phenotype-conditional sampling in generate/distributions.py.
These are statistical assertions over many draws (deterministic seed),
not exact-value checks -- the point is verifying the *direction* of
each physiological effect the generator claims to model.
"""

import numpy as np
import pytest

from bda_engine.generate.distributions import (
    PHENOTYPES,
    sample_demographics,
    sample_markers,
    sample_phenotype,
    sample_proms,
)
from bda_engine.schemas.common import BiomarkerKey, PromItemCode


def test_phenotype_weights_sum_to_one():
    total = sum(p.weight for p in PHENOTYPES.values())
    assert total == pytest.approx(1.0, abs=1e-6)


def test_every_phenotype_defines_all_nine_biomarkers():
    from bda_engine.schemas.common import BiomarkerKey as BK
    for name, phenotype in PHENOTYPES.items():
        assert set(phenotype.markers.keys()) == set(BK), name


def test_every_phenotype_defines_all_three_proms():
    for name, phenotype in PHENOTYPES.items():
        assert set(phenotype.proms.keys()) == set(PromItemCode), name


def test_sample_phenotype_respects_relative_weights():
    rng = np.random.default_rng(42)
    counts = {}
    for _ in range(5000):
        p = sample_phenotype(rng)
        counts[p.key] = counts.get(p.key, 0) + 1

    for key, phenotype in PHENOTYPES.items():
        observed_fraction = counts.get(key, 0) / 5000
        assert observed_fraction == pytest.approx(phenotype.weight, abs=0.03), key


def test_overt_hypothyroid_has_higher_tsh_than_healthy():
    rng = np.random.default_rng(1)
    hypo_tsh = [
        sample_markers(PHENOTYPES["overt_hypothyroid_autoimmune"], "female", rng)[BiomarkerKey.TSH]
        for _ in range(500)
    ]
    healthy_tsh = [
        sample_markers(PHENOTYPES["euthyroid_healthy"], "female", rng)[BiomarkerKey.TSH]
        for _ in range(500)
    ]
    assert np.mean(hypo_tsh) > np.mean(healthy_tsh) * 3


def test_overt_hypothyroid_has_lower_ft4_than_healthy():
    rng = np.random.default_rng(2)
    hypo_ft4 = [
        sample_markers(PHENOTYPES["overt_hypothyroid_autoimmune"], "female", rng)[BiomarkerKey.FT4]
        for _ in range(500)
    ]
    healthy_ft4 = [
        sample_markers(PHENOTYPES["euthyroid_healthy"], "female", rng)[BiomarkerKey.FT4]
        for _ in range(500)
    ]
    assert np.mean(hypo_ft4) < np.mean(healthy_ft4)


def test_hyperthyroid_has_suppressed_tsh_and_elevated_ft4():
    rng = np.random.default_rng(3)
    hyper = [
        sample_markers(PHENOTYPES["hyperthyroid"], "female", rng) for _ in range(500)
    ]
    healthy = [
        sample_markers(PHENOTYPES["euthyroid_healthy"], "female", rng) for _ in range(500)
    ]
    hyper_tsh = np.mean([m[BiomarkerKey.TSH] for m in hyper])
    healthy_tsh = np.mean([m[BiomarkerKey.TSH] for m in healthy])
    hyper_ft4 = np.mean([m[BiomarkerKey.FT4] for m in hyper])
    healthy_ft4 = np.mean([m[BiomarkerKey.FT4] for m in healthy])

    assert hyper_tsh < healthy_tsh
    assert hyper_ft4 > healthy_ft4


def test_autoimmune_phenotype_has_elevated_anti_tpo():
    rng = np.random.default_rng(4)
    autoimmune = [
        sample_markers(
            PHENOTYPES["overt_hypothyroid_autoimmune"], "female", rng
        )[BiomarkerKey.ANTI_TPO]
        for _ in range(500)
    ]
    healthy = [
        sample_markers(PHENOTYPES["euthyroid_healthy"], "female", rng)[BiomarkerKey.ANTI_TPO]
        for _ in range(500)
    ]
    assert np.mean(autoimmune) > np.mean(healthy) * 5


def test_ferritin_is_lower_in_females_than_males_same_phenotype():
    rng = np.random.default_rng(5)
    male = [
        sample_markers(PHENOTYPES["euthyroid_healthy"], "male", rng)[BiomarkerKey.FERRITIN]
        for _ in range(1000)
    ]
    female = [
        sample_markers(PHENOTYPES["euthyroid_healthy"], "female", rng)[BiomarkerKey.FERRITIN]
        for _ in range(1000)
    ]
    assert np.mean(male) > np.mean(female)


def test_micronutrient_deficient_phenotype_has_low_vitamin_d_b12_ferritin():
    rng = np.random.default_rng(6)
    deficient = [
        sample_markers(PHENOTYPES["micronutrient_deficient"], "male", rng) for _ in range(500)
    ]
    healthy = [
        sample_markers(PHENOTYPES["euthyroid_healthy"], "male", rng) for _ in range(500)
    ]
    for key in (BiomarkerKey.VIT_D_25OH, BiomarkerKey.VIT_B12, BiomarkerKey.FERRITIN):
        deficient_mean = np.mean([m[key] for m in deficient])
        healthy_mean = np.mean([m[key] for m in healthy])
        assert deficient_mean < healthy_mean, key


def test_all_marker_values_are_positive():
    rng = np.random.default_rng(7)
    for phenotype in PHENOTYPES.values():
        for _ in range(50):
            markers = sample_markers(phenotype, "female", rng)
            for key, value in markers.items():
                assert value > 0, f"{phenotype.key}/{key}"


def test_proms_are_integer_stepped_and_within_scale():
    rng = np.random.default_rng(8)
    scale_bounds = {
        PromItemCode.FATIGUE_SEVERITY: (1, 10),
        PromItemCode.BRAIN_FOG_FREQUENCY: (0, 4),
        PromItemCode.HAIR_LOSS: (0, 4),
    }
    for phenotype in PHENOTYPES.values():
        for _ in range(50):
            proms = sample_proms(phenotype, rng)
            for code, value in proms.items():
                assert value == int(value)
                lo, hi = scale_bounds[code]
                assert lo <= value <= hi, f"{phenotype.key}/{code}={value}"


def test_symptomatic_phenotypes_have_higher_fatigue_than_healthy():
    """The PROM/marker correlation is real (both keyed off phenotype),
    even though PROMs are not computed FROM markers -- see the R2 note
    in this module's docstring."""
    rng = np.random.default_rng(9)
    healthy_fatigue = [
        sample_proms(PHENOTYPES["euthyroid_healthy"], rng)[PromItemCode.FATIGUE_SEVERITY]
        for _ in range(500)
    ]
    hypo_fatigue = [
        sample_proms(PHENOTYPES["overt_hypothyroid_autoimmune"], rng)[PromItemCode.FATIGUE_SEVERITY]
        for _ in range(500)
    ]
    assert np.mean(hypo_fatigue) > np.mean(healthy_fatigue)


def test_sample_demographics_within_bounds():
    rng = np.random.default_rng(10)
    for _ in range(200):
        age, sex = sample_demographics(rng)
        assert 18 <= age <= 90
        assert sex in ("male", "female")


def test_reproducible_with_same_seed():
    rng1 = np.random.default_rng(123)
    rng2 = np.random.default_rng(123)
    m1 = sample_markers(PHENOTYPES["euthyroid_healthy"], "female", rng1)
    m2 = sample_markers(PHENOTYPES["euthyroid_healthy"], "female", rng2)
    assert m1 == m2
