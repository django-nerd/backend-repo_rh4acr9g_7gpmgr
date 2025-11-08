import os
import math
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Health
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "GoDigitalNest FastAPI Backend"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# -----------------------------
# Data models
# -----------------------------
class IPO(BaseModel):
    symbol: str
    name: str
    sector: str
    listDate: str
    issuePrice: float
    currentPrice: float

class IPODetail(IPO):
    description: Optional[str] = None
    registrar: Optional[str] = None
    exchanges: Optional[List[str]] = None
    lotSize: Optional[int] = None
    subscription: Optional[dict] = None
    timeline: Optional[dict] = None

# -----------------------------
# Sample data (replace with live NSE/BSE feeds in production)
# -----------------------------
IPOS: List[IPODetail] = [
    IPODetail(symbol="IDEAFO", name="IdeaForge", sector="Aerospace & Defence", listDate="2023-06-29", issuePrice=672, currentPrice=1360,
              description="Drone manufacturer serving defence and enterprise clients.", registrar="Link Intime", exchanges=["NSE", "BSE"], lotSize=22,
              subscription={"QIB": 80.6, "NII": 62.6, "RII": 85.2}, timeline={"bidding": ["2023-06-26", "2023-06-28"], "listing": "2023-06-29"}),
    IPODetail(symbol="TATATECH", name="Tata Technologies", sector="IT Services", listDate="2023-11-30", issuePrice=500, currentPrice=1210,
              description="Engineering and product development digital services company.", registrar="Link Intime", exchanges=["NSE", "BSE"], lotSize=30,
              subscription={"QIB": 203.4, "NII": 62.1, "RII": 16.5}, timeline={"bidding": ["2023-11-22", "2023-11-24"], "listing": "2023-11-30"}),
    IPODetail(symbol="EMS", name="EMS Ltd", sector="Utilities", listDate="2023-09-21", issuePrice=211, currentPrice=497,
              description="Water and waste water treatment solutions provider.", registrar="KFintech", exchanges=["NSE", "BSE"], lotSize=70,
              subscription={"QIB": 149.0, "NII": 81.0, "RII": 30.5}, timeline={"bidding": ["2023-09-08", "2023-09-12"], "listing": "2023-09-21"}),
]

INDICES = [
  {"name": "NIFTY 50", "last": 23200.5, "chg": 0.62},
  {"name": "NIFTY BANK", "last": 49875.9, "chg": -0.18},
  {"name": "SENSEX", "last": 76980.3, "chg": 0.41},
  {"name": "NIFTY IT", "last": 36420.1, "chg": 0.25},
]

STOCKS = [
  {"symbol": "RELIANCE", "name": "Reliance Industries", "price": 2965.4, "pe": 27.3, "pb": 2.4, "mcap": "20.4T"},
  {"symbol": "TCS", "name": "Tata Consultancy Services", "price": 3942.1, "pe": 30.8, "pb": 15.4, "mcap": "14.6T"},
  {"symbol": "HDFCBANK", "name": "HDFC Bank", "price": 1542.3, "pe": 19.2, "pb": 2.8, "mcap": "11.5T"},
  {"symbol": "ICICIBANK", "name": "ICICI Bank", "price": 1178.6, "pe": 20.4, "pb": 3.4, "mcap": "8.6T"},
  {"symbol": "INFY", "name": "Infosys", "price": 1624.8, "pe": 24.7, "pb": 7.8, "mcap": "6.8T"},
]

# -----------------------------
# IPO endpoints
# -----------------------------
@app.get("/api/ipos", response_model=List[IPO])
def list_ipos():
    return [IPO(**i.dict()) for i in IPOS]

@app.get("/api/ipos/{symbol}", response_model=IPODetail)
def ipo_detail(symbol: str):
    for i in IPOS:
        if i.symbol.lower() == symbol.lower():
            return i
    raise HTTPException(status_code=404, detail="IPO not found")

# -----------------------------
# Market snapshot endpoint
# -----------------------------
@app.get("/api/market")
def market_snapshot():
    return {"indices": INDICES, "stocks": STOCKS}

# -----------------------------
# Tools: Black–Scholes option pricing
# -----------------------------
class OptionRequest(BaseModel):
    S: float
    K: float
    T: float  # years
    r: float  # risk-free rate (decimals)
    sigma: float  # volatility (decimals)
    type: str  # 'call' or 'put'

class OptionResponse(BaseModel):
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float

from math import log, sqrt, exp
from statistics import NormalDist

norm = NormalDist()

def _black_scholes(S, K, T, r, sigma, is_call):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {k: 0.0 for k in ["price","delta","gamma","vega","theta","rho"]}
    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    if is_call:
        price = S * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
        rho = K * T * exp(-r * T) * norm.cdf(d2) / 100.0
        theta = (-(S * norm.pdf(d1) * sigma) / (2 * sqrt(T)) - r * K * exp(-r*T) * norm.cdf(d2)) / 365.0
    else:
        price = K * exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = -norm.cdf(-d1)
        rho = -K * T * exp(-r * T) * norm.cdf(-d2) / 100.0
        theta = (-(S * norm.pdf(d1) * sigma) / (2 * sqrt(T)) + r * K * exp(-r*T) * norm.cdf(-d2)) / 365.0
    gamma = norm.pdf(d1) / (S * sigma * sqrt(T))
    vega = S * norm.pdf(d1) * sqrt(T) / 100.0
    return {"price": price, "delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}

@app.post("/api/tools/black_scholes", response_model=OptionResponse)
def black_scholes(req: OptionRequest):
    is_call = req.type.lower() == 'call'
    res = _black_scholes(req.S, req.K, req.T, req.r, req.sigma, is_call)
    return OptionResponse(**res)

# -----------------------------
# Valuation and prediction stubs
# -----------------------------
class ValuationRequest(BaseModel):
    multiples: dict
    growth: float

@app.post("/api/valuation")
def valuation(req: ValuationRequest):
    medians = {"evEbitda": 12.4, "pe": 18.7, "pb": 3.1}
    priceByMultiple = {"evEbitda": 95, "pe": 102, "pb": 88}
    active = [k for k, v in req.multiples.items() if v]
    targetPrice = sum(priceByMultiple[k] for k in active) / len(active) if active else None
    impliedPremium = max(0.0, ((targetPrice or 0) - 90) / 90) * 100
    premiumValidated = impliedPremium <= req.growth * 1.2
    return {
        "targetPrice": targetPrice,
        "premiumValidated": premiumValidated,
        "medianMultiples": medians,
        "latencyMs": 5,
    }

class PredictRequest(BaseModel):
    npm: float
    subscription: float
    sentiment: float

@app.post("/api/predict")
def predict(req: PredictRequest):
    p = 0.35 * (req.npm / 20) + 0.4 * (req.subscription / 2) + 0.25 * req.sentiment
    p = max(0.0, min(1.0, p))
    return {
        "probability": p,
        "drivers": [
            f"NPM% contribution: {(req.npm / 20 * 35):.1f} pts",
            f"Subscription intensity: {(req.subscription / 2 * 40):.1f} pts",
            f"Social sentiment: {(req.sentiment * 25):.1f} pts",
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
