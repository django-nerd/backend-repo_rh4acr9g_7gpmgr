import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

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
        # Try to import database module
        from database import db as _db
        
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# -------------------- IPO API --------------------

def _serialize(doc):
    if not doc:
        return doc
    d = dict(doc)
    d.pop("_id", None)
    return d


def _fallback_list():
    return [
        {
            "name": "Sample IPO",
            "symbol": "SAMPLE",
            "sector": "General",
            "issuePrice": 100.0,
            "currentPrice": 110.0,
            "lotSize": 150,
            "listDate": "2025-01-15",
            "registrar": "KFintech",
            "exchanges": ["NSE", "BSE"],
            "timeline": {"bidding": ["2025-01-01", "2025-01-03"], "listing": "2025-01-15"},
            "subscription": {"QIB": 3.2, "NII": 1.8, "Retail": 2.4},
            "description": "Demo IPO for environments without DB.",
        }
    ]


def _ensure_seed_data():
    """Try to seed a few IPO docs if collection is empty; ignore all errors (read-only envs)."""
    try:
        if db is None:
            return
        count = db["ipo"].count_documents({})
        if count > 0:
            return
        seed = [
            {
                "name": "Alpha Tech Solutions",
                "symbol": "ALPHATECH",
                "sector": "Technology",
                "issuePrice": 120.0,
                "currentPrice": 168.0,
                "lotSize": 125,
                "listDate": datetime.utcnow().strftime("%Y-%m-%d"),
                "description": "Cloud-first enterprise software provider with strong ARR growth.",
                "registrar": "KFintech",
                "exchanges": ["NSE", "BSE"],
                "timeline": {"bidding": ["2025-11-01", "2025-11-04"], "listing": "2025-11-10"},
                "subscription": {"QIB": 12.5, "NII": 8.2, "Retail": 5.3},
            },
            {
                "name": "Greenfield Foods",
                "symbol": "GREENFD",
                "sector": "FMCG",
                "issuePrice": 90.0,
                "currentPrice": 85.0,
                "lotSize": 160,
                "listDate": "2025-10-15",
                "description": "Packaged foods with pan-India distribution.",
                "registrar": "Link Intime",
                "exchanges": ["NSE", "BSE"],
                "timeline": {"bidding": ["2025-10-01", "2025-10-03"], "listing": "2025-10-15"},
                "subscription": {"QIB": 2.1, "NII": 1.4, "Retail": 1.2},
            },
            {
                "name": "Nimbus Logistics",
                "symbol": "NIMBUS",
                "sector": "Logistics",
                "issuePrice": 150.0,
                "currentPrice": 199.0,
                "lotSize": 100,
                "listDate": "2025-09-20",
                "description": "Integrated supply-chain services with multimodal network.",
                "registrar": "KFintech",
                "exchanges": ["NSE"],
                "timeline": {"bidding": ["2025-09-10", "2025-09-12"], "listing": "2025-09-20"},
                "subscription": {"QIB": 6.8, "NII": 3.4, "Retail": 2.9},
            },
        ]
        for s in seed:
            try:
                create_document("ipo", s)
            except Exception:
                # Ignore write errors (e.g., read-only Cosmos or quota exceeded)
                return
    except Exception:
        # Never crash on seed in constrained environments
        return


@app.get("/api/ipos")
async def list_ipos():
    if db is None:
        return _fallback_list()
    try:
        _ensure_seed_data()
        docs = get_documents("ipo")
        if not docs:
            return _fallback_list()
        return [_serialize(d) for d in docs]
    except Exception:
        return _fallback_list()


@app.get("/api/ipos/{symbol}")
async def get_ipo(symbol: str):
    if db is None:
        # Serve from fallback
        items = _fallback_list()
        for it in items:
            if it["symbol"].lower() == symbol.lower():
                return it
        raise HTTPException(status_code=404, detail="IPO not found")

    try:
        doc = db["ipo"].find_one({"symbol": symbol})
        if not doc:
            # try case-insensitive symbol
            doc = db["ipo"].find_one({"symbol": {"$regex": f"^{symbol}$", "$options": "i"}})
        if not doc:
            # Fall back to demo if nothing in DB
            items = _fallback_list()
            for it in items:
                if it["symbol"].lower() == symbol.lower():
                    return it
            raise HTTPException(status_code=404, detail="IPO not found")
        return _serialize(doc)
    except Exception:
        # On any DB error, return fallback if symbol matches
        items = _fallback_list()
        for it in items:
            if it["symbol"].lower() == symbol.lower():
                return it
        raise HTTPException(status_code=404, detail="IPO not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
