from locust import Locust, TaskSet, task, between
import redis
from redis.sentinel import Sentinel

class RedisSentinelTaskSet(TaskSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sentinel = Sentinel([('int-redis-tester', 26379)], socket_timeout=0.1)
        self.master = self.sentinel.master_for('mymaster', socket_timeout=0.1)

    @task(1)
    def write_to_redis(self):
        key = "test_key"
        value = "test_value"
        self.master.set(key, value)

    @task(2)
    def read_from_redis(self):
        key = "test_key"
        self.master.get(key)

class RedisSentinelLocust(Locust):
    task_set = RedisSentinelTaskSet
    wait_time = between(1, 3)  # Time between consecutive tasks
