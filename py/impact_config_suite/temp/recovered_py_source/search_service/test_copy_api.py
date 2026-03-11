import requests
import json
import time

# Test the /copy endpoint with root_folder parameter
url = "http://localhost:7000/copy"

payload = {
    "batch_file": "my_test_batch.txt",
    "root_folder": "C:\\_IMPACT\\_LOCAL_FILES"
}

print("\n" + "="*60)
print("📤 TESTING /copy ENDPOINT")
print("="*60)
print(f"Payload being sent:")
print(json.dumps(payload, indent=2))
print("="*60)

time.sleep(1)  # Small delay to ensure output is clear

try:
    response = requests.post(url, json=payload)
    print(f"\n✅ Response Status: {response.status_code}")
    print(f"   Response: {response.text}")
    print("\n📋 NOW CHECK THE SERVER CONSOLE for the log output showing:")
    print("   '📨 API REQUEST - /copy'")
    print("   '   Batch file: my_test_batch.txt'")
    print("   '   Root folder: C:\\_IMPACT\\_LOCAL_FILES'")
    print("="*60)
except Exception as e:
    print(f"\n❌ Error: {e}")
