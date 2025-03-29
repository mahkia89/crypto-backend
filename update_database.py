import asyncio
from main import fetch_prices  # استفاده از همان فانکشنی که قیمت‌ها را آپدیت می‌کند

async def main():
    print("🔄 Fetching latest cryptocurrency prices...")
    await fetch_prices()
    print("✅ Prices updated successfully.")

if __name__ == "__main__":
    asyncio.run(main())
