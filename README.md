# Crypto Price Tracker Backend

## 📌 Overview
This is the backend service for **Crypto Price Tracker**, a cryptocurrency monitoring platform that fetches, stores, and visualizes price data from multiple sources, including **CoinPaprika, CoinGecko, Bitfinex, and KuCoin**. The backend is built with **FastAPI** and uses a **PostgreSQL database (hosted on Render)** for storage.

## 🚀 Features
- Fetches real-time cryptocurrency prices from multiple APIs.
- Stores price data in a PostgreSQL database.
- Generates historical price charts.
- Sends email alerts when price thresholds are met.
- Supports user settings like price alerts and dark mode.
- Periodically updates prices every 5 minutes.

## 🏗 Tech Stack
- **FastAPI** (for API development)
- **PostgreSQL** (hosted on Render for data storage)
- **httpx** (for asynchronous HTTP requests)
- **Matplotlib** (for generating price charts)
- **GitHub Actions** (for automated price updates)

## 📂 Project Structure
```
backend/
│── database.py              # Database connection & queries
│── main.py                  # Main FastAPI application
│── update_database.py       # Script to fetch new prices via GitHub Actions
│── check_alerts.py          # Price drop alert checker
│── email_system/
│   ├── email_sender.py      # Email sending module
│── config.py                # Configuration & constants
│── requirements.txt         # Dependencies
│── README.md                # Project documentation
```

## 🛠 Setup & Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/crypto-price-tracker.git
cd crypto-price-tracker/backend
```

### 2️⃣ Create a Virtual Environment & Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3️⃣ Set Up PostgreSQL Database
Ensure you have a PostgreSQL database running. Update `database.py` with your database credentials.

### 4️⃣ Run the Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at: **http://localhost:8000**

---

## 📡 API Endpoints

### 🔹 Root Endpoint
```
GET /
Response: {"message": "Hey, Crypto!"}
```

### 🔹 Fetch Live Prices
```
GET /prices
Response: {"status": "success", "message": "Prices updated."}
```

### 🔹 Get Stored Prices
```
GET /stored-prices
Response: {"status": "success", "data": [...]}
```

### 🔹 Get Chart Data
```
GET /chart-data/{coin_symbol}
Response: {"status": "success", "data": [{"timestamp": ..., "price": ...}]}
```

### 🔹 Get Chart Image
```
GET /chart-image/{coin_symbol}
Response: PNG image
```

### 🔹 Save User Settings
```
POST /save-settings
Body: {"email": "user@example.com", "price_drop_threshold": 5, "dark_mode": true}
Response: {"status": "success", "message": "Settings saved!"}
```

### 🔹 Get User Settings
```
GET /get-settings/{email}
Response: {"status": "success", "data": {...}}
```

### 🔹 Send Price Alert Email
```
POST /send-email
Body: {"email": "user@example.com", "symbol": "BTC"}
Response: {"status": "success", "message": "Email sent!"}
```

---

## 🏗 Deployment
The backend is deployed on **Render**. To update the deployed version:
```bash
git add .
git commit -m "Update backend"
git push origin main
```
GitHub Actions will automatically trigger a price update.

---

## 📜 License
This project is licensed under the **MIT License**. Feel free to use and modify it.

---

## 🤝 Contributing
Pull requests are welcome! If you want to contribute:
1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Commit your changes (`git commit -m "Added feature X"`)
4. Push to the branch (`git push origin feature-branch`)
5. Create a pull request

---

## 📧 Contact
For any issues or feature requests, reach out via [mahkiagolbashi@gmail.com]
(mailto:mahkiagolbashi@gmail.com).

