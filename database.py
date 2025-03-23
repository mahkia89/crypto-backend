import sqlite3
import aiosqlite

DATABASE_NAME = "crypto_prices.db"

import os
print(os.path.abspath("crypto_prices.db"))

async def create_database():
    """ Create database and prices table if they don't exist. """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                source TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def save_price(symbol, price, source):
    """ Save fetched price data into the database. """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("""
            INSERT INTO prices (symbol, price, source)
            VALUES (?, ?, ?)
        """, (symbol, price, source))
        await db.commit()


async def get_stored_prices():
    """ دریافت قیمت‌های ذخیره‌شده و مرتب‌سازی آنها """
    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()

    # گرفتن آخرین قیمت هر ارز از هر منبع
    cursor.execute("""
        SELECT symbol, price, source, timestamp 
        FROM prices 
        WHERE (symbol, timestamp) IN 
        (SELECT symbol, MAX(timestamp) FROM prices GROUP BY symbol, source)
        ORDER BY timestamp DESC
    """)
    
    prices = cursor.fetchall()
    conn.close()

    # سازماندهی داده‌ها به‌صورت گروه‌بندی‌شده
    structured_data = {}
    for row in prices:
        coin_symbol = row[0].split('-')[-1].upper()  # استاندارد کردن نام ارز (BTC, ETH, DOGE)
        if coin_symbol not in structured_data:
            structured_data[coin_symbol] = []
        structured_data[coin_symbol].append({"price": row[1], "source": row[2], "timestamp": row[3]})
    
    print(structured_data)

    return structured_data

async def get_all_stored_prices():
    """ دریافت تمامی داده‌های ذخیره‌شده از دیتابیس """
    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()

    # دریافت همه داده‌های ذخیره‌شده
    cursor.execute("SELECT symbol, price, source, timestamp FROM prices ORDER BY timestamp DESC")
    prices = cursor.fetchall()
    conn.close()

    # سازماندهی داده‌ها
    structured_data = {}
    for row in prices:
        coin_symbol = row[0].split('-')[-1].upper()
        if coin_symbol not in structured_data:
            structured_data[coin_symbol] = []
        structured_data[coin_symbol].append({"price": row[1], "source": row[2], "timestamp": row[3]})

    return structured_data

# Connect to database
conn = sqlite3.connect("crypto_prices.db")
cursor = conn.cursor()

# Create table to store prices
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
