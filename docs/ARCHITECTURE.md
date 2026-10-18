# Price Pantry — How It Works (Full Code Walkthrough)

A top-to-bottom explanation of the whole application: what each piece does, how
data flows from a supermarket website all the way to a chart in the browser, and
why the code is structured the way it is.

> New here? Read this top to bottom once. Each section builds on the previous
> one. For *running* the app see [COLD_START.md](COLD_START.md); this document is
> about *understanding* it.

---

## 1. What the application is

**Price Pantry** is a UK grocery **price-comparison** web app. Phase 1 (the
current build) covers a single supermarket — **Tesco** — and does three things:

1. **Scrapes** real product + price data from Tesco's website.
2. **Stores** it in a database as a *time-series* (every scrape is kept, so you
   build price history over time).
3. **Serves** it through an API and a web UI where you can browse, search, and
   see a product's price history on a chart.

The codebase is deliberately split into three independent services plus a
database, so that later phases (more supermarkets, price alerts, user accounts)
can be added without rewrites.

---

## 2. The big picture

```
                           ┌──────────────────────────────────────┐
                           │              YOUR BROWSER              │
                           │   http://localhost:3000  (the UI)      │
                           └───────────────┬────────────────────────┘
                                           │  HTTP (fetch) + JSON
                                           │  calls http://localhost:8000
                                           ▼
   ┌─────────────────┐          ┌──────────────────────┐
   │  FRONTEND        │          │  BACKEND (API)        │
   │  Next.js + React │          │  FastAPI (Python)     │
   │  port 3000       │          │  port 8000            │
   │                  │          │  /products /search    │
   │  - pages         │          │  /prices /health      │
   │  - React Query   │          └──────────┬───────────┘
   │  - Recharts      │                     │ SQLAlchemy ORM
   └─────────────────┘                      ▼
                                 ┌──────────────────────┐
   ┌─────────────────┐  writes   │  POSTGRESQL           │
   │  SCRAPER         │──────────▶│  port 5432            │
   │  Playwright+bs4  │  (shares  │  stores / products /  │
   │  (run on demand) │   schema) │  prices tables        │
   └────────┬────────┘           └──────────────────────┘
            │ drives a real Chrome
            ▼
   ┌─────────────────┐
   │  tesco.com       │   (public website, protected by Akamai bot defense)
   └─────────────────┘
```

