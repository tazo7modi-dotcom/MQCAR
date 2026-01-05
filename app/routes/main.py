from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from app.models import Product, Category, Cart, CartItem, Order, OrderItem, Extra, Address
from app.extensions import db
import requests
from sqlalchemy import or_

# FIX: Import both functions from payment.py (since we deleted utils.py)
from app.payment import get_user_currency, create_tap_charge

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    products = Product.query.limit(8).all()
    categories = Category.query.filter(Category.parent_id == None).all()
    uncategorized = Product.query.filter(Product.category_id == None).all()
    return render_template("main/home.html", products=products, categories=categories, uncategorized=uncategorized)

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('main/product.html', product=product)

@main_bp.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    # 1. Get Form Data
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    size = request.form.get('selected_size')
    color = request.form.get('color')
    
    # Get Juice Options
    nicotine = request.form.get('nicotine')
    juice_flavor = request.form.get('juice_flavor')

    # 2. Get Product & Price
    product = Product.query.get_or_404(product_id)
    final_price = product.get_price()
    
    extras_description = []

    # 3. Handle Juice Mode (Free Options)
    if nicotine:
        extras_description.append(f"Nicotine: {nicotine}")
    if juice_flavor:
        extras_description.append(f"Flavor: {juice_flavor}")

    # 4. Handle Paid Extras
    selected_extra_ids = request.form.getlist('extras')
    for extra_id in selected_extra_ids:
        extra = Extra.query.get(extra_id)
        if extra:
            final_price += extra.price
            extras_description.append(f"{extra.name} (+{extra.price})")
    
    # Create the description string (e.g. "Nicotine: 20mg | Flavor: Mango | Ice (+0.5)")
    extras_str = " | ".join(extras_description)

    # 5. Get or Create Cart
    cart = current_user.cart
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit() # Ensure cart has an ID

    # 6. Add Item to Cart
    # FIX: Use 'cart=cart' instead of 'cart_id=cart.id' to avoid SQL errors
    item = CartItem(
        cart=cart, 
        product_id=product.id,
        quantity=quantity,
        size=size,
        color=color,
        selected_extras=extras_str,
        unit_price=final_price 
    )
    
    db.session.add(item)
    db.session.commit()
    
    flash("Added to cart successfully!")
    return redirect(url_for('main.cart_page'))

@main_bp.route('/cart')
@login_required
def cart_page():
    cart = current_user.cart
    items = cart.cart_items if cart else []
    total = sum(item.unit_price * item.quantity for item in items)
    return render_template('main/cart.html', cart_items=items, total=total)

@main_bp.route('/remove_item/<int:item_id>')
@login_required
def remove_item(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('main.cart_page'))

@main_bp.route('/set_language/<lang_code>')
def set_language(lang_code):
    if lang_code in ['en', 'ar']:
        session['language'] = lang_code
    return redirect(request.referrer or url_for('main.home'))

