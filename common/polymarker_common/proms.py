"""Patient-reported outcome measures (PROMs): validation and numeric encoding."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from polymarker_common.catalog import prom_spec

BRAIN_FOG_LEVELS: tuple[str, ...] = tuple(prom_spec()["brain_fog_frequency"]["levels"])
HAIR_LOSS_LEVELS: tuple[str, ...] = tuple(prom_spec()["hair_loss"]["levels"])

# Binary symptom targets used by the risk models. Thresholds are part of the
# model contract and are recorded in the artifact manifest.
TARGETS = {
    "fatigue": "fatigue_severity >= 7",
    "brain_fog": "brain_fog_frequency in {often, always}",
    "hair_loss": "hair_loss in {moderate, severe}",
}


@dataclass(frozen=True)
class Proms:
    fatigue_severity: int
    brain_fog_frequency: str
    hair_loss: str

    @classmethod
    def from_dict(cls, data: dict) -> Proms:
        fatigue = int(data["fatigue_severity"])
        if not 1 <= fatigue <= 10:
            raise ValueError("fatigue_severity must be between 1 and 10")
        fog = str(data["brain_fog_frequency"]).strip().lower()
        if fog not in BRAIN_FOG_LEVELS:
            raise ValueError(f"brain_fog_frequency must be one of {BRAIN_FOG_LEVELS}")
        hair = str(data["hair_loss"]).strip().lower()
        if hair not in HAIR_LOSS_LEVELS:
            raise ValueError(f"hair_loss must be one of {HAIR_LOSS_LEVELS}")
        return cls(fatigue, fog, hair)

    def encoded(self) -> dict[str, int]:
        return {
            "fatigue_severity": self.fatigue_severity,
            "brain_fog_score": BRAIN_FOG_LEVELS.index(self.brain_fog_frequency),
            "hair_loss_score": HAIR_LOSS_LEVELS.index(self.hair_loss),
        }

    def targets(self) -> dict[str, int]:
        return {
            "fatigue": int(self.fatigue_severity >= 7),
            "brain_fog": int(self.brain_fog_frequency in ("often", "always")),
            "hair_loss": int(self.hair_loss in ("moderate", "severe")),
        }

    def to_dict(self) -> dict:
        return asdict(self)
