import requests
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

    # 2. Build the Payload (Strict Format Required)
    payload = {
        "amount": round(total_amount, 3),  # Ensure decimal precision
        "currency": currency,
        "threeDSecure": True,
        "save_card": False,
        "description": f"Order #{order_id}",
        "statement_descriptor": "Sample Store",
        
        # Metadata allows you to pass custom data back
        "metadata": {
            "order_id": order_id
        },
        
        # Customer Details
        "customer": {
            "first_name": customer_info.get('first_name', 'Guest'),
            "last_name": customer_info.get('last_name', 'User'),
            "email": customer_info.get('email'),
            "phone": {
                "country_code": customer_info['phone'].get('country_code', '973'),
                "number": customer_info['phone'].get('number')
            }
        },
        
        # Source is required (src_all = allow all cards/Apple Pay)
        "source": {"id": "src_all"},
        
        # REDIRECT URL (Must be Absolute URL with https://)
        "redirect": {
            "url": url_for('main.order_success', order_id=order_id, _external=True)
        }
    }

    # 3. Send Request & Debug
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        # PRINT ERROR TO CONSOLE IF IT FAILS
        if response.status_code != 200:
            print(f"\n🔴 TAP API ERROR: {data}\n")
            return None
            
        return data

    except Exception as e:
        print(f"🔴 CONNECTION ERROR: {e}")
        return None