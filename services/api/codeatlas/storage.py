"""Authenticated, scoped encrypted source envelopes. Key is never stored with ciphertext."""

import base64
import hashlib
import json
import os

from cryptography.fernet import Fernet
from codeatlas.source import SourceError


def cipher():
    key = os.environ.get("CODEATLAS_SOURCE_KEY")
    if not key:
        raise SourceError("source_key_unconfigured")
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise SourceError("source_key_invalid") from exc


def seal(content, tenant, repo, commit, path):
    envelope = dict(
        tenant=tenant,
        repository=repo,
        commit=commit,
        path=path,
        content=base64.b64encode(content).decode(),
    )
    return cipher().encrypt(json.dumps(envelope).encode()).decode(), hashlib.sha256(
        content
    ).hexdigest()


def unseal(record, commit):
    envelope = json.loads(cipher().decrypt(record["source_ciphertext"].encode()))
    expected = dict(
        tenant=record["organization_id"],
        repository=record["repository_id"],
        commit=commit,
        path=record["path"],
    )
    if any(envelope.get(k) != v for k, v in expected.items()):
        raise SourceError("source_scope_mismatch")
    content = base64.b64decode(envelope["content"], validate=True)
    if hashlib.sha256(content).hexdigest() != record["source_hash"]:
        raise SourceError("source_integrity_error")
    return content
