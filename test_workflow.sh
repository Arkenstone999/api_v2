#!/bin/bash

BASE_URL="http://localhost:8000"

echo "==================================="
echo "CrewSAS API Complete Workflow Test"
echo "==================================="

echo -e "\n1. Register User"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@test.com","password":"password123","full_name":"Demo User"}')
echo "$REGISTER_RESPONSE" | python3 -m json.tool

echo -e "\n2. Login"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@test.com","password":"password123"}')
echo "$LOGIN_RESPONSE" | python3 -m json.tool

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token. User may already exist. Trying login again..."
  exit 1
fi

echo -e "\n3. Create Project"
PROJECT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Project","description":"Testing workflow","source_type":"sas-code","target_type":"pyspark"}')
echo "$PROJECT_RESPONSE" | python3 -m json.tool

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$PROJECT_ID" ]; then
  echo "Failed to create project."
  exit 1
fi

echo -e "\n4. Create Test SAS File"
cat > /tmp/demo.sas << 'EOSF'
DATA output;
  SET input;
  new_var = old_var * 2;
  IF age > 18 THEN category = 'adult';
  ELSE category = 'minor';
RUN;
EOSF

echo -e "\n5. Upload SAS File"
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/projects/$PROJECT_ID/files" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@/tmp/demo.sas")
echo "$UPLOAD_RESPONSE" | python3 -m json.tool

echo -e "\n6. List Project Tasks (NEW ENDPOINT)"
TASKS_RESPONSE=$(curl -s "$BASE_URL/api/projects/$PROJECT_ID/tasks" \
  -H "Authorization: Bearer $TOKEN")
echo "$TASKS_RESPONSE" | python3 -m json.tool

TASK_ID=$(echo "$TASKS_RESPONSE" | python3 -c "import sys, json; tasks = json.load(sys.stdin); print(tasks[0]['id'] if tasks else '')" 2>/dev/null)

if [ -z "$TASK_ID" ]; then
  echo "No tasks found."
  exit 1
fi

echo -e "\n7. Get Task Details"
curl -s "$BASE_URL/api/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n8. Translate Single Task (Background)"
curl -s -X POST "$BASE_URL/api/tasks/$TASK_ID/translate" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n9. Check Task Status (wait 2 seconds)"
sleep 2
curl -s "$BASE_URL/api/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n10. Dashboard Stats"
curl -s "$BASE_URL/api/dashboard" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n==================================="
echo "Workflow test completed!"
echo "==================================="
echo -e "\nYour task ID is: $TASK_ID"
echo "Use this ID to check translation status:"
echo "curl -H 'Authorization: Bearer $TOKEN' $BASE_URL/api/tasks/$TASK_ID"
