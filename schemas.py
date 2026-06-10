"""Schema utilities for validating ecommerce item instances.

Provides `validate_item()` which raises `jsonschema.ValidationError` on failure.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any

SCHEMA_PATH = Path(__file__).parent / "schemas" / "item_schema.json"


def _load_item_schema() -> dict[str, Any]:
	with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
		return json.load(fh)


_ITEM_SCHEMA = _load_item_schema()


def validate_item(instance: dict[str, Any]) -> None:
	"""Validate `instance` against the ecommerce item JSON Schema.

	Raises:
		jsonschema.ValidationError: if the instance is invalid.
		jsonschema.SchemaError: if the schema itself is invalid.
	"""
	try:
		# Import here so the module can be imported even if jsonschema isn't installed.
		from jsonschema import validate

		validate(instance=instance, schema=_ITEM_SCHEMA)
	except ImportError as exc:  # pragma: no cover - environment issue
		raise ImportError(
			"jsonschema is required to validate items. Install with: pip install jsonschema"
		) from exc


if __name__ == "__main__":
	example = {"id": "SKU-12345", "price": 19.99, "stock_count": 42}
	try:
		validate_item(example)
		print(f"Valid example: {example}")
	except Exception as err:
		print(f"Validation failed: {err}")

