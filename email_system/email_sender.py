from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os


app = FastAPI()

# ایمیل و پسورد سرور SMTP
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# مدل درخواست
class EmailRequest(BaseModel):
    email: str
    symbol: str

@app.post("/send-email")
async def send_email(request: EmailRequest):
    email = request.email
    symbol = request.symbol

    # ایجاد لینک نمودار برای ایمیل
    chart_url = f"https://crypto-backend-3gse.onrender.com/chart-image/{symbol}"

    # متن ایمیل
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
