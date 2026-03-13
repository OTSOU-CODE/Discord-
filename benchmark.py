import timeit

# Generate mock tickets data
tickets_data = {f"ticket_{i}": {"channel_id": i, "status": "open"} for i in range(10000)}

# Scenario 1: Target channel ID is at the beginning (best case for any)
channel_id_early = 10

# Scenario 2: Target channel ID is at the end
channel_id_late = 9990

# Scenario 3: Target channel ID is not in the dictionary (worst case for both)
channel_id_not_found = 100000

def check_list_comprehension(channel_id):
    return channel_id in [data.get('channel_id') for data in tickets_data.values()]

def check_any_generator(channel_id):
    return any(data.get('channel_id') == channel_id for data in tickets_data.values())

if __name__ == "__main__":
    print("Benchmarking `channel_id in [list comprehension]` vs `any(generator)`")
    print("-" * 60)

    # Verify correctness
    assert check_list_comprehension(channel_id_early) == check_any_generator(channel_id_early)
    assert check_list_comprehension(channel_id_late) == check_any_generator(channel_id_late)
    assert check_list_comprehension(channel_id_not_found) == check_any_generator(channel_id_not_found)

    # Number of executions for timeit
    n = 1000

    # Early match
    time_list_early = timeit.timeit("check_list_comprehension(channel_id_early)", globals=globals(), number=n)
    time_any_early = timeit.timeit("check_any_generator(channel_id_early)", globals=globals(), number=n)
    print(f"Match Early (id={channel_id_early}):")
    print(f"  List comp: {time_list_early:.6f} s")
    print(f"  Any gen:   {time_any_early:.6f} s")
    print(f"  Speedup:   {time_list_early / time_any_early:.2f}x\n")

    # Late match
    time_list_late = timeit.timeit("check_list_comprehension(channel_id_late)", globals=globals(), number=n)
    time_any_late = timeit.timeit("check_any_generator(channel_id_late)", globals=globals(), number=n)
    print(f"Match Late (id={channel_id_late}):")
    print(f"  List comp: {time_list_late:.6f} s")
    print(f"  Any gen:   {time_any_late:.6f} s")
    print(f"  Speedup:   {time_list_late / time_any_late:.2f}x\n")

    # No match
    time_list_not_found = timeit.timeit("check_list_comprehension(channel_id_not_found)", globals=globals(), number=n)
    time_any_not_found = timeit.timeit("check_any_generator(channel_id_not_found)", globals=globals(), number=n)
    print(f"No Match (id={channel_id_not_found}):")
    print(f"  List comp: {time_list_not_found:.6f} s")
    print(f"  Any gen:   {time_any_not_found:.6f} s")
    print(f"  Speedup:   {time_list_not_found / time_any_not_found:.2f}x\n")
