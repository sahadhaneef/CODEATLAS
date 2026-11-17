# Dataset manifest contract (not an acquired benchmark)

Each future manifest is JSON with schema_version, repository_url, full commit_sha, license,
license_review, allowed_usage, languages, archive_sha256, provenance and split. No floating
branches or unreviewed redistribution are allowed. Model identities additionally require exact
revision, dimensions, tokenizer, license, truncation and normalization before use.

`dataset.schema.json` is generated from `codeatlas.contracts.DatasetManifest`. Validate a
manifest with that Pydantic model; it rejects floating commit refs and malformed archive hashes.
Run `python scripts/export_contracts.py --check` using Python 3.12 to check schema drift.

The only current corpus is first-party synthetic content in tests/test_foundation.py,
ControlledSource. It is served through the injected Source port; production allowlists are
unchanged. Its synthetic commit/tree IDs test pin propagation, not Git tree integrity or
semantic adapter accuracy. There is no benchmark score, third-party corpus, model selection,
parser span evidence or evaluation run yet.
