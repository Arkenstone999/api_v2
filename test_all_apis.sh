#!/bin/bash

#############################################
# Comprehensive API Test Script
# Tests ALL endpoints of CrewSAS Translation API
#############################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"
TEST_NAME="Test User"

# Global variables for tokens and IDs
TOKEN=""
API_KEY=""
USER_ID=""
PROJECT_ID=""
TASK_ID=""
COMMENT_ID=""

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

#############################################
# Helper Functions
#############################################

print_section() {
    echo ""
    echo -e "${CYAN}================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}================================================${NC}"
}

print_test() {
    ((TESTS_TOTAL++))
    echo -e "${BLUE}[TEST $TESTS_TOTAL]${NC} $1"
}

print_success() {
    ((TESTS_PASSED++))
    echo -e "${GREEN}✓ PASS:${NC} $1"
}

print_error() {
    ((TESTS_FAILED++))
    echo -e "${RED}✗ FAIL:${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ INFO:${NC} $1"
}

# Make HTTP request and capture response
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local headers=$4

    local url="${API_URL}${endpoint}"
    local response
    local http_code

    if [ -n "$data" ]; then
        if [ -n "$headers" ]; then
            response=$(curl -s --max-time 30 -w "\n%{http_code}" -X "$method" "$url" \
                -H "Content-Type: application/json" \
                $headers \
                -d "$data")
        else
            response=$(curl -s --max-time 30 -w "\n%{http_code}" -X "$method" "$url" \
                -H "Content-Type: application/json" \
                -d "$data")
        fi
    else
        if [ -n "$headers" ]; then
            response=$(curl -s --max-time 30 -w "\n%{http_code}" -X "$method" "$url" $headers)
        else
            response=$(curl -s --max-time 30 -w "\n%{http_code}" -X "$method" "$url")
        fi
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "$http_code|$body"
}

# Extract JSON field
extract_json_field() {
    local json=$1
    local field=$2
    echo "$json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('$field', ''))"
}

# Create test SAS file
create_test_sas_file() {
    local filename=$1
    cat > "$filename" << 'EOF'
DATA cars;
    SET sashelp.cars;
    WHERE origin = 'USA';
    price_usd = MSRP * 1.2;
RUN;

PROC MEANS DATA=cars;
    VAR MSRP price_usd;
    OUTPUT OUT=summary MEAN=avg_msrp avg_price;
RUN;
EOF
}

#############################################
# Test Functions
#############################################

test_health_check() {
    print_section "1. HEALTH & ROOT ENDPOINTS"

    print_test "GET /"
    result=$(make_request "GET" "/")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Root endpoint returned 200"
        print_info "Response: $body"
    else
        print_error "Root endpoint failed: HTTP $http_code"
    fi

    print_test "GET /health"
    result=$(make_request "GET" "/health")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Health check returned 200"
        print_info "Response: $body"
    else
        print_error "Health check failed: HTTP $http_code"
    fi
}

