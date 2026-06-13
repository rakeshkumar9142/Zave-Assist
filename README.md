# Zave Assist

AI-powered support platform that scales Zave from ~1,000 to 100,000+ monthly customer queries while minimizing AI token costs and preserving support quality.

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  Next.js (UI)   │────▶│  FastAPI (Backend)   │────▶│  Appwrite   │
│  Vercel         │     │  Render              │     │  Database   │
└─────────────────┘     └──────────┬───────────┘     └─────────────┘
                                   │
                          ┌────────┴────────┐
                          │ Decision Engine│
                          ├────────────────┤
                          │ Rule-based     │──▶ 87% queries (no AI)
                          │ Intent routing │
                          │ Gemini Flash   │──▶ Recommendations only
                          │ Escalation     │──▶ Human tickets
                          └────────────────┘
```

## Support Flows

| Flow | Method | AI Required |
|------|--------|-------------|
| Order Tracking | Database lookup | No |
| Cashback Issues | Database lookup | No |
| Coupon Problems | Validation engine | No |
| Payment Issues | Gateway verification | No |
| Returns & Refunds | Policy engine | No |
| Account Issues | OTP/reset workflows | No |
| Product Recommendations | Gemini Flash | Yes |
| Domain Restriction | Keyword blocklist | No |

## Quick Start

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env         # Add GEMINI_API_KEY optionally
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend (Next.js)

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## Demo Data

Try these in the chat:

- **Order tracking:** "Where is my order?" → `ZV123456`
- **Cashback:** "My cashback hasn't been credited" → `priya@example.com`
- **Coupon:** "My coupon isn't working" → `SAVE500`
- **Payment:** "Money was deducted but order failed" → `TXN111222333`
- **Returns:** "I want to return my product" → `ZV789012`
- **Account:** "I'm unable to log in, OTP not received"
- **Recommendations:** "Suggest the best earbuds under ₹2,000"
- **Blocked:** "Write Python code" or "Who won the World Cup?"

## Decision Engine

Every message follows this sequence:

1. **Identify intent** — keyword/pattern matching (no LLM)
2. **Check workflow** — does an operational handler exist?
3. **Query databases** — orders, cashback, coupons, payments
4. **Return deterministic response** — instant, zero tokens
5. **Use Gemini** — only for product recommendations
6. **Escalate** — fraud, payment mismatches, missing records, repeated failures

## Escalation Triggers

- Fraud reports
- Payment gateway mismatches
- Repeated dissatisfaction
- Missing backend records (2+ failed lookups)
- Multiple failed attempts (3+)

## Deployment

| Component | Platform | Config |
|-----------|----------|--------|
| Frontend | Vercel | Set `NEXT_PUBLIC_API_URL` |
| Backend | Render | Use `Procfile`, set env vars |
| Database | Appwrite | Set `APPWRITE_*` env vars |

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Optional | Enables AI recommendations |
| `APPWRITE_PROJECT_ID` | Optional | Appwrite project ID |
| `APPWRITE_API_KEY` | Optional | Appwrite API key |
| `FRONTEND_URL` | Optional | CORS origin |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API URL |

## Tech Stack

- **Frontend:** Next.js 16, Tailwind CSS 4, TypeScript
- **Backend:** Python FastAPI, Pydantic
- **Database:** Appwrite (with in-memory seed fallback)
- **AI:** Google Gemini 2.0 Flash (recommendations only)
