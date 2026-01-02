import uuid
import os
import random
import time
from datetime import datetime, timezone, timedelta

import requests

INGESTION_BASE_URL = os.getenv(
    "INGESTION_BASE_URL",
    "http://localhost:8081"   # host-safe default
)

ORDERS_ENDPOINT = f"{INGESTION_BASE_URL}/v1/orders"
HEALTH_ENDPOINT = f"{INGESTION_BASE_URL}/actuator/health"

# Merchant → Products mapping (matches seed data in db/02_seed.sql)
MERCHANT_PRODUCTS = {
    # Merchant 1: TechMart USA - 8 categories, 24 products
    1: [
        101, 102, 103, 104,  # Electronics
        111, 112, 113,       # Books
        121, 122, 123,       # Clothing
        131, 132, 133,       # Home & Garden
        141, 142, 143,       # Sports & Outdoors
        151, 152, 153,       # Toys & Games
        161, 162, 163,       # Health & Beauty
        171, 172, 173,       # Automotive
    ],
    # Merchant 2: EuroStyle - 5 categories, 15 products (luxury European)
    2: [
        201, 202, 203,       # Fashion
        211, 212, 213,       # Accessories
        221, 222, 223,       # Footwear
        231, 232, 233,       # Jewelry
        241, 242, 243,       # Watches
    ],
    # Merchant 3: BharatBazaar - 5 categories, 15 products (Indian marketplace)
    3: [
        301, 302, 303,       # Kitchen Appliances
        311, 312, 313,       # Home Decor
        321, 322, 323,       # Traditional Wear
        331, 332, 333,       # Ayurveda & Wellness
        341, 342, 343,       # Handicrafts
    ],
}



def random_order(order_date=None):
    merchant_id = random.choice(list(MERCHANT_PRODUCTS.keys()))
    product_ids = MERCHANT_PRODUCTS[merchant_id]

    if order_date is None:
        order_date = datetime.now(timezone.utc)
    
    order_date = order_date.isoformat()

    num_items = random.randint(1, min(4, len(product_ids)))
    items = []

    for _ in range(num_items):
        product_id = random.choice(product_ids)
        quantity = random.randint(1, 5)
        unit_price = round(random.uniform(10.0, 200.0), 2)

        items.append({
            "productId": product_id,
            "quantity": quantity,
            "unitPrice": unit_price,
        })

    return {
        "externalOrderId": str(uuid.uuid4()), # Add a unique UUID for each order
        "merchantId": merchant_id,
        "orderDate": order_date,
        "items": items,
    }


def wait_for_ingestion(timeout_seconds: int = 60):
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            resp = requests.get(HEALTH_ENDPOINT, timeout=3)
            if resp.status_code == 200:
                print("ingestion-service is up")
                return
        except Exception:
            pass

        print("Waiting for ingestion-service...")
        time.sleep(3)

    raise RuntimeError("ingestion-service not ready after timeout")


def send_orders(count: int = 20, delay_seconds: float = 1.0):
    for i in range(count):
        payload = random_order()
        try:
            resp = requests.post(ORDERS_ENDPOINT, json=payload, timeout=5)
            print(f"[{i+1}/{count}] {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[{i+1}/{count}] ERROR: {e}")

        time.sleep(delay_seconds)


def send_orders_continuously(delay_seconds: float = 1.0):
    i = 0
    while True:
        i += 1
        payload = random_order()
        try:
            resp = requests.post(ORDERS_ENDPOINT, json=payload, timeout=5)
            print(f"[continuous #{i}] {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[continuous #{i}] ERROR: {e}")
        time.sleep(delay_seconds)


def send_orders_for_past_days(days: int, max_orders_per_day: int):
    today = datetime.now(timezone.utc)
    for day in range(days, 0, -1):
        target_date = today - timedelta(days=day)
        num_orders = random.randint(1, max_orders_per_day)
        print(f"--- Sending {num_orders} orders for {target_date.date()} ---")
        for i in range(num_orders):
            # jitter the timestamp to make it more realistic
            jitter = timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            payload = random_order(order_date=target_date.replace(hour=0, minute=0, second=0, microsecond=0) + jitter)
            try:
                resp = requests.post(ORDERS_ENDPOINT, json=payload, timeout=5)
                print(f"[{i + 1}/{num_orders}] {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"[{i + 1}/{num_orders}] ERROR: {e}")
            time.sleep(0.1)


if __name__ == "__main__":
    backfill_days = int(os.getenv("BACKFILL_DAYS", "90"))
    max_orders_per_day = int(os.getenv("MAX_ORDERS_PER_DAY", "50"))
    
    wait_for_ingestion()

    if backfill_days > 0:
        print(f"Starting backfill for the last {backfill_days} days...")
        send_orders_for_past_days(days=backfill_days, max_orders_per_day=max_orders_per_day)

    count = int(os.getenv("ORDER_COUNT", "20"))
    delay = float(os.getenv("ORDER_DELAY_SECONDS", "1.0"))
    continuous = os.getenv("ORDER_CONTINUOUS", "false").lower() in {"true", "1", "yes"}

    if continuous:
        print("Starting continuous order generation mode...")
        send_orders_continuously(delay_seconds=delay)
    else:
        print(f"Starting generating {count} orders...")
        send_orders(count=count, delay_seconds=delay)
        
