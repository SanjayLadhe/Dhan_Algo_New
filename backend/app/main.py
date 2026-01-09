from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import asyncio
from datetime import datetime
from typing import List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Dhan Algo Backend...")
    # Start background tasks
    task = asyncio.create_task(market_data_simulator())
    yield
    # Cleanup
    task.cancel()
    logger.info("Shutting down...")

app = FastAPI(
    title="Dhan Algo Trading API",
    description="Backend API for algorithmic trading platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample market data simulator
async def market_data_simulator():
    """Simulates market data updates"""
    import random

    symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    base_prices = {"NIFTY": 22000, "BANKNIFTY": 48000, "FINNIFTY": 20000}

    while True:
        try:
            for symbol in symbols:
                base = base_prices[symbol]
                change = random.uniform(-0.5, 0.5)
                ltp = base + (base * change / 100)

                quote_data = {
                    "type": "quote",
                    "data": {
                        "symbol": symbol,
                        "ltp": round(ltp, 2),
                        "open": round(base, 2),
                        "high": round(ltp + random.uniform(0, 50), 2),
                        "low": round(ltp - random.uniform(0, 50), 2),
                        "close": round(base, 2),
                        "volume": random.randint(1000000, 5000000),
                        "change": round(ltp - base, 2),
                        "changePercent": round(change, 2),
                        "timestamp": datetime.now().isoformat(),
                    },
                    "timestamp": datetime.now().isoformat(),
                }

                await manager.broadcast(quote_data)
                base_prices[symbol] = ltp  # Update base for next iteration

            await asyncio.sleep(2)  # Update every 2 seconds
        except Exception as e:
            logger.error(f"Error in market data simulator: {e}")
            await asyncio.sleep(5)

@app.get("/")
async def root():
    return {
        "message": "Dhan Algo Trading API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/account/balance")
async def get_balance():
    """Get account balance"""
    return {
        "totalBalance": 1005000,
        "availableBalance": 950000,
        "usedMargin": 55000,
        "unrealizedPnL": 2500,
        "realizedPnL": 8750
    }

@app.get("/api/positions")
async def get_positions():
    """Get current positions"""
    return {
        "positions": []
    }

@app.get("/api/orders")
async def get_orders():
    """Get order history"""
    return {
        "orders": []
    }

@app.post("/api/orders/place")
async def place_order(order: dict):
    """Place a new order"""
    logger.info(f"Placing order: {order}")
    return {
        "orderId": "ORD123456",
        "status": "PENDING",
        "message": "Order placed successfully"
    }

@app.websocket("/ws/market-data")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            logger.info(f"Received from client: {data}")

            # Echo back or handle client requests
            try:
                message = json.loads(data)
                if message.get("type") == "subscribe":
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "success",
                        "symbols": message.get("symbols", [])
                    })
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
