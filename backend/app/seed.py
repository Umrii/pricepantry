"""Seed a small demo dataset so the app works before the scraper runs.

Idempotent: safe to run on every boot. Products are matched by URL; a price row
is only added when a product has none yet, so re-running won't stack prices.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.price import Price
from app.models.product import Product
from app.models.store import Store

TESCO = {
    "name": "Tesco",
    "slug": "tesco",
    "website_url": "https://www.tesco.com/groceries/",
    "logo_url": "https://www.tesco.com/favicon.ico",
}

# A representative slice of the Tesco grocery catalogue for the demo.
DEMO_PRODUCTS: list[dict] = [
    {
        "name": "Tesco British Semi Skimmed Milk 2.272L, 4 Pints",
        "brand": "Tesco",
        "weight": "2.272L",
        "category": "Milk",
        "url": "https://www.tesco.com/groceries/en-GB/products/254656543",
        "external_id": "254656543",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("1.65"),
        "unit_price": "£0.73/ltr",
    },
    {
        "name": "Tesco Free Range Medium Eggs 12 Pack",
        "brand": "Tesco",
        "weight": "12 pack",
        "category": "Eggs",
        "url": "https://www.tesco.com/groceries/en-GB/products/296704637",
        "external_id": "296704637",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("2.95"),
        "unit_price": "£0.25/each",
    },
    {
        "name": "Hovis Soft White Medium Bread 800g",
        "brand": "Hovis",
        "weight": "800g",
        "category": "Bread",
        "url": "https://www.tesco.com/groceries/en-GB/products/258958854",
        "external_id": "258958854",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("1.40"),
        "unit_price": "£0.18/100g",
    },
    {
        "name": "Tesco British Chicken Breast Fillets 650g",
        "brand": "Tesco",
        "weight": "650g",
        "category": "Poultry",
        "url": "https://www.tesco.com/groceries/en-GB/products/258507297",
        "external_id": "258507297",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("4.79"),
        "unit_price": "£7.37/kg",
    },
    {
        "name": "Coca-Cola Zero Sugar 2L",
        "brand": "Coca-Cola",
        "weight": "2L",
        "category": "Soft Drinks",
        "url": "https://www.tesco.com/groceries/en-GB/products/258445975",
        "external_id": "258445975",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("2.29"),
        "unit_price": "£1.15/ltr",
    },
    {
        "name": "Cathedral City Mature Cheddar Cheese 350g",
        "brand": "Cathedral City",
        "weight": "350g",
        "category": "Cheese",
        "url": "https://www.tesco.com/groceries/en-GB/products/274128308",
        "external_id": "274128308",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("3.50"),
        "unit_price": "£1.00/100g",
    },
    {
        "name": "Tesco Bananas Loose",
        "brand": "Tesco",
        "weight": "each",
        "category": "Fresh Fruit",
        "url": "https://www.tesco.com/groceries/en-GB/products/254603178",
        "external_id": "254603178",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("0.15"),
        "unit_price": "£0.83/kg",
    },
    {
        "name": "Walkers Ready Salted Crisps 6x25g",
        "brand": "Walkers",
        "weight": "6x25g",
        "category": "Crisps & Snacks",
        "url": "https://www.tesco.com/groceries/en-GB/products/301344489",
        "external_id": "301344489",
        "image_url": "https://digitalcontent.api.tesco.com/v2/media/ghs/placeholder.jpeg",
        "price": Decimal("1.75"),
        "unit_price": "£1.17/100g",
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        store = db.scalar(select(Store).where(Store.slug == TESCO["slug"]))
        if store is None:
            store = Store(**TESCO)
            db.add(store)
            db.flush()
            print(f"[seed] created store '{store.slug}'")

        created_products = 0
        added_prices = 0
        for item in DEMO_PRODUCTS:
            product = db.scalar(
                select(Product).where(
                    Product.store_id == store.id, Product.url == item["url"]
                )
            )
            if product is None:
                product = Product(
                    store_id=store.id,
                    external_id=item["external_id"],
                    name=item["name"],
                    brand=item["brand"],
                    weight=item["weight"],
                    category=item["category"],
                    image_url=item["image_url"],
                    url=item["url"],
                )
                db.add(product)
                db.flush()
                created_products += 1

            has_price = db.scalar(
                select(Price.id).where(Price.product_id == product.id).limit(1)
            )
            if has_price is None:
                db.add(
                    Price(
                        product_id=product.id,
                        price=item["price"],
                        currency="GBP",
                        unit_price=item.get("unit_price"),
                        in_stock=True,
                    )
                )
                added_prices += 1

        db.commit()
        print(
            f"[seed] done — {created_products} new products, {added_prices} price rows "
            f"({len(DEMO_PRODUCTS)} demo items total)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
