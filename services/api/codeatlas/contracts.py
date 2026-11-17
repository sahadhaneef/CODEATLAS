"""Phase 0 manifest contracts. No acquisition, model calls, or execution are enabled."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    repository_url: str
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    license: str
    license_review: str = Field(min_length=1)
    allowed_usage: list[str] = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: str = Field(min_length=1)
    split: Literal["fixture", "train", "validation", "test"]


class ModelCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    role: Literal["embedding", "reranker"]
    license: str
    dimensions: int | None
    tokenizer: str
    max_tokens: int = Field(gt=0)
    truncation: str
    normalization: str
    deployment: Literal["local_only"] = "local_only"
    approved_for_private_source: Literal[False] = False
