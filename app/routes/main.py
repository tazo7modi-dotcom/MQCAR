from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from flask_login import login_required, current_user
from app.models import Product, Category, Cart, CartItem, Order, OrderItem, Extra, Address,Review,ProductColor,ProductSize
from app.extensions import db
import requests
from sqlalchemy import or_
from flask_mail import Mail

# FIX: Import both functions from payment.py (since we deleted utils.py)
from app.payment import get_user_currency, create_tap_charge

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    products = Product.query.limit(8).all()
    categories = Category.query.filter(Category.parent_id == None).all()
    uncategorized = Product.query.filter(Product.category_id == None).all()
    reviews = Review.query.order_by(Review.created_at.desc()).limit(10).all()
 
    return render_template("main/home.html", products=products, categories=categories, uncategorized=uncategorized,reviews=reviews)


@main_bp.route('/submit-review', methods=['POST'])
def submit_review():
    name = request.form.get('name')
    comment = request.form.get('comment')
    rating = request.form.get('rating')

    if name and comment and rating:
        new_review = Review(name=name, comment=comment, rating=int(rating))
        db.session.add(new_review)
        db.session.commit()
        flash('Thank you for your review!', 'success')
    else:
        flash('Please fill in all fields.', 'error')

    return redirect(url_for('main.home'))




@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('main/product.html', product=product)



import uuid # Import this at the top of your file if not present
@main_bp.route('/add_to_cart', methods=['POST'])
# 1. REMOVED @login_required to allow Guests
def add_to_cart():
    # --- A. COMMON LOGIC (Get Data) ---
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    # NOTE: Your HTML sends 'color_id', so we grab that to find the variant
    color_id = request.form.get('color_id') 
    size_label = request.form.get('selected_size') # This is the size name (e.g. "500ml")
    
    # Get Juice Options
    nicotine = request.form.get('nicotine')
    juice_flavor = request.form.get('juice_flavor')

    # Get Product
    product = Product.query.get_or_404(product_id)
    
    # Start with the base product price
    final_price = product.get_price()
    
    # Get Color Name (for display in cart)
    color_name = None
    if color_id:
        color_obj = ProductColor.query.get(color_id)
        if color_obj:
            color_name = color_obj.name

            # --- INSERTED: SIZE PRICE CHECK ---
            # We look inside the selected color to find the specific size and its price
            if size_label:
                for s in color_obj.sizes:
                    if s.size_label == size_label:
                        # If this size has a specific price, OVERRIDE the base price
                        if s.price is not None:
                            final_price = s.price
                        break
            # ----------------------------------

    extras_description = []

    # Handle Juice Mode (Free Options)
    if nicotine:
        extras_description.append(f"Nicotine: {nicotine}")
    if juice_flavor:
        extras_description.append(f"Flavor: {juice_flavor}")

    # Handle Paid Extras
    selected_extra_ids = request.form.getlist('extras')
    for extra_id in selected_extra_ids:
        extra = Extra.query.get(extra_id)
        if extra:
            final_price += extra.price
            extras_description.append(f"{extra.name} (+{extra.price})")
    
    # Create the description string
    extras_str = " | ".join(extras_description)

    # --- B. BRANCHING LOGIC ---
    
    # 1. IF LOGGED IN: Save to Database
    if current_user.is_authenticated:
        cart = current_user.cart
        if not cart:
            cart = Cart(user_id=current_user.id)
            db.session.add(cart)
            db.session.commit() 

        item = CartItem(
            cart=cart, 
            product_id=product.id,
            quantity=quantity,
            size=size_label,
            color=color_name, # Save the name we found above
            selected_extras=extras_str,
            unit_price=final_price # <--- This is now correct!
        )
        db.session.add(item)
        db.session.commit()

    # 2. IF GUEST: Save to Session
    else:
        if 'cart' not in session:
            session['cart'] = []
        
        # Create a dictionary (JSON compatible)
        cart_item = {
            'uuid': str(uuid.uuid4()), # Generate ID so we can delete it later
            'product_id': product.id,
            'quantity': quantity,
            'size': size_label,
            'color': color_name, # Save the name
            'selected_extras': extras_str,
            'unit_price': float(final_price) # Make sure it's a number
        }
        
        # Save back to session
        current_cart = session['cart']
        current_cart.append(cart_item)
        session['cart'] = current_cart
    
    flash("Added to cart successfully!")
    # --- CALCULATE NEW CART COUNT ---
    if current_user.is_authenticated:
        # Re-query the cart to get the new count
        new_count = len(current_user.cart.cart_items)
    else:
        new_count = len(session.get('cart', []))

    # --- RETURN JSON INSTEAD OF REDIRECT ---
    return jsonify({
        'status': 'success', 
        'message': 'Added to cart successfully!',
        'cart_count': new_count
    })