# --- CHECKOUT ROUTE ---
@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = current_user.cart
    if not cart or not cart.cart_items:
        return redirect(url_for('main.cart_page'))

    items = cart.cart_items
    cart_total = sum(item.unit_price * item.quantity for item in items)
    
    addresses = current_user.addresses

    if request.method == 'POST':
        address_id = request.form.get('selected_address')
        final_addr = None
        
        # --- Address Logic ---
        if address_id:
            # Existing Address
            final_addr = Address.query.get(address_id)
            if not final_addr or final_addr.user_id != current_user.id:
                flash("Invalid address selected.", "error")
                return redirect(url_for('main.checkout'))
            
            try:
                phone_parts = final_addr.phone.split(' ', 1)
                code = phone_parts[0]  
                phone_clean = phone_parts[1].replace(" ", "") 
            except:
                code = ""
                phone_clean = final_addr.phone
                
        else:
            # New Address
            raw_phone = request.form.get('phone_number')
            code = request.form.get('phone_code')
            full_phone = f"{code} {raw_phone}"
            phone_clean = raw_phone

            new_addr = Address(
                user_id=current_user.id,
                full_name=request.form.get('full_name'),
                phone=full_phone,  
                street_address=request.form.get('street_address'),
                city=request.form.get('city'),
                country=request.form.get('country'),
                is_default=True
            )
            db.session.add(new_addr)
            db.session.commit()
            final_addr = new_addr

        # --- Shipping Logic ---
        country_check = final_addr.country.strip().lower()
        shipping_option = request.form.get('shipping_option', 'normal') 
        shipping_cost = 0.0

        if country_check == 'bahrain':
            if shipping_option == 'fast':
                shipping_cost = 3.0
            else:
                shipping_cost = 1.0 
        else:
            shipping_cost = 15.0 

        final_total_bhd = cart_total + shipping_cost
        shipping_string = f"{final_addr.full_name}, {final_addr.street_address}, {final_addr.city}, {final_addr.country}, {final_addr.phone}"

        # --- Create Order ---
        order = Order(
            user_id=current_user.id,
            total_amount=final_total_bhd,
            status='Pending',
            payment_status='Unpaid',
            shipping_details=shipping_string,
        )
        db.session.add(order)
        db.session.commit()

        # --- Add Items ---
        for cart_item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.unit_price,
                size=cart_item.size,
                color=cart_item.color,
                selected_extras=cart_item.selected_extras
            )
            db.session.add(order_item)
        db.session.commit()

        # --- Payment Preparation ---
        user_currency = get_user_currency()
        currency_data = current_app.config['CURRENCY_RATES'].get(user_currency)
        exchange_rate = currency_data['rate'] if currency_data else 1.0
        final_charge_amount = final_total_bhd * exchange_rate
        
        name_parts = final_addr.full_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else "Customer"

        customer_info = {
            'first_name': first_name,
            'last_name': last_name,
            'email': current_user.email,
            'phone': {
                'country_code': code,
                'number': phone_clean
            }
        }

        try:
            tap_response = create_tap_charge(
                total_amount=final_charge_amount,
                currency=user_currency, # Changed param name to match function
                customer_info=customer_info,
                order_id=order.id
            )
            
            if tap_response and 'transaction' in tap_response and 'url' in tap_response['transaction']:
                charge_id = tap_response.get('id')
                order.tap_charge_id = charge_id
                db.session.commit()
                return redirect(tap_response['transaction']['url'])
            else:
                flash("Payment Gateway Error: Could not generate link.", "error")
                return redirect(url_for('main.checkout'))
                
        except Exception as e:
            print(f"Payment Error: {e}")
            flash("Connection error with Payment Provider.", "error")
            return redirect(url_for('main.checkout'))

    return render_template('main/checkout.html', items=items, total=cart_total, addresses=addresses)
