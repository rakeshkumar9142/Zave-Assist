"""In-memory seed data used when Appwrite is not configured."""

from datetime import date, timedelta

TODAY = date(2026, 6, 13)

ORDERS = {
    "ZV123456": {
        "order_id": "ZV123456",
        "user_id": "user_001",
        "email": "priya@example.com",
        "product_name": "Sony WH-1000XM5 Headphones",
        "status": "out_for_delivery",
        "courier": "Delhivery",
        "expected_delivery": (TODAY + timedelta(days=1)).isoformat(),
        "amount": 24999,
        "category": "electronics",
        "delivered_at": None,
    },
    "ZV789012": {
        "order_id": "ZV789012",
        "user_id": "user_002",
        "email": "rahul@example.com",
        "product_name": "Realme Buds Air 6",
        "status": "delivered",
        "courier": "BlueDart",
        "expected_delivery": (TODAY - timedelta(days=3)).isoformat(),
        "amount": 1899,
        "category": "electronics",
        "delivered_at": (TODAY - timedelta(days=3)).isoformat(),
    },
    "ZV345678": {
        "order_id": "ZV345678",
        "user_id": "user_001",
        "email": "priya@example.com",
        "product_name": "Nike Air Max 90",
        "status": "confirmed",
        "courier": "Delhivery",
        "expected_delivery": (TODAY + timedelta(days=5)).isoformat(),
        "amount": 8999,
        "category": "footwear",
        "delivered_at": None,
    },
}

CASHBACK = {
    "ZV123456": {
        "order_id": "ZV123456",
        "email": "priya@example.com",
        "amount": 250,
        "status": "pending",
        "eligible": True,
        "credited_at": None,
    },
    "ZV789012": {
        "order_id": "ZV789012",
        "email": "rahul@example.com",
        "amount": 95,
        "status": "credited",
        "eligible": True,
        "credited_at": (TODAY - timedelta(days=3)).isoformat(),
    },
    "ZV345678": {
        "order_id": "ZV345678",
        "email": "priya@example.com",
        "amount": 0,
        "status": "not_eligible",
        "eligible": False,
        "credited_at": None,
    },
}

COUPONS = {
    "SAVE500": {
        "code": "SAVE500",
        "discount": 500,
        "min_cart": 5000,
        "max_uses": 1000,
        "used_count": 450,
        "expires_at": (TODAY + timedelta(days=30)).isoformat(),
        "active": True,
        "user_eligible": True,
    },
    "WELCOME100": {
        "code": "WELCOME100",
        "discount": 100,
        "min_cart": 500,
        "max_uses": 5000,
        "used_count": 4999,
        "expires_at": (TODAY + timedelta(days=60)).isoformat(),
        "active": True,
        "user_eligible": True,
    },
    "EXPIRED50": {
        "code": "EXPIRED50",
        "discount": 50,
        "min_cart": 200,
        "max_uses": 100,
        "used_count": 80,
        "expires_at": (TODAY - timedelta(days=10)).isoformat(),
        "active": False,
        "user_eligible": True,
    },
}

PAYMENTS = {
    "TXN987654321": {
        "transaction_id": "TXN987654321",
        "order_id": "ZV123456",
        "amount": 24999,
        "status": "success",
        "gateway_status": "captured",
        "order_created": True,
    },
    "TXN111222333": {
        "transaction_id": "TXN111222333",
        "order_id": None,
        "amount": 5999,
        "status": "failed",
        "gateway_status": "failed",
        "order_created": False,
        "refund_initiated": True,
    },
    "TXN444555666": {
        "transaction_id": "TXN444555666",
        "order_id": "ZV345678",
        "amount": 8999,
        "status": "mismatch",
        "gateway_status": "captured",
        "order_created": False,
    },
}

USERS = {
    "priya@example.com": {
        "email": "priya@example.com",
        "mobile_last4": "4821",
        "user_id": "user_001",
        "login_issues": [],
    },
    "rahul@example.com": {
        "email": "rahul@example.com",
        "mobile_last4": "7392",
        "user_id": "user_002",
        "login_issues": ["otp_not_received"],
    },
}

PRODUCTS = [
    # Earbuds
    {"name": "Realme Buds Air 6", "price": 1899, "rating": 4.5, "category": "earbuds"},
    {"name": "Oppo Enco Buds 3", "price": 1799, "rating": 4.3, "category": "earbuds"},
    {"name": "OnePlus Nord Buds 2", "price": 1999, "rating": 4.4, "category": "earbuds"},
    {"name": "boAt Airdopes 141", "price": 1299, "rating": 4.1, "category": "earbuds"},
    {"name": "Noise Buds VS104", "price": 999, "rating": 3.9, "category": "earbuds"},

    # Smartphones
    {"name": "Redmi Note 13", "price": 17999, "rating": 4.4, "category": "smartphones"},
    {"name": "Moto G64", "price": 16999, "rating": 4.5, "category": "smartphones"},
    {"name": "iQOO Z9", "price": 19999, "rating": 4.4, "category": "smartphones"},
    {"name": "Realme Narzo 70", "price": 15999, "rating": 4.3, "category": "smartphones"},
    {"name": "Samsung Galaxy M35", "price": 18999, "rating": 4.5, "category": "smartphones"},

    # Headphones
    {"name": "Sony WH-CH520", "price": 4999, "rating": 4.5, "category": "headphones"},
    {"name": "JBL Tune 760NC", "price": 5999, "rating": 4.4, "category": "headphones"},
    {"name": "Soundcore Life Q20", "price": 4499, "rating": 4.3, "category": "headphones"},
]

RETURN_WINDOW_DAYS = 7
NON_RETURNABLE_CATEGORIES = {"personal_care", "innerwear"}
