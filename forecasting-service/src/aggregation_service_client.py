import os
import consul
import requests
from typing import List, Dict, Any


class AggregationServiceClient:
    """
    Optional HTTP client for aggregation-service.
    NOTE:
    Forecasting-service should prefer direct DB reads.
    This client is useful for:
      - future decoupling
      - demos
      - fallback paths
    """

    def __init__(self):
        consul_host = os.getenv("CONSUL_HOST", "consul")
        consul_port = int(os.getenv("CONSUL_PORT", 8500))
        self.consul = consul.Consul(host=consul_host, port=consul_port)

    def _get_service_url(self, service_name: str) -> str:
        """
        Discover a service URL using Consul.
        Handles Docker + Spring Cloud registration correctly.
        """
        _, services = self.consul.health.service(service_name, passing=True)

        if not services:
            raise ConnectionError(
                f"Service '{service_name}' not found or not healthy in Consul"
            )

        service = services[0]

        # Prefer explicit service address, fallback to node address
        address = (
            service["Service"]["Address"]
            or service["Node"]["Address"]
        )
        port = service["Service"]["Port"]

        if not address or not port:
            raise ConnectionError(
                f"Invalid service registration for '{service_name}': {service}"
            )

        return f"http://{address}:{port}"

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
        base_url = self._get_service_url("aggregation-service")
        url = f"{base_url}/api/top-categories"

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
