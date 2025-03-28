import os
import asyncpg
import asyncio

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
        INSERT INTO prices (symbol, price, source)
        VALUES ($1, $2, $3)
    """, symbol, price, source)
    await conn.close()

async def get_stored_prices():
    """Fetch the latest stored price for each cryptocurrency from each source."""
    conn = await get_db_connection()
    rows = await conn.fetch("""
        SELECT symbol, price, source, timestamp FROM prices
        WHERE (symbol, source, timestamp) IN (
            SELECT symbol, source, MAX(timestamp) 
            FROM prices 
            GROUP BY symbol, source
        )
        ORDER BY timestamp DESC
    """)
    await conn.close()

    structured_data = {}
    for row in rows:
        coin_symbol = row["symbol"].split('-')[-1].upper()
        if coin_symbol not in structured_data:
            structured_data[coin_symbol] = []
        structured_data[coin_symbol].append({
            "price": row["price"],
            "source": row["source"],
            "timestamp": row["timestamp"]
        })

    return structured_data
