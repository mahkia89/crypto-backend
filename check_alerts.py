import requests

BACKEND_URL = "https://crypto-backend-3gse.onrender.com"

def trigger_price_check():
    """Call the backend to check price drops and send alerts."""
    response = requests.get(f"{BACKEND_URL}/check-price-drops")
    
    if response.status_code == 200:
        print("✅ Price check completed:", response.json())
    else:
        print("❌ Error checking prices:", response.text)

if __name__ == "__main__":
    trigger_price_check()
