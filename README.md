# AI-Powered Restaurant Recommendation System

A Zomato-inspired restaurant recommendation service that combines structured restaurant data from Hugging Face with [Groq](https://groq.com/) LLM inference to deliver personalized, explainable suggestions.

## Documentation

- [context.md](docs/context.md) — product requirements
- [architecture.md](docs/architecture.md) — technical architecture
- [implementation-plan.md](docs/implementation-plan.md) — phase-wise build plan
- [edge-cases.md](docs/edge-cases.md) — corner scenarios and test matrix

## Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com/)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then set GROQ_API_KEY
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (required for recommendations) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model for ranking and explanations |
| `GROQ_TEMPERATURE` | `0.3` | Sampling temperature |
| `HF_DATASET_NAME` | `ManikaSaini/zomato-restaurant-recommendation` | Hugging Face dataset |
| `DATA_CACHE_PATH` | `data/restaurants.parquet` | Local cache for preprocessed data |
| `MAX_CANDIDATES_FOR_LLM` | `20` | Max restaurants sent to the LLM |
| `TOP_K_RECOMMENDATIONS` | `5` | Number of recommendations to return |
| `BUDGET_LOW_MAX` | `500` | Upper bound (INR) for low budget tier |
| `BUDGET_MEDIUM_MAX` | `1500` | Upper bound (INR) for medium budget tier |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed frontend origins |

## Verify Installation (Phase 0)

```bash
python -c "from src.config import settings; print(settings.groq_model)"
pytest tests/test_config.py -v
```

## Verify Data Layer (Phase 1)

```bash
pytest tests/test_preprocessor.py tests/test_repository.py -v
python -c "
from src.data.loader import load_restaurants
from src.data.repository import RestaurantRepository
repo = RestaurantRepository(load_restaurants())
print(len(repo.get_all()), 'restaurants')
print(repo.get_locations()[:5])
"
```

First run downloads from Hugging Face and caches to `data/restaurants.parquet`. Subsequent runs load from cache.

## Verify Filter Layer (Phase 2)

```bash
pytest tests/test_filter.py -v
python -c "
from src.data.loader import load_restaurants
from src.data.repository import RestaurantRepository
from src.services.filter import RestaurantFilter
from src.services.preferences import PreferenceValidator
from src.models.preferences import UserPreferences

repo = RestaurantRepository(load_restaurants())
validator = PreferenceValidator(repo.get_locations(), repo.get_cuisines())
prefs = validator.validate({'location': 'Bangalore', 'budget': 'medium', 'min_rating': 4.0, 'cuisine': 'Italian'})
result = RestaurantFilter().filter(repo.get_all(), prefs)
print(len(result.candidates), 'candidates')
"
```

## Run API (Phase 4)

Start the FastAPI backend:

```bash
uvicorn src.api.app:app --reload --port 8000
# or
python src/main.py
```

OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Service status and dataset loaded flag |
| `GET` | `/api/v1/locations` | Distinct locations for dropdowns |
| `GET` | `/api/v1/cuisines` | Distinct cuisines for dropdowns |
| `POST` | `/api/v1/recommend` | Get ranked recommendations |

### Example Requests

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/locations
curl http://localhost:8000/api/v1/cuisines
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"location":"Indiranagar","budget":"medium","cuisine":"Italian","min_rating":4.0}'
```

### CLI (optional)

```bash
python -m src.ui.cli
```

## Verify API (Phase 4)

```bash
pytest tests/test_api.py -v
pytest -v
```

## Run Frontend (Phases 5–7)

Requires Node.js 20.9+ and the backend running on port 8000.

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). See [frontend/README.md](frontend/README.md) for details.

## Project Structure

```
frontend/               # Next.js desktop UI (Phases 5–7)
src/
├── config.py           # Centralized settings
├── models/             # Pydantic data models
├── data/               # Dataset loader, preprocessor, repository
│   ├── loader.py
│   ├── preprocessor.py
│   └── repository.py
├── services/           # Filter, prompt builder, Groq client, recommendation
├── api/                # FastAPI app, routes, schemas (Phase 4)
│   ├── app.py
│   ├── routes.py
│   └── schemas.py
└── ui/                 # CLI (Phase 4)
tests/
docs/
```

## License

MIT (adjust as needed)
