"""
Test script cho leak detection API
"""
import requests
import json

API_URL = "http://localhost:8001/api/v1/leak-detection"

# Test 1: Service status
print("=" * 80)
print("TEST 1: Service Status")
print("=" * 80)
response = requests.get(f"{API_URL}/status")
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

# Test 2: Detect leaks
print("=" * 80)
print("TEST 2: Detect Leaks")
print("=" * 80)
test_data = {
    "nodes_data": {
        "1359": [
            {
                "timestamp": 3600,
                "pressure": 45.2,
                "head": 50.1,
                "demand": 0.05
            },
            {
                "timestamp": 7200,
                "pressure": 44.8,
                "head": 49.8,
                "demand": 0.06
            }
        ],
        "1360": [
            {
                "timestamp": 3600,
                "pressure": 42.5,
                "head": 47.2,
                "demand": 0.03
            }
        ]
    }
}

response = requests.post(
    f"{API_URL}/detect",
    json=test_data,
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result.get('success')}")
    if 'data' in result:
        leaks = result['data'].get('leaks', [])
        summary = result['data'].get('summary', {})
        print(f"\nDetected Leaks: {len(leaks)}")
        print(f"Summary: {json.dumps(summary, indent=2)}")
        if leaks:
            print(f"\nTop 3 Leaks:")
            for i, leak in enumerate(leaks[:3], 1):
                print(f"  {i}. Node: {leak['node_id']}, Probability: {leak['probability']:.3f}, Time: {leak['timestamp']}")
else:
    print(f"Error: {response.text}")

print()
print("=" * 80)
print("[OK] TEST COMPLETED")
print("=" * 80)

