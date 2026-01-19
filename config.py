import os

class Config:
   
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-123'


    basedir = os.path.abspath(os.path.dirname(__file__))

  
    if os.path.exists('/var/data'):
     
        SQLALCHEMY_DATABASE_URI = 'sqlite:////var/data/store.db'
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'store.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    

    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  


    TAP_SECRET_KEY = os.environ.get('TAP_SECRET_KEY') or 'wqeodjqwobjdn'
    TAP_PUBLIC_KEY = os.environ.get('TAP_PUBLIC_KEY') or 'wkjdbjwq'

    # --- CURRENCY SETTINGS (Base: BHD) ---
    CURRENCY_RATES = {
        'BHD': {'rate': 1.0,   'symbol': 'BHD', 'decimals': 3},
        'SAR': {'rate': 9.95,  'symbol': 'SAR', 'decimals': 2},
        'AED': {'rate': 9.75,  'symbol': 'AED', 'decimals': 2},
        'KWD': {'rate': 0.81,  'symbol': 'KWD', 'decimals': 3},
        'QAR': {'rate': 9.68,  'symbol': 'QAR', 'decimals': 2},
        'OMR': {'rate': 1.02,  'symbol': 'OMR', 'decimals': 3},
    }

