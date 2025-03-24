from fastapi import FastAPI, Response
import httpx
import asyncio
import psycopg2
import matplotlib.pyplot as plt
import io
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# List of coins for both APIs
COINS = [
    ("btc-bitcoin", "bitcoin"),    # BTC
    ("eth-ethereum", "ethereum"),  # ETH
    ("doge-dogecoin", "dogecoin")  # DOGE
]

# Database connection setup
import asyncpg
from sqlalchemy import create_engine, MetaData, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "postgresql://postgres:HCDHjPQEaCieSfpisFOFBFLBortODAMi@postgres.railway.internal:5432/railway"

# Database connection setup
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

# 📌 Database table definition
class Price(Base):
    __tablename__ = 'prices'
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    price = Column(Float)
    source = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

async def get_price_coinpaprika(coin_id):
    """ Get price from CoinPaprika with extended timeout """
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return {"source": "CoinPaprika", "coin": coin_id, "price": data['quotes']['USD']['price']}
        except httpx.ReadTimeout:
            print(f"⚠️ Timeout error: CoinPaprika for {coin_id}")
            return {"source": "CoinPaprika", "coin": coin_id, "price": None}
    
    return {"source": "CoinPaprika", "coin": coin_id, "price": None}


async def get_price_coingecko(coin_id):
    """ Get price from CoinGecko """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return {"source": "CoinGecko", "coin": coin_id, "price": data[coin_id]['usd']}
    return {"source": "CoinGecko", "coin": coin_id, "price": None}

async def get_price_bitfinex(coin_id):
    """ Get price from Bitfinex """
    symbol_map = {
        "bitcoin": "tBTCUSD",
        "ethereum": "tETHUSD",
        "dogecoin": "tDOGEUSD"
    }
    
    if coin_id not in symbol_map:
        return {"source": "Bitfinex", "coin": coin_id, "price": None}

    url = f"https://api-pub.bitfinex.com/v2/ticker/{symbol_map[coin_id]}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return {"source": "Bitfinex", "coin": coin_id, "price": data[6]}  # Price at index 6
    
    return {"source": "Bitfinex", "coin": coin_id, "price": None}


async def get_price_kucoin(coin_id):
    """ Get price from KuCoin """
    symbol_map = {
        "bitcoin": "BTC-USDT",
        "ethereum": "ETH-USDT",
        "dogecoin": "DOGE-USDT"
    }
    
    if coin_id not in symbol_map:
        return {"source": "KuCoin", "coin": coin_id, "price": None}

    url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol_map[coin_id]}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return {"source": "KuCoin", "coin": coin_id, "price": data['data']['price']}
    
    return {"source": "KuCoin", "coin": coin_id, "price": None}

API_MAP = {
    "CoinPaprika": {"btc-bitcoin": "BTC", "eth-ethereum": "ETH", "doge-dogecoin": "DOGE"},
    "CoinGecko": {"bitcoin": "BTC", "ethereum": "ETH", "dogecoin": "DOGE"},
    "Bitfinex": {"bitcoin": "BTC", "ethereum": "ETH", "dogecoin": "DOGE"},
    "KuCoin": {"bitcoin": "BTC", "ethereum": "ETH", "dogecoin": "DOGE"}
}

async def fetch_prices():
    tasks = []
    for paprika_id, gecko_id in COINS:
        tasks.append(get_price_coinpaprika(paprika_id))
        tasks.append(get_price_coingecko(gecko_id))
        tasks.append(get_price_kucoin(gecko_id))
        tasks.append(get_price_bitfinex(gecko_id))

    results = await asyncio.gather(*tasks)

    db = SessionLocal()

    for result in results:
        if result["price"] is not None:
            price = Price(symbol=API_MAP[result["source"]].get(result["coin"], result["coin"]),
                          price=result["price"], source=result["source"])
            db.add(price)

    db.commit()
    db.close()

    print("✅ Prices updated in PostgreSQL database with normalized symbols.")

# Execution function
if __name__ == "__main__":
    asyncio.run(fetch_prices())

@app.get("/prices")
async def get_prices():
    """ Manually fetch new prices from API """
    await fetch_prices()
    print("🔄 Prices updated manually.")
    return {"status": "success", "message": "Prices updated and stored in database."}

# 📌 Function that runs automatically every 5 minutes
async def periodic_price_fetch():
    while True:
        await fetch_prices()
        await asyncio.sleep(300)  # 300 seconds = 5 minutes

@app.on_event("startup")
async def startup_event():
    """ Run background task on server start """
    asyncio.create_task(periodic_price_fetch())  # Run the scheduled task

@app.get("/stored-prices")
async def get_stored_prices_api():
    """ API to get latest stored prices from the database """
    db = SessionLocal()
    prices = db.query(Price).order_by(Price.timestamp.desc()).limit(50).all()
    db.close()
    print("📈 Fetched stored prices.")
    return {"status": "success", "data": prices}

@app.get("/all-prices")
async def get_all_prices_api():
    """ API to get all stored prices from the database """
    db = SessionLocal()
    prices = db.query(Price).all()
    db.close()
    print("📈 Fetched all stored prices.")
    return {"status": "success", "data": prices}

@app.get("/chart-data")
async def get_chart_data():
    """ Return chart data in JSON format """
    db = SessionLocal()
    prices = db.query(Price).order_by(Price.timestamp.desc()).limit(50).all()
    db.close()

    if not prices:
        print("❌ No data found in database!")
        return {"status": "error", "message": "No data available."}

    print("✅ Data fetched from DB:", prices)

    return {"status": "success", "data": prices}

@app.get("/chart-image/{coin_symbol}")
async def get_price_chart(coin_symbol: str):
    print(f"📊 Generating chart for {coin_symbol}")

    # Connect to the database
    db = SessionLocal()

    # Get data for the specified coin
    prices = db.query(Price).filter(Price.symbol == coin_symbol).order_by(Price.timestamp.desc()).all()
    db.close()

    if not prices:
        return Response(content="No data available", media_type="text/plain", status_code=404)

    # Organize data
    price_data = [p.price for p in prices]
    timestamps = [p.timestamp for p in prices]

    # Generate chart
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(timestamps, price_data, marker="o", linestyle="-", label=coin_symbol)
    ax.set_title(f"{coin_symbol} Price Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price (USD)")
    ax.legend()
    ax.grid(True)
    ax.tick_params(axis='x', rotation=45)

    # Save chart in memory
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    plt.close()

    return Response(content=img_buf.getvalue(), media_type="image/png")

from email_system.email_sender import generate_and_send_email

@app.get("/send-email")
async def send_price_chart_email():
    """ API to send price chart via email """
    return generate_and_send_email()
