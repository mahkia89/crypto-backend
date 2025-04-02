import requests

BACKEND_URL = "https://crypto-backend-3gse.onrender.com"

def trigger_price_check():
    """Call the backend to check price drops and send alerts."""
    try:
        response = requests.get(f"{BACKEND_URL}/check-price-drops", timeout=30)
        response.raise_for_status()
        print("✅ Price check completed:", response.json())
    except requests.exceptions.RequestException as e:
        print("❌ Error checking prices:", str(e))

if __name__ == "__main__":
    trigger_price_check()
