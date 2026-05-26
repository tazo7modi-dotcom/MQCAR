import os

def env(name, default=""):
    return os.environ.get(name, default)

def env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}

def env_float(name, default=0.0):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default

def env_pairs(name, default=None):
    raw = os.environ.get(name, '')
    if not raw and default:
        raw = default
    pairs = {}
    for item in raw.split(';'):
        if ':' not in item:
            continue
        key, value = item.split(':', 1)
        key = key.strip()
        if key:
            pairs[key] = value.strip()
    return pairs

def env_shipping_zones(store):
    raw = os.environ.get('CHECKOUT_SHIPPING_ZONES', '').strip()
    if not raw:
        return [{
            'name': env('CHECKOUT_COUNTRY_NAME', env('STORE_COUNTRY', 'Country')),
            'label': env('CHECKOUT_COUNTRY_LABEL', env('STORE_COUNTRY', 'Country')),
            'phone_code': store['phone_country_code'],
            'shipping_label': env('CHECKOUT_SHIPPING_LABEL', 'Standard Delivery'),
            'shipping_rate': env_float('CHECKOUT_LOCAL_SHIPPING_RATE', 0.0),
            'free_shipping_threshold': env_float('CHECKOUT_FREE_SHIPPING_THRESHOLD', 0.0),
        }]

    zones = []
    for chunk in raw.split(';'):
        parts = [part.strip() for part in chunk.split('|')]
        if len(parts) < 4:
            continue
        zones.append({
            'name': parts[0],
            'label': parts[1] or parts[0],
            'phone_code': parts[2],
            'shipping_label': parts[3] or 'Standard Delivery',
            'shipping_rate': float(parts[4]) if len(parts) > 4 and parts[4] else 0.0,
            'free_shipping_threshold': float(parts[5]) if len(parts) > 5 and parts[5] else 0.0,
        })
    return zones or env_shipping_zones(store)

