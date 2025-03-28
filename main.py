from fastapi import FastAPI
import asyncio
import httpx
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from database import save_price, create_database

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COINS = [
    ("btc-bitcoin", "bitcoin"),
    ("eth-ethereum", "ethereum"),
    ("doge-dogecoin", "dogecoin")
]

async def fetch_price_from_api(url, source, coin_id):
    """Generic function to fetch cryptocurrency prices from an API."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return {"source": source, "coin": coin_id, "price": data}
        except httpx.ReadTimeout:
            print(f"⚠️ Timeout error: {source} for {coin_id}")
    return {"source": source, "coin": coin_id, "price": None}

async def get_price_coinpaprika(coin_id):
    """Get price from CoinPaprika"""
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
    result = await fetch_price_from_api(url, "CoinPaprika", coin_id)
    return {"source": "CoinPaprika", "coin": coin_id, "price": result["price"]['quotes']['USD']['price']} if result["price"] else None

async def get_price_coingecko(coin_id):
    """Get price from CoinGecko"""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    result = await fetch_price_from_api(url, "CoinGecko", coin_id)
    return {"source": "CoinGecko", "coin": coin_id, "price": result["price"][coin_id]['usd']} if result["price"] else None

async def get_price_bitfinex(coin_id):
    """Get price from Bitfinex"""
    symbol_map = {
        "bitcoin": "tBTCUSD",
        "ethereum": "tETHUSD",
        "dogecoin": "tDOGEUSD"
    }
    if coin_id not in symbol_map:
        return None
    url = f"https://api-pub.bitfinex.com/v2/ticker/{symbol_map[coin_id]}"
    result = await fetch_price_from_api(url, "Bitfinex", coin_id)
    return {"source": "Bitfinex", "coin": coin_id, "price": result["price"][6]} if result["price"] else None

async def get_price_kucoin(coin_id):
    """Get price from KuCoin"""
    symbol_map = {
        "bitcoin": "BTC-USDT",
        "ethereum": "ETH-USDT",
        "dogecoin": "DOGE-USDT"
    }
    if coin_id not in symbol_map:
        return None
    url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol_map[coin_id]}"
    result = await fetch_price_from_api(url, "KuCoin", coin_id)
    return {"source": "KuCoin", "coin": coin_id, "price": result["price"]['data']['price']} if result["price"] else None

async def fetch_prices():
    """Fetch prices from multiple APIs and save them in the database."""
    tasks = []
    for paprika_id, gecko_id in COINS:
        tasks.append(get_price_coinpaprika(paprika_id))
        tasks.append(get_price_coingecko(gecko_id))
        tasks.append(get_price_bitfinex(gecko_id))
        tasks.append(get_price_kucoin(gecko_id))

    results = await asyncio.gather(*tasks)

    for result in results:
        if result and result["price"]:
            await save_price(result["coin"].upper(), float(result["price"]), result["source"])

    print("✅ Prices updated in PostgreSQL.")

@app.get("/prices")
async def get_prices():
    """Fetch new prices from APIs manually"""
    await fetch_prices()
    return {"status": "success", "message": "Prices updated."}

async def periodic_price_fetch():
    """Fetch prices every 5 minutes."""
    while True:
        await fetch_prices()
        await asyncio.sleep(300)  # 5 minutes

@app.on_event("startup")
async def startup_event():
    """Run table creation and background tasks on startup."""
    await create_database()
    asyncio.create_task(periodic_price_fetch())


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
