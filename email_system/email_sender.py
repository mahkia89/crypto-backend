import os
import psycopg2
import smtplib
import matplotlib.pyplot as plt
import io
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import random

# connect to db
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://crypto_db_b52e_user:mTcqgolkW8xSYVgngMhpp4eHKZeOJx8v@dpg-cvfqephopnds73bcc2a0-a/crypto_db_b52e")


def fetch_crypto_data():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    query = """
        SELECT currency, source, timestamp, price
        FROM crypto_prices
        WHERE timestamp >= NOW() - INTERVAL '24 HOURS'
        ORDER BY currency, source, timestamp;
    """
    cur.execute(query)
    data = cur.fetchall()
    conn.close()
    return data


def generate_chart(data):
    crypto_dict = {}
    
    for currency, source, timestamp, price in data:
        if currency not in crypto_dict:
            crypto_dict[currency] = {}
        if source not in crypto_dict[currency]:
            crypto_dict[currency][source] = {'timestamps': [], 'prices': []}
        
        crypto_dict[currency][source]['timestamps'].append(timestamp)
        crypto_dict[currency][source]['prices'].append(price)

    images = {}
    for currency, sources in crypto_dict.items():
        plt.figure(figsize=(8, 5))
        for source, values in sources.items():
            color = (random.random(), random.random(), random.random())  
            plt.plot(values['timestamps'], values['prices'], label=source, color=color)
        
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.title(f'Price Trend of {currency}')
        plt.legend()
        plt.xticks(rotation=45)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        images[currency] = base64.b64encode(buf.getvalue()).decode('utf-8')

    return images


def send_email(images):
    sender_email = os.getenv("EMAIL_USER")
    receiver_email = os.getenv("EMAIL_RECIEVER")
    password = os.getenv("EMAIL_PASS")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = "Daily Crypto Price Charts"

    body = "Here are the latest 24-hour price trends for cryptocurrencies.\n\n"
    msg.attach(MIMEText(body, "plain"))

    for currency, img_data in images.items():
        img_bytes = base64.b64decode(img_data)
        img_part = MIMEImage(img_bytes, name=f"{currency}.png")
        msg.attach(img_part)

    with smtplib.SMTP_SSL("smtp.example.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())


crypto_data = fetch_crypto_data()
charts = generate_chart(crypto_data)
send_email(charts)
