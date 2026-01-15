import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.utils import secure_filename
from sqlalchemy import func, extract
from datetime import datetime, timedelta

from app.models import db, Product, Category, Order, User, Extra, OrderItem,ProductSize,ProductColor,ProductImage, ColorImage,SizeImage
from app.translations import dictionary
import json

admin_bp = Blueprint('admin', __name__)

if os.path.exists('/var/data'):
    BASE_UPLOAD_PATH = '/var/data'
else:
    BASE_UPLOAD_PATH = os.path.join(os.getcwd(), 'app/static/uploads')


def _(key):
    lang = session.get('language', 'en')
    return dictionary.get(lang, {}).get(key, key)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

# --- 1. DASHBOARD ---



@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    product_count = Product.query.count()

    order_count = Order.query.filter(Order.payment_status.in_(['Paid', 'COD'])).count()

    total_revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(payment_status='Paid').scalar() or 0

    recent_orders = Order.query.filter(
    Order.payment_status.in_(['Paid', 'COD'])
).order_by(Order.created_at.desc()).limit(50).all()
    products = Product.query.all()
    all_categories = Category.query.all()

    search_query = request.args.get('q')
    if search_query:
      
        products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()
    else:
      
        products = Product.query.all()

    labels = [o.created_at.strftime("%d %b") for o in recent_orders[:7]][::-1]
    values = [o.total_amount for o in recent_orders[:7]][::-1]

    return render_template('admin/dashboard.html', 
                         product_count=product_count, 
                         order_count=order_count,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders,
                         products=products,
                         graph_labels=labels,
                         graph_values=values,
                         categories=all_categories)

# --- 2. UPDATE ORDER STATUS ---
@admin_bp.route('/update_order_status/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status:
        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} updated to {new_status}!", "success")
    
    return redirect(url_for('admin.dashboard'))

# --- 3. QUICK CATEGORY API ---
@admin_bp.route('/api/add_category', methods=['POST'])
@login_required
@admin_required
def api_add_category():
    data = request.get_json()
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({'error': 'Category already exists'}), 400

    new_cat = Category(name=name)
    db.session.add(new_cat)
    db.session.commit()
    
    return jsonify({'id': new_cat.id, 'name': new_cat.name})

import os
import json
from flask import render_template, redirect, url_for, request, flash, current_app
from werkzeug.utils import secure_filename
from flask_login import login_required






# Helper to define upload path
BASE_UPLOAD_PATH = '/var/data/uploads' # Adjust if your path is different

