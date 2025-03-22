import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import matplotlib.pyplot as plt
from datetime import datetime
import sqlite3
from dotenv import load_dotenv
import os

# بارگذاری تنظیمات از فایل .env
load_dotenv()

# اطلاعات ایمیل
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")

def create_chart(symbol, prices_by_source, timestamps_by_source):
    """ ایجاد نمودار قیمت برای هر ارز با چندین منبع """
    plt.figure(figsize=(12, 6))

    colors = ["blue", "red", "green", "orange", "purple"]
    for i, (source, prices) in enumerate(prices_by_source.items()):
        timestamps = timestamps_by_source[source]
        if prices and timestamps:
            plt.plot(timestamps, prices, marker="o", linestyle="-", label=source, color=colors[i % len(colors)])

    plt.xlabel("Time")
    plt.ylabel("Price (USD)")
    plt.title(f"{symbol} Price Trend")
    plt.legend(title="Source")
    plt.grid(True)
    plt.gcf().autofmt_xdate()  # تنظیم فرمت تاریخ

    img_buf = io.BytesIO()
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M")  # ساخت نام فایل بر اساس تاریخ
    filename = f"{symbol}_{timestamp_str}.png"
    plt.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)
    plt.close()
    
    return img_buf, filename  # برگرداندن نام فایل همراه با تصویر

def send_email(to_email, subject, message, chart_images):
    """ ارسال ایمیل با پیوست نمودارها """
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        # اضافه کردن نمودارها به ایمیل
        for img_buf, filename in chart_images:
            if img_buf is not None:
                img_buf.seek(0)
                image = MIMEImage(img_buf.read(), name=filename)
                msg.attach(image)

        # ارسال ایمیل
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        
        print("✅ ایمیل با موفقیت ارسال شد.")
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        print(f"❌ خطا در ارسال ایمیل: {e}")
        return {"status": "error", "message": str(e)}

def generate_and_send_email():
    """ این تابع برای تولید نمودارها و ارسال ایمیل است """
    conn = sqlite3.connect("crypto_prices.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT symbol, price, timestamp, source
        FROM prices 
        WHERE timestamp >= datetime('now', '-1 day') 
        ORDER BY symbol, source, timestamp ASC
    """)
    data = cursor.fetchall()
    conn.close()

    if not data:
        return {"status": "error", "message": "No data available."}

    # تقسیم داده‌ها بر اساس هر ارز و منبع
    prices_by_source = {"BTC": {}, "ETH": {}, "DOGE": {}}
    timestamps_by_source = {"BTC": {}, "ETH": {}, "DOGE": {}}

    for symbol, price, timestamp, source in data:
        if symbol in prices_by_source:
            if source not in prices_by_source[symbol]:
                prices_by_source[symbol][source] = []
                timestamps_by_source[symbol][source] = []
            prices_by_source[symbol][source].append(price)
            timestamps_by_source[symbol][source].append(datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))

    # ساخت نمودارها
    chart_images = []
    for symbol in ["BTC", "ETH", "DOGE"]:
        if prices_by_source[symbol]:  # فقط در صورتی که داده‌ای برای آن ارز وجود دارد
            chart, filename = create_chart(symbol, prices_by_source[symbol], timestamps_by_source[symbol])
            if chart:
                chart_images.append((chart, filename))

    # ارسال ایمیل
    recipient = "saragolbashi@gmail.com"
    subject = "Crypto Price Trend Charts"
    message = "سلام،\nدر این ایمیل نمودارهای روند قیمت ارزهای دیجیتال برای شما ارسال شده است."

    return send_email(recipient, subject, message, chart_images)