class Config:
   
    SECRET_KEY = env('SECRET_KEY', 'change-me-in-production')


    basedir = os.path.abspath(os.path.dirname(__file__))

  
    if os.path.exists('/var/data'):
     
        SQLALCHEMY_DATABASE_URI = 'sqlite:////var/data/store.db'
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'store.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    

    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024


    TAP_SECRET_KEY = env('TAP_SECRET_KEY')
    TAP_PUBLIC_KEY = env('TAP_PUBLIC_KEY')

    STORE_PROFILE_CODE = env('STORE_PROFILE_CODE', 'default')
    STORE_PROFILES = {
        'default': {
            'name': env('STORE_NAME', 'MQ CARS'),
            'legal_name': env('STORE_LEGAL_NAME', env('STORE_NAME', 'MQ CARS')),
            'logo': env('STORE_LOGO', '/static/logo-mq-transparent.png'),
            'secondary_logo': env('STORE_SECONDARY_LOGO', '/static/logo-mq-transparent.png'),
            'hero_image': env('STORE_HERO_IMAGE', '/static/Hero-image.png'),
            'country': env('STORE_COUNTRY', ''),
            'location_text': env('STORE_LOCATION_TEXT', 'Online store'),
            'phone': env('STORE_PHONE', ''),
            'phone_display': env('STORE_PHONE_DISPLAY', env('STORE_PHONE', '')),
            'phone_country_code': env('STORE_PHONE_COUNTRY_CODE', '+000'),
            'email': env('STORE_EMAIL', ''),
            'support_email': env('STORE_SUPPORT_EMAIL', env('STORE_EMAIL', '')),
            'admin_email': env('ADMIN_MAIL', env('STORE_EMAIL', '')),
            'instagram_url': env('STORE_INSTAGRAM_URL', ''),
            'tiktok_url': env('STORE_TIKTOK_URL', ''),
            'whatsapp_url': env('STORE_WHATSAPP_URL', ''),
            'powered_by_enabled': env('POWERED_BY_ENABLED', 'false').lower() == 'true',
            'powered_by_label': env('POWERED_BY_LABEL', ''),
            'powered_by_url': env('POWERED_BY_URL', ''),
            'pickup_address': env('STORE_PICKUP_ADDRESS', ''),
            'pickup_lng': env('STORE_PICKUP_LNG', '0'),
            'pickup_lat': env('STORE_PICKUP_LAT', '0'),
            'dispatch_name': env('STORE_DISPATCH_NAME', 'Store Dispatch'),
            'dispatch_email': env('STORE_DISPATCH_EMAIL', env('STORE_EMAIL', '')),
        }
    }

    STORE = STORE_PROFILES.get(STORE_PROFILE_CODE, STORE_PROFILES['default'])

    THEME = {
        'primary_color': env('STORE_PRIMARY_COLOR', '#111111'),
        'accent_color': env('STORE_ACCENT_COLOR', '#d97706'),
        'background_color': env('STORE_BACKGROUND_COLOR', '#ffffff'),
        'surface_color': env('STORE_SURFACE_COLOR', '#fafafa'),
        'text_color': env('STORE_TEXT_COLOR', '#1a1a1a'),
        'muted_text_color': env('STORE_MUTED_TEXT_COLOR', '#6b7280'),
        'font': env('STORE_FONT', 'Inter'),
        'heading_font': env('STORE_HEADING_FONT', 'Oswald'),
        'arabic_font': env('STORE_ARABIC_FONT', 'Cairo'),
        'button_radius': env('STORE_BUTTON_RADIUS', '0px'),
        'card_radius': env('STORE_CARD_RADIUS', '4px'),
        'logo_width': env('STORE_LOGO_WIDTH', '64px'),
        'logo_height': env('STORE_LOGO_HEIGHT', '64px'),
        'hero_overlay': env('STORE_HERO_OVERLAY', 'rgba(0, 0, 0, 0.10)'),
        'hero_position': env('STORE_HERO_POSITION', 'left center'),
    }

    HOME_SECTIONS = {
        'featured_categories': env_bool('SHOW_FEATURED_CATEGORIES', True),
        'why_us': env_bool('SHOW_WHY_US', True),
        'reviews': env_bool('SHOW_REVIEWS', True),
        'newsletter': env_bool('SHOW_NEWSLETTER', True),
        'policies': env_bool('SHOW_POLICIES', True),
    }

    PAYMENT_OPTIONS = {
        'cod': env_bool('ENABLE_COD', True),
        'tap': env_bool('ENABLE_TAP', True),
        'benefitpay': env_bool('ENABLE_BENEFITPAY', True),
        'card': env_bool('ENABLE_CARD_PAYMENT', True),
    }

    SEO = {
        'title': env('SEO_TITLE', STORE['name']),
        'description': env('SEO_DESCRIPTION', 'Shop automotive accessories online from ' + STORE['name']),
        'keywords': env('SEO_KEYWORDS', ''),
        'og_image': env('SEO_OG_IMAGE', STORE['hero_image']),
        'whatsapp_image': env('SEO_WHATSAPP_IMAGE', env('SEO_OG_IMAGE', STORE['hero_image'])),
    }

    POLICIES = {
        'last_updated': env('POLICY_LAST_UPDATED', 'Latest update'),
        'shipping_intro': env('POLICY_SHIPPING_INTRO', 'Delivery options, timing, and fees depend on your selected area.'),
        'shipping_points': [
            env('POLICY_SHIPPING_POINT_1', 'Shipping zones and rates are configured per store.'),
            env('POLICY_SHIPPING_POINT_2', 'Customers receive order updates after checkout.'),
            env('POLICY_SHIPPING_POINT_3', 'Contact support for special delivery requests.'),
        ],
        'refund_rule': env('POLICY_REFUND_RULE', 'Refund and return eligibility depends on the store policy.'),
        'refund_process': env('POLICY_REFUND_PROCESS', 'Contact support with your order number to start a request.'),
        'refund_condition': env('POLICY_REFUND_CONDITION', 'Items must meet the configured return conditions.'),
        'refund_note': env('POLICY_REFUND_NOTE', 'Shipping fees may be non-refundable unless required by the store policy.'),
        'privacy_intro': env('POLICY_PRIVACY_INTRO', 'Customer information is used to process orders and provide support.'),
        'privacy_points': [
            env('POLICY_PRIVACY_POINT_1', 'We collect checkout and contact information needed for orders.'),
            env('POLICY_PRIVACY_POINT_2', 'We do not sell customer information.'),
        ],
        'terms': env('POLICY_TERMS', 'By placing an order, customers agree to the configured store terms.'),
    }

    EMAIL_SETTINGS = {
        'brand_color': env('EMAIL_BRAND_COLOR', THEME['primary_color']),
        'accent_color': env('EMAIL_ACCENT_COLOR', THEME['accent_color']),
        'receipt_subject': env('EMAIL_RECEIPT_SUBJECT', 'Order Confirmation #{order_id} - {store_name}'),
        'admin_subject': env('EMAIL_ADMIN_SUBJECT', 'NEW ORDER #{order_id} | {amount} {currency} | {status}'),
        'support_cta': env('EMAIL_SUPPORT_CTA', 'Need help? Contact our support team.'),
    }

    STORE_GLOSSARY = env_pairs('STORE_GLOSSARY')

    STORE_TEXT = {
        'en': {
            'hero_title': env('STORE_HERO_TITLE_EN', STORE['name']),
            'hero_subtitle': env('STORE_HERO_SUBTITLE_EN', 'Premium automotive accessories selected for fit, finish, and daily driving comfort.'),
            'footer_about_text': env('STORE_FOOTER_ABOUT_EN', 'MQ CARS curates automotive accessories for clean styling, practical upgrades, and dependable everyday quality.'),
            'footer_location_virtual': env('STORE_LOCATION_TEXT_EN', STORE['location_text']),
            'why_dropi_title': env('STORE_WHY_TITLE_EN', 'Details that make every drive better'),
            'why_dropi_subtitle': env('STORE_WHY_SUBTITLE_EN', 'Quality accessories, clear fitment guidance, and fast support before and after checkout.'),
            'footer_rights': env('STORE_RIGHTS_EN', 'All Rights Reserved.'),
            'about_mission_desc': env('STORE_ABOUT_MISSION_EN', 'Built around practical, reliable shopping for every customer.'),
            'home_policy_ship_sub': env('HOME_POLICY_SHIPPING_SUB_EN', 'Configured delivery window'),
            'home_policy_return_sub': env('HOME_POLICY_RETURN_SUB_EN', 'Configured return policy'),
        },
        'ar': {
            'hero_title': env('STORE_HERO_TITLE_AR', STORE['name']),
            'hero_subtitle': env('STORE_HERO_SUBTITLE_AR', 'إكسسوارات سيارات مختارة بعناية للتناسق، الشكل المرتب، وراحة الاستخدام اليومي.'),
            'footer_about_text': env('STORE_FOOTER_ABOUT_AR', 'MQ CARS يختار إكسسوارات سيارات تجمع بين الشكل المرتب، الترقيات العملية، والجودة المناسبة للاستخدام اليومي.'),
            'footer_location_virtual': env('STORE_LOCATION_TEXT_AR', STORE['location_text']),
            'why_dropi_title': env('STORE_WHY_TITLE_AR', 'تفاصيل تخلي كل مشوار أفضل'),
            'why_dropi_subtitle': env('STORE_WHY_SUBTITLE_AR', 'إكسسوارات بجودة واضحة، مساعدة في اختيار المناسب، ودعم سريع قبل وبعد الطلب.'),
            'footer_rights': env('STORE_RIGHTS_AR', 'جميع الحقوق محفوظة.'),
            'about_mission_desc': env('STORE_ABOUT_MISSION_AR', 'تجربة تسوق عملية وموثوقة لكل عميل.'),
            'home_policy_ship_sub': env('HOME_POLICY_SHIPPING_SUB_AR', 'مدة توصيل قابلة للإعداد'),
            'home_policy_return_sub': env('HOME_POLICY_RETURN_SUB_AR', 'سياسة إرجاع قابلة للإعداد'),
        }
    }

    # --- CURRENCY SETTINGS (Base: BHD) ---
    CURRENCY_RATES = {
        'BHD': {'rate': 1.0,   'symbol': 'BHD', 'decimals': 3, 'country_en': 'Bahrain', 'country_ar': 'البحرين'},
        'SAR': {'rate': 9.95,  'symbol': 'SAR', 'decimals': 2, 'country_en': 'Saudi Arabia', 'country_ar': 'السعودية'},
        'AED': {'rate': 9.75,  'symbol': 'AED', 'decimals': 2, 'country_en': 'UAE', 'country_ar': 'الإمارات'},
        'KWD': {'rate': 0.81,  'symbol': 'KWD', 'decimals': 3, 'country_en': 'Kuwait', 'country_ar': 'الكويت'},
        'QAR': {'rate': 9.68,  'symbol': 'QAR', 'decimals': 2, 'country_en': 'Qatar', 'country_ar': 'قطر'},
        'OMR': {'rate': 1.02,  'symbol': 'OMR', 'decimals': 3, 'country_en': 'Oman', 'country_ar': 'عمان'},
    }


    MAIL_SERVER = env('MAIL_SERVER', 'mail.privateemail.com')
    MAIL_PORT = int(env('MAIL_PORT', '587'))
    MAIL_USE_TLS = env('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = env('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = env('MAIL_USERNAME', STORE['email'])
    MAIL_PASSWORD = env('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = (env('MAIL_SENDER_NAME', STORE['name']), env('MAIL_DEFAULT_SENDER', STORE['email']))

    SHIPPING_BASE_URL = env('SHIPPING_BASE_URL')
    SHIPPING_CLIENT_ID = env('SHIPPING_CLIENT_ID')
    SHIPPING_CLIENT_SECRET = env('SHIPPING_CLIENT_SECRET')
    SHIPPING_CUSTOMER_ID = env('SHIPPING_CUSTOMER_ID')
    STORE_PICKUP_ADDRESS = STORE['pickup_address']
    STORE_PICKUP_LNG = STORE['pickup_lng']
    STORE_PICKUP_LAT = STORE['pickup_lat']
    STORE_CONTACT_PHONE = STORE['phone']
    CHECKOUT_COUNTRIES = env_shipping_zones(STORE)
