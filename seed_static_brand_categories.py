"""Seed the fixed MQ CARS storefront brand categories in an existing database.

Usage inside the production container:
    python3 seed_static_brand_categories.py --dry-run
    python3 seed_static_brand_categories.py

This script is intentionally idempotent. It creates only missing root-level
brand categories and does not create, update, or delete products.
"""

import argparse

from app import create_app
from app.extensions import db
from app.models import Category, Product


STATIC_BRAND_NAMES = (
    'Toyota',
    'Mercedes-Benz',
    'BMW',
    'Hyundai',
    'Honda',
    'Chevrolet',
    'Lexus',
    'GMC',
    'Nissan',
    'Kia',
    'Mazda',
)


def seed_categories(dry_run=False):
    root_categories = Category.query.filter_by(parent_id=None).all()
    existing_by_name = {
        category.name.casefold(): category
        for category in root_categories
    }
    missing_names = [
        name for name in STATIC_BRAND_NAMES
        if name.casefold() not in existing_by_name
    ]

    print(f"Products currently in database: {Product.query.count()}")
    print(f"Fixed brand categories already present: {len(STATIC_BRAND_NAMES) - len(missing_names)}")

    if not missing_names:
        print("No changes required. All fixed storefront brand categories already exist.")
        return

    print("Missing fixed brand categories:")
    for name in missing_names:
        print(f"  - {name}")

    if dry_run:
        print("Dry run only. No database changes were made.")
        return

    try:
        for name in missing_names:
            db.session.add(Category(name=name))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    print(f"Created {len(missing_names)} fixed storefront brand categories.")
    print(f"Products currently in database: {Product.query.count()}")


def main():
    parser = argparse.ArgumentParser(
        description='Create missing MQ CARS fixed brand categories without altering products.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report missing brand categories without changing the database.',
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        seed_categories(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
