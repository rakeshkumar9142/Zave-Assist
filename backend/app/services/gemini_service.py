
from app.config import settings
from app.database import db

try:
    import google.generativeai as genai
except ImportError:
    genai = None


async def get_product_recommendations(query: str, max_price: int = 2000) -> str:
    """
    Use Gemini only for product recommendations.
    Falls back to deterministic recommendations if Gemini fails.
    """

    # Detect category from user query
    query_lower = query.lower()

    if any(word in query_lower for word in ["smartphone", "phone", "mobile"]):
        category = "smartphones"
    elif any(word in query_lower for word in ["earbud", "earbuds", "buds"]):
        category = "earbuds"
    elif any(word in query_lower for word in ["headphone", "headphones"]):
        category = "headphones"
    else:
        category = "earbuds"

    # Fetch products
    products = db.get_products(category=category, max_price=max_price)

    if not products:
        return (
            f"I couldn't find any {category} under ₹{max_price:,}. "
            "Please try increasing your budget."
        )

    product_context = "\n".join(
        f"- {p['name']}: ₹{p['price']}, Rating {p['rating']}/5"
        for p in products[:5]
    )



    # Fallback checks
    if not settings.gemini_api_key:
        print("Fallback Reason: Missing Gemini API Key")
        return _fallback_recommendation(products, max_price)

    if genai is None:
        print("Fallback Reason: google-generativeai package not installed")
        return _fallback_recommendation(products, max_price)

    try:
        

        genai.configure(api_key=settings.gemini_api_key)

   

        # Try this model first
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
You are Zave Assist, a shopping assistant for Zave.

User Query:
"{query}"

Available products:
{product_context}

Recommend the top 3 options based on:
- Value for money
- Ratings
- User requirements

Instructions:
- Keep the response concise.
- Use numbered recommendations.
- Mention prices using ₹.
- Keep under 150 words.
"""

    

        response = model.generate_content(prompt)

      

        if hasattr(response, "text") and response.text:
            return response.text.strip()

        print("Gemini returned empty response.")
        return _fallback_recommendation(products, max_price)

    except Exception as e:
        print("\n========== GEMINI ERROR ==========")
        print(repr(e))
        print("==================================\n")

        return _fallback_recommendation(products, max_price)


def _fallback_recommendation(products: list[dict], max_price: int) -> str:
    """
    Deterministic fallback recommendations.
    """

    if not products:
        return (
            f"I couldn't find products under ₹{max_price:,}. "
            "Please try increasing your budget."
        )

    top3 = products[:3]

    lines = [
        f"Based on value for money and reviews under ₹{max_price:,}, I recommend:\n"
    ]

    for i, product in enumerate(top3, 1):
        lines.append(
            f"{i}. {product['name']} — ₹{product['price']:,} "
            f"(Rating: {product['rating']}/5)"
        )

    return "\n".join(lines)