@main_bp.route('/payment_success')
@login_required
def payment_success():
    tap_id = request.args.get('tap_id') 
    
    if not tap_id:
        flash("Invalid payment identifier.", "error")
        return redirect(url_for('main.home'))

    order = Order.query.filter_by(tap_charge_id=tap_id).first()
    
    # Verify with Tap API
    url = f"https://api.tap.company/v2/charges/{tap_id}"
    headers = {
        "Authorization": f"Bearer {current_app.config['TAP_SECRET_KEY']}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
    except Exception:
        flash("Could not verify payment.", "error")
        return redirect(url_for('main.cart_page'))
    
    is_paid = False
    if data.get('status') == 'CAPTURED':
        is_paid = True
    
    if order and is_paid and order.payment_status == 'Unpaid':
        order.payment_status = 'Paid'
        
        # --- PREPARE LOYVERSE DATA ---
        loyverse_updates = []
        # You should preferably put this token in your config.py
        LOYVERSE_TOKEN = "YOUR_ACCESS_TOKEN_HERE" 
        
        # Deduct Inventory
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                # 1. Update Local Database
                if product.quantity >= item.quantity:
                    product.quantity -= item.quantity
                else:
                    product.quantity = 0 
                
                # 2. Check for Loyverse ID and Prepare Update
                if product.loyverse_id:
                    loyverse_updates.append({
                        "variant_id": product.loyverse_id,
                        "in_stock": float(product.quantity) # Send the NEW remaining amount
                    })
        
        # --- SEND TO LOYVERSE (Background Sync) ---
        if loyverse_updates:
            try:
                requests.post(
                    "https://api.loyverse.com/v1.0/inventory",
                    json={"inventory_levels": loyverse_updates},
                    headers={
                        "Authorization": f"Bearer {LOYVERSE_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    timeout=5 # Short timeout so user doesn't wait long
                )
                print(f"✅ Synced {len(loyverse_updates)} items to Loyverse.")
            except Exception as e:
                print(f"⚠️ Loyverse Sync Failed: {e}")

        # Clear Cart
        if current_user.cart:
             CartItem.query.filter_by(cart_id=current_user.cart.id).delete()
        
        db.session.commit()
        return render_template('main/success.html', order=order)

    elif order and order.payment_status == 'Paid':
        return render_template('main/success.html', order=order)
    else:
        flash("Payment failed or cancelled.", "error")
        return redirect(url_for('main.cart_page'))

@main_bp.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('main/account.html', user=current_user, orders=orders)

from werkzeug.security import check_password_hash

@main_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    
    if not check_password_hash(current_user.password_hash, old_password):
        flash("Incorrect old password.", "error")
        return redirect(url_for('main.account'))
    
    current_user.set_password(new_password)
    db.session.commit()
    flash("Password updated successfully!", "success")
    return redirect(url_for('main.account'))

@main_bp.route('/delete_address/<int:address_id>')
@login_required
def delete_address(address_id):
    address = Address.query.get_or_404(address_id)
    if address.user_id == current_user.id:
        db.session.delete(address)
        db.session.commit()
        flash("Address deleted.")
    return redirect(url_for('main.account'))

@main_bp.route('/category/<int:category_id>')
def category_view(category_id):
    category = Category.query.get_or_404(category_id)
    
    sort_option = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    query = Product.query.filter_by(category_id=category_id)

    if min_price and min_price.isdigit():
        query = query.filter(Product.price >= float(min_price))
    if max_price and max_price.isdigit():
        query = query.filter(Product.price <= float(max_price))

    if sort_option == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_option == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.id.desc())

    filtered_products = query.all()

    return render_template(
        'main/category_view.html', 
        category=category, 
        products=filtered_products, 
        current_sort=sort_option,
        min_price=min_price,
        max_price=max_price
    )

@main_bp.route('/collection/signature')
def signature_view():
    products = Product.query.filter(Product.category_id == None).all()
    return render_template('main/category_view.html', title="Signature Collection", products=products)

@main_bp.route('/set_currency/<code>')
def set_currency(code):
    if code in current_app.config['CURRENCY_RATES']:
        session['currency'] = code  
    return redirect(request.referrer or url_for('main.home'))

@main_bp.route('/help')
def help_page():
    return render_template('main/help.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash("Message sent successfully! We will get back to you soon.", "success")
        return redirect(url_for('main.contact'))
    return render_template('main/contact.html')

@main_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    label_filter = request.args.get('label')
    sort_option = request.args.get('sort', 'newest')
    
    products_query = Product.query.outerjoin(Category)

    if query:
        if query.lower().startswith('ref'):
            try:
                prod_id = int(query[3:])
                products_query = products_query.filter(Product.id == prod_id)
            except ValueError:
                products_query = products_query.filter(Product.id == -1)
        else:
            search_term = f"%{query}%"
            products_query = products_query.filter(
                or_(
                    Product.name.ilike(search_term),
                    Category.name.ilike(search_term)
                )
            )

    if label_filter and label_filter != 'all':
        products_query = products_query.filter(Product.label == label_filter)

    if sort_option == 'price_asc':
        products_query = products_query.order_by(Product.price.asc())
    elif sort_option == 'price_desc':
        products_query = products_query.order_by(Product.price.desc())
    else: 
        products_query = products_query.order_by(Product.id.desc())

    results = products_query.all()
    
    existing_labels = db.session.query(Product.label).distinct().filter(Product.label != None).all()
    labels_list = [l[0] for l in existing_labels]

    return render_template(
        'main/search_results.html', 
        products=results, 
        query=query, 
        labels=labels_list,
        current_label=label_filter,
        current_sort=sort_option
    )