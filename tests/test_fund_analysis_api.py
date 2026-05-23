import requests
import json
import time

def test_fund_analysis():
    # 1. Login to get token
    login_url = "http://localhost:8000/api/auth/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    print("Logging in...")
    # Authentication endpoint expects JSON payload
    login_response = requests.post(login_url, json=login_data)
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return

    token = login_response.json().get("data", {}).get("access_token")
    if not token:
        print(f"No token found in response: {login_response.text}")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 2. Submit analysis task
    url = "http://localhost:8000/api/analysis/single"
    # Using the fund code from our slice requirements
    payload = {
        "symbol": "270042",
        "instrument_type": "fund",
        "trade_date": "2025-01-15"
    }
    
    print(f"Submitting fund analysis request: {payload}")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"Failed to submit task. Status: {response.status_code}, Response: {response.text}")
        return
        
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

    if "data" not in data or "task_id" not in data["data"]:
        print("Error: No task_id in response")
        return

    task_id = data["data"]["task_id"]
    print(f"\nTask ID: {task_id}")
    
    # Poll for completion
    poll_url = f"http://localhost:8000/api/analysis/tasks/{task_id}/status"
    max_retries = 60  # Increase to 5 minutes timeout
    retry_count = 0

    print("\nPolling for completion...")
    while retry_count < max_retries:
        poll_response = requests.get(poll_url, headers=headers)
        if poll_response.status_code == 200:
            task_data = poll_response.json().get("data", {})
            status = task_data.get("status")
            print(f"Status: {status}")
            
            if status == "completed":
                print("\nTask completed successfully!")
                result = task_data.get("result", {})
                print(f"Final Decision: {result.get('final_trade_decision')}")
                print(f"Instrument Type: {result.get('instrument_type')}")
                return
            elif status == "failed":
                print(f"\nTask failed: {task_data.get('error')}")
                return
        else:
            print(f"Failed to check status. Status: {poll_response.status_code}")
            
        time.sleep(5)
        retry_count += 1
        
    print("\nTimeout waiting for task completion")

if __name__ == "__main__":
    test_fund_analysis()
