# API Testing Guide

## Comprehensive Test Script

The `test_all_apis.sh` script tests **ALL** API endpoints systematically.

### What It Tests

#### 1. Health & Root Endpoints
- `GET /` - Root endpoint
- `GET /health` - Health check with DB status

#### 2. Authentication (7 tests)
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login with JWT
- `GET /api/auth/me` - Get current user (JWT auth)
- `GET /api/auth/me` - Get current user (API Key auth)
- `GET /api/auth/usage` - Usage statistics
- `POST /api/auth/regenerate-api-key` - Regenerate API key
- `GET /api/auth/me` - Unauthorized access (should fail with 401)

#### 3. Quick Translation (3 tests)
- `POST /api/translate` - Quick translate JSON payload
- `POST /api/translate/file` - File upload translation
- `POST /api/translate` - Empty code validation (should fail)

#### 4. Project Management (8 tests)
- `POST /api/projects` - Create project
- `GET /api/projects` - List all projects
- `GET /api/projects/{id}` - Get project details
- `PATCH /api/projects/{id}` - Update project
- `POST /api/projects/{id}/files` - Upload .sas files
- `GET /api/projects/{id}/tasks` - List project tasks
- `POST /api/projects/{id}/translate` - Start translation (async)
- `GET /api/projects/{id}` - Check status after translation

#### 5. Task Management (5 tests)
- `GET /api/tasks/{id}` - Get task details
- `PATCH /api/tasks/{id}` - Update task status
- `POST /api/tasks/{id}/comments` - Add comment
- `GET /api/tasks/{id}/comments` - List comments
- `POST /api/tasks/{id}/translate` - Translate single task

#### 6. Dashboard (1 test)
- `GET /api/dashboard` - Get statistics

#### 7. Rate Limiting (1 test)
- Check rate limit headers

#### 8. Error Handling (4 tests)
- Invalid project ID (404)
- Invalid task ID (404)
- Invalid source/target types (400/422)
- Invalid file upload (400)

#### 9. Cleanup (1 test)
- `DELETE /api/projects/{id}` - Delete project

**Total: 30+ comprehensive tests**

---

## Usage

### Start the API First

```bash
# Terminal 1: Start the API
uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### Run All Tests

```bash
# Terminal 2: Run tests
./test_all_apis.sh
```

### Custom API URL

```bash
# Test against different host/port
API_URL=http://localhost:8080 ./test_all_apis.sh
```

---

## Output Format

The script provides:
- ✅ **Color-coded output** (green = pass, red = fail)
- 📊 **Test counters** showing progress
- ℹ️ **Info messages** with relevant data (IDs, tokens, etc.)
- 📝 **Detailed responses** for debugging
- 📈 **Summary statistics** at the end

### Example Output

```
================================================
2. AUTHENTICATION ENDPOINTS
================================================
[TEST 3] POST /api/auth/register
✓ PASS: User registration successful
ℹ INFO: User ID: 123e4567-e89b-12d3-a456-426614174000
ℹ INFO: API Key: ak_1234567890abcdef

[TEST 4] POST /api/auth/login
✓ PASS: User login successful
ℹ INFO: JWT Token obtained

================================================
TEST SUMMARY
================================================

Total Tests: 30
Passed: 30
Failed: 0

╔════════════════════════════════════════╗
║   ALL TESTS PASSED! ✓ ✓ ✓             ║
╚════════════════════════════════════════╝
```

---

## Test Flow

The script follows a realistic user workflow:

1. **Register** new user → get API key
2. **Login** → get JWT token
3. **Test both auth methods** (JWT + API Key)
4. **Quick translation** (JSON + file upload)
5. **Create project** → get project ID
6. **Upload files** to project
7. **Start translation** (background job)
8. **Check progress** and status
9. **Manage tasks** (get, update, comment)
10. **View dashboard** stats
11. **Cleanup** (delete project)

Each step depends on previous steps, mimicking real usage.

---

## Requirements

The script requires:
- `curl` - HTTP requests
- `python3` - JSON parsing
- `bash` - Script execution

All are standard on Linux/Mac. For Windows, use WSL or Git Bash.

---

## Troubleshooting

### API Not Reachable
```
✗ FAIL: API is not reachable at http://localhost:8000
```
**Fix:** Start the API first:
```bash
uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000
```

### Database Errors
```
✗ FAIL: User registration failed: HTTP 500
```
**Fix:** Run database migration:
```bash
uv run python -m crewsastosparksql.api.migrate_db
```

### Permission Denied
```
bash: ./test_all_apis.sh: Permission denied
```
**Fix:** Make executable:
```bash
chmod +x test_all_apis.sh
```

---

## What Makes This Test Script Good

1. ✅ **Comprehensive** - Tests all 30+ endpoints
2. ✅ **Realistic** - Follows actual user workflow
3. ✅ **Clear output** - Color-coded, easy to read
4. ✅ **Error handling** - Tests both success and failure cases
5. ✅ **Self-contained** - Creates test data automatically
6. ✅ **Cleanup** - Removes test data after
7. ✅ **Stateful** - Tests depend on each other (like real usage)
8. ✅ **Configurable** - Custom API URL via env var

---

## CI/CD Integration

Use in CI/CD pipelines:

```bash
# GitHub Actions / GitLab CI
- name: Test API
  run: |
    # Start API in background
    uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000 &
    sleep 5
    # Run tests
    ./test_all_apis.sh
```

---

## Manual Testing Alternative

For quick manual testing of individual endpoints:

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123","full_name":"Test"}'

# 2. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"pass123"}'

# 3. Translate
curl -X POST http://localhost:8000/api/translate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sas_code":"DATA test; SET input; RUN;"}'
```

But the automated script is faster and more reliable.
