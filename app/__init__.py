import os
from flask import Flask, session, send_from_directory
from config import Config
from .extensions import db, migrate, login_manager
from app.translations import dictionary
from deep_translator import GoogleTranslator
from functools import lru_cache
import re
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix



if os.path.exists('/var/data'):
    BASE_UPLOAD_PATH = '/var/data'
else:
    BASE_UPLOAD_PATH = os.path.join(os.getcwd(), 'app/static/uploads')


GLOSSARY = {
    # --- Categories ---
    "devices & kits": "أجهزة وكيتات",
    "pod devices": "أجهزة البود",
    "disposables": "سحبات جاهزة",
    "disposable": "سحبة جاهزة",
    "free base juice": "نكهات فريبز",
    "salt nic juice": "نكهات سولت",
    "coils & pods": "كويلات وبودات",
    "nicotine pouch": "أظرف نيكوتين",
    "nicotine pouches": "أظرف نيكوتين",
    "cigarettes": "سجائر",
    "hookahs": "شيشة ومعسل",
    "accessories": "إكسسوارات",

    # --- Technical Terms ---
    "salt nic": "سولت نيكوتين",
    "free base": "فريبز",
    "e-liquid": "نكهة إلكترونية",
    "e-juice": "نكهة",
    "juice": "نكهة",
    "vape": "فيب",
    "starter kit": "كيت للمبتدئين",
    "kit": "كيت",
    "mod": "مود",
    "tank": "تانك",
    "coil": "كويل",
    "coils": "كويلات",
    "pod": "بود",
    "pods": "بودات",
    "cartridge": "بود",
    "puffs": "سحبة",
    "battery": "بطارية",
    "charger": "شاحن",
    "grape": "عنب",
    "mint": "نعناع",
    "mango": "مانجو",
    "ice": "ايس",
    "watermelon": "جح",
    "tobacco": "توباكو",
    
    # --- Popular Brands ---
    "geekvape": "جيك فيب",
    "vaporesso": "فابوريسو",
    "smok": "سموك",
    "uwell": "يو ويل",
    "voopoo": "فوبو",
    "caliburn": "كاليبرن",
    "nasty": "ناستي",
    "elfbar": "إلف بار",
    "tugboat": "توق بوت",
    "yuoto": "يوتو",
    "tokyo": "طوكيو"
}


@lru_cache(maxsize=2000)
def cached_translate(text, target_lang='ar'):
    if not text or not isinstance(text, str):
        return text if text else ""
        
    if target_lang == 'ar' and any("\u0600" <= c <= "\u06FF" for c in text):
        return text

    processed_text = text
    lower_text = text.lower()
    
    for eng_word, ar_word in GLOSSARY.items():
        if eng_word in lower_text:
            pattern = re.compile(re.escape(eng_word), re.IGNORECASE)
            processed_text = pattern.sub(ar_word, processed_text)

    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(processed_text)
    except Exception:
        return text

mail = Mail()
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)



    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # User Loader
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(BASE_UPLOAD_PATH, filename)

    # Context Processor: Global Cart Count
    @app.context_processor
    def inject_cart_count():
        from flask_login import current_user
        count = 0
        try:
            if current_user.is_authenticated and current_user.cart:
                count = sum(item.quantity for item in current_user.cart.cart_items)
        except Exception:
            count = 0
        return dict(cart_count=count)

    from app.payment import get_user_currency 

    @app.context_processor
    def inject_currency_data():
        return dict(current_currency=get_user_currency())

    @app.template_filter('currency')
    def currency_filter(amount):
        if amount is None: return ""
        code = get_user_currency()
        currency_data = app.config['CURRENCY_RATES'].get(code, app.config['CURRENCY_RATES']['BHD'])
        rate = currency_data['rate']
        symbol = currency_data['symbol']
        decimals = currency_data['decimals']
        
        try:
            converted_amount = float(amount) * rate
            return f"{symbol} {converted_amount:,.{decimals}f}"
        except (ValueError, TypeError):
            return amount

    @app.context_processor
    def inject_categories():
        from .models import Category 
        try:
            roots = Category.query.filter_by(parent_id=None).all()
            return dict(global_categories=roots)
        except Exception:
            return dict(global_categories=[])
    
    @app.context_processor
    def inject_translation():
        lang = session.get('language', 'en')
        def translate(key):
            return dictionary.get(lang, {}).get(key, key) 
        
        layout_dir = dictionary[lang]['direction']
        layout_font = dictionary[lang]['font']

        return dict(
            _ = translate,          
            current_lang = lang,     
            layout_dir = layout_dir,
            layout_font = layout_font
        )
    
    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp


    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')


    @app.template_filter('translate_dynamic')
    def translate_dynamic_filter(text):
        current_lang = session.get('language', 'en')
        if current_lang != 'ar':
            return text
        return cached_translate(str(text))

    return app