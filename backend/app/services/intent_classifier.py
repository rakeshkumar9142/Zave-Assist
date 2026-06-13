import re

from app.models.schemas import Intent

ORDER_ID_PATTERN = re.compile(r"ZV\d{6}", re.IGNORECASE)
TXN_PATTERN = re.compile(r"TXN\d{9}", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
COUPON_PATTERN = re.compile(r"\b[A-Z]{2,}\d{2,}\b")

IRRELEVANT_KEYWORDS = [
    "write python", "write code", "javascript", "programming",
    "world cup", "cricket score", "weather", "news",
    "tell me a joke", "poem", "story", "homework",
    "who won", "president", "election",
]

INTENT_PATTERNS: list[tuple[Intent, list[str]]] = [
    (Intent.ORDER_TRACKING, [
        "where is my order", "track order", "order status", "delivery status",
        "when will i receive", "shipping update", "track my package",
    ]),
    (Intent.CASHBACK, [
        "cashback", "cash back", "reward not credited", "points not received",
        "cashback pending", "cashback not credited",
    ]),
    (Intent.COUPON, [
        "coupon", "promo code", "discount code", "voucher", "coupon not working",
        "code not working", "promo not working",
    ]),
    (Intent.PAYMENT, [
        "payment failed", "money deducted", "transaction failed", "refund",
        "charged twice", "payment issue", "order failed but paid",
        "deducted but", "deducted but the order", "order failed",
    ]),
    (Intent.RETURN_REFUND, [
        "return", "refund my order", "send back", "exchange", "return product",
        "want to return", "initiate return",
    ]),
    (Intent.ACCOUNT, [
        "login", "log in", "sign in", "otp", "password", "unable to access",
        "can't login", "cannot login", "account locked", "verify email",
    ]),
    (Intent.RECOMMENDATION, [
        "recommend", "suggest", "best", "which should i buy", "compare",
        "under ₹", "under rs", "budget", "good earbuds", "good phone",
    ]),
    (Intent.ESCALATION, [
        "fraud", "scam", "speak to human", "talk to agent", "manager",
        "complaint", "very unhappy", "worst experience", "legal action",
    ]),
    (Intent.GREETING, [
        "hello", "hi", "hey", "good morning", "good evening", "namaste",
    ]),
]


def classify_intent(message: str) -> Intent:
    text = message.lower().strip()

    for keyword in IRRELEVANT_KEYWORDS:
        if keyword in text:
            return Intent.IRRELEVANT

    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if pattern in text:
                return intent

    if ORDER_ID_PATTERN.search(message):
        return Intent.ORDER_TRACKING
    if TXN_PATTERN.search(message):
        return Intent.PAYMENT
    if COUPON_PATTERN.search(message):
        return Intent.COUPON
    if EMAIL_PATTERN.search(message):
        return Intent.CASHBACK

    return Intent.UNKNOWN


def extract_order_id(message: str) -> str | None:
    match = ORDER_ID_PATTERN.search(message)
    return match.group(0).upper() if match else None


def extract_transaction_id(message: str) -> str | None:
    match = TXN_PATTERN.search(message)
    return match.group(0).upper() if match else None


def extract_email(message: str) -> str | None:
    match = EMAIL_PATTERN.search(message)
    return match.group(0).lower() if match else None


def extract_coupon_code(message: str) -> str | None:
    upper = message.upper().strip()
    for code in ["SAVE500", "WELCOME100", "EXPIRED50"]:
        if code in upper:
            return code
    match = COUPON_PATTERN.search(upper)
    return match.group(0) if match else None


def extract_price_limit(message: str) -> int | None:
    patterns = [
        r"under\s*₹?\s*([\d,]+)",
        r"under\s*rs\.?\s*([\d,]+)",
        r"below\s*₹?\s*([\d,]+)",
        r"₹\s*([\d,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    return None
