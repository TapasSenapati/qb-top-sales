import consul
import os
import socket
import atexit

consul_client = None
SERVICE_ID = None

def register_service():
    """Registers the service with Consul."""
    global consul_client, SERVICE_ID

    consul_host = os.getenv("CONSUL_HOST", "localhost")
    consul_port = int(os.getenv("CONSUL_PORT", 8500))
    
    service_name = os.getenv("SERVICE_NAME", "forecasting-service")
    service_port = int(os.getenv("SERVICE_PORT", 8000))
    service_ip = os.getenv("SERVICE_HOST", socket.gethostname())
    SERVICE_ID = f"{service_name}-{service_ip}-{service_port}"

    consul_client = consul.Consul(host=consul_host, port=consul_port)

    health_check_url = f"http://{service_ip}:{service_port}/health"
    
    consul_client.agent.service.register(
        name=service_name,
        service_id=SERVICE_ID,
        address=service_ip,
        port=service_port,
        check=consul.Check.http(health_check_url, interval="10s", timeout="3s")
    )
    print(f"Service '{SERVICE_ID}' registered with Consul.")
    atexit.register(deregister_service)

def deregister_service():
    """Deregisters the service from Consul."""
    if consul_client and SERVICE_ID:
        print(f"Deregistering service '{SERVICE_ID}' from Consul.")
        consul_client.agent.service.deregister(service_id=SERVICE_ID)