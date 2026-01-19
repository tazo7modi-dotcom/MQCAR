import requests
import sys # Needed to force logs to appear
from flask import current_app, url_for

def create_tap_charge(total_amount, currency, customer_info, order_id):
    """
    Sends a request to Tap Payment API (V2) to generate a payment link.
    """
    url = "https://api.tap.company/v2/charges"
    
    # 1. Prepare Authorization
    headers = {
        "Authorization": f"Bearer {current_app.config['TAP_SECRET_KEY']}",
        "Content-Type": "application/json"
    }

    # --- FIX 1: FORCE HTTPS FOR REDIRECT URL ---
    # Tap rejects 'http' links in production. We must ensure it starts with 'https'.
    raw_url = url_for('main.order_success', order_id=order_id, _external=True)
    if raw_url.startswith("http://"):
        redirect_url = raw_url.replace("http://", "https://", 1)
    else:
        redirect_url = raw_url
    # -------------------------------------------

    # --- FIX 2: CLEAN PHONE NUMBER ---
    # Ensure country code has no '+' sign and everything is stripped of spaces
    country_code = customer_info['phone'].get('country_code', '973').replace('+', '').strip()
    phone_number = customer_info['phone'].get('number', '').strip()
    # ---------------------------------

    # 2. Build the Payload
    payload = {
        "amount": round(total_amount, 3),
        "currency": currency,
        "threeDSecure": True,
        "save_card": False,
        "description": f"Order #{order_id}",
        "statement_descriptor": "Store",
        
        "metadata": {
            "order_id": order_id
        },
        
        "customer": {
            "first_name": customer_info.get('first_name', 'Guest'),
            "last_name": customer_info.get('last_name', 'User'),
            "email": customer_info.get('email'),
            "phone": {
                "country_code": country_code,
                "number": phone_number
            }
        },
        
        "source": {"id": "src_all"},
        
        "redirect": {
            "url": redirect_url
        }
    }

    # 3. Send Request & Debug
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        # --- FIX 3: FORCE LOGGING TO CONSOLE ---
        print(f"\n🚀 TAP REQUEST SENT:", file=sys.stdout)
        print(f"URL: {redirect_url}", file=sys.stdout)
        print(f"STATUS: {response.status_code}", file=sys.stdout)
        print(f"RESPONSE: {data}", file=sys.stdout)
        sys.stdout.flush() # Forces the log to appear immediately in Coolify
        # ---------------------------------------
        
        if response.status_code != 200:
            return None
            
        return data

    except Exception as e:
        print(f"🔴 CONNECTION ERROR: {e}", file=sys.stdout)
        sys.stdout.flush()
        return None