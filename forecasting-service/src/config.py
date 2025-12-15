import os

CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))
AGGREGATION_SERVICE_NAME = os.getenv("AGGREGATION_SERVICE_NAME", "aggregation-service")
