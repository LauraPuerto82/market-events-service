# Market Events Service

Build a FastAPI service that aggregates financial market events (earnings, dividends, splits) from multiple providers and exposes a unified API.

**Time:** 2-3 days

## What You're Building

A service that:

- Fetches events from two external providers (simulated in `providers/`)
- Normalizes their different formats into a unified schema
- Stores in PostgreSQL with deduplication
- Caches with Redis
- Exposes a REST API

## API Spec

### `GET /api/v1/events`

| Parameter    | Type   | Required | Description                                 |
| ------------ | ------ | -------- | ------------------------------------------- |
| `symbols`    | string | No       | Comma-separated (e.g., `AAPL,MSFT`)         |
| `event_type` | string | No       | `earnings`, `dividend`, `economic`, `split` |
| `from_date`  | string | No       | YYYY-MM-DD                                  |
| `to_date`    | string | No       | YYYY-MM-DD                                  |
| `limit`      | int    | No       | Default 50, max 500                         |
| `offset`     | int    | No       | Pagination offset                           |

Response:

```json
{
  "data": [
    {
      "id": "uuid",
      "symbol": "AAPL",
      "event_type": "earnings",
      "event_date": "2026-02-20",
      "title": "Q1 2026 Earnings Release",
      "details": {},
      "created_at": "2026-02-15T10:30:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

Include `X-Cache: HIT` or `X-Cache: MISS` header.

### `GET /api/v1/events/{event_id}`

Single event by ID.

### `POST /api/v1/events/sync`

```json
{
  "symbols": ["AAPL", "MSFT"],
  "force": false
}
```

Response:

```json
{
  "status": "completed",
  "symbols_synced": ["AAPL", "MSFT"],
  "symbols_skipped": [],
  "events_created": 12,
  "events_updated": 3,
  "errors": []
}
```

- `force: false` skips symbols synced in the last hour
- `force: true` always fetches fresh

### `GET /api/v1/health`

Service health with Redis/DB status.

## Providers

The `providers/` folder contains two simulated external APIs. They have different interfaces and return different data formats.

**Don't modify anything in `providers/`** - treat them like external APIs you can't control.

Check the docstrings for details on rate limits and error handling.

## Data Model

Design your schema considering:

- Both providers might return the same real-world event with different IDs
- You need deduplication
- Query by symbol, date range, type

## Deliverables

1. Working service (`docker-compose up` should work)
2. Your README with setup instructions and architecture notes
3. Tests for core logic

## Setup

```bash
docker-compose up -d
cp .env.example .env
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

## Questions?

If something's unclear, document your assumptions and move on.

---

## Implementation

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/LauraPuerto82/market-events-service.git
cd market-events-service

# 2. Start PostgreSQL and Redis
docker-compose up -d

# 3. Copy environment variables
cp .env.example .env        # Linux/macOS
copy .env.example .env      # Windows

# 4. Install dependencies
poetry install

# 5. Run database migrations
poetry run alembic upgrade head

# 6. Start the service
poetry run uvicorn app.main:app --reload
```

The service runs at `http://localhost:8000`. Interactive API docs are available at `http://localhost:8000/docs`.

### Running the tests

```bash
poetry run pytest
```

The test suite requires Docker to be running (deduplication tests use the real database). All other tests are fully isolated with mocks.

### Architecture

The project follows a layered architecture:

```
app/
├── api/routes/       # HTTP layer — request/response handling
├── services/         # Business logic — orchestration, caching, sync
├── repositories/     # Data access — SQL queries, upserts
├── integrations/     # Provider clients and data normalizers
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic request/response schemas
├── core/             # Configuration (pydantic-settings)
└── database/         # Engine, session factory
```

Each layer only depends on the layer below it. Routes depend on services, services depend on repositories and integrations, repositories depend on models.

### Key design decisions

**Deduplication via natural key**
Events are deduplicated on `(symbol, event_type, event_date)`. Both providers may return the same real-world event with different internal IDs. This constraint ensures only one row exists per event regardless of source. The upsert updates `title` and `details` on conflict, so the most recent data wins.

**Concurrent provider fetches**
Each symbol is fetched from both providers simultaneously using `asyncio.gather()`. Provider errors are captured individually. If one provider fails, the other's results are still stored and the error is reported in the response without aborting the sync.

**Retry strategy**

- Provider A: respects `RateLimitError.retry_after` for rate limits; exponential backoff (`2^attempt` seconds) for unavailability
- Provider B: fixed delay on timeout, up to 2 retries; stuck pagination detection to avoid infinite loops

**Cache-aside pattern**
`GET /api/v1/events` checks Redis first. On a miss, the database is queried and the result is cached with a 5-minute TTL. A successful sync invalidates all `events:*` keys so stale data is never served. The `X-Cache: HIT/MISS` header is always included in the response.

**Sync cooldown**
By default, a symbol is skipped if it was synced within the last hour. The `force: true` flag bypasses this check, useful for manual refreshes.

**Timezone handling**
All datetime columns use `DateTime(timezone=True)` and all Python datetimes use `datetime.now(UTC)`. Naive datetimes are never used.

### Assumptions

- Provider B's `scheduled_at` field is used as the event date (date part only, time discarded)
- Provider B categories not in the known mapping are passed through unchanged as the event type
- The `details` field stores provider-specific structured data as JSON with no enforced schema
- The health endpoint checks liveness of both PostgreSQL and Redis; it returns 503 if either is unreachable