**Key idea:** the three services never call each other's code directly. They
communicate only through:
- the **database** (scraper writes rows; backend reads them), and
- **HTTP + JSON** (frontend calls the backend's REST API).

That decoupling is what makes the system easy to extend.

### The technology choices at a glance

| Service  | Stack | Why |
|----------|-------|-----|
| Backend  | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic, Postgres (`psycopg` v3) | Fast, typed, auto-generates OpenAPI docs, clean migrations |
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind, React Query, Recharts | Modern React, server/client split, caching, charts |
| Scraper  | Playwright (real browser automation), BeautifulSoup (HTML parsing) | Tesco is a JS-heavy, bot-protected site — needs a real browser |
| Infra    | Docker Compose, PostgreSQL 16 | One-command local stack |

---

## 3. Repository layout

```
Price Pantry/
├── docker-compose.yml        # Defines db + backend + frontend + scraper services
├── .env / .env.example       # Shared configuration (DB creds, URLs, scraper knobs)
├── bootstrap.ps1             # One-shot local cold-start setup
│
├── backend/                  # ── FastAPI application ──
│   ├── app/
│   │   ├── main.py           # App entrypoint: creates FastAPI, CORS, mounts routes
│   │   ├── core/config.py    # Settings loaded from env (.env)
│   │   ├── db/
│   │   │   ├── base.py       # Declarative Base + timestamp mixin
│   │   │   └── session.py    # Engine, session factory, get_db() dependency
│   │   ├── models/           # SQLAlchemy ORM tables: Store, Product, Price
│   │   ├── schemas/          # Pydantic request/response shapes
│   │   ├── crud/             # Database query functions (the "repository" layer)
│   │   ├── api/routes/       # HTTP endpoints: health, products, search, prices
│   │   ├── api/router.py     # Bundles all routers together
│   │   └── seed.py           # Inserts 8 demo products so the app works empty
│   ├── alembic/              # Database migrations (schema versioning)
│   ├── tests/test_smoke.py   # API tests against in-memory SQLite
│   └── Dockerfile
│
├── scrapers/                 # ── Data collection ──
│   ├── run.py                # CLI entrypoint: orchestrates a scrape + persist
│   ├── base.py               # AbstractScraper — the interface future stores implement
│   ├── tesco/scraper.py      # The Tesco scraper (Playwright + the anti-bot logic)
│   ├── db.py                 # Scraper's own ORM models + persist() (mirrors backend)
│   ├── config.py             # Scraper settings from env
│   ├── scrape_tesco.ps1      # Helper: runs the scraper with real Chrome
│   └── Dockerfile
│
├── frontend/                 # ── Next.js web UI ──
│   ├── src/app/              # App Router pages: / , /search , /products/[id]
│   ├── src/components/       # UI building blocks (cards, chart, search bar…)
│   ├── src/lib/api.ts        # Typed client for the backend API
│   ├── src/lib/types.ts      # TypeScript mirrors of the API response shapes
│   └── Dockerfile
│
└── docs/                     # COLD_START.md, LOCAL_DEV.md, this file
```

---

## 4. The data model (the foundation)

Everything revolves around three tables. Defined as ORM classes in
[backend/app/models/](../backend/app/models) and created by the migration
[0001_initial_schema.py](../backend/alembic/versions/0001_initial_schema.py).

```
┌────────────┐        ┌──────────────────────┐        ┌───────────────────┐
│  stores    │ 1    ∞ │  products            │ 1    ∞ │  prices           │
├────────────┤────────├──────────────────────┤────────├───────────────────┤
│ id (PK)    │        │ id (PK)              │        │ id (PK)           │
│ name       │        │ store_id (FK)────────┼───────▶│ product_id (FK)   │
│ slug  (uq) │◀───────┤ external_id (Tesco#) │        │ price  (Numeric)  │
│ website_url│        │ name                 │        │ currency (GBP)    │
│ logo_url   │        │ brand / weight       │        │ unit_price (text) │
└────────────┘        │ category             │        │ in_stock (bool)   │
                      │ image_url            │        │ scraped_at  ⏱     │
                      │ url                  │        └───────────────────┘
                      │ UNIQUE(store_id,url) │
                      └──────────────────────┘
```

### Why prices are a *separate* table (the most important design decision)

A naive design would put `price` as a column on `products` and overwrite it each
scrape. Instead, **every scrape inserts a brand-new `prices` row**. That means:

- The product's **current price** = its most recent `prices` row.
- The product's **price history** = all its `prices` rows over time.

This is a classic **time-series** pattern. It's why the price-history chart
exists, and it's why you see the current price *rise* after re-scraping. See the
comment in [price.py](../backend/app/models/price.py):

> *"Every scrape inserts a new row rather than updating an existing one, which
> is exactly what Phase 3 (historical pricing) needs."*

### Two ways a product is identified

- `external_id` — Tesco's own product number (e.g. `254656543`). **Stable.**
- `url` — the product page link. Can change format (`/groceries/…` vs `/shop/…`).

The `UNIQUE(store_id, url)` constraint prevents duplicate listings, but the
scraper prefers matching on `external_id` when deciding whether a product already
exists (see §7.4) — more robust when Tesco changes its URL scheme.

---

## 5. End-to-end data flow (follow one request)

### A) "I open the home page"

```
Browser → GET localhost:3000/  (Next.js renders HomePage)
   │
   │  HomePage (page.tsx) runs a React Query:  api.listProducts(page=1, size=12)
   ▼
Browser → GET localhost:8000/products?page=1&page_size=12   (fetch, JSON)
   │
   ▼  FastAPI route list_products()  [api/routes/products.py]
   │     └─ crud.list_products(db, page, page_size)   [crud/product.py]
   │          └─ SELECT products + JOIN store + load prices, LIMIT/OFFSET
   │     └─ for each product: crud.to_read(p)  → attaches latest_price
   │     └─ Page.create(...)  → wraps items with total/page/pages
   ▼
Backend → JSON { items:[…], total, page, page_size, pages }
   │
   ▼  React Query caches it; ProductGrid renders ProductCard × 12
Browser shows the product grid.
```

### B) "I click a product"

```
Browser → localhost:3000/products/42   (Next.js dynamic route)
   │  ProductPage reads id from the URL, runs api.getProduct(42)
   ▼
Browser → GET localhost:8000/products/42
   ▼  route get_product() → crud.get_product() → crud.to_detail()
   │     to_detail() adds price_history = ALL price rows (newest first)
   ▼
Backend → JSON { …product…, latest_price, price_history:[…] }
   ▼
PriceHistoryChart reverses history → oldest-to-newest → draws a Recharts line.
```

That's the whole system in two traces. The rest of this document zooms into each
layer.

---

## 6. Backend deep dive (FastAPI)

The backend is organized in **layers**, each with a single responsibility. A
request flows *down* through them and data flows back *up*:

```
HTTP request
   │
   ▼  api/routes/*.py     ── HTTP concern: parse query params, status codes
   │                          Depends(get_db) injects a database session
   ▼  crud/*.py           ── Database concern: build & run SQLAlchemy queries
   │                          + convert ORM objects → Pydantic schemas
   ▼  models/*.py         ── ORM: Python classes mapped to tables
   ▼  PostgreSQL
   │
   ▲  schemas/*.py        ── Validation/serialization: the JSON shape returned
HTTP response (JSON)
```

### 6.1 Configuration — `core/config.py`

A Pydantic-Settings `Settings` object reads environment variables (and a `.env`
file). The important one is `database_url`. Two subtle but crucial details:

- **Default is `localhost`**, so running the backend natively "just works".
  Docker Compose overrides it with host `db` (the service name on the Docker
  network). This is the single most common source of "can't connect" confusion
  — covered in the troubleshooting tables.
- A **validator upgrades the driver**: a plain `postgresql://…` URL is rewritten
  to `postgresql+psycopg://…` so SQLAlchemy uses the modern psycopg v3 driver.

### 6.2 Database session — `db/session.py`

- `engine` — the connection pool (`pool_pre_ping=True` silently recovers dropped
  connections).
- `SessionLocal` — a factory that produces a `Session` (a unit of work).
- `get_db()` — a **FastAPI dependency** (generator): it opens a session, `yield`s
  it to the route, and **always closes it** in `finally`. Every endpoint gets a
  fresh session per request via `Depends(get_db)`.

### 6.3 Models — `models/`

Plain SQLAlchemy 2.0 declarative classes (`Store`, `Product`, `Price`) with typed
`Mapped[...]` columns and **relationships**:

- `Store.products` ↔ `Product.store`
- `Product.prices` ↔ `Price.product`

The relationship that makes "current price" trivial:

```python
# models/product.py
prices: Mapped[list["Price"]] = relationship(
    back_populates="product",
    cascade="all, delete-orphan",
    order_by="Price.scraped_at.desc()",   # newest first, always
)
```

Because prices are always ordered newest-first, `product.prices[0]` is the latest
price everywhere in the code. `cascade="all, delete-orphan"` means deleting a
product deletes its prices too.

`TimestampMixin` (in `db/base.py`) adds DB-managed `created_at` / `updated_at`.

### 6.4 Schemas — `schemas/`

Pydantic models define the **JSON contract** — what the API accepts and returns,
separate from the DB models:

- `StoreRead`, `PriceRead` — straightforward row representations.
- `ProductRead` — list view: product fields + its `store` + a derived
  `latest_price` and `currency`.
- `ProductDetail(ProductRead)` — detail view: everything above **plus**
  `price_history: list[PriceRead]`.
- `Page[T]` (in `common.py`) — a **generic pagination envelope**
  `{ items, total, page, page_size, pages }`. `Page.create()` computes the page
  count with `ceil(total / page_size)`.

`model_config = ConfigDict(from_attributes=True)` lets Pydantic read directly
from ORM objects.

### 6.5 CRUD — `crud/product.py` (the interesting layer)

This is the "repository" — all SQL lives here, keeping routes thin.

- `_base_query()` — selects products and **eager-loads** related data to avoid
  the N+1 query problem:
  - `joinedload(Product.store)` — one JOIN for the store.
  - `selectinload(Product.prices)` — a second query fetching all prices for the
    page's products in one go.
- `list_products()` / `search_products()` — apply filters, run a **count** query
  for the total, then a **LIMIT/OFFSET** query for the page. Search uses
  `ILIKE '%term%'` on name **or** brand (case-insensitive).
- `to_read()` / `to_detail()` — convert an ORM `Product` into the Pydantic
  schema, deriving `latest_price` from `product.prices[0]` (newest, thanks to the
  relationship ordering).

> **Note:** `.unique()` is required on these queries because `joinedload` can
> produce duplicate parent rows; it de-duplicates them in Python.

### 6.6 Routes — `api/routes/`

Thin HTTP adapters. Each declares its `response_model` (so FastAPI validates
output and documents it), validates query params, calls CRUD, and returns.

| Method & path          | Route file     | Returns |
|------------------------|----------------|---------|
| `GET /health`          | `health.py`    | `{status, database}` — also pings the DB with `SELECT 1` |
| `GET /products`        | `products.py`  | `Page[ProductRead]` (supports `page`, `page_size`, `category`) |
| `GET /products/{id}`   | `products.py`  | `ProductDetail` (404 if missing) |
| `GET /search?q=`       | `search.py`    | `Page[ProductRead]` |
| `GET /prices`          | `prices.py`    | `list[PriceRead]` (optional `product_id` filter) |

`api/router.py` bundles them; `main.py` includes that bundle, adds **CORS**
(so the browser on :3000 may call :8000), and exposes `/` and the auto-generated
Swagger docs at **`/docs`**.

### 6.7 Migrations & seed

- **Alembic** ([alembic/env.py](../backend/alembic/env.py)) versions the schema.
  It injects `settings.database_url` and imports `app.models` so
  `Base.metadata` knows every table. `alembic upgrade head` applies
  [0001_initial_schema.py](../backend/alembic/versions/0001_initial_schema.py),
  which creates the three tables and their indexes.
- **Seed** ([seed.py](../backend/app/seed.py)) inserts the Tesco store + 8 demo
  products so the UI isn't empty before you scrape. It's **idempotent**: products
  are matched by URL, and a price is only added if the product has none — so
  re-running on every boot won't stack duplicates.

On Docker boot the backend runs all three in sequence:
`alembic upgrade head && python -m app.seed && uvicorn …` (see
[docker-compose.yml](../docker-compose.yml)).

---

## 7. Scraper deep dive (the hard part)

Tesco's site is a React app behind **Akamai Bot Manager**. You cannot just
`GET` a URL with `requests` — you'd get `403 Access Denied`. The scraper drives a
**real browser** with Playwright, gets past the bot defense, then parses the
rendered HTML with BeautifulSoup.

### 7.1 Orchestration — `run.py` + `base.py`

`run.py` is the CLI. It builds a `TescoScraper`, calls `.run()`, and persists the
results (unless `--dry-run`). Flags: `--categories`, `--max-pages`, `--headful`,
`--dry-run`.

`base.py` defines `AbstractScraper` — the **contract** every store scraper
implements. Its `run()` loops categories, calls `scrape_products()`, and
**de-duplicates by URL**. This is the extension point for Phase 2:

```
          AbstractScraper  (defines run(), dedup, the 3 abstract methods)
                │
   ┌────────────┼─────────────┬──────────────┐
 Tesco        Asda       Sainsbury's     Morrisons   ← future, no change to run.py
```

Adding a supermarket = subclass `AbstractScraper`, implement three methods. The
persistence and orchestration stay identical.

### 7.2 Getting past Akamai — the `_warmup()` method

This is the cleverest part of the codebase. Akamai sets a cookie called
**`_abck`**. On a fresh/automated session it holds an *unvalidated* token
(contains `~-1~`) and protected pages return `403`. It only becomes *validated*
after Akamai's JavaScript sensor observes "human-like" behavior and POSTs its
telemetry back.

So before scraping, `_warmup()`:

1. Loads the Tesco **homepage** (not the protected search page).
2. Accepts the cookie banner (privacy-preserving — only what's needed to view the
   grid).
3. **Polls the `_abck` cookie for ~22s** while moving the mouse and scrolling
   randomly, waiting for it to drop the `~-1~` marker (= validated).
4. Visits the **groceries landing page** in-session to further legitimize things.

The cookies live on the browser **context**, so they carry over automatically to
the search requests that follow.

### 7.3 The fingerprint & the real-Chrome trick — `run()`

Several layers of disguise so the browser doesn't look automated:

- **Realistic context**: Windows Chrome user-agent, `en-GB` locale,
  `Europe/London` timezone, a normal 1366×900 viewport, `Accept-Language` header.
- **Launch args**: `--disable-blink-features=AutomationControlled`.
- **Stealth JS** (`_STEALTH_JS`, injected before page scripts run): hides
  `navigator.webdriver`, fakes `languages`/`plugins`, adds `window.chrome`.

But the decisive factor (learned during development): **bundled Chromium still
fails Akamai; the user's real installed Chrome passes.** So `run()` supports:

```
PW_CHANNEL=chrome          → use real Chrome instead of bundled Chromium
PW_USER_DATA_DIR=<path>    → a persistent profile (looks like a returning user)
```

When `PW_USER_DATA_DIR` is set it uses `launch_persistent_context`; otherwise a
normal ephemeral context. The helper [scrape_tesco.ps1](../scrapers/scrape_tesco.ps1)
sets these for you. **This is why the real scrape must run on the host (with
Chrome + a display), not in the headless Docker container.**

### 7.4 Fetch → parse → normalize — `scrape_products`, `_fetch`, `_parse`

For each category and page (`1..max_pages`):

1. **`_fetch(url)`** navigates to the search URL, accepts cookies, and waits for
   the product grid using a **list of fallback selectors** (Tesco changes its
   markup often), then returns the rendered HTML. Between pages it sleeps a random
   1.5–3.5s to be polite.
2. **`_parse(html)`** uses BeautifulSoup to find product tiles (again with
   selector fallbacks), and for each tile extracts:
   - `external_id` + `url` from the `/products/(\d+)` link (regex),
   - `name` (several selector fallbacks),
   - `price` via regex `£\s?(\d+(?:\.\d{1,2})?)` on the tile's text,
   - `unit_price` (e.g. `£0.65/100g`) via regex,
   - `image_url`, and heuristic `brand` (first token / "Tesco") and `weight`
     (regex for `2L`, `800g`, `6x25g`, …).

Each becomes a `ScrapedProduct` dataclass (defined in `db.py`) — the scraper's
normalized output, independent of Tesco's HTML.

### 7.5 Persistence — `db.py::persist()`

`run.py` opens a session, ensures the Tesco `Store` row exists
(`get_or_create_store`), then `persist()`s the list. For each scraped product:

1. **Find existing** product: first by `(store_id, external_id)` — the robust
   key — then fall back to `(store_id, url)`.
2. If none, **insert** a new `products` row; otherwise **refresh** its mutable
   metadata (name, brand, weight, category, image, and the url).
3. **Always insert a new `prices` row** (when a price was found) — this is what
   builds the time-series.

Returns `(new_products, price_rows)` which `run.py` prints.

> The scraper defines its **own copy** of the ORM models in `db.py` rather than
> importing the backend's. This keeps the services independent at the cost of a
> little duplication — the docstring flags extracting a shared package as a Phase
> 2 cleanup. The scraper never creates tables; the backend's Alembic owns the
> schema.

### 7.6 `debug_fetch.py`

A small diagnostic that loads a single search URL and prints the HTTP status,
whether `_abck` validated, which selectors matched, and a body preview — used
when a run returns zero products to tell "blocked" apart from "selectors changed".

---

## 8. Frontend deep dive (Next.js)

A Next.js 15 **App Router** app in TypeScript. Styling is Tailwind; data fetching
is React Query; charts are Recharts.

### 8.1 Shell — `layout.tsx` + `providers.tsx`

`layout.tsx` is the root HTML shell (header, `<main>`, footer) wrapping every
page. It mounts `Providers`, which creates a single **React Query** `QueryClient`
(`staleTime: 30s`, no refetch on window focus). React Query handles caching,
loading, and error states so pages don't manage fetch state by hand.

### 8.2 The API client — `lib/api.ts` + `lib/types.ts`

`api.ts` is the **only** place that talks to the backend. It builds URLs, calls
`fetch` with `cache: "no-store"` (always fresh prices), throws on non-OK, and
returns typed JSON. `types.ts` mirrors the backend's Pydantic schemas as
TypeScript interfaces, so the data is typed end-to-end.

The base URL comes from `process.env.NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`). **Gotcha:** `NEXT_PUBLIC_*` vars are **inlined at build
time**, which is why the frontend Dockerfile takes it as a build `ARG` — the
browser, not the container, calls the API, so it must be the host-visible URL.

