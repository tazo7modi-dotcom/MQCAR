import requests
from flask import current_app
import json
import time

class ShippingService:
    def __init__(self):
        self.base_url = current_app.config['SHIPPING_BASE_URL']
        self.client_id = current_app.config['SHIPPING_CLIENT_ID']
        self.client_secret = current_app.config['SHIPPING_CLIENT_SECRET']
        self.customer_id = current_app.config['SHIPPING_CUSTOMER_ID']

    def _get_access_token(self):
        """
        Gets the Bearer Token. 
        Note: Verify the exact URL for the token endpoint with your provider.
        """
        url = f"{self.base_url}/api/v1/auth/token" 
        payload = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "grantType": "client_credentials" 
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json().get('accessToken')
        except Exception as e:
            print(f"Shipping Auth Error: {e}")
            return None

    def create_delivery_order(self, local_order, address_obj):
        token = self._get_access_token()
        if not token:
            return None

        url = f"{self.base_url}/api/v1/customer/order/pickup-delivery"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept-Language": "en"
        }

        # --- PREPARE DATA ---
        
        # 1. Timestamps (0 = Not Scheduled / ASAP)
        # If you wanted to schedule it for 1 hour later, you'd use milliseconds here.
        complete_after = 0
        complete_before = 0 

        # 2. Store Coordinates (From Config) - MUST BE [LONG, LAT]
        store_lng = float(current_app.config.get('STORE_PICKUP_LNG', 0))
        store_lat = float(current_app.config.get('STORE_PICKUP_LAT', 0))

        # --- CONSTRUCT PAYLOAD ---
        payload = {
            "customerId": self.customer_id,
            # If the API requires referenceId at the top level:
            "referenceId": str(local_order.id), 
            
            # --- PICKUP (YOUR STORE) ---
            "pickup": {
                "address": current_app.config['STORE_PICKUP_ADDRESS'],
                # Optional: "addressDetail": "Warehouse A",
                
                # CONTACT INFO (Directly inside pickup, per your doc)
                "fullName": "Store Dispatch",
                "phone": current_app.config['STORE_CONTACT_PHONE'],
                "email": "dispatch@store.com",
                
                # TIMESTAMPS
                "completeAfter": complete_after,
                "completeBefore": complete_before,
                
                # COORDINATES: [Longitude, Latitude]
                "coordinates": [store_lng, store_lat],
                
                "placeId": "" # Doc says set this to empty string
            },
            
            # --- DELIVERY (THE CUSTOMER) ---
            "delivery": {
                "address": f"{address_obj.street_address}, {address_obj.city}, {address_obj.country}",
                "addressDetail": "", # Optional apartment info if you collected it
                
                # CONTACT INFO
                "fullName": address_obj.full_name,
                "phone": address_obj.phone,
                "email": getattr(address_obj, 'email', ""), # If you have email on address object
                
                # TIMESTAMPS
                "completeAfter": complete_after,
                "completeBefore": complete_before,
                
                # COORDINATES for Customer
                # Since your checkout form DOES NOT collect Lat/Long from the user,
                # we usually send [0, 0] or omit it. 
                # Most APIs will use the text address to find the location if coords are 0.
                "coordinates": [0, 0], 
                
                "placeId": ""
            }
        }

        try:
            print(f"Sending Shipping Payload: {json.dumps(payload, indent=2)}") # Debugging
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Check where the ID is in their response
            return data.get('data', {}).get('id') 
            
        except Exception as e:
            print(f"Create Shipping Order Error: {e}")
            if 'response' in locals():
                print(f"API Response: {response.text}")
            return None

    def get_tracking_events(self, external_order_id):
        # (Keep this function the same as before)
        token = self._get_access_token()
        if not token: return []

        url = f"{self.base_url}/api/v1/customer/order/event"
        params = {"customerId": self.customer_id, "orderId": external_order_id}
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            return data.get('data', [])
        except Exception:
            return []