@main_bp.route('/cart')
# 1. REMOVED @login_required
def cart_page():
    items = []
    total = 0.0

    if current_user.is_authenticated:
        # --- LOGGED IN: Get from Database ---
        cart = current_user.cart
        if cart:
            items = cart.cart_items
            total = sum(item.unit_price * item.quantity for item in items)
            
    else:
        # --- GUEST: Get from Session ---
        session_cart = session.get('cart', [])
        

        for s_item in session_cart:
            product = Product.query.get(s_item['product_id'])
            if product:

                fake_item = type('CartItem', (object,), {
                    'id': s_item['uuid'], 
                    'product': product,   
                    'quantity': s_item['quantity'],
                    'unit_price': s_item['unit_price'],
                    'size': s_item['size'],
                    'color': s_item['color'],
                    'selected_extras': s_item['selected_extras']
                })
                
                items.append(fake_item)
                total += (fake_item.unit_price * fake_item.quantity)

    return render_template('main/cart.html', cart_items=items, total=total)




@main_bp.route('/remove_item/<item_id>') # Changed from <int:item_id> to <item_id> to accept Strings
# @login_required <-- REMOVED
def remove_item(item_id):
    
    # --- LOGIC FOR LOGGED IN USERS (Database) ---
    if current_user.is_authenticated:
        try:
            # We must try to convert the string 'item_id' to an integer
            db_id = int(item_id)
            
            item = CartItem.query.get_or_404(db_id)
            if item.cart.user_id == current_user.id:
                db.session.delete(item)
                db.session.commit()
        except ValueError:
            # If item_id is not a number (e.g. it's a UUID string), ignore it
            pass

    # --- LOGIC FOR GUESTS (Session) ---
    else:
        if 'cart' in session:
            cart_list = session['cart']
            
            # Create a new list keeping everything EXCEPT the item with this UUID
            # This effectively "deletes" the item
            updated_list = [i for i in cart_list if i.get('uuid') != item_id]
            
            # Save the updated list back to the session
            session['cart'] = updated_list

    return redirect(url_for('main.cart_page'))





@main_bp.route('/set_language/<lang_code>')
def set_language(lang_code):
    if lang_code in ['en', 'ar']:
        session['language'] = lang_code
    return redirect(request.referrer or url_for('main.home'))




# --- HELPER FUNCTION (Place this above checkout) ---
def get_cart_data():
    """Returns (list_of_items, total_price) for both Guests and Users"""
    items = []
    total = 0.0

    if current_user.is_authenticated:
        # DB Cart
        cart = current_user.cart
        if cart:
            items = cart.cart_items
            total = sum(item.unit_price * item.quantity for item in items)
    else:
        # Session Cart
        session_cart = session.get('cart', [])
        for s_item in session_cart:
            product = Product.query.get(s_item['product_id'])
            if product:
                # Create mimic object
                fake_item = type('CartItem', (object,), {
                    'product_id': product.id,
                    'product': product,
                    'quantity': s_item['quantity'],
                    'unit_price': s_item['unit_price'],
                    'size': s_item['size'],
                    'color': s_item['color'],
                    'selected_extras': s_item['selected_extras']
                })
                items.append(fake_item)
                total += (fake_item.unit_price * fake_item.quantity)
    
    return items, total

from app.utils import create_tap_charge
from app.mail import send_order_receipt

