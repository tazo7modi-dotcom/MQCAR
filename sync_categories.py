import requests
import json
from app import create_app, db
from app.models import Product, Category
import os

# CONFIG
LOYVERSE_TOKEN = os.environ.get('LOYVERSE_TOKEN') 
API_BASE_URL = "https://api.loyverse.com/v1.0"

app = create_app()

def sync_categories():
    print("🚀 Fetching Categories from Loyverse...")
    
    headers = {"Authorization": f"Bearer {LOYVERSE_TOKEN}"}
    
    # --- STEP 1: Get Loyverse Categories (UUID -> Name) ---
    loy_cat_map = {} # { 'Loyverse_ID': 'Category Name' }
    
    cursor = None
    while True:
        resp = requests.get(f"{API_BASE_URL}/categories?limit=250&cursor={cursor or ''}", headers=headers)
        if resp.status_code != 200: 
            print("Error fetching categories")
            break
        data = resp.json()
        
        for cat in data.get('categories', []):
            loy_cat_map[cat['id']] = cat['name']
            
        cursor = data.get('cursor')
        if not cursor: break

    print(f"   Found {len(loy_cat_map)} categories in Loyverse.")

    # --- STEP 2: Map to Local Database IDs ---
    # We want: { 'Loyverse_UUID': Local_DB_ID }
    uuid_to_local_id = {}
    
    with app.app_context():
        print("\n🔗 Linking to local categories...")
        for loy_id, name in loy_cat_map.items():
            # Try to find category by name (Case insensitive)
            local_cat = Category.query.filter(Category.name.ilike(name)).first()
            
            if local_cat:
                uuid_to_local_id[loy_id] = local_cat.id
                print(f"   ✅ Linked '{name}' -> ID {local_cat.id}")
            else:
                # OPTIONAL: Create category if it doesn't exist?
                # Uncomment lines below to auto-create missing categories
                # new_cat = Category(name=name)
                # db.session.add(new_cat)
                # db.session.commit()
                # uuid_to_local_id[loy_id] = new_cat.id
                # print(f"   ✨ Created new category '{name}'")
                print(f"   ⚠️  Skipping '{name}' (Not found in local DB)")

    # --- STEP 3: Update Products ---
    # We need the product dump to know which product belongs to which category UUID
    try:
        with open('loyverse_dump.json', 'r', encoding='utf-8') as f:
            items_data = json.load(f)
    except FileNotFoundError:
        print("\n❌ Error: 'loyverse_dump.json' not found. We need it to match items.")
        return

    print("\n💾 Updating Product Categories...")
    
    with app.app_context():
        updated_count = 0
        
        for item in items_data:
            loy_cat_id = item.get('category_id')
            
            # If item has a category AND we mapped that category
            if loy_cat_id and loy_cat_id in uuid_to_local_id:
                local_cat_id = uuid_to_local_id[loy_cat_id]
                
                # Find the product
                product = Product.query.filter_by(name=item['item_name']).first()
                if product:
                    product.category_id = local_cat_id
                    updated_count += 1
        
        db.session.commit()
        print(f"\n🎉 DONE! Updated category for {updated_count} products.")

if __name__ == "__main__":
    sync_categories()