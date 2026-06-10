# lab-1

Contains the `processor.py` script and sample user data for testing.

The file now includes a production-ready utility `safe_ingest_user_metadata` that validates JSON files using Pydantic.

Run:

```bash
python3 processor.py lab-1/user_metadata.json --log lab-1/parsed.log
```