@main_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    items, cart_total = get_cart_data()
    
    if not items:
        return redirect(url_for('main.cart_page'))

    addresses = current_user.addresses if current_user.is_authenticated else []

    if request.method == 'POST':
        # --- 1. Address & Guest Logic ---
        address_id = request.form.get('selected_address')
        final_addr = None
        
        if address_id and current_user.is_authenticated:
            final_addr = Address.query.get(address_id)
            if not final_addr or final_addr.user_id != current_user.id:
                flash("Invalid address selected.", "error")
                return redirect(url_for('main.checkout'))
            try:
                phone_parts = final_addr.phone.split(' ', 1)
                code = phone_parts[0]  
                phone_clean = phone_parts[1].replace(" ", "") 
            except:
                code = "+973" 
                phone_clean = final_addr.phone
        else:
            raw_phone = request.form.get('phone_number')
            code = request.form.get('phone_code')
            full_phone = f"{code} {raw_phone}"
            phone_clean = raw_phone
            
            if current_user.is_authenticated:
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
            else:
                final_addr = type('Address', (object,), {
                    'full_name': request.form.get('full_name'),
                    'phone': full_phone,
                    'street_address': request.form.get('street_address'),
                    'city': request.form.get('city'),
                    'country': request.form.get('country')
                })

        # --- 2. Shipping Logic ---
        country_check = final_addr.country.strip().lower()
        shipping_option = request.form.get('shipping_option', 'normal') 
        shipping_cost = 0.0

        if country_check == 'bahrain':
            shipping_cost = 0.0 if shipping_option == 'fast' else 0 
        else:
            shipping_cost = 0.0 

        final_total_bhd = cart_total + shipping_cost
        customer_email = current_user.email if current_user.is_authenticated else request.form.get('email', 'guest@example.com')
        shipping_string = f"{final_addr.full_name}, {final_addr.street_address}, {final_addr.city}, {final_addr.country}, {final_addr.phone}, Email: {customer_email}"

        # --- 3. Create Order ---
        order_user_id = current_user.id if current_user.is_authenticated else None
        
        order = Order(
            user_id=order_user_id,
            total_amount=final_total_bhd,
            status='Pending',
            payment_status='Unpaid', 
            full_name=final_addr.full_name,
            phone=final_addr.phone,
            street_address=final_addr.street_address,
            city=final_addr.city,
            country=final_addr.country,
            shipping_details=shipping_string,
        )
        db.session.add(order)
        db.session.commit()

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

        # ======================================================
        #  4. PROCESS PAYMENT & INVENTORY
        # ======================================================
        payment_method = request.form.get('payment_method') 
        if payment_method == 'cod':
            # --- OPTION A: CASH ON DELIVERY ---
            order.payment_status = 'COD'
            
            # --- FIXED INVENTORY LOGIC (SIZE BASED) ---
            try:
                for cart_item in items:
                    product = Product.query.get(cart_item.product_id)
                    
                    # 1. Check if this is a variant product (Has Color & Size)
                    if cart_item.color and cart_item.size:
                        
                        # Find the Color first
                        color_obj = ProductColor.query.filter_by(
                            product_id=product.id, 
                            name=cart_item.color
                        ).first()
                        
                        if color_obj:
                            # Find the Size inside that Color
                            size_obj = ProductSize.query.filter_by(
                                color_id=color_obj.id, 
                                size_label=cart_item.size
                            ).first()
                            
                            if size_obj:
                                # Check Stock
                                if size_obj.quantity < cart_item.quantity:
                                    raise Exception(f"Out of stock: {product.name} ({cart_item.size})")
                                
                                # DEDUCT SIZE QUANTITY
                                size_obj.quantity -= cart_item.quantity
                                
                                # CRITICAL: Also update the Main Product Total
                                # This ensures the homepage knows stock has dropped
                                product.quantity -= cart_item.quantity 
                                
                                db.session.add(size_obj)
                                db.session.add(product)
                            else:
                                raise Exception(f"Size database error for {product.name}")
                        else:
                            raise Exception(f"Color database error for {product.name}")
                            
                    # 2. Handle Simple Products (No variants)
                    else:
                        if product.quantity < cart_item.quantity:
                            raise Exception(f"Out of stock: {product.name}")
                        product.quantity -= cart_item.quantity
                        db.session.add(product)
                        
                # Commit the changes to DB
                db.session.commit()
                
                # Send Receipt (Optional)
                # send_order_receipt(order)
                
            except Exception as e:
                db.session.rollback()
                db.session.delete(order) # Delete order if failed
                db.session.commit()
                flash(str(e), "error")
                return redirect(url_for('main.cart_page'))

            # Clear Cart
            if current_user.is_authenticated:
                cart = Cart.query.filter_by(user_id=current_user.id).first()
                if cart:
                    CartItem.query.filter_by(cart_id=cart.id).delete()
            else:
                session.pop('cart', None) 
            
            db.session.commit()
            
            flash(f"Order placed! Please pay {final_total_bhd} BD upon delivery.", "success")
            return redirect(url_for('main.order_success', order_id=order.id))

        else:
            # --- OPTION B: ONLINE PAYMENT ---
            # NOTE: Do NOT deduct inventory here for Online Payment.
            # If you deduct here and the user cancels on the Tap page, you lose stock.
            # You must put the "Deduct Inventory Logic" inside your 'payment_success' route.
            
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
                'email': customer_email,
                'phone': {
                    'country_code': code,
                    'number': phone_clean
                }
            }

            try:
                tap_response = create_tap_charge(
                    total_amount=final_charge_amount,
                    currency=user_currency,
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



@main_bp.route('/order-success/<int:order_id>') 
def order_success(order_id):
    # 1. Find the order safely
    order = Order.query.get_or_404(order_id)
    
    # ---------------------------------------------------------
    # SCENARIO A: Cash on Delivery (COD) -> Just show Success
    # ---------------------------------------------------------
    if order.payment_status == 'COD':
        return render_template('main/success.html', order=order)

    # ---------------------------------------------------------
    # SCENARIO B: Already Paid -> Just show Success
    # ---------------------------------------------------------
    if order.payment_status == 'Paid':
        return render_template('main/success.html', order=order)

    # ---------------------------------------------------------
    # SCENARIO C: Online Payment Verification (Requires Tap ID)
    # ---------------------------------------------------------
    tap_id = request.args.get('tap_id') or order.tap_charge_id
    
    if not tap_id:
        flash("Order incomplete or payment failed.", "error")
        return redirect(url_for('main.cart_page'))

    # Verify with Tap API
    url = f"https://api.tap.company/v2/charges/{tap_id}"
    headers = {
        "Authorization": f"Bearer {current_app.config['TAP_SECRET_KEY']}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
    except Exception:
        flash("Connection error: Could not verify payment.", "error")
        return redirect(url_for('main.cart_page'))
    
    # Check if CAPTURED
    if data.get('status') == 'CAPTURED' and order.payment_status == 'Unpaid':
        order.payment_status = 'Paid'
        send_order_receipt(order)
        
        # --- 1. INVENTORY DEDUCTION (The Fix) ---
        try:
            for item in order.items:
                product = Product.query.get(item.product_id)
                
                if product:
                    # A. Handle Variant Products (Color + Size)
                    if item.color and item.size:
                        # Find the specific variant row
                        variant_size = ProductSize.query.join(ProductColor).filter(
                            ProductColor.product_id == product.id,
                            ProductColor.name == item.color,
                            ProductSize.size_label == item.size
                        ).first()
                        
                        if variant_size:
                            # Subtract from specific size
                            variant_size.quantity -= item.quantity
                            # Subtract from master product total
                            product.quantity -= item.quantity
                            
                    # B. Handle Simple Products
                    else:
                        product.quantity -= item.quantity

        except Exception as e:
            # Log the error, but don't stop the user since they already paid
            print(f"⚠️ Inventory Update Error for Order {order.id}: {e}")

        # --- 2. CLEAR CART ---
        if current_user.is_authenticated:
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            if cart:
                CartItem.query.filter_by(cart_id=cart.id).delete()
        else:
            session.pop('cart', None)
        
        # --- 3. SAVE EVERYTHING ---
        db.session.commit()
        
        return render_template('main/success.html', order=order)

    # If we got here, payment failed or wasn't captured
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
def help():
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




@main_bp.route('/about')
def about():
    return render_template('main/about.html')





@main_bp.route('/products/all')
def all_products_view():
    # 1. Create a "Fake" Category object 
    # This ensures your existing 'category_view.html' template works without errors
    # because it expects a variable named 'category' with a .name attribute.
    fake_category = type('Category', (object,), {'name': 'All Products', 'id': 0})

    # 2. Get Sorting and Filtering Parameters (Same as your category_view)
    sort_option = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    # 3. Start query with ALL products (No category filter)
    query = Product.query

    # 4. Apply Price Filters
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
        category=fake_category, 
        products=filtered_products, 
        current_sort=sort_option,
        min_price=min_price,
        max_price=max_price
    )