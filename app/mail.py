from flask import render_template, current_app
from flask_mail import Message
from app import mail
from threading import Thread

def send_async_email(app, msg):
    """Sends email in background."""
    with app.app_context():
        try:
            # DEBUG: Print connection details to logs
            print(f"📨 ATTEMPTING SEND -> Host: {app.config.get('MAIL_SERVER')} | Port: {app.config.get('MAIL_PORT')} | User: {app.config.get('MAIL_USERNAME')}")
            
            mail.send(msg)
            print("✅ Email sent successfully!")
        except Exception as e:
            print(f"🔴 ASYNC EMAIL ERROR: {e}")

def send_order_receipt(order):
    """Generates the receipt and sends it"""
    try:
        # --- 1. ROBUST EMAIL EXTRACTION ---
        # Try to find the email safely, fallback to a default if missing
        recipient_email = None
        
        # Method A: Try to find 'Email:' in the string
        if "Email: " in order.shipping_details:
            parts = order.shipping_details.split('Email: ')
            if len(parts) > 1:
                # Take the part after 'Email: ' and clean whitespace
                recipient_email = parts[1].strip()
        
        # Method B: Fallback - If extraction failed, is there a user attached?
        if not recipient_email and order.user_id:
            # You might need to import User model or fetch it
            # Assuming order.user is available via relationship
            if order.user and order.user.email:
                recipient_email = order.user.email

        # If we still don't have an email, we can't send.
        if not recipient_email or '@' not in recipient_email:
            print(f"⚠️ SKIPPING EMAIL: Could not find valid email address in order #{order.id}")
            return

        print(f"📝 Preparing receipt for Order #{order.id} to {recipient_email}")

        # --- 2. PREPARE MESSAGE ---
        subject = f"Order Confirmation #{order.id} - Dropi"
        
        msg = Message(
            subject=subject,
            recipients=[recipient_email]
        )
        
        # Render HTML template
        msg.html = render_template('email/receipt.html', order=order)
        
        # --- 3. SEND ---
        # We pass the app context so the thread knows the config
        Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
        
    except Exception as e:
        print(f"🔴 MAIN EMAIL LOGIC FAILED: {e}")