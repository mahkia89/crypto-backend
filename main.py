from fastapi import FastAPI
import asyncio
import httpx
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from database import save_price, create_database, get_chart_prices, get_stored_prices

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
                try:
                    data = response.json()
                    if isinstance(data, dict) and "usd" in data:
                        print(f"Data from {source} for {coin_id}: {data}")  # Log the response
                        return {"source": source, "coin": coin_id, "price": data}
                    else:
                        print(f"⚠️ Invalid or missing data in response from {source} for {coin_id}")
                except ValueError:
                    print(f"⚠️ Failed to parse JSON from {source} for {coin_id}")
            else:
                print(f"⚠️ Error from {source} for {coin_id}: {response.status_code}")
        except httpx.ReadTimeout:
            print(f"⚠️ Timeout error: {source} for {coin_id}")
    return {"source": source, "coin": coin_id, "price": None}



async def get_price_coinpaprika(coin_id):
    """Get price from CoinPaprika"""
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
    result = await fetch_price_from_api(url, "CoinPaprika", coin_id)
    if result["price"] and isinstance(result["price"], dict):
        return {"source": "CoinPaprika", "coin": coin_id, "price": result["price"]['quotes']['USD']['price']}
    return None

async def get_price_coingecko(coin_id):
    """Get price from CoinGecko with retries"""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    retries = 5
    for _ in range(retries):
        result = await fetch_price_from_api(url, "CoinGecko", coin_id)
        if result["price"]:
            return {"source": "CoinGecko", "coin": coin_id, "price": result["price"][coin_id]["usd"]}
        else:
            print(f"⚠️ Failed to fetch data for {coin_id} from CoinGecko, retrying...")
            await asyncio.sleep(2)  # Sleep before retrying
    return None


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
    if result["price"] and isinstance(result["price"], list) and len(result["price"]) > 6:
        return {"source": "Bitfinex", "coin": coin_id, "price": result["price"][6]}
    else:
        print(f"⚠️ Data missing for {coin_id} from Bitfinex")
        return None


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

    return {
        "status": "success",
        "data": [{"timestamp": p.timestamp, "price": p.price} for p in prices],
    }

@app.get("/chart-image/{coin_symbol}")
async def get_price_chart(coin_symbol: str):
    """Generate and return a price chart as an image."""

    prices = await get_chart_prices(coin_symbol)

    if not prices:
        return Response(content="No data available", media_type="text/plain", status_code=404)

    timestamps = [p["timestamp"] for p in prices]  # Now it works
    price_data = [p.price for p in prices]

    # Generate chart
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(timestamps, price_data, marker="o", linestyle="-", label=coin_symbol.upper())
    ax.set_title(f"{coin_symbol.upper()} Price Trend")
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

from email_system.email_sender import generate_and_send_email

@app.get("/send-email")
async def send_price_chart_email():
    """ API to send price chart via email """
    return generate_and_send_email()
