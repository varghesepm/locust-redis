from locust import User, task, between
import redis
from kubernetes import client, config
import time

class SentinelMasterPod:
    def __init__(self, namespace='default', sentinel_service_name='int-redis-tester'):
        self.namespace = namespace
        self.sentinel_service_name = sentinel_service_name
        self.api = None

    def authenticate_kubernetes_api(self):
        try:
            # Load Kubernetes configuration and initialize the API client with RBAC support
            config.load_incluster_config()
            self.api = client.CoreV1Api()
        except Exception as e:
            raise RuntimeError("Failed to authenticate Kubernetes API: " + str(e))

    def get_sentinel_master_pod(self):
        if not self.api:
            self.authenticate_kubernetes_api()

        while True:
            try:
                # Get the Service for the Redis Sentinel
                service = self.api.read_namespaced_service(self.sentinel_service_name, self.namespace)
                # Check if the Service has an external IP or hostname
                if service.spec.type == 'LoadBalancer' and service.status.load_balancer and service.status.load_balancer.ingress:
                    if service.status.load_balancer.ingress[0].hostname:
                        master_address = service.status.load_balancer.ingress[0].hostname
                    else:
                        master_address = service.status.load_balancer.ingress[0].ip
                else:
                    # Use the headless service name (StatefulSet format) to get the Redis master pod IP
                    # Replace 'mymaster' with the actual Redis master pod name
                    stateful_set_name = 'int-redis-tester-server'
                    stateful_set_pod_list = self.api.list_namespaced_pod(self.namespace, label_selector=f"statefulset.kubernetes.io/pod-name={stateful_set_name}-0")
                    if stateful_set_pod_list.items:
                        master_address = stateful_set_pod_list.items[0].status.pod_ip
                    else:
                        raise ValueError("LoadBalancer hostname, ClusterIP, or ExternalIP not found in Service status.")
                    
                return master_address
            except Exception as e:
                print(f"Error: {e}. Retrying in 5 seconds...")
                time.sleep(5)

class RedisSentinelUser(User):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.master_pod = None
        self.sentinel_master = None

    def on_start(self):
        # Initialize the SentinelMasterPod class with the namespace and the service name of the Redis Sentinel
        sentinel_master = SentinelMasterPod(namespace='default', sentinel_service_name='int-redis-tester')
        # Get the address of the Redis Sentinel master pod
        self.master_pod = sentinel_master.get_sentinel_master_pod()

        # If master_pod is not found, raise an error or handle it as per your requirements
        if self.master_pod is None:
            raise ValueError("Redis Sentinel master pod address not found.")

        self.sentinel_master = redis.StrictRedis(host=self.master_pod, port=6379, decode_responses=True)

    @task(1)
    def write_to_redis(self):
        key = "test_key"
        value = "test_value"
        self.sentinel_master.set(key, value)
        print(f"Successfully set '{key}' to '{value}' in Redis.")

    @task(2)
    def read_from_redis(self):
        # Fetch an existing key from Redis and use it with the GET command
        existing_key = "test_key"
        value = self.sentinel_master.get(existing_key)
        print(f"Value of '{existing_key}': {value}")

class RedisSentinelLocust(User):
    wait_time = between(1, 3)  # Time between consecutive tasks
    tasks = [RedisSentinelUser]
