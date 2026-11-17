"""Bounded GitHub object reader. No Git process, checkout, redirects or repository code."""

import base64
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import quote, urlsplit


class SourceError(Exception):
    pass


def canonical_remote(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", parsed.path)
    ):
        raise ValueError("Only canonical https://github.com/owner/repository URLs are allowed")
    owner, repo = parsed.path[1:].split("/")
    repo = repo.removesuffix(".git")
    if owner in (".", "..") or repo in ("", ".", ".."):
        raise ValueError("Invalid repository path")
    return f"https://github.com/{owner}/{repo}"


def valid_ref(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}", value):
        raise ValueError("Invalid ref")
    if ".." in value or "//" in value or value.endswith(("/", ".lock")):
        raise ValueError("Invalid ref")
    return value


def sha(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{40}", value):
        raise SourceError("invalid_provider_object")
    return value


@dataclass(frozen=True)
class Entry:
    path: str
    blob_sha: str
    size: int
    mode: str


class Source(Protocol):
    def resolve(self, remote: str, ref: str) -> tuple[str, str]: ...
    def inventory(self, remote: str, commit: str, tree: str) -> list[Entry]: ...
    def blob(self, remote: str, entry: Entry) -> bytes: ...


class PinnedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise SourceError("denied_destination")
        # Connect to this validated address, never resolve a second time. Verify TLS hostname.
        address = addresses[0]
        sock = socket.socket(address[0], address[1], address[2])
        sock.settimeout(self.timeout)
        try:
            sock.connect(address[4])
            self.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class GitHubSource:
    def __init__(self):
        self.deadline = time.monotonic() + 1800
        self.bytes_read = 0

    def get(self, path):
        if time.monotonic() >= self.deadline:
            raise SourceError("ingestion_deadline")
        connection = PinnedHTTPS("api.github.com", timeout=15)
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "CodeAtlas-foundation",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise SourceError("provider_unavailable_or_denied")
            body = response.read(16 * 1024 * 1024 + 1)
            self.bytes_read += len(body)
            if len(body) > 16 * 1024 * 1024 or self.bytes_read > 1024**3:
                raise SourceError("fetch_size_limit")
            return json.loads(body)
        except (OSError, ValueError, http.client.HTTPException) as exc:
            raise SourceError("provider_transport_error") from exc
        finally:
            connection.close()

    def prefix(self, remote):
        return "/repos/" + canonical_remote(remote).removeprefix("https://github.com/")

    def resolve(self, remote, ref):
        data = self.get(self.prefix(remote) + "/commits/" + quote(valid_ref(ref), safe=""))
        return sha(data["sha"]), sha(data["commit"]["tree"]["sha"])

    def inventory(self, remote, commit, tree):
        sha(commit)
        data = self.get(self.prefix(remote) + "/git/trees/" + sha(tree) + "?recursive=1")
        if data.get("truncated"):
            raise SourceError("truncated_tree")
        entries = [
            Entry(e["path"], sha(e["sha"]), e.get("size", 0), e["mode"])
            for e in data["tree"]
            if e["type"] != "tree"
        ]
        if len(entries) > 100000 or sum(e.size for e in entries) > 1024**3:
            raise SourceError("inventory_size_limit")
        return entries

    def blob(self, remote, entry):
        data = self.get(self.prefix(remote) + "/git/blobs/" + sha(entry.blob_sha))
        if data.get("encoding") != "base64":
            raise SourceError("unsupported_blob_encoding")
        content = base64.b64decode(data["content"])
        digest = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if digest != entry.blob_sha or len(content) != entry.size:
            raise SourceError("blob_integrity_error")
        return content


def classify(entry):
    path = PurePosixPath(entry.path)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in entry.path
        or "\0" in entry.path
        or ":" in entry.path
        or len(entry.path) > 2048
    ):
        raise SourceError("unsafe_path")
    if entry.mode not in ("100644", "100755"):
        return "excluded", "symlink_or_submodule"
    sensitive = (".env", ".aws", ".ssh", ".git", "node_modules", "vendor", "dist")
    if (
        any(p.lower() in sensitive or p.lower().startswith(".env.") for p in path.parts)
        or path.suffix.lower() in (".pem", ".key", ".p12", ".pfx")
        or path.name.lower() in ("credentials", "id_rsa", "id_ed25519")
    ):
        return "excluded", "sensitive_or_generated_path"
    if entry.size > 1024 * 1024:
        return "oversized", "text_size_limit"
    if path.name.lower() not in ("readme", "license", "copying") and path.suffix.lower() not in (
        ".py",
        ".ts",
        ".tsx",
        ".md",
        ".txt",
        ".json",
        ".toml",
        ".yaml",
        ".yml",
    ):
        return "unsupported", "unsupported_extension"
    return "inventoried", None
