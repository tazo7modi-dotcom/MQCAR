from .extensions import db
from .models import Category


STATIC_BRAND_CATEGORIES = (
    {
        'name': 'Toyota',
        'key': 'toyota',
        'image_path': 'main-cats-images/toyota-logo-2020-europe-download.png',
    },
    {
        'name': 'Mercedes-Benz',
        'key': 'mercedes-benz',
        'image_path': 'main-cats-images/Mercedes-Benz-logo-2011-640x369.jpg',
    },
    {
        'name': 'BMW',
        'key': 'bmw',
        'image_path': 'main-cats-images/bmw-logo-2020-gray-download.png',
    },
    {
        'name': 'Hyundai',
        'key': 'hyundai',
        'image_path': 'main-cats-images/hyundai-logo-2011-download.png',
    },
    {
        'name': 'Honda',
        'key': 'honda',
        'image_path': 'main-cats-images/honda-logo-2000-full-download.png',
    },
    {
        'name': 'Chevrolet',
        'key': 'chevrolet',
        'image_path': 'main-cats-images/Chevrolet-logo-2013-640x281.jpg',
    },
    {
        'name': 'Lexus',
        'key': 'lexus',
        'image_path': 'main-cats-images/Lexus-logo-1988-640x266.jpg',
    },
    {
        'name': 'GMC',
        'key': 'gmc',
        'image_path': 'main-cats-images/GMC-logo-640x145.jpg',
    },
    {
        'name': 'Nissan',
        'key': 'nissan',
        'image_path': 'main-cats-images/nissan-logo-2020-black.png',
    },
    {
        'name': 'Kia',
        'key': 'kia',
        'image_path': 'main-cats-images/Kia-logo-640x321.jpg',
    },
    {
        'name': 'Mazda',
        'key': 'mazda',
        'image_path': 'main-cats-images/mazda-logo-2018-vertical-download.png',
    },
)

STATIC_BRAND_CATEGORY_NAMES = frozenset(
    category['name'] for category in STATIC_BRAND_CATEGORIES
)


def ensure_static_brand_categories():
    """Create fixed storefront brand categories once and return their records."""
    root_categories = Category.query.filter_by(parent_id=None).all()
    existing_by_name = {
        category.name.casefold(): category
        for category in root_categories
    }
    resolved = {}
    changed = False

    for definition in STATIC_BRAND_CATEGORIES:
        lookup_name = definition['name'].casefold()
        category = existing_by_name.get(lookup_name)
        if category is None:
            category = Category(name=definition['name'])
            db.session.add(category)
            db.session.flush()
            root_categories.append(category)
            existing_by_name[lookup_name] = category
            changed = True
        resolved[definition['key']] = category

    if changed:
        db.session.commit()

    return root_categories, resolved


def build_static_brand_tiles(categories_by_key):
    return [
        {
            'name': definition['name'],
            'image_path': definition['image_path'],
            'category_id': categories_by_key[definition['key']].id,
        }
        for definition in STATIC_BRAND_CATEGORIES
    ]


def is_static_brand_category(category):
    return (
        category.parent_id is None
        and category.name in STATIC_BRAND_CATEGORY_NAMES
    )
