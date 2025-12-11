import os
import random
from datetime import datetime, timezone

import requests

INGESTION_BASE_URL = os.getenv("INGESTION_BASE_URL", "http://ingestion-service:8081")
ORDERS_ENDPOINT = f"{INGESTION_BASE_URL}/v1/orders"

MERCHANT_IDS = [1, 2, 3]
PRODUCT_IDS = [101, 102, 103, 104, 105]
CURRENCIES = ["USD", "EUR", "INR"]


def random_order():
    merchant_id = random.choice(MERCHANT_IDS)
    order_date = datetime.now(timezone.utc).isoformat()
    currency = random.choice(CURRENCIES)

    num_items = random.randint(1, 4)
    items = []
    for _ in range(num_items):
        product_id = random.choice(PRODUCT_IDS)
        quantity = random.randint(1, 5)
        unit_price = round(random.uniform(10.0, 200.0), 2)
        items.append(
            {
                "productId": product_id,
                "quantity": quantity,
                "unitPrice": unit_price,
            }
        )

    return {
        "merchantId": merchant_id,
        "orderDate": order_date,
        "currency": currency,
        "items": items,
    }

HEALTH_ENDPOINT = f"{INGESTION_BASE_URL}/actuator/health"

def wait_for_ingestion(timeout_seconds: int = 60):
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            resp = requests.get(HEALTH_ENDPOINT, timeout=3)
            if resp.status_code == 200:
                print("Ingestion-service is up")
                return
        except Exception:
            pass
        print("Waiting for ingestion-service...")
        time.sleep(3)
    raise RuntimeError("Ingestion-service not ready after timeout")

def send_orders(count: int = 20):
    for i in range(count):
        payload = random_order()
        try:
            resp = requests.post(ORDERS_ENDPOINT, json=payload, timeout=5)
            print(f"[{i+1}/{count}] status={resp.status_code} body={resp.text}")
        except Exception as e:
            print(f"[{i+1}/{count}] ERROR: {e}")


if __name__ == "__main__":
    count = int(os.getenv("ORDER_COUNT", "20"))
    wait_for_ingestion()
    send_orders(count=count)
