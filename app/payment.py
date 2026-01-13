import requests
from flask import current_app, url_for, session

def get_user_currency():
    """Helper to get user currency or default to BHD"""
    return session.get('currency', 'BHD')

def create_tap_charge(total_amount, currency, customer_info, order_id):
    url = "https://api.tap.company/v2/charges"
    
    headers = {
        "Authorization": f"Bearer {current_app.config['TAP_SECRET_KEY']}",
        "Content-Type": "application/json"
    }

   
    raw_code = str(customer_info['phone'].get('country_code', '973'))
    clean_code = raw_code.replace('+', '').strip()
    if not clean_code: clean_code = "973"

    clean_number = str(customer_info['phone'].get('number', '')).replace(' ', '')

  
    decimals = 3 if currency in ['BHD', 'KWD', 'OMR'] else 2
    rounded_amount = round(float(total_amount), decimals)

   
    redirect_url = url_for('main.order_success', _external=True)

    payload = {
        "amount": rounded_amount,
        "currency": currency,
        "threeDSecure": True,
        "save_card": False,
        "description": f"Order #{order_id}",
        "source": {
            "id": "src_all" 
        },
        "customer": {
            "first_name": customer_info.get('first_name', 'Guest'),
            "last_name": customer_info.get('last_name', 'Customer'),
            "email": customer_info.get('email', 'no-email@example.com'),
            "phone": {
                "country_code": clean_code, 
                "number": clean_number
            }
        },
        "redirect": {
            "url": redirect_url
        }
    }

    print(f"🚀 SENDING TO TAP: Amount={rounded_amount} {currency}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code != 200:
            print(f"⚠️ TAP API ERROR [{response.status_code}]: {response_data}")
            
        return response_data
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ NETWORK ERROR: {e}")
        return None