"""Schema 4 -- PromResponse (silver layer).

Patient-Reported Outcome Measures: chronic fatigue, brain fog, hair loss
(docs/ARCHITECTURE.md section 1). Instruments are pinned here:
  - FATIGUE_SEVERITY:     1-10 numeric rating scale (NRS)
  - BRAIN_FOG_FREQUENCY:  0-4 ordinal (never/rarely/sometimes/often/always)
  - HAIR_LOSS:            0-4 ordinal severity
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bda_engine.schemas.common import PromItemCode, PromScaleType

SCHEMA_VERSION = "1.0.0"

INSTRUMENT_NAME = "CAREFLOW_PROM_V1"

# The fixed scale for each item -- used both by the synthetic generator
# and to validate a real submission before it's persisted.
ITEM_SCALES: dict[PromItemCode, tuple[PromScaleType, int, int]] = {
    PromItemCode.FATIGUE_SEVERITY: (PromScaleType.NRS, 1, 10),
    PromItemCode.BRAIN_FOG_FREQUENCY: (PromScaleType.ORDINAL, 0, 4),
    PromItemCode.HAIR_LOSS: (PromScaleType.ORDINAL, 0, 4),
}


class PromItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_code: PromItemCode
    value_raw: str
    value_numeric: float
    scale_min: int
    scale_max: int
    scale_type: PromScaleType

    @model_validator(mode="after")
    def _value_within_scale(self):
        if not (self.scale_min <= self.value_numeric <= self.scale_max):
            raise ValueError(
                f"{self.item_code}: value_numeric={self.value_numeric} "
                f"outside [{self.scale_min}, {self.scale_max}]"
            )
        return self


class PromDerived(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fatigue_score: float
    brain_fog_score: float
    hair_loss_score: float
    # Simple average of the three 0-1 normalized scores. A placeholder
    # aggregate -- not a validated composite instrument.
    composite_burden: float


class PromResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION

    response_id: str
    patient_id: str
    instrument: str = INSTRUMENT_NAME
    instrument_version: str = "1.0.0"

    submitted_at: datetime
    # Partition key for silver/prom_responses/.
    survey_date: date
    recall_window_days: int = Field(default=7, ge=1)

    items: list[PromItem]
    derived: PromDerived

    is_synthetic: bool = False

    @model_validator(mode="after")
    def _all_three_items_present(self):
        codes = {item.item_code for item in self.items}
        expected = set(PromItemCode)
        if codes != expected:
            raise ValueError(
                f"PromResponse must include exactly "
                f"{sorted(c.value for c in expected)}, "
                f"got {sorted(c.value for c in codes)}"
            )
        return self
