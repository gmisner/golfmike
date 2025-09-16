#!/usr/bin/env python3
"""
Simple test script for AviationWeather.gov API
"""

import requests
import json

def test_api():
    print("🌤️  Testing AviationWeather.gov API...")
    
    try:
        # Test with a simple METAR request
        url = "https://aviationweather.gov/api/data/metar"
        params = {
            'ids': 'KLAX',
            'hours': 1,
            'format': 'json'
        }
        
        print(f"Making request to: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Got {len(data)} METAR records")
            if data:
                sample = data[0]
                print(f"Sample METAR: {sample.get('icaoId', 'Unknown')} - {sample.get('rawOb', 'No data')[:100]}...")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_api()


