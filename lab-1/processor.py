#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Tuple, Union

from pydantic import BaseModel, ValidationError, field_validator

MAX_MEMORY_BYTES = 10_000_000

logger = logging.getLogger("processor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


class UserMetadata(BaseModel):
    user_id: int
    email: str
    signup_date: date

    model_config = {
        "extra": "forbid",
    }

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or value.count("@") != 1:
            raise ValueError("email must be a valid email address")
        return value


def _validate_local_path(file_path: Union[str, Path]) -> Path:
    base_dir = Path.cwd().resolve()
    path = Path(file_path)

    if path.is_absolute():
        raise ValueError("Absolute paths are not allowed.")

    resolved_path = (base_dir / path).resolve()
    if base_dir != resolved_path and base_dir not in resolved_path.parents:
        raise ValueError("File path must be inside the current working directory.")

    return resolved_path


def safe_ingest_user_metadata(file_path: Union[str, Path]) -> Tuple[bool, dict]:
    try:
        resolved_path = _validate_local_path(file_path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {resolved_path}")
        if resolved_path.is_dir():
            raise ValueError("Expected a file path, not a directory.")

        file_size = resolved_path.stat().st_size
        if file_size > MAX_MEMORY_BYTES:
            logger.info(
                "Large file detected (%s bytes); parsing JSON from stream to avoid loading full text into memory.",
                file_size,
            )

        with resolved_path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        if not isinstance(payload, dict):
            raise ValueError("Expected top-level JSON object with user metadata.")

        model = UserMetadata.model_validate(payload)
        logger.info("Validated user metadata for user_id=%s", model.user_id)
        return True, {"status": "validated", "payload": model}

    except FileNotFoundError as error:
        logger.error("FileNotFoundError: %s", error)
        return False, {"status": "failed", "reason": str(error)}
    except PermissionError as error:
        logger.error("PermissionError: %s", error)
        return False, {"status": "failed", "reason": str(error)}
    except ValidationError as error:
        error_details = []
        for item in error.errors():
            sanitized = item.copy()
            if isinstance(sanitized.get("ctx"), dict):
                sanitized["ctx"] = {k: str(v) for k, v in sanitized["ctx"].items()}
            sanitized["msg"] = str(sanitized.get("msg"))
            error_details.append(sanitized)
        logger.error("ValidationError: %s", error_details)
        return False, {"status": "failed", "reason": json.dumps(error_details, ensure_ascii=False)}
    except json.JSONDecodeError as error:
        logger.error("JSONDecodeError: %s", error)
        return False, {"status": "failed", "reason": str(error)}
    except ValueError as error:
        logger.error("Validation failed: %s", error)
        return False, {"status": "failed", "reason": str(error)}
    except Exception as error:
        logger.exception("Unexpected error while ingesting metadata: %s", error)
        return False, {"status": "failed", "reason": "Unexpected error occurred."}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse user metadata JSON file and validate it with Pydantic."
    )
    parser.add_argument("input", help="Input JSON user metadata file path")
    parser.add_argument("--log", "-l", help="Optional log file path", default=None)
    parser.add_argument(
        "--level",
        "-v",
        help="Logging level (DEBUG/INFO/WARNING/ERROR)",
        default="INFO",
    )
    args = parser.parse_args()

    if args.log:
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(file_handler)

    logger.setLevel(getattr(logging, args.level.upper(), logging.INFO))

    success, result = safe_ingest_user_metadata(args.input)
    if success:
        logger.info("Ingestion successful for user_id=%s", result["payload"].user_id)
        print(result)
        sys.exit(0)

    logger.error("Ingestion failed: %s", result["reason"])
    print(result)
    sys.exit(1)


if __name__ == "__main__":
    main()
