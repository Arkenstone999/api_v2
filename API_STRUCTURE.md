# CrewSAS Translation API - Structure & Endpoints

## Architecture

```
api/
├── app.py                          FastAPI application
├── dependencies.py                 Auth, DB, rate limit dependencies
├── database.py                     SQLAlchemy setup
├── db_models.py                    Database models
├── models.py                       Pydantic request/response models
├── routes/
│   ├── auth.py                     Authentication endpoints
│   ├── projects.py                 Project management
│   ├── tasks.py                    Task management
│   ├── translate.py                Translation endpoints
│   └── dashboard.py                Dashboard metrics
├── services/
│   ├── translation_service.py      Core translation logic
│   ├── project_service.py          Project business logic
│   └── task_service.py             Task business logic
└── utils/
    └── auth.py                     Auth utilities
```

## Endpoints

### Root & Health
```
GET  /                      API information
GET  /health                Health check with DB status
```

### Authentication (`/api/auth`)
```
POST /api/auth/register              Register new user
POST /api/auth/login                 Login user (returns JWT)
GET  /api/auth/me                    Get current user info
GET  /api/auth/usage                 Get usage statistics
POST /api/auth/regenerate-api-key    Regenerate API key
```

### Translation (`/api`)
```
POST /api/translate                  Quick translate (JSON payload)
POST /api/translate/file             Translate .sas file upload
```

### Projects (`/api/projects`)
```
GET    /api/projects                 List all projects
POST   /api/projects                 Create new project
GET    /api/projects/{id}            Get project details
PATCH  /api/projects/{id}            Update project
DELETE /api/projects/{id}            Delete project
POST   /api/projects/{id}/files     Upload .sas files to project
POST   /api/projects/{id}/translate  Start translation (async)
```

### Tasks (`/api/tasks`)
```
GET   /api/tasks/{id}                Get task details
PATCH /api/tasks/{id}                Update task
POST  /api/tasks/{id}/translate      Translate single task (async)
GET   /api/tasks/{id}/comments       List comments
POST  /api/tasks/{id}/comments       Add comment
```

### Dashboard (`/api/dashboard`)
```
GET /api/dashboard                   Get statistics and recent activity
```

## Authentication Methods

1. **JWT Bearer Token**: Obtain via `/api/auth/login`
   ```
   Authorization: Bearer <token>
   ```

2. **API Key**: Use your API key from registration
   ```
   X-API-Key: <your-api-key>
   ```

## Example Usage

### 1. Register & Login
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","full_name":"User"}'

curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### 2. Quick Translation (Text)
```bash
curl -X POST http://localhost:8000/api/translate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"sas_code":"DATA test; SET input; RUN;"}'
```

### 3. File Translation
```bash
curl -X POST http://localhost:8000/api/translate/file \
  -H "Authorization: Bearer <token>" \
  -F "file=@example.sas"
```

### 4. Project-Based Translation
```bash
# Create project
curl -X POST http://localhost:8000/api/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Project","description":"Test","source_type":"sas-code","target_type":"pyspark"}'

# Upload files
curl -X POST http://localhost:8000/api/projects/{project_id}/files \
  -H "Authorization: Bearer <token>" \
  -F "files=@file1.sas" \
  -F "files=@file2.sas"

# Start translation
curl -X POST http://localhost:8000/api/projects/{project_id}/translate \
  -H "Authorization: Bearer <token>"

# Check project status
curl -X GET http://localhost:8000/api/projects/{project_id} \
  -H "Authorization: Bearer <token>"
```

## Database Models

### User
- Authentication
- API key
- Monthly request limit
- Usage tracking

### Project
- Name, description
- Source type (sas-code, sas-eg)
- Target type (sql, pyspark)
- Status, progress
- File count

### ConversionTask
- Project relation
- Source code, target code
- Status, version
- Rationale
- Execution timestamps
- Error messages

### Comment
- Task relation
- Author, content
- Line number
- Resolved status

## Rate Limiting

- Tracked per user per month
- Default: 1000 requests/month
- Headers returned:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`

## Translation Flow

1. **Input**: SAS code (text or file)
2. **Processing**:
   - CrewAI agents analyze code
   - Platform decision (SQL vs PySpark)
   - Code translation
   - Validation & testing
   - Review & approval
3. **Output**: Translated code + rationale

## Error Handling

- 400: Bad request (invalid input)
- 401: Unauthorized (missing/invalid auth)
- 403: Forbidden (inactive user)
- 404: Not found
- 429: Rate limit exceeded
- 500: Internal server error

## Running the API

```bash
uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables

Required in `.env`:
```
SECRET_KEY=<your-secret-key>
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_ENDPOINT=<endpoint>
AZURE_OPENAI_API_VERSION=<version>
AZURE_OPENAI_DEPLOYMENT=<deployment>
```
