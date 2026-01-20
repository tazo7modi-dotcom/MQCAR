from flask import render_template, current_app
from flask_mail import Message
from app import mail
from threading import Thread

def send_async_email(app, msg):
    """Sends email in background to not slow down the checkout"""
    with app.app_context():
        mail.send(msg)

def send_order_receipt(order):
    """Generates the receipt and sends it"""
    try:
        subject = f"تأكيد طلب #{order.id} - Dropi"
        
     
        msg = Message(
            subject=subject,
            recipients=[order.shipping_details.split('Email: ')[1]] # Extract email safely
        )
        
        # Render HTML template (See Step 6)
        msg.html = render_template('email/receipt.html', order=order)
        
        # Send in background (Threading)
        # We pass 'current_app._get_current_object()' to allow the thread to access config
        Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
        print(f"📧 هذا رصيد تأكيداً على طلبك #{order.id}")
        
    except Exception as e:
        print(f"🔴 Email Failed: {e}")