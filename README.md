# Salesorder — Order Review

An independent portfolio prototype inspired by Flowit's public description of Salesorder and its focus on AI, automation, integrations and business-process software.

## What this demonstrates

- B2B customer order-history analysis
- Explainable anomaly scoring
- Change detection against a historical baseline
- Reason codes instead of a black-box prediction
- Prioritised sales follow-up queue
- Review / dismiss / re-open workflow
- FastAPI REST API with OpenAPI/Swagger docs
- Lightweight responsive dashboard
- Synthetic demo data

## Product flow

`Order history → baseline → anomaly signals → attention score → explanation → suggested action → sales review queue`

The prototype deliberately uses deterministic rules for the first version. This keeps the signal explainable and gives a clear place to add predictive analytics or an LLM explanation layer later without hiding the underlying decision logic.

## API

- `GET /api/health` — health/version check
- `GET /api/dashboard` — summary + prioritised review queue
- `POST /api/orders/analyze` — analyse a customer order
- `PATCH /api/reviews/{customer}/status` — mark a review `open`, `reviewed`, or `dismissed`
- `GET /docs` — interactive Swagger documentation

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Architecture notes

The MVP keeps persistence in memory so the demo is zero-setup. A production iteration would move review state and order history to PostgreSQL, add authentication/audit logging, and introduce customer/SKU-level trend features.

## Important

This project is **not affiliated with Flowit**. It uses synthetic data and does not reproduce or claim knowledge of Flowit's private architecture, data, algorithms or internal systems. The project was created independently as a demonstration of how one could approach a small problem adjacent to Flowit's publicly described product and engineering themes.
