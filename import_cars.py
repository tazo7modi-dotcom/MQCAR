import os
import shutil
from app import create_app, db
from app.models import Category

app = create_app()

def import_cars():
    with app.app_context():
        base_dir = os.path.abspath(os.path.dirname(__file__))
        source_root = os.path.join(base_dir, 'app', 'cat')
        dest_root_relative = 'cars' 
        dest_root = os.path.join(base_dir, 'app', 'static', dest_root_relative)

        if not os.path.exists(source_root):
            print(f"Error: Source folder not found at {source_root}")
            return

        print("🚀 Starting Auto-Import...")

        for main_cat_name in os.listdir(source_root):
            main_cat_path = os.path.join(source_root, main_cat_name)

            if os.path.isdir(main_cat_path):
                print(f"\n📂 Processing Main Category: {main_cat_name}")

             
                main_cat = Category.query.filter_by(name=main_cat_name, parent_id=None).first()
                if not main_cat:
                    main_cat = Category(name=main_cat_name, parent_id=None)
                    db.session.add(main_cat)
                    db.session.commit()
                    print(f"   ✅ Created Parent Category: {main_cat_name}")
                
                dest_cat_folder = os.path.join(dest_root, main_cat_name)
                os.makedirs(dest_cat_folder, exist_ok=True)

                for filename in os.listdir(main_cat_path):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        
                        src_file_path = os.path.join(main_cat_path, filename)
                        name_without_ext = os.path.splitext(filename)[0]
                        
                 
                        if '_' in name_without_ext:
                            sub_name, model_years = name_without_ext.rsplit('_', 1)
                        elif '-' in name_without_ext:
                   
                            parts = name_without_ext.split('-', 1)
                            sub_name = parts[0]
                            model_years = parts[1] if len(parts) > 1 else None
                        else:
                            sub_name = name_without_ext
                            model_years = None

                        print(f"   🚗 Found Car: {sub_name} (Years: {model_years})")

                      
                        dest_file_path = os.path.join(dest_cat_folder, filename)
                        shutil.copy2(src_file_path, dest_file_path)
                        db_image_url = f"{dest_root_relative}/{main_cat_name}/{filename}"


                        sub_cat = Category.query.filter_by(
                            name=sub_name, 
                            parent_id=main_cat.id, 
                            model_years=model_years
                        ).first()
                        
                        if sub_cat:
                           
                            sub_cat.image_url = db_image_url
                            print(f"      🔄 Updated existing sub-category.")
                        else:
                            
                            sub_cat = Category(
                                name=sub_name,
                                parent_id=main_cat.id,
                                model_years=model_years,
                                image_url=db_image_url
                            )
                            db.session.add(sub_cat)
                            print(f"      ✨ Created new sub-category.")

                db.session.commit()

        print("\n🎉 Import Finished Successfully!")

if __name__ == "__main__":
    import_cars()