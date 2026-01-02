import os
import requests
from typing import List, Dict, Any


class AggregationServiceClient:
    """
    HTTP client for aggregation-service.
    Uses direct URL from environment variable AGGREGATION_SERVICE_URL.
    """

    def __init__(self):
        # Default to docker service name if not set
        self.base_url = os.getenv("AGGREGATION_SERVICE_URL", "http://aggregation-service:8082")

    def get_top_categories(
        self,
        merchant_id: int,
        bucket_type: str,
        bucket_start: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch top categories from aggregation-service.
        """
        url = f"{self.base_url}/api/top-categories"

        params = {
            "merchantId": merchant_id,
            "bucketType": bucket_type,
            "bucketStart": bucket_start,
            "limit": limit,
        }

        try:
            print(f"[forecasting] Calling aggregation-service: {url} {params}")
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"Aggregation-service returned HTTP {response.status_code}: {response.text}"
            ) from e

        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Failed to connect to aggregation-service at {url}"
            ) from e


# Instantiate lazily if needed
aggregation_service_client = AggregationServiceClient()
