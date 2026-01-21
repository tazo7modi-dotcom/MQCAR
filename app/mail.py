from flask import render_template, current_app
from flask_mail import Message
from app import mail
from threading import Thread
import os

# --- CONFIG: PUT YOUR PRIVATE EMAIL HERE ---
ADMIN_NOTIFY_EMAIL = os.environ.get('ADMIN_MAIL') or 'tazo.7modi@gmail.com'

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
            msg_customer = Message(
                subject=f"Order Confirmation #{order.id} - Dropi",
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
        admin_subject = f"🔔 NEW ORDER #{order.id} | {order.total_amount} BD | {order.payment_status}"
        
        msg_admin = Message(
            subject=admin_subject,
            recipients=[ADMIN_NOTIFY_EMAIL]
        )
        
        # You can reuse the receipt template, or make a simple body
        msg_admin.body = f"""
        New Order Received!
        -------------------
        Order ID: {order.id}
        Amount: {order.total_amount} BD
        Status: {order.payment_status}
        Customer: {order.full_name}
        Phone: {order.phone}
        
        Items:
        """
        # Add item list to admin text email
        for item in order.items:
            msg_admin.body += f"\n- {item.product.name} (x{item.quantity})"
            if item.size: msg_admin.body += f" [{item.size}]"

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