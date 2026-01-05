import requests
import json
import time
import os

LOYVERSE_TOKEN = os.environ.get('LOYVERSE_TOKEN')   
API_BASE_URL = "https://api.loyverse.com/v1.0"

def get_all_loyverse_items():
    headers = {
        "Authorization": f"Bearer {LOYVERSE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    all_items = []
    cursor = None
    page_count = 1

    print("🚀 Starting extraction from Loyverse...")

    while True:
       
        url = f"{API_BASE_URL}/items?limit=250"
        if cursor:
            url += f"&cursor={cursor}"

        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code} - {response.text}")
                break

            data = response.json()
            items_batch = data.get('items', [])
            all_items.extend(items_batch)

            print(f"   Fetched page {page_count}... (Total so far: {len(all_items)})")

            # Check if there is a next page
            cursor = data.get('cursor')
            if not cursor:
                break  # No more pages, exit loop
            
            page_count += 1
            time.sleep(0.2) # Be nice to the API

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            break

    return all_items

# 2. RUN AND SAVE
if __name__ == "__main__":
    items = get_all_loyverse_items()
    
    # Save to a file so you can analyze the structure
    with open('loyverse_dump.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Extraction Complete! Saved {len(items)} items to 'loyverse_dump.json'.")