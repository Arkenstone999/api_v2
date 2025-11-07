#!/bin/bash

BASE_URL="http://localhost:8000"

echo "Testing CrewSAS Translation API"
echo "================================"

echo -e "\n1. Health Check"
curl -s "$BASE_URL/health" | python3 -m json.tool

echo -e "\n\n2. Register User"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}')
echo $REGISTER_RESPONSE | python3 -m json.tool

echo -e "\n\n3. Login"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
echo $LOGIN_RESPONSE | python3 -m json.tool

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token. Exiting."
  exit 1
fi

echo -e "\n\n4. Get Current User"
curl -s "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n\n5. Create Project"
PROJECT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Project","description":"Testing upload","source_type":"sas-code","target_type":"pyspark"}')
echo $PROJECT_RESPONSE | python3 -m json.tool

PROJECT_ID=$(echo $PROJECT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "Failed to create project. Exiting."
  exit 1
fi

echo -e "\n\n6. Create Test SAS File"
cat > /tmp/test.sas << 'EOSF'
DATA output;
  SET input;
  new_var = old_var * 2;
RUN;
EOSF

echo -e "\n\n7. Upload SAS File to Project"
curl -s -X POST "$BASE_URL/api/projects/$PROJECT_ID/files" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@/tmp/test.sas" | python3 -m json.tool

echo -e "\n\n8. Get Project Status"
curl -s "$BASE_URL/api/projects/$PROJECT_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n\n9. Get Dashboard"
curl -s "$BASE_URL/api/dashboard" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n\nTest completed!"
