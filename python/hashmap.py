"""Exercise Python's string hash map, the counterpart of chibicc's hashmap.c.

Based on chibicc commit 0aad326f3550b3d4c499d4078fcc65cc2dbf7626.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""


def hashmap_test():
    # Python's built-in dictionary provides the hash-table implementation.
    entries = {}
    for index in range(5000):
        entries[f"key {index}"] = index
    for index in range(1000, 2000):
        entries.pop(f"key {index}", None)
    for index in range(1500, 1600):
        entries[f"key {index}"] = index
    for index in range(6000, 7000):
        entries[f"key {index}"] = index
    for index in range(7000):
        present = index < 1000 or 1500 <= index < 1600 or 2000 <= index < 5000 or index >= 6000
        assert entries.get(f"key {index}") == (index if present else None)
    entries["key 0"] = 42
    assert entries["key 0"] == 42
    assert entries.get("no such key") is None
    print("OK")
