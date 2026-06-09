# Day2

A simple FastAPI webhook processor for Stripe payment events.

## Files added

- `main.py` - FastAPI application with idempotent Stripe webhook handling.
- `config.py` - application settings and Redis/DB configuration.
- `database.py` - SQLAlchemy ORM session, model, and initialization.
- `payment.py` - Pydantic schema for Stripe webhook payload validation.
- `requirements.txt` - dependencies for running the app.

## Run locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start Redis locally and then run the FastAPI app:
   ```bash
   uvicorn main:app --reload
   ```

The webhook endpoint is available at `POST /webhook`.
