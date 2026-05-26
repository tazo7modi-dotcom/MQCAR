from flask import render_template, current_app
from flask_mail import Message
from app import mail
from threading import Thread
import os


def send_async_emails(app, messages):
    """
    Sends a LIST of emails in the background.
    Doing it in one batch is more efficient than opening two threads.
    """
    with app.app_context():
        for msg in messages:
            try:
                print(f"📨 SENDING EMAIL: {msg.subject} -> {msg.recipients}")
                mail.send(msg)
            except Exception as e:
                print(f"🔴 EMAIL ERROR for {msg.recipients}: {e}")

def send_order_receipt(order):
    """Generates the customer receipt AND the admin notification"""
    try:
        messages_to_send = []

        # ==========================================
        # 1. PREPARE CUSTOMER EMAIL
        # ==========================================
        recipient_email = None
        
        # Robust extraction logic
        if "Email: " in order.shipping_details:
            recipient_email = order.shipping_details.split('Email: ')[1].strip()
        
        if not recipient_email and order.user_id and order.user.email:
            recipient_email = order.user.email

        if recipient_email and '@' in recipient_email:
            receipt_subject = current_app.config['EMAIL_SETTINGS']['receipt_subject'].format(
                order_id=order.id,
                store_name=current_app.config['STORE']['name'],
                amount=order.total_amount,
                currency=current_app.config['CURRENCY_RATES']['BHD']['symbol'],
                status=order.payment_status,
            )
            msg_customer = Message(
                subject=receipt_subject,
                recipients=[recipient_email]
            )
            msg_customer.html = render_template('email/receipt.html', order=order)
            messages_to_send.append(msg_customer)
        else:
            print(f"⚠️ No customer email found for Order #{order.id} (Skipping customer receipt)")

        # ==========================================
        # 2. PREPARE ADMIN NOTIFICATION (To You)
        # ==========================================
        # Make the subject informative so you see the value immediately on your phone
        currency_symbol = current_app.config['CURRENCY_RATES']['BHD']['symbol']
        admin_subject = current_app.config['EMAIL_SETTINGS']['admin_subject'].format(
            order_id=order.id,
            store_name=current_app.config['STORE']['name'],
            amount=order.total_amount,
            currency=currency_symbol,
            status=order.payment_status,
        )
        
        admin_email = current_app.config['STORE'].get('admin_email')
        msg_admin = None
        if admin_email:
            msg_admin = Message(
                subject=admin_subject,
                recipients=[admin_email]
            )
        
        # You can reuse the receipt template, or make a simple body
        if msg_admin:
            msg_admin.body = f"""
        New Order Received!
        -------------------
        Order ID: {order.id}
        Amount: {order.total_amount} {currency_symbol}
        Status: {order.payment_status}
        Customer: {order.full_name}
        Phone: {order.phone}
        
        Items:
        """
            # Add item list to admin text email
            for item in order.items:
                msg_admin.body += f"\n- {item.product.name} (x{item.quantity})"
                if item.size:
                    msg_admin.body += f" [{item.size}]"

            messages_to_send.append(msg_admin)
        # ==========================================
        # 3. SEND BOTH IN BACKGROUND
        # ==========================================
        if messages_to_send:
            Thread(
                target=send_async_emails, 
                args=(current_app._get_current_object(), messages_to_send)
            ).start()
        
    except Exception as e:
        print(f"🔴 MAIN EMAIL LOGIC FAILED: {e}")
