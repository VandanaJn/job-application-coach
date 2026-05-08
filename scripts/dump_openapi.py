"""Dump the FastAPI OpenAPI schema to a JSON file.

Used by the frontend codegen pipeline. CI re-runs this and fails the
PR if the committed schema/types are stale relative to the routes.

Run from repo root:
    python scripts/dump_openapi.py
"""
import json
import os
import sys
from pathlib import Path

# DynamoDB table names are read at api.config import time. Set placeholders
# so the FastAPI app can boot without a real environment.
os.environ.setdefault("DYNAMODB_TABLE_NAME", "schema-dump")
os.environ.setdefault("DYNAMODB_USERS_TABLE", "schema-dump")
os.environ.setdefault("DYNAMODB_JOBS_TABLE", "schema-dump")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import app  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUT.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(Path.cwd())} ({len(schema['paths'])} paths)")


if __name__ == "__main__":
    main()
