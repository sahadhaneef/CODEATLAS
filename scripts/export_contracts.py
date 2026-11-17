"""Export/check deterministic Phase 0 API and manifest schemas without starting services."""

import argparse
import json
from pathlib import Path

from codeatlas.config import Settings
from codeatlas.contracts import DatasetManifest, ModelCandidate
from codeatlas.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    app = create_app(
        Settings("sqlite://", "contract-export-only-a" * 2, "contract-export-only-b" * 2)
    )
    documents = {
        "docs/api/openapi.json": app.openapi(),
        "evals/manifests/dataset.schema.json": DatasetManifest.model_json_schema(),
        "docs/models/candidate.schema.json": ModelCandidate.model_json_schema(),
    }
    for name, document in documents.items():
        path = ROOT / name
        content = json.dumps(document, indent=2, sort_keys=True) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Contract drift: regenerate {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print("Contracts match" if args.check else "Contracts exported")


if __name__ == "__main__":
    main()
