import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from codeatlas.contracts import DatasetManifest, ModelCandidate


def test_model_candidates_are_pinned_and_private_source_disabled():
    candidates = json.loads(
        (Path(__file__).resolve().parents[1] / "docs/models/candidates.json").read_text()
    )
    assert {ModelCandidate(**c).role for c in candidates} == {"embedding", "reranker"}
    with pytest.raises(ValidationError):
        ModelCandidate(**{**candidates[0], "revision": "latest"})
    with pytest.raises(ValidationError):
        ModelCandidate(**{**candidates[0], "approved_for_private_source": True})


def test_dataset_contract_rejects_unpinned_ref():
    record = dict(
        repository_url="https://github.com/example/fixture",
        commit_sha="a" * 40,
        license="first-party",
        license_review="Synthetic fixture",
        allowed_usage=["test"],
        languages=["python"],
        archive_sha256="b" * 64,
        provenance="unit test",
        split="fixture",
    )
    assert DatasetManifest(**record).schema_version == 1
    with pytest.raises(ValidationError):
        DatasetManifest(**{**record, "commit_sha": "main"})
