import os
import sys
import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str
    token_a: str
    token_b: str
    environment: str = "development"
    identities: dict = field(default_factory=dict)
    auth_mode: str = "development"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_keys: dict = field(default_factory=dict)

    def validate(self):
        if sys.version_info[:2] != (3, 12):
            raise ValueError("CodeAtlas requires Python 3.12")
        if self.auth_mode == "oidc":
            if (
                not self.oidc_issuer.startswith("https://")
                or not self.oidc_audience
                or not self.oidc_keys
            ):
                raise ValueError("OIDC issuer, audience and pinned signing keys required")
            if self.token_a or self.token_b or self.identities:
                raise ValueError("Development identities must be absent in OIDC mode")
            return
        if self.auth_mode != "development" or self.environment != "development":
            raise ValueError("Development identity production startup refused")
        if min(len(self.token_a), len(self.token_b)) < 24 or self.token_a == self.token_b:
            raise ValueError("Set two distinct development bearer tokens of at least 24 characters")
        if any(t.startswith("replace-") for t in (self.token_a, self.token_b)):
            raise ValueError("Replace example tokens before startup")
        for token, actor in self.identities.items():
            if len(token) < 24 or token in (self.token_a, self.token_b) or len(actor) != 3:
                raise ValueError("Invalid development identity mapping")
            if actor[2] not in ("owner", "admin", "developer", "viewer"):
                raise ValueError("Invalid organization role")

    @classmethod
    def from_env(cls):
        value = cls(
            os.environ.get("CODEATLAS_DATABASE_URL", ""),
            os.environ.get("CODEATLAS_DEV_TOKEN_A", ""),
            os.environ.get("CODEATLAS_DEV_TOKEN_B", ""),
            os.environ.get("CODEATLAS_ENV", "development"),
            json.loads(os.environ.get("CODEATLAS_DEV_IDENTITIES", "{}")),
            os.environ.get("CODEATLAS_AUTH_MODE", "development"),
            os.environ.get("CODEATLAS_OIDC_ISSUER", ""),
            os.environ.get("CODEATLAS_OIDC_AUDIENCE", ""),
            json.loads(os.environ.get("CODEATLAS_OIDC_KEYS", "{}")),
        )
        value.validate()
        if not value.database_url:
            raise ValueError("CODEATLAS_DATABASE_URL is required; run migrations before startup")
        return value
