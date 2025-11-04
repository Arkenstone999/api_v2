# Authentication & Rate Limiting

Simple, production-ready authentication and rate limiting for the CrewSasToSparkSql API.

## Features

- **JWT Token Authentication** - Standard bearer token auth
- **API Key Authentication** - For programmatic access
- **Rate Limiting** - 1000 requests per user per month (configurable)
- **User Isolation** - Each user only sees their own projects/tasks
- **Secure Password Hashing** - Using bcrypt

## Quick Start

### 1. Install Dependencies

```bash
cd CrewSas
uv sync
```

### 2. Configure Environment

Edit `.env` and set a strong secret key:

```bash
SECRET_KEY=your-random-secret-key-here
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Start the Server

```bash
uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run Tests

```bash
./test_api.sh
```

## API Endpoints

### Authentication

#### Register
```bash
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "yourpassword",
  "full_name": "Your Name"
}

Response:
{
  "id": "user-uuid",
  "email": "user@example.com",
  "full_name": "Your Name",
  "api_key": "generated-api-key",
  "monthly_request_limit": 1000,
  "is_active": true,
  "created_at": "2025-11-03T..."
}
```

#### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "yourpassword"
}

Response:
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

#### Get Current User
```bash
GET /api/auth/me
Authorization: Bearer {jwt-token}
# OR
X-API-Key: {api-key}

Response:
{
  "id": "user-uuid",
  "email": "user@example.com",
  ...
}
```

#### Get Usage Stats
```bash
GET /api/auth/usage
X-API-Key: {api-key}

Response:
{
  "current_month_usage": 42,
  "monthly_limit": 1000,
  "remaining": 958
}
```

#### Regenerate API Key
```bash
POST /api/auth/regenerate-api-key
Authorization: Bearer {jwt-token}

Response: (new user object with new api_key)
```

## Using Authentication

### Option 1: JWT Token (Browser/Mobile Apps)

```bash
# 1. Login to get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}' \
  | jq -r '.access_token')

# 2. Use token in requests
curl -X GET http://localhost:8000/api/projects \
  -H "Authorization: Bearer $TOKEN"
```

### Option 2: API Key (Scripts/Services)

```bash
# Get API key from registration or user profile
API_KEY="your-api-key"

# Use in requests
curl -X GET http://localhost:8000/api/projects \
  -H "X-API-Key: $API_KEY"
```

## Rate Limiting

- **Default Limit**: 1000 requests per user per month
- **Tracked Per**: User (not IP address)
- **Reset**: First day of each month
- **Headers**: Each response includes:
  - `X-RateLimit-Limit`: Your monthly limit
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: When the limit resets

When exceeded:
```json
{
  "detail": "Monthly request limit (1000) exceeded. Current usage: 1000. Try again next month."
}
HTTP Status: 429 Too Many Requests
```

## Protected Endpoints

All project/task/dashboard endpoints require authentication:

- `POST /api/projects` - Create project
- `GET /api/projects` - List your projects
- `GET /api/projects/{id}` - Get project
- `PATCH /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project
- `POST /api/projects/{id}/files` - Upload files
- `GET /api/projects/{id}/tasks` - List tasks
- `GET /api/dashboard/stats` - Dashboard stats

## Database Models

### User
- `id` - Unique identifier
- `email` - Unique email (used for login)
- `hashed_password` - Bcrypt hashed password
- `api_key` - Unique API key for programmatic access
- `monthly_request_limit` - Request quota (default: 1000)
- `is_active` - Account status

### Usage
- Tracks requests per user per month
- Automatically created on first request of the month
- Fields: `user_id`, `year`, `month`, `request_count`

### Project
- Now includes `user_id` foreign key
- Users can only access their own projects

## Configuration

### Environment Variables

```bash
# Required
SECRET_KEY=your-random-secret-key-min-32-chars

# Optional
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000  # Comma-separated
```

### Adjusting Rate Limits

Update a user's limit directly in the database:

```sql
UPDATE users SET monthly_request_limit = 5000 WHERE email = 'user@example.com';
```

Or add an admin endpoint to manage this.

## Security Notes

1. **Secret Key**: Use a strong, random secret key in production
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **CORS**: Configure `ALLOWED_ORIGINS` to only include your frontend domains

3. **HTTPS**: Always use HTTPS in production

4. **Password Requirements**: Implement password strength requirements in production

5. **API Keys**: Treat API keys like passwords - never commit them to git

## Testing

The `test_api.sh` script covers:
- User registration
- Login with JWT
- API key authentication
- Rate limit headers
- Project CRUD operations
- Unauthorized access attempts
- User isolation

Run it:
```bash
./test_api.sh
```

## Troubleshooting

### "Not authenticated" error
- Check JWT token is valid and not expired (7 days)
- Check API key is correct
- Ensure Authorization header format: `Bearer {token}`
- Ensure API key header format: `X-API-Key: {key}`

### "Monthly request limit exceeded"
- Check usage: `GET /api/auth/usage`
- Wait for next month or increase limit in database

### Database errors
- Delete the database and restart: `rm data/crewsas.db`
- Run migrations: Database auto-initializes on startup

## Architecture

Simple and clean:
- **auth.py** - Authentication utilities (JWT, password hashing, API keys)
- **routes_auth.py** - Auth endpoints (register, login, me)
- **rate_limit.py** - Rate limiting dependency
- **db_models.py** - User and Usage models
- All existing routes protected with `Depends(get_current_user)` and `Depends(check_rate_limit)`

No overengineering. Just works.
