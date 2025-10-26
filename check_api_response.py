#!/usr/bin/env python3
"""
Script để kiểm tra cấu trúc API response thực tế
"""

import requests
import json

def check_api_response():
    """Kiểm tra cấu trúc API response"""
    print("Checking API Response Structure")
    print("=" * 50)
    
    # Test simulation API
    params = {
        "station_codes": ["13085"],
        "hours_back": 24,
        "duration": 24,
        "hydraulic_timestep": 1,
        "report_timestep": 1
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/scada/simulation-with-realtime",
            json=params,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nFull Response Structure:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            print("\nResponse Analysis:")
            print(f"- Type: {type(data)}")
            print(f"- Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if isinstance(data, dict):
                for key, value in data.items():
                    print(f"- {key}: {type(value)} = {value}")
                    
            return data
        else:
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Exception: {e}")
        return None

if __name__ == "__main__":
    check_api_response()
