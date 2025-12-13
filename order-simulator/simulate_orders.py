import os
import random
import time
from datetime import datetime, timezone

import requests

INGESTION_BASE_URL = os.getenv(
    "INGESTION_BASE_URL",
    "http://localhost:8081"   # host-safe default
)

ORDERS_ENDPOINT = f"{INGESTION_BASE_URL}/v1/orders"
HEALTH_ENDPOINT = f"{INGESTION_BASE_URL}/actuator/health"

# Merchant → Products mapping (matches seed data)
MERCHANT_PRODUCTS = {
    1: [101, 102, 103],
    2: [104],
    3: [105],
}

CURRENCIES = ["USD", "EUR", "INR"]


def random_order():
    merchant_id = random.choice(list(MERCHANT_PRODUCTS.keys()))
    product_ids = MERCHANT_PRODUCTS[merchant_id]

    order_date = datetime.now(timezone.utc).isoformat()
    currency = random.choice(CURRENCIES)

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
        "merchantId": merchant_id,
        "orderDate": order_date,
        "currency": currency,
        "items": items,
    }


def wait_for_ingestion(timeout_seconds: int = 60):
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            resp = requests.get(HEALTH_ENDPOINT, timeout=3)
            if resp.status_code == 200:
                print("✅ ingestion-service is up")
                return
        except Exception:
            pass

        print("⏳ Waiting for ingestion-service...")
        time.sleep(3)

    raise RuntimeError("❌ ingestion-service not ready after timeout")


def send_orders(count: int = 20, delay_seconds: float = 1.0):
    for i in range(count):
        payload = random_order()
        try:
            resp = requests.post(ORDERS_ENDPOINT, json=payload, timeout=5)
            print(f"[{i+1}/{count}] {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[{i+1}/{count}] ERROR: {e}")

        time.sleep(delay_seconds)


if __name__ == "__main__":
    count = int(os.getenv("ORDER_COUNT", "20"))
    delay = float(os.getenv("ORDER_DELAY_SECONDS", "1.0"))

    wait_for_ingestion()
    send_orders(count=count, delay_seconds=delay)
