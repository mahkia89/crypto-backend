import os
import asyncpg
import asyncio
from config import COINS
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Price  

# Database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://crypto_db_b52e_user:mTcqgolkW8xSYVgngMhpp4eHKZeOJx8v@dpg-cvfqephopnds73bcc2a0-a/crypto_db_b52e")

async def get_db_connection():
    """Establish a connection with the PostgreSQL database."""
    return await asyncpg.connect(DATABASE_URL)

async def create_database():
    """Ensure the `prices` table exists."""
    conn = await get_db_connection()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            source TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await conn.close()

async def save_price(symbol, price, source):
    """Save cryptocurrency price to PostgreSQL."""
    conn = await get_db_connection()
    await conn.execute("""
        INSERT INTO prices (symbol, price, source, timestamp)
        VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
    """, symbol, price, source)
    await conn.close()


async def get_last_price(coin_symbol: str, session: AsyncSession):
    """Retrieve the last known price of a given coin."""
    result = await session.execute(
        select(Price).where(Price.coin_symbol == coin_symbol).order_by(Price.timestamp.desc()).limit(1)
    )
    price_entry = result.scalars().first()
    return price_entry.price if price_entry else None

async def get_last_price_dict():
    """Retrieve the most recent price for all tracked cryptocurrencies."""
    conn = await get_db_connection()
    rows = await conn.fetch("""
        SELECT DISTINCT ON (symbol) symbol, price
        FROM prices
        WHERE symbol IN ('BTC', 'ETH', 'DOGE')
        ORDER BY symbol, timestamp DESC
    """)
    await conn.close()

    return {row["symbol"].upper(): row["price"] for row in rows}

async def get_stored_prices():
    """Fetch all stored price history for each cryptocurrency from each source."""
    conn = await get_db_connection()
    rows = await conn.fetch("""
        SELECT symbol, price, source, timestamp
        FROM prices
        WHERE symbol IN ('BTC', 'ETH', 'DOGE')
        ORDER BY timestamp DESC
    """)
    await conn.close()

    structured_data = {}
    for row in rows:
        coin_symbol = row["symbol"].upper()
        if coin_symbol not in structured_data:
            structured_data[coin_symbol] = []
        structured_data[coin_symbol].append({
            "price": row["price"],
            "source": row["source"],
            "timestamp": row["timestamp"]
        })

    return structured_data

async def get_chart_prices(coin_symbol):
    """Fetch all historical prices for a specific cryptocurrency, grouped by source."""
    conn = await get_db_connection()
    rows = await conn.fetch("""
        SELECT price, source, timestamp 
        FROM prices 
        WHERE symbol = UPPER($1)
        ORDER BY timestamp ASC
    """, coin_symbol.upper())

    await conn.close()

    structured_data = {}
    for row in rows:
        source = row["source"]
        if source not in structured_data:
            structured_data[source] = []  # Create a list for each source

        structured_data[source].append({
            "timestamp": row["timestamp"],
            "price": row["price"]
        })
    
    print(f"🔍 Fetching chart prices for: {coin_symbol}")
    print(f"🔍 get_chart_prices({coin_symbol}) fetched data: {structured_data}")

    return structured_data
