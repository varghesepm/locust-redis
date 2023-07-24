from locust import User, task, between
import redis
from redis.sentinel import Sentinel

class RedisSentinelUser(User):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sentinel = Sentinel([('int-redis-tester', 26379)], socket_timeout=0.1)

    def get_master(self):
        return self.sentinel.discover_master('mymaster')

    @task(1)
    def write_to_redis(self):
        key = "test_key"
        value = "test_value"
        master = self.get_master()
        self.master = master[0]
        self.master.set(key, value)

    @task(2)
    def read_from_redis(self):
        key = "test_key"
        master = self.get_master()
        self.master = master[0]
        self.master.get(key)

class RedisSentinelLocust(User):
    wait_time = between(1, 3)  # Time between consecutive tasks
    tasks = [RedisSentinelUser]
