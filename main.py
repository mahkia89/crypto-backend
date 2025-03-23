from fastapi import FastAPI, Response
import httpx
import asyncio
import psycopg2
import matplotlib.pyplot as plt
import io
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import json
import os

# GitHub Data Source
GITHUB_RAW_URL = "https://raw.githubusercontent.com/mahkia89/crypto-db/main/prices.json"

# PostgreSQL Database Connection Details
DB_HOST = "dpg-cvfqephopnds73bcc2a0-a"  # Render internal hostname
DB_NAME = "crypto_db_b52e"  # Replace with your actual DB name
DB_USER = "crypto_db_b52e_user"  # Replace with your actual username
DB_PASSWORD = "mTcqgolkW8xSYVgngMhpp4eHKZeOJx8v"  # Replace with your actual password
DB_PORT = "5432"  # Default PostgreSQL port

# Function to get a database connection
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

app = FastAPI()

# CORS Middleware (Allows external frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create PostgreSQL Table
def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        price REAL NOT NULL,
        source TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Fetch prices from GitHub
async def fetch_prices_from_github():
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(GITHUB_RAW_URL)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, str):  # If GitHub returns it as a string, parse it manually
                    data = json.loads(data)
                if not isinstance(data, list):  # Ensure it's a list of dictionaries
                    raise ValueError("Invalid JSON format: Expected a list of dictionaries")
                return data
            except json.JSONDecodeError:
                print("❌ Failed to parse JSON from GitHub!")
                return None
    print("❌ Failed to fetch prices from GitHub!")
    return None


# Update database with new prices
async def update_prices():
    data = await fetch_prices_from_github()
    if data:
        conn = get_db_connection()
        cursor = conn.cursor()

        for coin in data:
            cursor.execute(
                "INSERT INTO prices (symbol, price, source) VALUES (%s, %s, %s)",
                (coin["symbol"], coin["price"], "GitHub DB")
            )

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Prices updated from GitHub database.")
    else:
        print("❌ Failed to fetch prices from GitHub!")

# API route to trigger price update
@app.get("/prices")
async def get_prices():
    await update_prices()
    return {"status": "success", "message": "Prices updated from GitHub and stored in database."}

# Background Task: Periodically update prices
async def periodic_price_fetch():
    while True:
        await update_prices()
        await asyncio.sleep(300)  # Update every 5 minutes

@app.on_event("startup")
async def startup_event():
    create_database()
    asyncio.create_task(periodic_price_fetch())

# Generate Price Chart for a Specific Coin
@app.get("/chart-image/{coin_symbol}")
async def get_price_chart(coin_symbol: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price, timestamp FROM prices WHERE symbol = %s ORDER BY timestamp DESC", (coin_symbol,))
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    if not data:
        return Response(content="No data available", media_type="text/plain", status_code=404)

    prices = [row[0] for row in data]
    timestamps = [row[1] for row in data]
    
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

# Send Price Chart via Email
from email_system.email_sender import generate_and_send_email

@app.get("/send-email")
async def send_price_chart_email():
    return generate_and_send_email()