### 8.3 Pages (App Router, file = route)

| File | Route | What it does |
|------|-------|--------------|
| `app/page.tsx` | `/` | Hero + search bar; React Query `listProducts(page)`; shows skeleton/error/grid + pagination |
| `app/search/page.tsx` | `/search?q=` | Reads `q` from the URL, `search(q, page)`; resets to page 1 when `q` changes; wrapped in `<Suspense>` because it uses `useSearchParams` |
| `app/products/[id]/page.tsx` | `/products/:id` | `getProduct(id)`; renders image, details, current price, "View on Tesco", and the price-history chart |

All three are **client components** (`"use client"`) because they use hooks
(React Query, URL params).

### 8.4 Components

- `ProductGrid` → maps products to `ProductCard`s (responsive 2/3/4 columns).
- `ProductCard` → image, category badge, name, `PriceTag`, weight; links to the
  detail page.
- `PriceTag` + `lib/utils.ts::formatPrice` → formats numbers as GBP via
  `Intl.NumberFormat`, or `—` when there's no price.
- `SearchBar` → controlled input that routes to `/search?q=…` on submit.
- `Pagination` → Prev/Next with page indicator; hides itself when there's one
  page.
- `PriceHistoryChart` → the payoff. Reverses history to oldest-first, maps to
  `{date, price}`, and draws a Recharts line. **If there are fewer than 2 points
  it shows a "not enough data yet" message** — which is why a product needs ≥2
  scrapes before the chart appears.
