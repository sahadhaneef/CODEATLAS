"""Future adapter contracts only; no models or execution backends are constructed."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AuthorizedScope:
    organization_id: str
    repository_id: str
    commit_sha: str


class ModelGateway(Protocol):
    def generate(self, *, scope: AuthorizedScope, model_revision: str, evidence: list[str]) -> str:
        """Requires explicit tenant provider/retention policy; unavailable until implemented."""
        ...
