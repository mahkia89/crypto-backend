from fastapi import FastAPI
import asyncio
import httpx
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from database import save_price, create_database, get_chart_prices, get_stored_prices
import matplotlib.pyplot as plt
import io
from fastapi.responses import Response
from pydantic import BaseModel
from config import COINS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COIN_SYMBOLS = {
    "btc": "BTC",
    "bitcoin": "BTC",
    "BITCOIN": "BTC",
    "btc-bitcoin": "BTC",
    "eth": "ETH",
    "ethereum": "ETH",
    "ETHEREUM": "ETH",
    "eth-ethereum": "ETH",
    "doge": "DOGE",
    "dogecoin": "DOGE",
    "DOGECOIN": "DOGE",
    "doge-dogecoin": "DOGE",
}

import httpx

async def fetch_price_from_api(url, source, coin_id, expected_structure="dict", price_path=None):
    """Generic function to fetch cryptocurrency prices from an API."""
    
    standardized_coin_id = COIN_SYMBOLS.get(coin_id.upper(), coin_id.upper())

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url)
            print(f"Raw response from {source}: {response.text}")  # Log full response
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Parsed data from {source} for {coin_id}: {data}")  # Log parsed data
                    
                    if expected_structure == "dict" and isinstance(data, dict):
                        # Navigate through the nested dictionary using price_path
                        price = data
                        for key in price_path:
                            if key not in price:
                                print(f"⚠️ Missing key '{key}' in path at {source} for {coin_id}")
                                return None
                            price = price[key]
                        if isinstance(price, str) and price.replace('.', '', 1).isdigit():
                            price = float(price)  # تبدیل رشته به عدد اعشاری
                        elif not isinstance(price, (int, float)):
                            print(f"⚠️ Unexpected price format from {source} for {coin_id}: {price}")
                            return None

                        return {"source": source, "coin": standardized_coin_id, "price": price}

                    elif expected_structure == "list" and isinstance(data, list) and len(data) > 6:
                        return {"source": source, "coin": standardized_coin_id, "price": data[6]}

                    print(f"⚠️ Invalid or missing data in response from {source} for {coin_id}")
                except ValueError:
                    print(f"⚠️ Failed to parse JSON from {source} for {coin_id}")
            else:
                print(f"⚠️ Error from {source} for {coin_id}: {response.status_code}")
        except httpx.ReadTimeout:
            print(f"⚠️ Timeout error: {source} for {coin_id}")
    
    return {"source": source, "coin": standardized_coin_id, "price": None}


async def get_price_coinpaprika(coin_id):
    """Get price from CoinPaprika"""
    
    standardized_coin = COIN_SYMBOLS.get(coin_id.lower())  # Convert to standard symbol
    
    if not standardized_coin:
        return None  # Skip if the coin is not in our mapping
    
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
    return await fetch_price_from_api(url, "CoinPaprika", standardized_coin, expected_structure="dict", price_path=["quotes", "USD", "price"])


async def get_price_coingecko(coin_id):
    """Get price from CoinGecko"""
    print(f"Checking bitfinex price for: {coin_id}")
    standardized_coin = COIN_SYMBOLS.get(coin_id.lower())

    if not standardized_coin:
        return None
        
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id.lower()}&vs_currencies=usd"
    return await fetch_price_from_api(url, "CoinGecko", standardized_coin, expected_structure="dict", price_path=[coin_id, "usd"])

async def get_price_bitfinex(coin_id):
    """Get price from Bitfinex"""
    print(f"Checking bitfinex price for: {coin_id}") 
    
    symbol_map = {
        "bitcoin": "tBTCUSD",
        "ethereum": "tETHUSD",
        "ETH": "tETHUSD",
        "BTC": "tBTCUSD"
    }
    if coin_id not in symbol_map:
        return None
    
    url = f"https://api-pub.bitfinex.com/v2/ticker/{symbol_map[coin_id]}"
    return await fetch_price_from_api(url, "Bitfinex", coin_id, expected_structure="list")

async def get_price_kucoin(coin_id):
    """Get price from KuCoin"""
    print(f"Checking KuCoin price for: {coin_id}") 
    
    symbol_map = {
        "bitcoin": "BTC-USDT",
        "ethereum": "ETH-USDT",
        "dogecoin": "DOGE-USDT",
        "BTC": "BTC-USDT",
        "ETH": "ETH-USDT",
        "DOGE": "DOGE-USDT"
    }

    if coin_id not in symbol_map:
        return None

    url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol_map[coin_id]}"
    return await fetch_price_from_api(url, "KuCoin", coin_id, expected_structure="dict", price_path=["data", "price"])

async def fetch_prices():
    print("🔄 Fetching latest cryptocurrency prices...", flush=True)
    
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

@app.get("/")
async def read_root():
    return {"message": "Hey, Crypto!"}

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
    prices = await get_stored_prices()
    return {"status": "success", "data": prices}


@app.get("/chart-data/{coin_symbol}")
async def get_chart_data(coin_symbol: str):
    """Return chart data for a specific coin in JSON format."""
    prices = await get_chart_prices(coin_symbol)

    if not prices:
        return {"status": "error", "message": "No data available."}

    # Check the format of 'prices' and extract the correct data
    # Assuming 'prices' is a dictionary where each key contains a list of prices for a specific source
    data = []
    for source, price_data in prices.items():
        for p in price_data:
            # Extract timestamp and price
            if isinstance(p, dict) and 'timestamp' in p and 'price' in p:
                data.append({"timestamp": p['timestamp'], "price": p['price']})

    if not data:
        return {"status": "error", "message": "No valid price data found."}

    return {"status": "success", "data": data}


import matplotlib.pyplot as plt
import io
from fastapi import FastAPI, Response


@app.get("/chart-image/{coin_symbol}")
async def get_price_chart(coin_symbol: str):
    """Generate and return a price chart with different sources as different lines."""

    prices = await get_chart_prices(coin_symbol)  # Get price data from different sources

    if not prices:
        return Response(content="No data available", media_type="text/plain", status_code=404)

    # Define color mapping for different sources
    source_colors = {
        "CoinPaprika": "blue",
        "CoinGecko": "green",
        "KuCoin": "red",
        "Bitfinex": "orange",
    }

    fig, ax = plt.subplots(figsize=(10, 5))

    for source, data in prices.items():
        if not data:  # Skip empty data
            continue

        timestamps = [p["timestamp"] for p in data]  # Extract timestamps
        price_data = [p["price"] for p in data]      # Extract price values

        # Sort data by timestamp (if necessary)
        sorted_data = sorted(zip(timestamps, price_data), key=lambda x: x[0])
        timestamps, price_data = zip(*sorted_data)

        # Choose color or default to black if not in mapping
        color = source_colors.get(source, "black")

        ax.plot(timestamps, price_data, marker="o", linestyle="-", label=source, color=color)

    # Set chart labels and title
    ax.set_title(f"{coin_symbol.upper()} Price Trend from Different Sources")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price (USD)")
    ax.legend()
    ax.grid(True)
    ax.tick_params(axis="x", rotation=45)

    # Save chart in memory
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    plt.close()

    return Response(content=img_buf.getvalue(), media_type="image/png")

class EmailRequest(BaseModel):
    email: str
    symbol: str

@app.post("/send-email")
async def email_sender_api(request: EmailRequest):
    response = await email_sender(request) 
    
    if response["status"] == "success":
        return response
    else:
        raise HTTPException(status_code=500, detail=response["message"])