- `components/ui/*` → small styled primitives (button, card, input).

---

## 9. How the services connect (and the two classic gotchas)

```
                     localhost (your machine)                 Docker network
                     ─────────────────────────                ───────────────
 browser → :3000 (frontend)
 browser → :8000 (backend)          ← NEXT_PUBLIC_API_URL      backend → db:5432
 scraper → :5432 (DB, native run)      points the BROWSER      (DATABASE_URL uses
                                       at :8000                  host "db")
```

1. **`db` vs `localhost`.** Inside Docker, services reach Postgres at host `db`
   (the compose service name). Running natively, there's no `db` host — it's
   `localhost`. The backend's config defaults to `localhost` and Compose
   overrides it to `db`. A `could not translate host name "db"` error means a
   native process picked up the Docker `.env`.

2. **`NEXT_PUBLIC_API_URL` is build-time.** It's compiled into the browser bundle,
   so it must be the URL the **browser** can reach (`http://localhost:8000`), not
   an internal Docker address. That's why it's both a Docker build `ARG` and a
   runtime env var.

---

## 10. Configuration reference

All configuration is environment variables (see [.env.example](../.env.example)):

| Variable | Used by | Meaning |
|----------|---------|---------|
| `POSTGRES_USER/PASSWORD/DB` | db (Compose) | Postgres credentials |
| `DATABASE_URL` | backend, scraper | SQLAlchemy connection string (`db` in Docker, `localhost` native) |
| `CORS_ORIGINS` | backend | Comma-separated origins allowed to call the API |
| `NEXT_PUBLIC_API_URL` | frontend | Browser-facing backend URL (build-time inlined) |
| `SCRAPER_MAX_PAGES` | scraper | Result pages to walk per category |
| `SCRAPER_HEADLESS` | scraper | Headless vs visible browser |
| `PW_CHANNEL` / `PW_USER_DATA_DIR` | scraper | Use real Chrome + persistent profile (the Akamai bypass) |

