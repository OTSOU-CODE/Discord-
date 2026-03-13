import asyncio
import time

class MockUser:
    def __init__(self, id):
        self.id = id

class MockClient:
    def __init__(self):
        self._cache = {123: MockUser(123)}

    def get_user(self, user_id):
        # O(1) cache lookup
        return self._cache.get(user_id)

    async def fetch_user(self, user_id):
        # Simulate network latency (e.g. 50ms API call)
        await asyncio.sleep(0.05)
        return MockUser(user_id)

async def run_benchmark():
    client = MockClient()
    user_id = 123

    print("Benchmarking user fetch in reminder loop...")

    # Baseline: fetch_user directly
    iterations = 100
    start_time = time.perf_counter()
    for _ in range(iterations):
        user = await client.fetch_user(user_id)
    baseline_time = time.perf_counter() - start_time
    print(f"Baseline (fetch_user): {baseline_time:.4f} seconds for {iterations} iterations")

    # Optimized: get_user or fetch_user
    start_time = time.perf_counter()
    for _ in range(iterations):
        user = client.get_user(user_id) or await client.fetch_user(user_id)
    optimized_time = time.perf_counter() - start_time
    print(f"Optimized (get_user or fetch_user): {optimized_time:.4f} seconds for {iterations} iterations")

    if optimized_time < baseline_time:
        improvement = (baseline_time - optimized_time) / baseline_time * 100
        print(f"Improvement: {improvement:.2f}% faster")
        print(f"Time saved: {baseline_time - optimized_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
