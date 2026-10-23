# 🛒 Price Pantry

> A data-engineering & AI-powered platform that aggregates grocery prices from major UK supermarkets, compares products, tracks historical prices, and recommends the cheapest shopping basket.

**Phase 1 (MVP)** delivers an end-to-end price-comparison website powered by real **Tesco** data.

---

## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | Next.js · TypeScript · TailwindCSS · shadcn/ui · React Query · Recharts |
| Backend   | FastAPI · SQLAlchemy · Alembic · Pydantic |
| Database  | PostgreSQL 16 |
| Scraper   | Playwright · BeautifulSoup |
| DevOps    | Docker · Docker Compose |

---

## Project structure

```
price-pantry/
├── backend/     FastAPI app, SQLAlchemy models, Alembic migrations
├── frontend/    Next.js app (Home / Search / Product Details)
├── scrapers/    Playwright Tesco scraper (AbstractScraper base)
├── docs/        Documentation
├── data/        Local raw scrape dumps (gitignored)
└── docker-compose.yml
```

---

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build db backend frontend
```

- API:      http://localhost:8000  (docs at `/docs`)
- Frontend: http://localhost:3000

The backend automatically runs migrations and seeds a small demo dataset on first boot, so the app works immediately.

### Scrape real Tesco data

Tesco is protected by **Akamai Bot Manager**, which serves `403 Access Denied`
to headless / bundled-Chromium browsers. What reliably gets through is a
**headful run using your real installed Chrome** (`channel=chrome`) with a
persistent profile and a homepage warm-up — all built into the scraper.

Because that needs a real display + Chrome, run it **on the host** (not in the
Docker scraper container, which has neither):

```powershell
cd scrapers
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
$env:PW_CHANNEL="chrome"
$env:PW_USER_DATA_DIR="$env:TEMP\pp-chrome-profile"
$env:DATABASE_URL="postgresql+psycopg://pricepantry:pricepantry@localhost:5432/pricepantry"
python -m run --headful --categories milk bread eggs cheese chicken --max-pages 1
```

A helper wraps this: `scrapers/scrape_tesco.ps1`.

Ingestion is **idempotent**: a run inserts a new `prices` row only when the
price has *changed* since the last observation; an unchanged price is
re-confirmed by bumping `last_seen_at` instead of stacking duplicate rows. So
re-running builds a clean price-change history without inflating the table.
Products are de-duplicated by store-native `external_id` (see Data model below).

> The Docker `scraper` service (`docker compose run --rm scraper`) still runs and
> demonstrates the architecture, but Akamai blocks it (headless, no real Chrome).
> Useful for `--dry-run` wiring checks; use the host command above for real data.

---

## Local development (without Docker)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# point DATABASE_URL at localhost, then:
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## API endpoints

| Method | Path              | Description |
|--------|-------------------|-------------|
| GET    | `/health`         | Liveness check (also pings the DB) |
| GET    | `/products`       | Paginated product list (`page`, `page_size`, `category`); each item carries `latest_price` + `price_updated_at` |
| GET    | `/products/{id}`  | Product detail + latest price + bounded price history (`history_limit`, default 90) |
| GET    | `/search`         | Search products (`q`, `page`, `page_size`) |
| GET    | `/prices`         | Price records (`product_id`, `limit`) |

All list/detail responses are Pydantic-validated; the latest valid price is
selected **database-side** (window query, no full-history load, no N+1).

---

## Data model & data integrity

The schema separates the three concerns a comparison platform needs. (A
*canonical product* layer that links listings across retailers is intentionally
**deferred** to the comparison phase — see `docs/ARCHITECTURE.md`.)

| Table | Role | Key points |
|-------|------|------------|
| `stores` | **Retailer** identity | unique `slug` |
| `products` | **Retailer listing** (one store's representation) | `store_id`, `external_id`, `url`, name/brand/weight/category |
| `prices` | **Price observations** (time-series) | `price` `Numeric(10,2)`, `currency`, `in_stock`, `scraped_at`, `last_seen_at` |

Guarantees:
- **Monetary** values use `Numeric(10,2)`; currency is explicit on every observation.
- **Identity / no duplicates:** `UNIQUE(store_id, url)` and a **partial unique
  index** `UNIQUE(store_id, external_id) WHERE external_id IS NOT NULL`. The
  scraper matches on `external_id` first (store-scoped), then URL, and handles
  concurrent-insert conflicts via a savepoint + re-query (no duplicate rows).
- **History preserved:** observations are append-only; `scraped_at` is when a
  price first appeared, `last_seen_at` when it was most recently re-confirmed.
  "Current price" = newest by `(scraped_at DESC, id DESC)`; freshness uses
  `last_seen_at`. Invalid/failed extractions store **no** observation.
- **Timestamps** are stored in UTC (`timestamptz`).
- **Indexes:** `(product_id, scraped_at, id)` for per-product latest/history,
  `scraped_at` for the global `/prices` feed, plus name/brand/category for search.

### Migrations

Alembic, reproducible from an empty database (`alembic upgrade head`):

| Revision | Purpose |
|----------|---------|
| `0001_initial` | stores / products / prices + base indexes |
| `0002_price_index` | composite `(product_id, scraped_at, id)` index |
| `0003_product_identity` | de-dupe + partial unique index on `(store_id, external_id)` |
| `0004_price_last_seen` | add `last_seen_at` (idempotent ingestion), backfilled from `scraped_at` |

---

## Roadmap

- **Phase 1** ✅ MVP — single store (Tesco), search, product pages
- **Phase 2** — Multi-store (Asda, Sainsbury's, Morrisons)
- **Phase 3** — Historical pricing & analytics
- **Phase 4** — Basket comparison / optimizer
- **Phase 5** — Automated ETL pipeline (Celery, Redis, S3)
- **Phase 6** — AI product matching (RapidFuzz, embeddings, pgvector)
- **Phase 7** — AI shopping assistant
- **Phase 8** — Analytics dashboard
