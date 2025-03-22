from fastapi import FastAPI, Response
import httpx
import asyncio
import sqlite3
import matplotlib.pyplot as plt
import io
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import json

GITHUB_RAW_URL = "https://raw.githubusercontent.com/mahkia89/crypto-db/refs/heads/main/prices.json"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "API is running!"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint working!"}

def create_database():
    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        price REAL NOT NULL,
        source TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

async def fetch_prices_from_github():
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(GITHUB_RAW_URL)
        print("🔹 GitHub Fetch Status:", response.status_code)  # لاگ برای تست
        print("🔹 Response:", response.text[:500])  # لاگ 500 کاراکتر اول
        if response.status_code == 200:
            try:
                data = response.json()
                return data
            except json.JSONDecodeError:
                print("❌ JSON Decode Error!")
                return None
        return None


async def update_prices():
    data = await fetch_prices_from_github()
    if data:
        conn = sqlite3.connect("crypto_prices.db")
        cursor = conn.cursor()

        from datetime import datetime

        for coin in data:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # تبدیل به string برای sqlite
            cursor.execute(
                "INSERT INTO prices (symbol, price, source, timestamp) VALUES (?, ?, ?, ?)",
                (coin["symbol"], coin["price"], "GitHub DB", timestamp)
            )

        conn.commit()
        conn.close()
        print("✅ Prices updated from GitHub database.")
    else:
        print("❌ Failed to fetch prices from GitHub!")

@app.get("/prices")
async def get_prices():
    await update_prices()
    return {"status": "success", "message": "Prices updated from GitHub and stored in database."}
    
@app.get("/stored-prices")
async def stored_prices():
    return await get_prices()

async def periodic_price_fetch():
    while True:
        await update_prices()
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    create_database()
    asyncio.create_task(periodic_price_fetch())

@app.get("/chart-image/{coin_symbol}")
async def get_price_chart(coin_symbol: str):
    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()
    cursor.execute("SELECT price, timestamp FROM prices WHERE symbol = ? ORDER BY timestamp DESC", (coin_symbol,))
    data = cursor.fetchall()
    conn.close()

    if not data:
        return Response(content="No data available", media_type="text/plain", status_code=404)

    prices = [row[0] for row in data]
    
    timestamps = []
    for row in data:
        try:
            timestamps.append(datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            print(f"❌ Error parsing timestamp: {row[1]}")

    timestamps = [datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S") for row in data]
    
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, prices, marker="o", linestyle="-")
    plt.title(f"{coin_symbol} Price Trend")
    plt.xlabel("Time")
    plt.ylabel("Price (USD)")
    plt.grid(True)
    plt.xticks(rotation=45)
    
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    plt.close()
    
    return Response(content=img_buf.getvalue(), media_type="image/png")

from email_system.email_sender import generate_and_send_email

@app.get("/send-email")
async def send_price_chart_email():
    result = generate_and_send_email()
    return {"status": "success", "message": result}

