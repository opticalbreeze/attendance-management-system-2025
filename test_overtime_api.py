#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""時間外申告API テストスクリプト"""

import requests
import json

# テストデータ
test_data = {
    "employee_num": "2952089",  # 文字列として送信
    "application_date": "2025-11-06",
    "work_date": "2025-11-05",
    "overtime_entries": [
        {
            "start_time": "18:00",
            "end_time": "20:00",
            "description": "テスト申告"
        }
    ]
}

print("=" * 80)
print("時間外申告API テスト")
print("=" * 80)
print(f"URL: http://localhost:5000/api/overtime")
print(f"Method: POST")
print(f"Data: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
print()

try:
    response = requests.post(
        'http://localhost:5000/api/overtime',
        json=test_data,
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 80)

