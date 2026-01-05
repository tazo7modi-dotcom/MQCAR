import requests
import json
import time
from app import create_app, db
from app.models import Product
import os

# 1. SETUP
LOYVERSE_TOKEN = os.environ.get('LOYVERSE_TOKEN') 
API_BASE_URL = "https://api.loyverse.com/v1.0"

app = create_app()

def sync_inventory_sum():
    # --- STEP A: Load Map ---
    try:
        with open('loyverse_dump.json', 'r', encoding='utf-8') as f:
            items_data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: 'loyverse_dump.json' not found.")
        return

    id_to_name_map = {}
    for item in items_data:
        if item.get('variants'):
            variant_id = item['variants'][0]['variant_id']
            id_to_name_map[variant_id] = item['item_name']

    print(f"🗺️  Mapped {len(id_to_name_map)} products.")

    # --- STEP B: Fetch Inventory ---
    print("🚀 Fetching live stock levels...")
    
    headers = {
        "Authorization": f"Bearer {LOYVERSE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    inventory_levels = []
    cursor = None
    
    while True:
        url = f"{API_BASE_URL}/inventory?limit=250"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200: break
            data = response.json()
            inventory_levels.extend(data.get('inventory_levels', []))
            cursor = data.get('cursor')
            if not cursor: break
            time.sleep(0.2)
        except: break

    print(f"📦 Retrieved {len(inventory_levels)} stock records.")

    # --- STEP C: CALCULATE TOTALS IN PYTHON FIRST ---
    # This prevents overwriting. We sum them up by Variant ID.
    stock_totals = {} 

    for record in inventory_levels:
        variant_id = record.get('variant_id')
        stock_level = record.get('in_stock', 0)
        
        # Add to existing total for this variant
        current_total = stock_totals.get(variant_id, 0)
        stock_totals[variant_id] = current_total + float(stock_level)

    # --- STEP D: Update Database Once ---
    print("💾 Saving TOTAL quantities to database...")
    
    with app.app_context():
        updated_count = 0
        
        for variant_id, total_qty in stock_totals.items():
            product_name = id_to_name_map.get(variant_id)
            
            if product_name:
                product = Product.query.filter_by(name=product_name).first()
                if product:
                    product.quantity = int(total_qty)
                    updated_count += 1

        db.session.commit()
        print(f"\n✅ SUCCESS! Updated Total Stock for {updated_count} products.")

if __name__ == "__main__":
    sync_inventory_sum()