"""
Export each pydantic schema to JSON Schema under reference/json_schema/.

These files are the committed, language-agnostic contract -- anything
reading Parquet from the data lake without importing bda_engine's Python
package (a notebook, a different service, a CI check) can validate
against these instead.

Run from the bda_engine/ directory:
    uv run python scripts/export_json_schema.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bda_engine.schemas import ALL_SCHEMAS

# reference/ lives at the repo root, not inside bda_engine/ -- see the
# comment on REFERENCE_DIR in bda_engine/src/bda_engine/reference_data.py.
OUT_DIR = Path(__file__).resolve().parents[2] / "reference" / "json_schema"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, model in ALL_SCHEMAS.items():
        schema = model.model_json_schema()
        out_path = OUT_DIR / f"{name}.schema.json"
        out_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
