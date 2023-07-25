### Pyhton
from kubernetes import client, config
from locust import User, task, between
import time redis

class SentinelMasterPod:
    def __init__(self, namespace='antelope-int', sentinel_service_name='int-redis-tester'):
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
        while True:
            try:
                if not self.api:
                    self.authenticate_kubernetes_api()

                # Get the Service for the Redis Sentinel
                service = self.api.read_namespaced_service(self.sentinel_service_name, self.namespace)
                # Get the master pod name from the Service status
                master_pod_name = service.status.load_balancer.ingress[0].hostname
                return master_pod_name
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
        sentinel_master = SentinelMasterPod(namespace='antelope-int', sentinel_service_name='int-redis-tester')
        # Get the name of the Redis Sentinel master pod
        self.master_pod = sentinel_master.get_sentinel_master_pod()
        self.sentinel_master = redis.StrictRedis(host=self.master_pod, port=26379, decode_responses=True)

    @task(1)
    def write_to_redis(self):
        key = "test_key"
        value = "test_value"
        self.sentinel_master.set(key, value)

    @task(2)
    def read_from_redis(self):
        key = "test_key"
        self.sentinel_master.get(key)

class RedisSentinelLocust(User):
    wait_time = between(1, 3)  # Time between consecutive tasks
    tasks = [RedisSentinelUser]
