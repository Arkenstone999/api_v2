# CrewSAS Translation API

SAS to PySpark/SQL translation service powered by [crewAI](https://crewai.com). Clean FastAPI implementation with authentication, rate limiting, and project management.

## Quick Start

### 1. Installation

```bash
pip install uv
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 2. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `SECRET_KEY` - JWT secret (already set)
- `AZURE_OPENAI_API_KEY` - Azure OpenAI key
- `AZURE_OPENAI_ENDPOINT` - Azure endpoint
- `AZURE_OPENAI_API_VERSION` - API version
- `AZURE_OPENAI_DEPLOYMENT` - Model deployment

### 3. Initialize Database

```bash
uv run python -m crewsastosparksql.api.migrate_db
```

### 4. Start API

```bash
uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Test

```bash
./test_api.sh
```

## API Endpoints

```
POST /api/auth/register              Register user
POST /api/auth/login                 Login (returns JWT)
POST /api/translate                  Quick translate (JSON)
POST /api/translate/file             Translate .sas file
POST /api/projects                   Create project
POST /api/projects/{id}/files        Upload .sas files
POST /api/projects/{id}/translate    Start translation
GET  /api/dashboard                  Get metrics
GET  /health                         Health check
```

## CLI Usage

```bash
uv run python -m crewsastosparksql.main path/to/file.sas
uv run python -m crewsastosparksql.main examples/cars.sas
```

## Understanding Your Crew

The CrewSasToSparkSql Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Support

For support, questions, or feedback regarding the Crewsastosparksql Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
