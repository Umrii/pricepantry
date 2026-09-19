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

Each run inserts fresh `prices` rows (time-series), so re-running builds price
history. Products are de-duplicated by store-native `external_id`.

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
| GET    | `/health`         | Liveness check |
| GET    | `/products`       | Paginated product list (`page`, `page_size`, `category`) |
| GET    | `/products/{id}`  | Product detail + latest price + price history |
| GET    | `/search`         | Search products (`q`, `page`, `page_size`) |
| GET    | `/prices`         | Price records (`product_id`) |

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