test_authentication() {
    print_section "2. AUTHENTICATION ENDPOINTS"

    # Test 1: Register
    print_test "POST /api/auth/register"
    result=$(make_request "POST" "/api/auth/register" \
        "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"full_name\":\"$TEST_NAME\"}")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "201" ]; then
        print_success "User registration successful"
        USER_ID=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
        API_KEY=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
        print_info "User ID: $USER_ID"
        print_info "API Key: $API_KEY"
    else
        print_error "User registration failed: HTTP $http_code - $body"
        exit 1
    fi

    # Test 2: Login
    print_test "POST /api/auth/login"
    result=$(make_request "POST" "/api/auth/login" \
        "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "User login successful"
        TOKEN=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
        print_info "JWT Token obtained"
    else
        print_error "User login failed: HTTP $http_code - $body"
        exit 1
    fi

    # Test 3: Get current user (with JWT)
    print_test "GET /api/auth/me (with JWT)"
    result=$(make_request "GET" "/api/auth/me" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Get current user with JWT successful"
        print_info "Response: $body"
    else
        print_error "Get current user failed: HTTP $http_code"
    fi

    # Test 4: Get current user (with API Key)
    print_test "GET /api/auth/me (with API Key)"
    result=$(make_request "GET" "/api/auth/me" "" "-H \"X-API-Key: $API_KEY\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Get current user with API Key successful"
    else
        print_error "Get current user with API Key failed: HTTP $http_code"
    fi

    # Test 5: Get usage statistics
    print_test "GET /api/auth/usage"
    result=$(make_request "GET" "/api/auth/usage" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Get usage statistics successful"
        print_info "Response: $body"
    else
        print_error "Get usage statistics failed: HTTP $http_code"
    fi

    # Test 6: Regenerate API key
    print_test "POST /api/auth/regenerate-api-key"
    result=$(make_request "POST" "/api/auth/regenerate-api-key" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Regenerate API key successful"
        NEW_API_KEY=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
        print_info "New API Key: $NEW_API_KEY"
        # Use new API key for subsequent tests
        API_KEY=$NEW_API_KEY
    else
        print_error "Regenerate API key failed: HTTP $http_code"
    fi

    # Test 7: Test authentication failure
    print_test "GET /api/auth/me (no auth - should fail)"
    result=$(make_request "GET" "/api/auth/me")
    http_code=$(echo "$result" | cut -d'|' -f1)

    if [ "$http_code" = "401" ]; then
        print_success "Unauthorized access correctly rejected with 401"
    else
        print_error "Expected 401 but got HTTP $http_code"
    fi
}

test_quick_translation() {
    print_section "3. QUICK TRANSLATION ENDPOINTS"

    # Test 1: Translate code (JSON)
    print_test "POST /api/translate (quick translate)"
    SAS_CODE="DATA test; SET input; x = y + 1; RUN;"
    result=$(make_request "POST" "/api/translate" \
        "{\"sas_code\":\"$SAS_CODE\"}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Quick translation successful"
        print_info "Execution time: $(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('execution_time_seconds', 'N/A'))")"
    else
        print_error "Quick translation failed: HTTP $http_code - $body"
    fi

    # Test 2: Translate file upload
    print_test "POST /api/translate/file (file upload)"

    # Create test file
    TEST_FILE="test_upload.sas"
    create_test_sas_file "$TEST_FILE"

    result=$(curl -s --max-time 60 -w "\n%{http_code}" -X POST "${API_URL}/api/translate/file" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$TEST_FILE")
    http_code=$(echo "$result" | tail -n1)
    body=$(echo "$result" | sed '$d')

    if [ "$http_code" = "200" ]; then
        print_success "File translation successful"
        print_info "Translated file: $TEST_FILE"
    else
        print_error "File translation failed: HTTP $http_code - $body"
    fi

    # Cleanup
    rm -f "$TEST_FILE"

    # Test 3: Empty code should fail
    print_test "POST /api/translate (empty code - should fail)"
    result=$(make_request "POST" "/api/translate" \
        "{\"sas_code\":\"\"}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)

    if [ "$http_code" = "400" ]; then
        print_success "Empty code correctly rejected with 400"
    else
        print_error "Expected 400 but got HTTP $http_code"
    fi
}

test_projects() {
    print_section "4. PROJECT MANAGEMENT ENDPOINTS"

    # Test 1: Create project
    print_test "POST /api/projects (create project)"
    result=$(make_request "POST" "/api/projects" \
        "{\"name\":\"Test Project\",\"description\":\"Testing API\",\"source_type\":\"sas-code\",\"target_type\":\"pyspark\"}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "201" ]; then
        print_success "Project created successfully"
        PROJECT_ID=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
        print_info "Project ID: $PROJECT_ID"
    else
        print_error "Project creation failed: HTTP $http_code - $body"
        exit 1
    fi

    # Test 2: List projects
    print_test "GET /api/projects (list all projects)"
    result=$(make_request "GET" "/api/projects" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "List projects successful"
        project_count=$(echo "$body" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
        print_info "Found $project_count project(s)"
    else
        print_error "List projects failed: HTTP $http_code"
    fi

    # Test 3: Get specific project
    print_test "GET /api/projects/{id} (get project details)"
    result=$(make_request "GET" "/api/projects/$PROJECT_ID" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Get project details successful"
        print_info "Response: $body"
    else
        print_error "Get project details failed: HTTP $http_code"
    fi

    # Test 4: Update project
    print_test "PATCH /api/projects/{id} (update project)"
    result=$(make_request "PATCH" "/api/projects/$PROJECT_ID" \
        "{\"name\":\"Updated Test Project\",\"description\":\"Updated description\"}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Project update successful"
    else
        print_error "Project update failed: HTTP $http_code"
    fi

    # Test 5: Upload files to project
    print_test "POST /api/projects/{id}/files (upload .sas files)"

    # Create multiple test files
    create_test_sas_file "test_file1.sas"
    create_test_sas_file "test_file2.sas"

    result=$(curl -s --max-time 30 -w "\n%{http_code}" -X POST "${API_URL}/api/projects/$PROJECT_ID/files" \
        -H "Authorization: Bearer $TOKEN" \
        -F "files=@test_file1.sas" \
        -F "files=@test_file2.sas")
    http_code=$(echo "$result" | tail -n1)
    body=$(echo "$result" | sed '$d')

    if [ "$http_code" = "202" ]; then
        print_success "File upload successful"
        print_info "Response: $body"
    else
        print_error "File upload failed: HTTP $http_code - $body"
    fi

    # Cleanup
    rm -f test_file1.sas test_file2.sas

    # Test 6: List project tasks
    print_test "GET /api/projects/{id}/tasks (list tasks)"
    result=$(make_request "GET" "/api/projects/$PROJECT_ID/tasks" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "List project tasks successful"
        task_count=$(echo "$body" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
        print_info "Found $task_count task(s)"

        # Extract first task ID for later tests
        if [ "$task_count" -gt 0 ]; then
            TASK_ID=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")
            print_info "Task ID for testing: $TASK_ID"
        fi
    else
        print_error "List project tasks failed: HTTP $http_code"
    fi

    # Test 7: Start project translation (background job)
    print_test "POST /api/projects/{id}/translate (start translation)"
    result=$(make_request "POST" "/api/projects/$PROJECT_ID/translate" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "202" ]; then
        print_success "Translation started (async job)"
        print_info "Response: $body"
        print_info "Waiting 5 seconds for background job..."
        sleep 5
    else
        print_error "Start translation failed: HTTP $http_code - $body"
    fi

    # Test 8: Check project status after translation
    print_test "GET /api/projects/{id} (check status after translation)"
    result=$(make_request "GET" "/api/projects/$PROJECT_ID" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Project status check successful"
        status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
        progress=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('progress', 0))")
        print_info "Status: $status, Progress: $progress%"
    else
        print_error "Project status check failed: HTTP $http_code"
    fi
}

test_tasks() {
    print_section "5. TASK MANAGEMENT ENDPOINTS"

    if [ -z "$TASK_ID" ]; then
        print_info "Skipping task tests - no task ID available"
        return
    fi

    # Test 1: Get task details
    print_test "GET /api/tasks/{id} (get task details)"
    result=$(make_request "GET" "/api/tasks/$TASK_ID" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Get task details successful"
        print_info "Response: $body"
    else
        print_error "Get task details failed: HTTP $http_code"
    fi

    # Test 2: Update task
    print_test "PATCH /api/tasks/{id} (update task)"
    result=$(make_request "PATCH" "/api/tasks/$TASK_ID" \
        "{\"status\":\"reviewed\"}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Task update successful"
    else
        print_error "Task update failed: HTTP $http_code"
    fi

    # Test 3: Add comment to task
    print_test "POST /api/tasks/{id}/comments (add comment)"
    result=$(make_request "POST" "/api/tasks/$TASK_ID/comments" \
        "{\"content\":\"This is a test comment\",\"line_number\":10}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "201" ]; then
        print_success "Comment added successfully"
        COMMENT_ID=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
        print_info "Comment ID: $COMMENT_ID"
    else
        print_error "Add comment failed: HTTP $http_code"
    fi

    # Test 4: List task comments
    print_test "GET /api/tasks/{id}/comments (list comments)"
    result=$(make_request "GET" "/api/tasks/$TASK_ID/comments" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "List comments successful"
        comment_count=$(echo "$body" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
        print_info "Found $comment_count comment(s)"
    else
        print_error "List comments failed: HTTP $http_code"
    fi

    # Test 5: Translate single task
    print_test "POST /api/tasks/{id}/translate (translate single task)"
    result=$(make_request "POST" "/api/tasks/$TASK_ID/translate" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "202" ]; then
        print_success "Single task translation started"
        print_info "Response: $body"
    else
        print_error "Single task translation failed: HTTP $http_code - $body"
    fi
}

test_dashboard() {
    print_section "6. DASHBOARD ENDPOINT"

    print_test "GET /api/dashboard (get dashboard statistics)"
    result=$(make_request "GET" "/api/dashboard" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)
    body=$(echo "$result" | cut -d'|' -f2)

    if [ "$http_code" = "200" ]; then
        print_success "Dashboard statistics retrieved"
        print_info "Response: $body"
    else
        print_error "Dashboard failed: HTTP $http_code"
    fi
}

test_project_deletion() {
    print_section "7. PROJECT DELETION (CLEANUP)"

    if [ -z "$PROJECT_ID" ]; then
        print_info "Skipping deletion - no project ID available"
        return
    fi

    print_test "DELETE /api/projects/{id} (delete project)"
    result=$(make_request "DELETE" "/api/projects/$PROJECT_ID" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)

    if [ "$http_code" = "204" ]; then
        print_success "Project deleted successfully"
    else
        print_error "Project deletion failed: HTTP $http_code"
    fi
}

test_rate_limiting() {
    print_section "8. RATE LIMITING TEST"

    print_test "Check rate limit headers"
    result=$(curl -s --max-time 10 -i -X GET "${API_URL}/api/auth/me" \
        -H "Authorization: Bearer $TOKEN" 2>&1 | grep -i "X-RateLimit")

    if [ -n "$result" ]; then
        print_success "Rate limit headers present"
        print_info "$result"
    else
        print_info "Rate limit headers not found (may not be implemented)"
    fi
}

test_error_cases() {
    print_section "9. ERROR HANDLING TESTS"

    # Test 1: Invalid project ID
    print_test "GET /api/projects/{invalid_id} (should return 404)"
    result=$(make_request "GET" "/api/projects/invalid-uuid-123" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)

    if [ "$http_code" = "404" ]; then
        print_success "Invalid project ID correctly returns 404"
    else
        print_error "Expected 404 but got HTTP $http_code"
    fi

    # Test 2: Invalid task ID
    print_test "GET /api/tasks/{invalid_id} (should return 404)"
    result=$(make_request "GET" "/api/tasks/invalid-uuid-456" "" "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)

    if [ "$http_code" = "404" ]; then
        print_success "Invalid task ID correctly returns 404"
    else
        print_error "Expected 404 but got HTTP $http_code"
    fi

    # Test 3: Invalid source/target type
    print_test "POST /api/projects (invalid types - should return 400)"
    result=$(make_request "POST" "/api/projects" \
        "{\"name\":\"Bad Project\",\"description\":\"Test\",\"source_type\":\"invalid\",\"target_type\":\"invalid\"}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    http_code=$(echo "$result" | cut -d'|' -f1)

    if [ "$http_code" = "400" ] || [ "$http_code" = "422" ]; then
        print_success "Invalid types correctly rejected with $http_code"
    else
        print_error "Expected 400/422 but got HTTP $http_code"
    fi

    # Test 4: Upload non-.sas file
    print_test "POST /api/projects/{id}/files (invalid file type - should fail)"

    # Create a text file
    echo "Not a SAS file" > test_invalid.txt

    # Create a dummy project for this test
    result=$(make_request "POST" "/api/projects" \
        "{\"name\":\"Temp Project\",\"description\":\"Test\",\"source_type\":\"sas-code\",\"target_type\":\"sql\"}" \
        "-H \"Authorization: Bearer $TOKEN\"")
    TEMP_PROJECT_ID=$(echo "$result" | cut -d'|' -f2 | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

    result=$(curl -s --max-time 30 -w "\n%{http_code}" -X POST "${API_URL}/api/projects/$TEMP_PROJECT_ID/files" \
        -H "Authorization: Bearer $TOKEN" \
        -F "files=@test_invalid.txt")
    http_code=$(echo "$result" | tail -n1)

    if [ "$http_code" = "400" ]; then
        print_success "Invalid file type correctly rejected with 400"
    else
        print_error "Expected 400 but got HTTP $http_code"
    fi

    # Cleanup
    rm -f test_invalid.txt
    make_request "DELETE" "/api/projects/$TEMP_PROJECT_ID" "" "-H \"Authorization: Bearer $TOKEN\"" > /dev/null
}

#############################################
# Main Test Execution
#############################################

main() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     CrewSAS Translation API - Comprehensive Test Suite    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    print_info "API URL: $API_URL"
    print_info "Test Email: $TEST_EMAIL"
    echo ""

    # Check if API is running
    if ! curl -s --max-time 5 "${API_URL}/" > /dev/null 2>&1; then
        print_error "API is not reachable at $API_URL"
        print_info "Please start the API with: uv run uvicorn crewsastosparksql.api.app:app --host 0.0.0.0 --port 8000"
        exit 1
    fi

    print_success "API is reachable"

    # Run all test suites
    test_health_check
    test_authentication
    test_quick_translation
    test_projects
    test_tasks
    test_dashboard
    test_rate_limiting
    test_error_cases
    test_project_deletion

    # Print summary
    print_section "TEST SUMMARY"
    echo ""
    echo -e "${CYAN}Total Tests:${NC} $TESTS_TOTAL"
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║   ALL TESTS PASSED! ✓ ✓ ✓             ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${RED}╔════════════════════════════════════════╗${NC}"
        echo -e "${RED}║   SOME TESTS FAILED                    ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════╝${NC}"
        exit 1
    fi
}

# Run main function
main
