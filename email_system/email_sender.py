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
