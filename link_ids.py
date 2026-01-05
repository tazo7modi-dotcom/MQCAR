import requests
import json
from app import create_app, db
from app.models import Product
import os
# CONFIG
LOYVERSE_TOKEN = os.environ.get('LOYVERSE_TOKEN')  
API_BASE_URL = "https://api.loyverse.com/v1.0"

app = create_app()

def populate_loyverse_ids():
    print("🚀 Fetching Item IDs from Loyverse...")
    
    # 1. Fetch all items from Loyverse
    headers = {"Authorization": f"Bearer {LOYVERSE_TOKEN}"}
    cursor = None
    id_map = {} # { 'Product Name': 'Variant ID' }

    while True:
        resp = requests.get(f"{API_BASE_URL}/items?limit=250&cursor={cursor or ''}", headers=headers)
        if resp.status_code != 200: break
        data = resp.json()
        
        for item in data.get('items', []):
            if item.get('variants'):
                # Map Name -> First Variant ID
                id_map[item['item_name']] = item['variants'][0]['variant_id']
        
        cursor = data.get('cursor')
        if not cursor: break

    print(f"✅ Found {len(id_map)} items. Updating database...")

    # 2. Update Flask Database
    with app.app_context():
        count = 0
        for name, vid in id_map.items():
            product = Product.query.filter_by(name=name).first()
            if product:
                product.loyverse_id = vid
                count += 1
        
        db.session.commit()
        print(f"🎉 Linked {count} products to their Loyverse IDs!")

if __name__ == "__main__":
    populate_loyverse_ids()