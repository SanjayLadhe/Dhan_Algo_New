import json
import websocket
import pandas as pd
from datetime import datetime

ticks = []  # store tick data

def on_message(ws, message):
    data = json.loads(message)
    if "data" in data and "ltp" in data["data"][0]:
        tick = {
            "time": datetime.now(),
            "ltp": float(data["data"][0]["ltp"])
        }
        ticks.append(tick)

def on_open(ws):
    print("✅ Connected to Dhan WebSocket")
    payload = {
        "data": {
            "symbols": ["DRREDDY 28 OCT 1260 CALL"]
        },
        "type": "subscribe"
    }
    ws.send(json.dumps(payload))

ws = websocket.WebSocketApp(
    "wss://api.dhan.co/v2/market-stream",
    on_open=on_open,
    on_message=on_message
)

ws.run_forever()
