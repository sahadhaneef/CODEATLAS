"""Controlled first-party experiments, not production indexing or repository execution."""

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("language", ["python", "typescript", "tsx"])
def test_tree_sitter_byte_spans_and_crlf(language):
    pytest.importorskip("tree_sitter")
    from spikes.parsing import definitions

    content = (
        "# 😀\r\ndef café():\r\n    return 'é'\r\n"
        if language == "python"
        else '// 😀\r\nfunction café() { return "é"; }\r\n'
    ).encode()
    result = definitions(content, language)
    assert not result["has_errors"]
    span = result["definitions"][0]
    assert span["name"] == "café" and span["start_line"] == 2
    assert span["start_byte"] > content.decode().index(
        "def" if language == "python" else "function"
    )
    assert content[span["start_byte"] : span["end_byte"]].startswith(
        b"def " if language == "python" else b"function "
    )
    assert result["capability"] == "syntax_only" and not result["resolved_references"]


def test_tree_sitter_reports_partial_parse():
    pytest.importorskip("tree_sitter")
    from spikes.parsing import definitions

    assert definitions(b"def broken(:\n", "python")["has_errors"]


def test_pyright_cli_capabilities_without_repository_config(tmp_path):
    script = ROOT / "spikes/semantic/node_modules/pyright/dist/pyright.js"
    if not script.exists() or not shutil.which("node"):
        pytest.skip("Run npm ci --ignore-scripts in spikes/semantic")
    (tmp_path / "fixture.py").write_text(
        'def greet(name: str) -> str:\n    return name\nvalue: int = greet("ok")\n',
        encoding="utf-8",
    )
    # Entire project is first-party, temporary and server-configured. No imported config used.
    config = {
        "include": ["fixture.py"],
        "pythonVersion": "3.12",
        "typeCheckingMode": "basic",
        "typeshedPath": str(script.parent / "typeshed-fallback"),
        "useLibraryCodeForTypes": False,
        "extraPaths": [],
    }
    (tmp_path / "pyrightconfig.json").write_text(json.dumps(config), encoding="utf-8")
    result = subprocess.run(
        [
            shutil.which("node"),
            str(script),
            "--project",
            str(tmp_path / "pyrightconfig.json"),
            "--outputjson",
            "--pythonpath",
            sys.executable,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 1  # deliberate assignment mismatch, never run fixture.py
    output = json.loads(result.stdout)
    assert output["version"] == "1.1.405"
    assert any(d.get("rule") == "reportAssignmentType" for d in output["generalDiagnostics"])
    assert "references" not in output  # CLI diagnostics are not a public definition/reference API.


def test_typescript_signature_and_utf16_conversion():
    directory = ROOT / "spikes/semantic"
    if not (directory / "node_modules/typescript").exists() or not shutil.which("node"):
        pytest.skip("Run npm ci --ignore-scripts in spikes/semantic")
    result = subprocess.run(
        [shutil.which("node"), str(directory / "probe.cjs")],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    output = json.loads(result.stdout)
    assert output["version"] == "5.8.3" and output["resolution"] == "resolved"
    assert output["startByte"] > output["startUtf16"]
    assert not output["configLoaded"] and not output["emitted"]
