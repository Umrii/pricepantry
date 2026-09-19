# Grocery Price Intelligence Platform (UK)

> A data engineering and AI-powered platform that aggregates grocery prices from major UK supermarkets, compares products, tracks historical prices, and recommends the cheapest shopping basket.

---

# Goals

## Primary Goal

Build a production-quality portfolio project demonstrating:

- Backend Engineering
- Data Engineering
- Web Scraping
- Database Design
- API Development
- Cloud Deployment
- AI-powered Product Matching
- Data Analytics

---

# Tech Stack

## Frontend

- Next.js
- TypeScript
- TailwindCSS
- shadcn/ui
- React Query
- Recharts

---

## Backend

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic

---

## Database

- PostgreSQL
- pgvector (later)

---

## Data Engineering

- Playwright
- BeautifulSoup
- Pandas
- Celery
- Redis
- Airflow (Phase 2)

---

## AI

- Sentence Transformers
- RapidFuzz
- OpenAI API (optional)
- pgvector

---

## DevOps

- Docker
- Docker Compose
- GitHub Actions
- AWS EC2
- AWS S3

---

# Phase 1 - MVP

Estimated Time:
2-3 weeks

## Objective

Create a working comparison website using data from **one supermarket**.

---

### Tasks

### Project Setup

- Create GitHub repository
- Dockerize application
- Setup FastAPI
- Setup Next.js
- Configure PostgreSQL
- Configure Alembic

---

### Database

Tables

- products
- stores
- prices

---

### Scraper

Target:

- Tesco

Collect:

- Product Name
- Brand
- Price
- Weight
- Category
- Image
- URL

Store into PostgreSQL.

---

### Backend API

Endpoints

GET /products

GET /products/{id}

GET /search

GET /prices

---

### Frontend

Pages

- Home
- Search
- Product Details

Features

- Search
- Pagination
- Price display

---

# Deliverable

✅ Live application

---

# Phase 2 - Multi-store Support

Estimated Time:
2 weeks

Add

- Asda
- Sainsbury's
- Morrisons

Update scraper architecture.

```
AbstractScraper
    |
-------------------------
|        |       |      |
Tesco  Asda  Sainsbury Morrisons
```

Each scraper implements:

```
scrape_products()

scrape_categories()

scrape_price()
```

---

# Deliverable

Users can compare prices between supermarkets.

---

# Phase 3 - Historical Pricing

Objective

Track prices over time.

Instead of updating prices:

```
Milk

£1.45
```

Store

```
Milk

2026-08-01 £1.45

2026-08-02 £1.39

2026-08-03 £1.39
```

Features

- Price History
- Lowest Ever Price
- Average Price
- Price Change %

Dashboard

- Line charts
- Category inflation

---

# Deliverable

Historical analytics dashboard.

---

# Phase 4 - Basket Comparison

Objective

Allow users to compare an entire shopping basket.

Example

Shopping List

- Eggs
- Bread
- Milk
- Chicken

Output

Tesco

£18.20

Asda

£17.90

Morrisons

£18.60

Cheapest

Asda

---

Stretch Goal

Hybrid Basket

Buy

Eggs → Aldi

Chicken → Tesco

Milk → Lidl

Total Savings

£3.90

---

# Deliverable

Basket optimizer.

---

# Phase 5 - Data Engineering

Introduce a real data pipeline.

Architecture

```
Playwright
      │
      ▼
Raw JSON
      │
Cleaning
      │
Normalization
      │
Warehouse
      │
Analytics
```

New Components

- Redis
- Celery
- Daily Scheduler
- S3 Raw Storage

Store

```
raw/

processed/

analytics/
```

---

# Deliverable

Automated daily ETL pipeline.

---

# Phase 6 - AI Product Matching

Problem

```
Coca Cola Zero 2L

Coke Zero Bottle 2L

Coca-Cola Zero Sugar 2 Litre
```

Need to identify them as the same product.

Stage 1

RapidFuzz

Stage 2

Sentence Embeddings

Stage 3

Vector Search

Store embeddings using

pgvector

---

Deliverable

Automatic cross-store product matching.

---

# Phase 7 - AI Shopping Assistant

Examples

User

> Cheapest ingredients for chicken biryani

User

> Find healthy breakfast under £15

User

> Show protein sources below £5

Pipeline

```
User Question

↓

LLM

↓

Database

↓

Response
```

---

# Phase 8 - Analytics Dashboard

Visualisations

- Price trends
- Inflation by category
- Cheapest supermarket
- Most discounted products
- Weekly changes
- Brand comparison

---

# Future Ideas

## User Accounts

- Saved baskets
- Favourite products
- Price alerts

---

## Notifications

Email

Push

Telegram

---

## OCR

Upload receipt

↓

Parse receipt

↓

Track spending

---

## Machine Learning

Predict

- Future prices
- Sale periods
- Inflation

---

## Mobile App

React Native

---

# Suggested Repository Structure

```
grocery-price-platform/

backend/

frontend/

scrapers/

workers/

shared/

docker/

docs/

infra/

data/

tests/
```

---

# Resume Highlights

This project demonstrates

- Python
- FastAPI
- PostgreSQL
- Docker
- Playwright
- SQLAlchemy
- Redis
- Celery
- Data Engineering
- ETL Pipelines
- AI Product Matching
- REST APIs
- Cloud Deployment
- System Design

---

# Definition of Success

Minimum Success

- Compare prices from 3+ supermarkets
- Search products
- Historical price tracking
- Live deployment

Stretch Success

- AI-powered product matching
- Basket optimization
- Daily automated ETL pipeline
- Analytics dashboard
- Cloud deployment with CI/CD
- Production-quality architecture