@admin_bp.route('/product/new', defaults={'product_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_product(product_id):
    product = Product.query.get_or_404(product_id) if product_id else Product()
    
    if request.method == 'POST':
        try:
            # ==========================================
            # 1. BASIC INFO
            # ==========================================
            product.name = request.form.get('name')
            try:
                product.price = float(request.form.get('price'))
            except (ValueError, TypeError):
                product.price = 0.0
                
            cat_id = request.form.get('category_id')
            product.category_id = int(cat_id) if cat_id else None
            product.description = request.form.get('description')
            product.label = request.form.get('label')
            
            # Checkbox: 'on' if checked, None if not
            product.is_juice = True if request.form.get('is_juice') else False
            
            # Ensure product exists to get an ID for filenames
            if not product.id:
                db.session.add(product)
                db.session.flush()

            # ==========================================
            # 2. MAIN GALLERY
            # ==========================================
            
            # A. New Uploads
            main_files = request.files.getlist('main_images[]')
            for file in main_files:
                if file and file.filename != '':
                    filename = secure_filename(f"main_{product.id}_{file.filename}")
                    save_dir = os.path.join(BASE_UPLOAD_PATH, 'products')
                    os.makedirs(save_dir, exist_ok=True)
                    file.save(os.path.join(save_dir, filename))
                    
                    db_path = f'products/{filename}'
                    
                    # Logic: If no cover, set as cover. Else add to gallery.
                    if not product.image_url:
                        product.image_url = db_path
                    else:
                        new_img = ProductImage(product_id=product.id, image_url=db_path)
                        db.session.add(new_img)

            # B. Deletions
            delete_main_ids = request.form.getlist('delete_main_image[]')
            if delete_main_ids:
                ProductImage.query.filter(ProductImage.id.in_(delete_main_ids)).delete(synchronize_session=False)


            # ==========================================
            # 3. VARIANTS (Colors/Flavors, Sizes, Images)
            # ==========================================
            variants_json = request.form.get('variants_json')
            
            # Force flags true if using this system
            product.has_colors = True 
            product.has_sizes = True 
            
            total_calculated_qty = 0
            kept_color_ids = [] 

            if variants_json:
                variants_data = json.loads(variants_json)

                for i, v_data in enumerate(variants_data):
                    # --- A. Manage ProductColor ---
                    color = None
                    if v_data.get('id'):
                        color = ProductColor.query.get(v_data['id'])
                    
                    if not color:
                        color = ProductColor(product_id=product.id)
                        db.session.add(color)
                    
                    color.name = v_data.get('name', 'Standard')
                    color.code = v_data.get('code', '#000000')
                    
                    db.session.flush() 
                    kept_color_ids.append(color.id)

                    # --- B. Manage Sizes (Bottles) ---
                    # 1. Delete old sizes (This cascades and deletes old SizeImage rows!)
                    ProductSize.query.filter_by(color_id=color.id).delete()
                    
                    for j, s_data in enumerate(v_data.get('sizes', [])):
                        try:
                            qty = int(s_data.get('qty', 0))
                        except:
                            qty = 0
                        
                        try:
                            s_price = float(s_data.get('price')) if s_data.get('price') else None
                        except:
                            s_price = None

                        # 2. Create New Size
                        new_size = ProductSize(
                            color_id=color.id, 
                            size_label=s_data.get('label', '500ml'),
                            quantity=qty,
                            price=s_price,
                        )
                        db.session.add(new_size)
                        db.session.flush() # Need ID for images

                        # -------------------------------------------------------
                        # 3. RESTORE OLD SIZE IMAGES (The Fix)
                        # -------------------------------------------------------
                        # The JS sends a list of URLs for images that were already there.
                        # We must re-insert them into the SizeImage table.
                        existing_urls = s_data.get('existing_images', [])
                        
                        for url in existing_urls:
                            # URL is like "/static/uploads/products/sizes/abc.jpg"
                            # We need relative path "products/sizes/abc.jpg"
                            if 'uploads/' in url:
                                clean_path = url.split('uploads/', 1)[1]
                                # Create entry
                                restored_img = SizeImage(
                                    size_id=new_size.id,
                                    image_url=clean_path
                                )
                                db.session.add(restored_img)

                        # -------------------------------------------------------
                        # 4. SAVE NEW SIZE UPLOADS (Multiple)
                        # -------------------------------------------------------
                        size_img_key = f"size_images_{i}_{j}[]" 
                        files = request.files.getlist(size_img_key)
                        
                        for s_file in files:
                            if s_file and s_file.filename != '':
                                fname = secure_filename(f"sz_{product.id}_{color.id}_{j}_{s_file.filename}")
                                save_path = os.path.join(BASE_UPLOAD_PATH, 'products/sizes')
                                os.makedirs(save_path, exist_ok=True)
                                s_file.save(os.path.join(save_path, fname))
            
                                # Add new DB entry
                                size_image = SizeImage(
                                    size_id=new_size.id,
                                    image_url=f'products/sizes/{fname}'
                                )
                                db.session.add(size_image)

                        total_calculated_qty += qty

                    # --- C. Manage Variant Images (Color Images) ---
                    # Uploads
                    file_key = f'variant_images_{i}[]'
                    v_files = request.files.getlist(file_key)
                    
                    for v_file in v_files:
                        if v_file and v_file.filename != '':
                            fname = secure_filename(f"v_{product.id}_{color.id}_{v_file.filename}")
                            v_save_dir = os.path.join(BASE_UPLOAD_PATH, 'products/variants')
                            os.makedirs(v_save_dir, exist_ok=True)
                            v_file.save(os.path.join(v_save_dir, fname))
                            
                            new_col_img = ColorImage(color_id=color.id, image_url=f'products/variants/{fname}')
                            db.session.add(new_col_img)

                    # Deletions
                    if v_data.get('id'):
                        del_col_imgs = request.form.getlist(f'delete_color_image_{v_data["id"]}[]')
                        if del_col_imgs:
                            ColorImage.query.filter(ColorImage.id.in_(del_col_imgs)).delete(synchronize_session=False)

                # --- D. Cleanup Removed Colors ---
                if kept_color_ids:
                    ProductColor.query.filter(
                        ProductColor.product_id == product.id,
                        ~ProductColor.id.in_(kept_color_ids)
                    ).delete(synchronize_session=False)
                
                # Update Total Quantity
                product.quantity = total_calculated_qty

            # ==========================================
            # 4. EXTRAS
            # ==========================================
            Extra.query.filter_by(product_id=product.id).delete()
            ex_names = request.form.getlist('extra_name[]')
            ex_prices = request.form.getlist('extra_price[]')
            
            for n, p in zip(ex_names, ex_prices):
                if n.strip():
                    try:
                        price_val = float(p)
                    except:
                        price_val = 0.0
                    new_extra = Extra(name=n, price=price_val, product_id=product.id)
                    db.session.add(new_extra)

            db.session.commit()
            flash("Product saved successfully!", "success")
            return redirect(url_for('admin.dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"Error Saving Product: {e}") # Print error to console
            flash(f"Error saving product: {str(e)}", "error")
            return redirect(request.url)

    # GET Request
    categories = Category.query.all()
    return render_template('admin/product_form.html', product=product, categories=categories)


# --- 5. DELETE PRODUCT ---
@admin_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('admin.dashboard'))

# --- 6. NEW CATEGORY (Updated for Persistent Disk) ---
@admin_bp.route('/category/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_category():
    all_categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        model_years = request.form.get('model_years')
        parent_id = request.form.get('parent_id')
        
        image_db_path = None

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                
                # Save to /var/data/categories
                save_dir = os.path.join(BASE_UPLOAD_PATH, 'categories')
                os.makedirs(save_dir, exist_ok=True)
                
                file.save(os.path.join(save_dir, filename))
                image_db_path = f'categories/{filename}'
        
        parent_id = int(parent_id) if parent_id else None
            
        new_cat = Category(name=name, parent_id=parent_id, image_url=image_db_path, model_years=model_years)
        
        db.session.add(new_cat)
        db.session.commit()
        
        flash(_('msg_cat_created'))
        return redirect(url_for('admin.dashboard')) 
        
    return render_template('admin/category_form.html', categories=all_categories)

# --- 7. EDIT CATEGORY (Updated for Persistent Disk) ---
@admin_bp.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    all_categories = Category.query.filter(Category.id != id).all()

    if request.method == 'POST':
        category.name = request.form.get('name')
        parent_id = request.form.get('parent_id')
        category.parent_id = int(parent_id) if parent_id else None
        category.model_years = request.form.get('model_years')

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                
                # Save to /var/data/categories
                save_dir = os.path.join(BASE_UPLOAD_PATH, 'categories')
                os.makedirs(save_dir, exist_ok=True)
                
                file.save(os.path.join(save_dir, filename))
                category.image_url = f'categories/{filename}'

        db.session.commit()
        flash('Category updated successfully!')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/edit_category.html', category=category, categories=all_categories)

# --- 8. DELETE CATEGORY ---
@admin_bp.route('/category/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    try:
        db.session.delete(category)
        db.session.commit()
        flash(_('msg_cat_deleted'))
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}")
    return redirect(url_for('admin.dashboard'))

# --- 9. DEALS ---
@admin_bp.route('/deals', methods=['GET', 'POST'])
@login_required
@admin_required
def deals():
    categories = Category.query.all()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'clear':
            Product.query.update({Product.discount_percentage: 0})
            db.session.commit()
            flash(_('msg_deal_cleared'))
        elif action == 'apply':
            percentage = int(request.form.get('percentage'))
            target_type = request.form.get('target_type') 
            if target_type == 'all':
                Product.query.update({Product.discount_percentage: percentage})
            else:
                cat_id = int(target_type)
                Product.query.filter_by(category_id=cat_id).update({Product.discount_percentage: percentage})
            db.session.commit()
            flash(_('msg_deal_applied'))
        return redirect(url_for('admin.deals'))
    return render_template('admin/deals.html', categories=categories)

# --- 10. VIEW ORDER ---
@admin_bp.route('/order/<int:order_id>')
@login_required
@admin_required
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)
from sqlalchemy import or_
# Make sure you import ProductSize and ProductColor if not already imported

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    now = datetime.utcnow()
    current_month = now.month
    current_year = now.year
    
    # --- 1. REVENUE (Includes 'Paid' AND 'COD') ---
    # We filter for orders that are NOT 'Unpaid' or 'Pending' (adjust based on your exact statuses)
    # Or specifically: status IN ['Paid', 'COD']
    valid_statuses = ['Paid', 'COD']
    
    monthly_revenue = db.session.query(func.sum(Order.total_amount))\
        .filter(extract('month', Order.created_at) == current_month)\
        .filter(extract('year', Order.created_at) == current_year)\
        .filter(Order.payment_status.in_(valid_statuses)).scalar() or 0

    last_month_date = now.replace(day=1) - timedelta(days=1)
    last_month_revenue = db.session.query(func.sum(Order.total_amount))\
        .filter(extract('month', Order.created_at) == last_month_date.month)\
        .filter(extract('year', Order.created_at) == last_month_date.year)\
        .filter(Order.payment_status.in_(valid_statuses)).scalar() or 0
    
    growth_percent = 0
    if last_month_revenue > 0:
        growth_percent = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100

    # --- 2. TOP PRODUCTS (Includes 'COD') ---
    top_products = db.session.query(
        Product.name, 
        Product.image_url,
        func.sum(OrderItem.quantity).label('total_sold'),
        func.sum(OrderItem.price * OrderItem.quantity).label('total_earned')
    ).join(OrderItem).join(Order).filter(Order.payment_status.in_(valid_statuses))\
     .group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    # --- 3. LOW STOCK (Check Variants Too) ---
    low_stock_alerts = []
    
    # A. Check Main Products (for simple products without variants)
    simple_low = Product.query.filter(Product.has_colors == False, Product.quantity < 5).all()
    for p in simple_low:
        low_stock_alerts.append({
            'id': p.id,
            'name': p.name,
            'variant': 'General Stock',
            'qty': p.quantity
        })

    # B. Check Specific Variants (Colors/Sizes)
    # We join ProductSize -> ProductColor -> Product to get the names
    variant_low = db.session.query(Product.id, Product.name, ProductColor.name, ProductSize.size_label, ProductSize.quantity)\
        .join(ProductColor, ProductColor.product_id == Product.id)\
        .join(ProductSize, ProductSize.color_id == ProductColor.id)\
        .filter(ProductSize.quantity < 5).all()

    for p_id, p_name, c_name, s_label, qty in variant_low:
        low_stock_alerts.append({
            'id': p_id,
            'name': p_name,
            'variant': f"{c_name} - {s_label}",
            'qty': qty
        })

    return render_template('admin/analytics.html', 
                           monthly_revenue=monthly_revenue,
                           growth_percent=growth_percent,
                           top_products=top_products,
                           low_stock=low_stock_alerts)

import requests
from app.models import Product





from flask import Blueprint, request, jsonify
from app.models import Product, db

# If adding to main.py, use main_bp. If admin.py, use admin_bp
# Let's assume you put it in main.py so it's accessible publicly
main_bp = Blueprint('main', __name__) 

@main_bp.route('/api/loyverse/webhook', methods=['POST'])
def loyverse_webhook():
    """
    Receives inventory updates from Loyverse automatically.
    """
    data = request.json
    
    # Loyverse sends a list of events. We only care about inventory updates.
    events = data.get('events', [])
    
    updated_count = 0
    
    for event in events:
        # Check if this is an inventory update event
        if event.get('type') == 'INVENTORY_LEVEL_UPDATED':
            payload = event.get('data', {})
            variant_id = payload.get('variant_id')
            new_stock = payload.get('in_stock')
            
            if variant_id and new_stock is not None:
                # Find product by the ID we saved in Step 2
                product = Product.query.filter_by(loyverse_id=variant_id).first()
                
                if product:
                    product.quantity = int(float(new_stock))
                    updated_count += 1

    if updated_count > 0:
        db.session.commit()
        print(f"⚡ Webhook: Updated stock for {updated_count} items.")
        return jsonify({'status': 'success', 'updated': updated_count}), 200
    
    return jsonify({'status': 'ignored'}), 200


@admin_bp.route('/sync_loyverse_stock')
@login_required
@admin_required
def sync_loyverse_stock():
    LOYVERSE_TOKEN = os.environ.get('LOYVERSE_TOKEN') 
    HEADERS = {"Authorization": f"Bearer {LOYVERSE_TOKEN}", "Content-Type": "application/json"}
    BASE_URL = "https://api.loyverse.com/v1.0"

    try:
        cursor = None
        created_count = 0
        updated_count = 0
        
        # --- PHASE 1: FETCH ITEMS & PRICES ---
        while True:
            resp = requests.get(f"{BASE_URL}/items?limit=250&cursor={cursor or ''}", headers=HEADERS)
            data = resp.json()
            
            for item in data.get('items', []):
                name = item.get('item_name')
                
                # Check if product exists
                product = Product.query.filter_by(name=name).first()
                
                # GET PRICE & SKU (With Safety Fix)
                price = 0.0
                variant_id = None
                variants = item.get('variants', [])
                
                if variants:
                    v = variants[0]
                    variant_id = v.get('variant_id')
                    
                    # SAFETY FIX: Use (value or 0) to handle None/null values
                    if v.get('stores'):
                        # Check store price, fallback to 0 if None
                        raw_price = v['stores'][0].get('price')
                        price = float(raw_price or 0)
                    else:
                        # Check default price, fallback to 0 if None
                        raw_price = v.get('default_price')
                        price = float(raw_price or 0)
                
                if not product:
                    # CREATE NEW PRODUCT
                    product = Product(
                        name=name,
                        price=price,
                        description=item.get('description', ''),
                        # Only use image if it exists
                        image_url=item.get('image_url') or '', 
                        quantity=0, 
                        label="New",
                        loyverse_id=variant_id
                    )
                    db.session.add(product)
                    created_count += 1
                else:
                    # LINK EXISTING PRODUCT
                    if not product.loyverse_id and variant_id:
                        product.loyverse_id = variant_id
                        
                    # Optional: Update price if you want to sync prices too
                    # product.price = price 
                    
            cursor = data.get('cursor')
            if not cursor: break
            
        db.session.commit() # Save items before syncing stock

        # --- PHASE 2: SYNC STOCK NUMBERS ---
        stock_totals = {}
        cursor = None
        while True:
            resp = requests.get(f"{BASE_URL}/inventory?limit=250&cursor={cursor or ''}", headers=HEADERS)
            data = resp.json()
            
            for record in data.get('inventory_levels', []):
                vid = record.get('variant_id')
                
                # SAFETY FIX: Handle None in stock levels
                raw_qty = record.get('in_stock')
                qty = float(raw_qty or 0)
                
                stock_totals[vid] = stock_totals.get(vid, 0) + qty
                
            cursor = data.get('cursor')
            if not cursor: break

        # Update Database with Stock Totals
        for vid, total_qty in stock_totals.items():
            product = Product.query.filter_by(loyverse_id=vid).first()
            if product:
                product.quantity = int(total_qty)
                updated_count += 1
        
        db.session.commit()
        
        msg = f"Sync Complete! Created {created_count} new products. Updated stock for {updated_count} items."
        flash(msg, "success")

    except Exception as e:
        # Print error to console for debugging
        print(f"SYNC ERROR: {e}")
        flash(f"Sync Error: {str(e)}", "error")

    return redirect(url_for('admin.dashboard'))