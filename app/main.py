from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="Salesorder AI Order Review",
    version="0.2.0",
    description="Independent prototype for reviewing unusual B2B customer order behaviour and prioritising sales follow-up."
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class Order(BaseModel):
    order_date: date
    amount: float = Field(gt=0)
    units: int = Field(gt=0)


class AnalyzeRequest(BaseModel):
    customer: str = Field(min_length=1)
    historical_orders: List[Order] = Field(min_length=3)
    current_order: Order


class ReviewStatus(BaseModel):
    status: str = Field(pattern="^(open|reviewed|dismissed)$")


class Analysis(BaseModel):
    id: str
    customer: str
    current_amount: float
    baseline_amount: float
    amount_change_pct: float
    current_units: int
    baseline_units: float
    unit_change_pct: float
    anomaly_score: int
    severity: str
    reasons: List[str]
    suggested_action: str
    status: str = "open"


def pct_change(current: float, baseline: float) -> float:
    return 0.0 if baseline == 0 else ((current - baseline) / baseline) * 100


def analyze(req: AnalyzeRequest) -> Analysis:
    amounts = [o.amount for o in req.historical_orders]
    units = [o.units for o in req.historical_orders]
    amount_baseline = mean(amounts)
    units_baseline = mean(units)
    amount_change = pct_change(req.current_order.amount, amount_baseline)
    unit_change = pct_change(req.current_order.units, units_baseline)

    score = 0
    reasons: List[str] = []

    if amount_change <= -30:
        score += 40
        reasons.append(f"Order value is {abs(amount_change):.0f}% below the customer's historical average.")
    elif amount_change >= 50:
        score += 30
        reasons.append(f"Order value is {amount_change:.0f}% above the customer's historical average.")

    if unit_change <= -30:
        score += 30
        reasons.append(f"Order volume is {abs(unit_change):.0f}% below the customer's historical average.")
    elif unit_change >= 50:
        score += 20
        reasons.append(f"Order volume is {unit_change:.0f}% above the customer's historical average.")

    if len(amounts) >= 4:
        deviation = pstdev(amounts) or 1
        z = abs(req.current_order.amount - amount_baseline) / deviation
        if z >= 2:
            score += 20
            reasons.append("The current order is more than two standard deviations from the historical pattern.")

    score = min(score, 100)
    if score >= 70:
        severity = "High"
        action = "Create a sales follow-up: review recent account activity and possible demand change before fulfilment."
    elif score >= 40:
        severity = "Medium"
        action = "Review the account and compare this order with recent customer activity before taking action."
    else:
        severity = "Low"
        action = "Monitor the account; the current signals do not suggest immediate intervention."

    if not reasons:
        reasons.append("The current order is within the customer's normal historical range.")

    return Analysis(
        id=str(uuid4())[:8], customer=req.customer,
        current_amount=req.current_order.amount, baseline_amount=amount_baseline,
        amount_change_pct=amount_change, current_units=req.current_order.units,
        baseline_units=units_baseline, unit_change_pct=unit_change,
        anomaly_score=score, severity=severity, reasons=reasons,
        suggested_action=action,
    )


def demo_order(customer: str, values: List[float], units: List[int], current: float, current_units: int) -> Analysis:
    base = date.today()
    history = [Order(order_date=base - timedelta(days=30 * (len(values) - i)), amount=a, units=u)
               for i, (a, u) in enumerate(zip(values, units))]
    return analyze(AnalyzeRequest(
        customer=customer,
        historical_orders=history,
        current_order=Order(order_date=base, amount=current, units=current_units),
    ))


# Synthetic demo data only. It is intentionally close to the workflow being demonstrated,
# not copied from any private Flowit/Salesorder data.
reviews: Dict[str, Analysis] = {}
for item in [
    demo_order("Nordic Manufacturing Ltd", [19800, 21400, 22100, 20500, 21900, 21000], [980,1040,1080,1010,1060,1020], 8400, 430),
    demo_order("Baltic Supplies", [14200, 15100, 14900, 15600, 15300, 15000], [710,760,740,780,750,755], 8700, 470),
    demo_order("Karo Industries", [9200, 9800, 10100, 9500, 9900, 9700], [460,490,500,475,495,485], 15700, 790),
    demo_order("Metro Parts", [11200, 10800, 11500, 10900, 11100, 11400], [560,540,575,545,555,570], 10900, 550),
]:
    reviews[item.customer] = item


@app.get("/", include_in_schema=False)
def home():
    return FileResponse("app/static/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/api/dashboard")
def dashboard():
    items = list(reviews.values())
    priority = {"High": 0, "Medium": 1, "Low": 2}
    items.sort(key=lambda x: (priority[x.severity], -x.anomaly_score))
    return {
        "summary": {
            "customers_reviewed": len(items),
            "needs_attention": sum(x.severity in {"High", "Medium"} and x.status == "open" for x in items),
            "high_priority": sum(x.severity == "High" and x.status == "open" for x in items),
            "reviewed": sum(x.status == "reviewed" for x in items),
        },
        "reviews": items,
    }


@app.post("/api/orders/analyze", response_model=Analysis)
def analyze_order(req: AnalyzeRequest):
    result = analyze(req)
    reviews[result.customer] = result
    return result


@app.patch("/api/reviews/{customer}/status", response_model=Analysis)
def update_status(customer: str, body: ReviewStatus):
    result = reviews.get(customer)
    if not result:
        raise HTTPException(status_code=404, detail="Customer review not found")
    result.status = body.status
    return result
