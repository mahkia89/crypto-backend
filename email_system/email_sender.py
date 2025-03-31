from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


origins = [
    "http://localhost:3000",  # If front is running on local
    "https://crypto-frontend-lbkz.onrender.com/",  # If front is running on render
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # All methods of HTTP
    allow_headers=["*"],  # All headers
)

# Email and password set in secrets
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


class EmailRequest(BaseModel):
    email: str
    symbol: str

@app.post("/send-email")
async def send_email(request: EmailRequest):
    print("📩 Received email request:", request.dict())  # Log for requesting email
    email = request.email
    symbol = request.symbol

    # Plot for email
    chart_url = f"https://crypto-backend-3gse.onrender.com/chart-image/{symbol}"

    # email body
    email_body = f"""
    <h2>گزارش تغییرات قیمت {symbol}</h2>
    <p>این گزارش به‌صورت خودکار برای شما ارسال شده است.</p>
    <img src="{chart_url}" alt="Crypto Chart" width="500"/>
    <p>با احترام، تیم کریپتو داشبورد</p>
    """

    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = email
    msg["Subject"] = f"📊 Changing Price {symbol}"
    msg.attach(MIMEText(email_body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, email, msg.as_string())
        server.quit()
        return {"status": "success", "message": "email has been sent!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def check_price_drops():
    """Check price drops and send alerts to users."""
    global user_settings

    for email, settings in user_settings.items():
        threshold = settings["price_drop_threshold"]
        
        for coin, price_data in stored_prices.items():
            if len(price_data) < 2:
                continue  # Not enough data to compare
            
            latest_price = price_data[-1]["price"]
            one_hour_ago_price = price_data[0]["price"]

            drop_percentage = ((one_hour_ago_price - latest_price) / one_hour_ago_price) * 100
            
            if drop_percentage >= threshold:
                await send_email_alert(email, coin, drop_percentage, latest_price)

async def send_email_alert(email, coin, drop_percentage, latest_price):
    """Send email alert to user"""
    subject = f"⚠️ {coin} dropped {drop_percentage:.2f}%!"
    body = f"The price of {coin} has dropped {drop_percentage:.2f}% in the last hour. Current price: ${latest_price:.2f}."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "your-email@example.com"
    msg["To"] = email

    # Send email using SMTP
    with smtplib.SMTP("smtp.example.com", 587) as server:
        server.starttls()
        server.login("your-email@example.com", "your-password")
        server.sendmail("your-email@example.com", email, msg.as_string())

    print(f"Email alert sent to {email}")

