# interface/api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    order_type: str
    side: str
    price: Optional[float] = None

@app.get("/status")
async def get_status():
    """Get system status"""
    return {"status": "running"}

@app.get("/positions")
async def get_positions():
    """Get current positions"""
    return {"positions": []}

@app.post("/trade")
async def place_trade(trade: TradeRequest):
    """Place new trade"""
    return {"order_id": "123"}

@app.get("/report/{date}")
async def get_report(date: str):
    """Get trading report"""
    return {"date": date, "pnl": 0}