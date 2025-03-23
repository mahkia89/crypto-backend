from fastapi import FastAPI, Response
import httpx
import asyncio
import sqlite3
import matplotlib.pyplot as plt
import io
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # برای تست، همه درخواست‌ها را قبول می‌کند
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# لیست کوین‌ها برای هر دو API
COINS = [
    ("btc-bitcoin", "bitcoin"),    # BTC
    ("eth-ethereum", "ethereum"),  # ETH
    ("doge-dogecoin", "dogecoin")  # DOGE
]

# 📌 ساخت دیتابیس (اگر وجود نداشته باشد)
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

async def get_price_coinpaprika(coin_id):
    """ دریافت قیمت از CoinPaprika با تایم‌اوت بیشتر """
    url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
    
    async with httpx.AsyncClient(timeout=15.0) as client:  # افزایش timeout به 15 ثانیه
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return {"source": "CoinPaprika", "coin": coin_id, "price": data['quotes']['USD']['price']}
        except httpx.ReadTimeout:
            print(f"⚠️ Timeout error: CoinPaprika برای {coin_id}")
            return {"source": "CoinPaprika", "coin": coin_id, "price": None}
    
    return {"source": "CoinPaprika", "coin": coin_id, "price": None}


async def get_price_coingecko(coin_id):
    """ دریافت قیمت از CoinGecko """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return {"source": "CoinGecko", "coin": coin_id, "price": data[coin_id]['usd']}
    return {"source": "CoinGecko", "coin": coin_id, "price": None}

async def get_price_bitfinex(coin_id):
    """ دریافت قیمت از Bitfinex """
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
            return {"source": "Bitfinex", "coin": coin_id, "price": data[6]}  # قیمت در index 6
    
    return {"source": "Bitfinex", "coin": coin_id, "price": None}


async def get_price_kucoin(coin_id):
    """ دریافت قیمت از KuCoin """
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

    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()

    cursor.executemany("INSERT INTO prices (symbol, price, source) VALUES (?, ?, ?)", [
        (API_MAP[result["source"]].get(result["coin"], result["coin"]), result["price"], result["source"])
        for result in results if result["price"] is not None
    ])

    conn.commit()
    conn.close()
    print("✅ Prices updated in database with normalized symbols.")

# اجرای تابع
if __name__ == "__main__":
    asyncio.run(fetch_prices())

@app.get("/prices")
async def get_prices():
    """ دریافت قیمت‌های جدید به صورت دستی از طریق API """
    await fetch_prices()
    print("🔄 Prices updated manually.")
    return {"status": "success", "message": "Prices updated and stored in database."}

# 📌 تابعی که به صورت خودکار هر 5 دقیقه اجرا می‌شود
async def periodic_price_fetch():
    while True:
        await fetch_prices()
        await asyncio.sleep(20)  # 300 ثانیه = 5 دقیقه

@app.on_event("startup")
async def startup_event():
    """ اجرا شدن وظیفه‌ی بک‌گراند هنگام استارت سرور """
    create_database()  # اول دیتابیس رو میسازیم
    asyncio.create_task(periodic_price_fetch())  # اجرای تسک زمان‌بندی‌شده

# 📌 اضافه کردن API برای دریافت قیمت‌های ذخیره‌شده
from database import get_stored_prices  # تابعی برای گرفتن قیمت‌های ذخیره‌شده
from database import get_all_stored_prices  # تابعی برای گرفتن تمامی قیمت‌های ذخیره‌شده

@app.get("/stored-prices")
async def get_stored_prices_api():
    """ API برای دریافت آخرین قیمت‌های ذخیره‌شده در دیتابیس، به‌صورت منظم """
    prices = await get_stored_prices()
    print("📈 Fetched stored prices.")
    return {"status": "success", "data": prices}

@app.get("/all-prices")
async def get_all_prices_api():
    """ API برای دریافت تمامی قیمت‌های ذخیره‌شده در دیتابیس """
    prices = await get_all_stored_prices()
    print("📈 Fetched all stored prices.")
    return {"status": "success", "data": prices}

@app.get("/chart-data")
async def get_chart_data():
    """ برگرداندن داده‌های چارت به‌صورت JSON """
    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT symbol, price, source, timestamp FROM prices ORDER BY timestamp DESC LIMIT 50")
    data = cursor.fetchall()

    conn.close()

    if not data:
        print("❌ No data found in database!")  # لاگ برای چک کردن دیتابیس
        return {"status": "error", "message": "No data available."}

    print("✅ Data fetched from DB:", data)  # نمایش دیتای دریافتی

    return {"status": "success", "data": data}
@app.get("/chart-image/{coin_symbol}")
async def get_price_chart(coin_symbol: str):
    print(f"📊 Generating chart for {coin_symbol}")

    # اتصال به پایگاه داده
    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()

    # دریافت داده‌های مربوط به کوین مشخص‌شده
    cursor.execute("SELECT price, source, timestamp FROM prices WHERE symbol = ? ORDER BY timestamp DESC", (coin_symbol,))
    data = cursor.fetchall()
    conn.close()

    if not data:
        return Response(content="No data available", media_type="text/plain", status_code=404)

    # سازماندهی داده‌ها
    prices = {}
    timestamps = {}
    sources = set()

    for price, source, timestamp in data:
        if source not in prices:
            prices[source] = []
            timestamps[source] = []
        prices[source].append(price)
        timestamps[source].append(datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))
        sources.add(source)

    # رسم نمودار
    fig, ax = plt.subplots(figsize=(10, 5))
    source_colors = {"CoinPaprika": "red", "CoinGecko": "blue", "Bitfinex": "green", "KuCoin": "purple"}

    for source in prices:
        ax.plot(timestamps[source], prices[source], marker="o", linestyle="-", label=source, color=source_colors.get(source, "black"))

    ax.set_title(f"{coin_symbol} Price Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price (USD)")
    ax.legend()
    ax.grid(True)
    ax.tick_params(axis='x', rotation=45)

    # ذخیره نمودار در حافظه
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    plt.close()

    return Response(content=img_buf.getvalue(), media_type="image/png")



from email_system.email_sender import send_email
from io import BytesIO
from fastapi import FastAPI
from email_system.email_sender import generate_and_send_email

@app.get("/send-email")
async def send_price_chart_email():
    """This API is for sending crypto prices"""
    return generate_and_send_email()


