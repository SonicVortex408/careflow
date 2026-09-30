"""LOINC mapping + unit conversion (implementation shared with bda_engine).

See ``polymarker_common.normalizer``; re-exported here so service code has one
import location and the online and batch paths cannot diverge.
"""

from polymarker_common.normalizer import (  # noqa: F401
    NormalizedResult,
    clean_unit,
    convert_to_canonical,
    match_name,
    normalize_result,
    parse_value,
)
