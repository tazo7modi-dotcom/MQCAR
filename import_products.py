import json
import os
from app import create_app, db
from app.models import Product, Category


app = create_app()

def import_loyverse_data():
    
    try:
        with open('loyverse_dump.json', 'r', encoding='utf-8') as f:
            items = json.load(f)
    except FileNotFoundError:
        print("❌ Error: 'loyverse_dump.json' not found. Make sure it is in the same folder.")
        return

    print(f"🚀 Starting import of {len(items)} items...")
    
    with app.app_context():
        count = 0
        skipped = 0
        
        for item in items:
            try:
               
                name = item.get('item_name')
                image_url = item.get('image_url')
                description = item.get('description', '')
                
               
                if item.get('deleted_at'):
                    continue

                
                variants = item.get('variants', [])
                price = 0.0
                sku = None
                
                if variants:
                    first_variant = variants[0]
                    
                    if first_variant.get('stores'):
                        price = first_variant['stores'][0].get('price', 0.0)
                    else:
                        price = first_variant.get('default_price', 0.0)
                    
                    sku = first_variant.get('sku')

                
                existing = Product.query.filter_by(name=name).first()
                if existing:
                    print(f"   ⚠️  Skipping '{name}' (Already exists)")
                    skipped += 1
                    continue

               
                new_prod = Product(
                    name=name,
                    description=description,
                    price=float(price) if price else 0.0,
                    image_url=image_url, 
                    quantity=0, 
                    label="Loyverse Import" 
                )
                
                
                if sku:
                    new_prod.description = f"{description or ''} \n(SKU: {sku})".strip()

                db.session.add(new_prod)
                count += 1
                
               
                if count % 100 == 0:
                    db.session.commit()
                    print(f"   ✅ Imported {count} items...")

            except Exception as e:
                print(f"   ❌ Error importing {item.get('item_name')}: {e}")

        # Final Commit
        db.session.commit()
        print(f"\n🎉 DONE! Imported: {count}, Skipped: {skipped}")

if __name__ == "__main__":
    import_loyverse_data()