---

## 11. Running it (pointers)

- **Full cold start / setup:** [COLD_START.md](COLD_START.md) (`bootstrap.ps1`).
- **Day-to-day local dev:** [LOCAL_DEV.md](LOCAL_DEV.md).
- **In short:** `docker compose up -d db` → `cd backend; .\dev.ps1` →
  `cd frontend; npm run dev` → scrape with
  `cd scrapers; .\scrape_tesco.ps1 milk bread eggs`.
- **Tests:** `cd backend; .\.venv\Scripts\python.exe -m pytest` — 5 smoke tests
  run the whole API against in-memory SQLite (no Postgres needed), verifying
  routes, schemas, pagination, search, 404s, and price history wiring.

---

## 12. Why it's built this way (design rationale & roadmap)

- **Three decoupled services.** Scraping, serving, and UI have very different
  runtimes and failure modes. Keeping them separate (talking only via DB + HTTP)
  means the API stays up on seed/old data even when a scrape fails, and new
  supermarkets or a mobile client can be added without touching the others.
- **Time-series prices.** Storing every observation (not overwriting) is what
  enables price history and, later, price-drop alerts — the core value of a
  comparison site.
- **`AbstractScraper` + normalized `ScrapedProduct`.** The pipeline
  (dedup → persist) is store-agnostic; only parsing is store-specific. Phase 2 is
  "add subclasses".
