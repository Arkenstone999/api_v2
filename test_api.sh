#!/bin/bash

# API Testing Script for CrewSasToSparkSql
# Tests authentication and rate limiting features

API_URL="http://localhost:8000"
EMAIL="test@example.com"
PASSWORD="SecurePass123!"

echo "================================"
echo "CrewSasToSparkSql API Tests"
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check (No Auth Required)${NC}"
curl -s -X GET "$API_URL/health" | jq .
echo ""

# Test 2: Register a new user
echo -e "${BLUE}Test 2: Register New User${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"full_name\": \"Test User\"
  }")

echo "$REGISTER_RESPONSE" | jq .
API_KEY=$(echo "$REGISTER_RESPONSE" | jq -r '.api_key')
USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.id')
echo -e "${GREEN}API Key: $API_KEY${NC}"
echo ""

# Test 3: Login to get JWT token
echo -e "${BLUE}Test 3: Login to Get JWT Token${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\"
  }")

echo "$LOGIN_RESPONSE" | jq .
JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
echo -e "${GREEN}JWT Token: $JWT_TOKEN${NC}"
echo ""

# Test 4: Get current user info using JWT
echo -e "${BLUE}Test 4: Get Current User Info (Using JWT)${NC}"
curl -s -X GET "$API_URL/api/auth/me" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq .
echo ""

# Test 5: Get current user info using API Key
echo -e "${BLUE}Test 5: Get Current User Info (Using API Key)${NC}"
curl -s -X GET "$API_URL/api/auth/me" \
  -H "X-API-Key: $API_KEY" | jq .
echo ""

# Test 6: Get usage statistics
echo -e "${BLUE}Test 6: Get Usage Statistics${NC}"
curl -s -X GET "$API_URL/api/auth/usage" \
  -H "X-API-Key: $API_KEY" | jq .
echo ""

# Test 7: Create a project (requires auth)
echo -e "${BLUE}Test 7: Create Project (With Auth)${NC}"
PROJECT_RESPONSE=$(curl -s -X POST "$API_URL/api/projects" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name": "Test Migration Project",
    "description": "Testing authentication and rate limiting",
    "source_type": "sas-code",
    "target_type": "sql"
  }')

echo "$PROJECT_RESPONSE" | jq .
PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.id')
echo -e "${GREEN}Project ID: $PROJECT_ID${NC}"
echo ""

# Test 8: List projects
echo -e "${BLUE}Test 8: List Projects${NC}"
curl -s -X GET "$API_URL/api/projects" \
  -H "X-API-Key: $API_KEY" | jq .
echo ""

# Test 9: Get specific project
echo -e "${BLUE}Test 9: Get Specific Project${NC}"
curl -s -X GET "$API_URL/api/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq .
echo ""

# Test 10: Get dashboard stats
echo -e "${BLUE}Test 10: Get Dashboard Stats${NC}"
curl -s -X GET "$API_URL/api/dashboard/stats" \
  -H "X-API-Key: $API_KEY" | jq .
echo ""

# Test 11: Try accessing without authentication (should fail)
echo -e "${BLUE}Test 11: Try Accessing Without Auth (Should Fail)${NC}"
curl -s -X GET "$API_URL/api/projects" | jq .
echo ""

# Test 12: Try with invalid API key (should fail)
echo -e "${BLUE}Test 12: Try With Invalid API Key (Should Fail)${NC}"
curl -s -X GET "$API_URL/api/projects" \
  -H "X-API-Key: invalid-key-12345" | jq .
echo ""

# Test 13: Update project
echo -e "${BLUE}Test 13: Update Project${NC}"
curl -s -X PATCH "$API_URL/api/projects/$PROJECT_ID" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "status": "converting",
    "progress": 25
  }' | jq .
echo ""

# Test 14: Regenerate API Key
echo -e "${BLUE}Test 14: Regenerate API Key${NC}"
NEW_KEY_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/regenerate-api-key" \
  -H "Authorization: Bearer $JWT_TOKEN")

echo "$NEW_KEY_RESPONSE" | jq .
NEW_API_KEY=$(echo "$NEW_KEY_RESPONSE" | jq -r '.api_key')
echo -e "${GREEN}New API Key: $NEW_API_KEY${NC}"
echo ""

# Test 15: Test new API key works
echo -e "${BLUE}Test 15: Test New API Key Works${NC}"
curl -s -X GET "$API_URL/api/projects" \
  -H "X-API-Key: $NEW_API_KEY" | jq .
echo ""

# Test 16: Delete project
echo -e "${BLUE}Test 16: Delete Project${NC}"
curl -s -X DELETE "$API_URL/api/projects/$PROJECT_ID" \
  -H "X-API-Key: $NEW_API_KEY" -w "\nHTTP Status: %{http_code}\n"
echo ""

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Summary:"
echo "- User ID: $USER_ID"
echo "- Email: $EMAIL"
echo "- API Key: $NEW_API_KEY"
echo "- JWT Token: ${JWT_TOKEN:0:50}..."
echo ""
echo "Usage Information:"
echo "Get your usage: curl -X GET $API_URL/api/auth/usage -H \"X-API-Key: $NEW_API_KEY\""
