# Corporate Data Engineering Pipeline Directives## Code Conventions- Target Environment: Python 3.11+- All string formatting must strictly utilize **f-strings**. - Legacy `%` formatting or `.format()` methods are explicitly **PROHIBITED**.
## Library Restrictions- **PROHIBITED:** Never use the legacy `urllib` or `requests` libraries for asynchronous HTTP tasks.- **MANDATED:** Always use `httpx` or `aiohttp` for async networking operations.
## Output Schema Standardization- All API endpoint utilities must return a strictly formatted JSON structure matching this exact casing:```json
{
  "status_code": 200,
  "payload_data": {},
  "execution_timestamp": "ISO-8601-string"
}