- **Defensive scraping.** Multiple selector fallbacks, regex price extraction,
  and the warm-up/real-Chrome strategy acknowledge that scraping a hostile,
  frequently-changing site is the riskiest part — so failures degrade gracefully
  (zero products → keep old data) and are diagnosable (`debug_fetch.py`).

### Phase roadmap (hinted throughout the code)

| Phase | Feature | Where it slots in |
|-------|---------|-------------------|
| 1 ✅ | Tesco scrape + API + UI | this build |
| 2 | More supermarkets | new `AbstractScraper` subclasses; extract shared ORM package |
| 3 | Historical pricing / alerts | already enabled by the `prices` time-series |
| 6 | Cross-store product matching | a matching layer linking `products` rows — no schema change needed |

---

## 13. Glossary

- **ORM** — Object-Relational Mapper (SQLAlchemy); Python classes ↔ DB tables.
- **Migration** — a versioned, repeatable schema change (Alembic).
- **Dependency injection** — FastAPI's `Depends(get_db)` supplying a DB session
  per request.
- **Eager loading** — fetching related rows up front (`joinedload`/`selectinload`)
  to avoid many small queries (the N+1 problem).
- **Time-series** — storing successive observations over time rather than a
  single current value.
- **`_abck`** — Akamai's bot-detection cookie; must "validate" before Tesco
  serves protected pages.
- **Headless/headful** — a browser with no visible window vs a visible one.
- **App Router** — Next.js's file-based routing where each `page.tsx` is a route.
- **React Query** — client library that fetches, caches, and tracks
  loading/error state for server data.
```
