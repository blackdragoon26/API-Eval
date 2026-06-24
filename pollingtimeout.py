import os
import time
import requests

# ==========================================
# 1. THE POLLING FUNCTION
# ==========================================
def poll_task_status(activity_id, api_key, max_wait=60):
    url = f"https://api.fortyguard.com/v1/status/{activity_id}"
    headers = {"api-key": api_key}
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            resp = requests.get(url, headers=headers)
            
            if resp.status_code != 200:
                print(f"❌ Error checking status: {resp.status_code} - {resp.text}")
                return
                
            data = resp.json()
            # Handle casing inconsistencies (e.g., "Processing" vs "processing")
            status = data.get("status", "").lower() 
            
            if status in ["succeeded", "completed"]:
                print("✅ Task completed successfully!")
                return
            elif status == "failed":
                print("❌ Task failed on the server side.")
                print("Error details:", data)
                return
            else:
                print(f"⏳ Task is '{status}'... waiting 5s.")
                time.sleep(5)
        except Exception as e:
            print(f"⚠️ Error during polling request: {e}")
            time.sleep(5)
            
    print("⏱️ Timeout: Task did not complete within the time limit.")

# ==========================================
# 2. THE MAIN EXECUTION BLOCK
# ==========================================
def main():
    # 1. Get API Key from environment variable
    API_KEY = os.environ.get("FORTYGUARD_API_KEY")
    if not API_KEY:
        print("❌ Error: FORTYGUARD_API_KEY environment variable is not set.")
        print("Please run: export FORTYGUARD_API_KEY='your_key_here'")
        return

    # 2. Submit a task to get an activity_id
    submit_url = "https://api.fortyguard.com/v1/heatmap"
    headers = {
        "api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Standard test payload (New York coordinates)
    payload = {
        "polygon_aoi": {
            "type": "Polygon",
            "coordinates": [[
                [-74.0060, 40.7128],
                [-74.0050, 40.7128],
                [-74.0050, 40.7138],
                [-74.0060, 40.7138],
                [-74.0060, 40.7128]
            ]]
        },
        "date_time": {
            "start_date": "2024-07-15",
            "start_time": "14:00",
            "filter_type": 1
        },
        "granularity": 100
    }

    print("🚀 Submitting task to Heatmap endpoint...")
    try:
        response = requests.post(submit_url, headers=headers, json=payload)
        print(f"📡 Submission Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Safely extract activity_id from nested JSON
            activity_id = data.get("data", {}).get("activity_id") or data.get("activity_id")
            
            if not activity_id:
                print("⚠️ Could not find activity_id in response.")
                print("Server Response:", data)
                return
                
            print(f"✅ Task submitted! Activity ID: {activity_id}\n")
            
            # 3. Poll the status
            print("⏱️ Starting to poll status (Timeout set to 60s for quick testing)...")
            poll_task_status(activity_id, API_KEY, max_wait=60)
        else:
            print(f"❌ Failed to submit task. Server returned {response.status_code}.")
            print("Response:", response.text)
            
    except Exception as e:
        print(f"❌ An error occurred during submission: {e}")

if __name__ == "__main__":
    main()