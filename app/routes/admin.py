import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.utils import secure_filename
from sqlalchemy import func, extract
from datetime import datetime, timedelta

from app.models import db, Product, Category, Order, User, Extra, OrderItem
from app.translations import dictionary

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
    order_count = Order.query.filter_by(payment_status='Paid').count()
    
    # Total Revenue (Paid orders only)
    total_revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(payment_status='Paid').scalar() or 0

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    products = Product.query.all()
    all_categories = Category.query.all()

    search_query = request.args.get('q')
    if search_query:
        # Filter by name (case-insensitive)
        products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()
    else:
        # Show all if no search
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

# --- 4. MANAGE PRODUCT (Updated for Persistent Disk) ---
@admin_bp.route('/product/new', defaults={'product_id': None}, methods=['GET', 'POST'])
@admin_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_product(product_id):
    product = Product.query.get_or_404(product_id) if product_id else Product()
    
    if request.method == 'POST':
        # --- A. Basic Info ---
        product.name = request.form.get('name')
        product.price = float(request.form.get('price'))
        cat_id = request.form.get('category_id')
        product.label = request.form.get('label')
        product.category_id = int(cat_id) if cat_id else None
        product.description = request.form.get('description')
        product.is_juice = True if request.form.get('is_juice') else False
        
        if product.is_juice:
            product.juice_flavors = request.form.get('juice_flavors')
            product.juice_nicotine = request.form.get('juice_nicotine') # <--- Add this line
        else:
            product.juice_flavors = None
            product.juice_nicotine = None

        db.session.add(product)
        # --- B. Image Upload (PERSISTENT STORAGE) ---
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                
                # 1. Define save directory (e.g., /var/data/products)
                save_dir = os.path.join(BASE_UPLOAD_PATH, 'products')
                os.makedirs(save_dir, exist_ok=True)
                
                # 2. Save the file
                file.save(os.path.join(save_dir, filename))
                
                # 3. Store relative path in DB
                product.image_url = f'products/{filename}'

        # --- C. Dynamic Options (Sizes) ---
        product.has_sizes = True if request.form.get('enable_sizes') else False
        product.available_sizes = request.form.get('sizes_input') if product.has_sizes else None

        # --- D. Dynamic Options (Colors) ---
        product.has_colors = True if request.form.get('enable_colors') else False
        if product.has_colors:
            c_names = request.form.getlist('color_name[]')
            c_codes = request.form.getlist('color_code[]')
            combined = []
            for n, c in zip(c_names, c_codes):
                if n.strip():
                    combined.append(f"{n.strip()}|{c.strip()}")
            product.available_colors = ",".join(combined)
        else:
            product.available_colors = None

        db.session.add(product)
        db.session.commit()

        # --- E. Extras ---
        Extra.query.filter_by(product_id=product.id).delete()
        ex_names = request.form.getlist('extra_name[]')
        ex_prices = request.form.getlist('extra_price[]')
        
        for n, p in zip(ex_names, ex_prices):
            if n.strip():
                new_extra = Extra(name=n, price=float(p), product_id=product.id)
                db.session.add(new_extra)

        qty = request.form.get('quantity')
        product.quantity = int(qty) if qty else 1
        
        db.session.commit()
        
        flash("Product saved successfully!", "success")
        return redirect(url_for('admin.dashboard'))

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

# --- 11. ANALYTICS ---
@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    now = datetime.utcnow()
    current_month = now.month
    current_year = now.year
    
    monthly_revenue = db.session.query(func.sum(Order.total_amount))\
        .filter(extract('month', Order.created_at) == current_month)\
        .filter(extract('year', Order.created_at) == current_year)\
        .filter(Order.payment_status == 'Paid').scalar() or 0

    last_month_date = now.replace(day=1) - timedelta(days=1)
    last_month_revenue = db.session.query(func.sum(Order.total_amount))\
        .filter(extract('month', Order.created_at) == last_month_date.month)\
        .filter(extract('year', Order.created_at) == last_month_date.year)\
        .filter(Order.payment_status == 'Paid').scalar() or 0
    
    growth_percent = 0
    if last_month_revenue > 0:
        growth_percent = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100

    top_products = db.session.query(
        Product.name, 
        Product.image_url,
        func.sum(OrderItem.quantity).label('total_sold'),
        func.sum(OrderItem.price * OrderItem.quantity).label('total_earned')
    ).join(OrderItem).join(Order).filter(Order.payment_status == 'Paid')\
     .group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    low_stock = Product.query.filter(Product.quantity < 5).all()

    return render_template('admin/analytics.html', 
                           monthly_revenue=monthly_revenue,
                           growth_percent=growth_percent,
                           top_products=top_products,
                           low_stock=low_stock)


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