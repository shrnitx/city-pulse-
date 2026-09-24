#!/usr/bin/env python3
"""
Comprehensive backend testing for CityPulse Civic Intelligence app
Tests all backend endpoints with proper authentication and role-based access
"""
import requests
import json
import io
from datetime import datetime, timezone, timedelta

# Base URL from frontend/.env
BASE_URL = "https://87d279e3-c0bd-4c1c-8eb4-6f0923fa9f52.preview.emergentagent.com/api"

# Demo credentials from test_credentials.md
SOCIETY_CODE = "GV-48291"
PASSWORD = "CityPulse2025!"
DEMO_ACCOUNTS = {
    "owner": {"username": "owner", "role": "initial_admin"},
    "blockb.admin": {"username": "blockb.admin", "role": "admin"},
    "utilities.admin": {"username": "utilities.admin", "role": "admin"},
    "elena": {"username": "elena", "role": "resident"}
}

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name):
    test_results["passed"].append(test_name)
    print(f"✅ PASS: {test_name}")

def log_fail(test_name, error):
    test_results["failed"].append({"test": test_name, "error": str(error)})
    print(f"❌ FAIL: {test_name}")
    print(f"   Error: {error}")

def log_warning(test_name, message):
    test_results["warnings"].append({"test": test_name, "message": message})
    print(f"⚠️  WARNING: {test_name}")
    print(f"   Message: {message}")

# Store tokens for different users
tokens = {}

def test_health():
    """Test 1: Health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                log_pass("Health endpoint returns ok")
            else:
                log_fail("Health endpoint", f"Status not ok: {data}")
        else:
            log_fail("Health endpoint", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Health endpoint", str(e))

def test_demo_info():
    """Test 2: Demo info endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/auth/demo", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("society_code") == SOCIETY_CODE and data.get("password") == PASSWORD:
                log_pass("Demo info endpoint returns correct credentials")
            else:
                log_fail("Demo info endpoint", f"Incorrect credentials: {data}")
        else:
            log_fail("Demo info endpoint", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Demo info endpoint", str(e))

def test_login(username, expected_role):
    """Test 3: Login with demo accounts"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "society_code": SOCIETY_CODE,
                "username": username,
                "password": PASSWORD
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data and "society" in data:
                tokens[username] = data["token"]
                if data["user"]["role"] == expected_role:
                    log_pass(f"Login as {username} ({expected_role})")
                    return data
                else:
                    log_fail(f"Login as {username}", f"Expected role {expected_role}, got {data['user']['role']}")
            else:
                log_fail(f"Login as {username}", f"Missing required fields: {data}")
        else:
            log_fail(f"Login as {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Login as {username}", str(e))
    return None

def test_invalid_login():
    """Test 4: Invalid login credentials"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "society_code": SOCIETY_CODE,
                "username": "invalid_user",
                "password": "wrong_password"
            },
            timeout=10
        )
        if response.status_code == 401:
            log_pass("Invalid login rejected with 401")
        else:
            log_fail("Invalid login", f"Expected 401, got {response.status_code}")
    except Exception as e:
        log_fail("Invalid login", str(e))

def test_session_validation(username):
    """Test 5: Session token validation on protected route"""
    if username not in tokens:
        log_fail(f"Session validation for {username}", "No token available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "user" in data and "society" in data:
                log_pass(f"Session validation for {username}")
            else:
                log_fail(f"Session validation for {username}", f"Missing fields: {data}")
        else:
            log_fail(f"Session validation for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Session validation for {username}", str(e))

def test_register_new_resident():
    """Test 6: Register a new resident"""
    import random
    username = f"test_resident_{random.randint(1000, 9999)}"
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "society_code": SOCIETY_CODE,
                "username": username,
                "password": "TestPassword123!",
                "name": "Test Resident",
                "area": "Test Block"
            },
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            if "token" in data and "user" in data:
                log_pass("Register new resident")
                return username
            else:
                log_fail("Register new resident", f"Missing fields: {data}")
        else:
            log_fail("Register new resident", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Register new resident", str(e))
    return None

def test_register_with_email():
    """Test NEW: Register with email (globally unique)"""
    import random
    import time
    # Generate unique email with timestamp to avoid conflicts
    unique_email = f"newuser{random.randint(10000, 99999)}_{int(time.time())}@example.com"
    username = f"emailuser_{random.randint(1000, 9999)}"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "society_code": SOCIETY_CODE,
                "username": username,
                "password": "SecurePass123!",
                "name": "Email Test User",
                "email": unique_email,
                "area": "Block C"
            },
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            if "token" in data and "user" in data and "society" in data:
                if data["user"].get("email") == unique_email.lower():
                    log_pass("Register with unique email returns 201")
                    return {"email": unique_email, "password": "SecurePass123!", "token": data["token"]}
                else:
                    log_fail("Register with email", f"Email not set correctly: {data['user'].get('email')}")
            else:
                log_fail("Register with email", f"Missing fields: {data}")
        else:
            log_fail("Register with email", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Register with email", str(e))
    return None

def test_register_duplicate_email(email):
    """Test NEW: Register with duplicate email returns 409"""
    import random
    username = f"duplicate_{random.randint(1000, 9999)}"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "society_code": SOCIETY_CODE,
                "username": username,
                "password": "AnotherPass123!",
                "name": "Duplicate Email User",
                "email": email,
                "area": "Block D"
            },
            timeout=10
        )
        if response.status_code == 409:
            log_pass("Duplicate email registration rejected with 409")
        else:
            log_fail("Duplicate email registration", f"Expected 409, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Duplicate email registration", str(e))

def test_register_invalid_email():
    """Test NEW: Register with invalid email format returns 422"""
    import random
    username = f"invalidemail_{random.randint(1000, 9999)}"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "society_code": SOCIETY_CODE,
                "username": username,
                "password": "ValidPass123!",
                "name": "Invalid Email User",
                "email": "notanemail",
                "area": "Block E"
            },
            timeout=10
        )
        if response.status_code == 422:
            log_pass("Invalid email format rejected with 422")
        else:
            log_fail("Invalid email format", f"Expected 422, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Invalid email format", str(e))

def test_login_with_email(email, password):
    """Test NEW: Login with email and password (no society code)"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login-email",
            json={
                "email": email,
                "password": password
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data and "society" in data:
                log_pass("Login with email returns 200 with token")
                return data["token"]
            else:
                log_fail("Login with email", f"Missing fields: {data}")
        else:
            log_fail("Login with email", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Login with email", str(e))
    return None

def test_login_email_wrong_password(email):
    """Test NEW: Login with wrong password returns 401"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login-email",
            json={
                "email": email,
                "password": "WrongPassword123!"
            },
            timeout=10
        )
        if response.status_code == 401:
            log_pass("Login with wrong password rejected with 401")
        else:
            log_fail("Login with wrong password", f"Expected 401, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Login with wrong password", str(e))

def test_login_email_nonexistent(email="nonexistent@example.com"):
    """Test NEW: Login with non-existent email returns 401"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login-email",
            json={
                "email": email,
                "password": "SomePassword123!"
            },
            timeout=10
        )
        if response.status_code == 401:
            log_pass("Login with non-existent email rejected with 401")
        else:
            log_fail("Login with non-existent email", f"Expected 401, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Login with non-existent email", str(e))

def test_email_token_validation(token):
    """Test NEW: Token from email login works on protected route"""
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "user" in data and "society" in data:
                log_pass("Email login token validated on /auth/me")
            else:
                log_fail("Email token validation", f"Missing fields: {data}")
        else:
            log_fail("Email token validation", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Email token validation", str(e))

def test_logout(username):
    """Test 7: Logout invalidates token"""
    if username not in tokens:
        log_fail(f"Logout {username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/logout",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            # Try to use the token again - should fail
            response2 = requests.get(
                f"{BASE_URL}/auth/me",
                headers={"Authorization": f"Bearer {tokens[username]}"},
                timeout=10
            )
            if response2.status_code == 401:
                log_pass(f"Logout {username} invalidates token")
            else:
                log_fail(f"Logout {username}", f"Token still valid after logout")
        else:
            log_fail(f"Logout {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Logout {username}", str(e))

def test_civic_data(username):
    """Test 8: Civic data panels (weather/aqi/traffic)"""
    if username not in tokens:
        log_fail(f"Civic data for {username}", "No token available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/civic",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            # Check for simulated civic data
            if "weather" in data or "aqi" in data or "traffic" in data:
                log_pass(f"Civic data panels for {username}")
            else:
                log_fail(f"Civic data for {username}", f"Missing civic data fields: {data}")
        else:
            log_fail(f"Civic data for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Civic data for {username}", str(e))

def test_list_problems(username):
    """Test 9: List problems"""
    if username not in tokens:
        log_fail(f"List problems for {username}", "No token available")
        return None
    
    try:
        response = requests.get(
            f"{BASE_URL}/problems",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "items" in data and "total" in data:
                log_pass(f"List problems for {username} (found {data['total']} cases)")
                return data["items"]
            else:
                log_fail(f"List problems for {username}", f"Missing fields: {data}")
        else:
            log_fail(f"List problems for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"List problems for {username}", str(e))
    return None

def test_problem_detail(username, case_id):
    """Test 10: Get problem detail"""
    if username not in tokens:
        log_fail(f"Problem detail for {username}", "No token available")
        return None
    
    try:
        response = requests.get(
            f"{BASE_URL}/problems/{case_id}",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "id" in data and "title" in data and "timeline" in data:
                log_pass(f"Problem detail for {username}")
                return data
            else:
                log_fail(f"Problem detail for {username}", f"Missing fields: {data}")
        else:
            log_fail(f"Problem detail for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Problem detail for {username}", str(e))
    return None

def test_report_problem(username):
    """Test 11: Report a new problem"""
    if username not in tokens:
        log_fail(f"Report problem for {username}", "No token available")
        return None
    
    try:
        observed_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        response = requests.post(
            f"{BASE_URL}/problems",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={
                "title": "Test Problem - Broken Street Light on Main Road",
                "description": "The street light near the community center has been non-functional for several days, creating safety concerns for evening pedestrians.",
                "category": "Electricity",
                "location": "Main Road near Community Center",
                "observed_at": observed_time,
                "duration": "3 days",
                "affected_area": "Main Road Block A",
                "evidence_ids": []
            },
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            if "case_id" in data and "report_id" in data:
                log_pass(f"Report problem for {username}")
                return data["case_id"]
            else:
                log_fail(f"Report problem for {username}", f"Missing fields: {data}")
        else:
            log_fail(f"Report problem for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Report problem for {username}", str(e))
    return None

def test_vote_on_problem(username, case_id):
    """Test 12: Vote on a problem"""
    if username not in tokens:
        log_fail(f"Vote on problem for {username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/problems/{case_id}/signals",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={"vote": 1},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Vote on problem for {username}")
            else:
                log_fail(f"Vote on problem for {username}", f"Response not ok: {data}")
        else:
            log_fail(f"Vote on problem for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Vote on problem for {username}", str(e))

def test_confirm_affected(username, case_id):
    """Test 13: Confirm affected by problem"""
    if username not in tokens:
        log_fail(f"Confirm affected for {username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/problems/{case_id}/signals",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={"affected": True},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Confirm affected for {username}")
            else:
                log_fail(f"Confirm affected for {username}", f"Response not ok: {data}")
        else:
            log_fail(f"Confirm affected for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Confirm affected for {username}", str(e))

def test_follow_problem(username, case_id):
    """Test 14: Follow a problem"""
    if username not in tokens:
        log_fail(f"Follow problem for {username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/problems/{case_id}/signals",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={"following": True},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Follow problem for {username}")
            else:
                log_fail(f"Follow problem for {username}", f"Response not ok: {data}")
        else:
            log_fail(f"Follow problem for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Follow problem for {username}", str(e))

def test_add_comment(username, case_id):
    """Test 15: Add comment to problem"""
    if username not in tokens:
        log_fail(f"Add comment for {username}", "No token available")
        return None
    
    try:
        response = requests.post(
            f"{BASE_URL}/problems/{case_id}/comments",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={"text": "This is a test comment. I have also noticed this issue in my area."},
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            if data.get("ok") and "id" in data:
                log_pass(f"Add comment for {username}")
                return data["id"]
            else:
                log_fail(f"Add comment for {username}", f"Missing fields: {data}")
        else:
            log_fail(f"Add comment for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Add comment for {username}", str(e))
    return None

def test_mark_comment_helpful(username, comment_id):
    """Test 16: Mark comment as helpful"""
    if username not in tokens or not comment_id:
        log_fail(f"Mark comment helpful for {username}", "No token or comment_id available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/comments/{comment_id}/helpful",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Mark comment helpful for {username}")
            else:
                log_fail(f"Mark comment helpful for {username}", f"Response not ok: {data}")
        else:
            log_fail(f"Mark comment helpful for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Mark comment helpful for {username}", str(e))

def test_admin_verify_case(admin_username, case_id):
    """Test 17: Admin verify case"""
    if admin_username not in tokens:
        log_fail(f"Admin verify case for {admin_username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/cases/{case_id}/action",
            headers={"Authorization": f"Bearer {tokens[admin_username]}"},
            json={"action": "verify"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Admin verify case for {admin_username}")
            else:
                log_fail(f"Admin verify case for {admin_username}", f"Response not ok: {data}")
        else:
            log_fail(f"Admin verify case for {admin_username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Admin verify case for {admin_username}", str(e))

def test_admin_assign_case(admin_username, case_id, assignee_id):
    """Test 18: Admin assign case"""
    if admin_username not in tokens:
        log_fail(f"Admin assign case for {admin_username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/cases/{case_id}/action",
            headers={"Authorization": f"Bearer {tokens[admin_username]}"},
            json={"action": "assign", "assignee_id": assignee_id},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Admin assign case for {admin_username}")
            else:
                log_fail(f"Admin assign case for {admin_username}", f"Response not ok: {data}")
        else:
            log_fail(f"Admin assign case for {admin_username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Admin assign case for {admin_username}", str(e))

def test_admin_status_change(admin_username, case_id, new_status):
    """Test 19: Admin change case status"""
    if admin_username not in tokens:
        log_fail(f"Admin status change for {admin_username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/cases/{case_id}/action",
            headers={"Authorization": f"Bearer {tokens[admin_username]}"},
            json={"action": "status", "status": new_status, "note": "Test status change"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Admin status change to {new_status} for {admin_username}")
            else:
                log_fail(f"Admin status change for {admin_username}", f"Response not ok: {data}")
        else:
            log_fail(f"Admin status change for {admin_username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Admin status change for {admin_username}", str(e))

def test_admin_official_update(admin_username, case_id):
    """Test 20: Admin add official update"""
    if admin_username not in tokens:
        log_fail(f"Admin official update for {admin_username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/cases/{case_id}/action",
            headers={"Authorization": f"Bearer {tokens[admin_username]}"},
            json={"action": "update", "note": "Official update: Work has been scheduled for next week."},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Admin official update for {admin_username}")
            else:
                log_fail(f"Admin official update for {admin_username}", f"Response not ok: {data}")
        else:
            log_fail(f"Admin official update for {admin_username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Admin official update for {admin_username}", str(e))

def test_resident_cannot_access_admin(resident_username, case_id):
    """Test 21: Resident cannot access admin endpoints (403)"""
    if resident_username not in tokens:
        log_fail(f"Resident admin access test for {resident_username}", "No token available")
        return
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/cases/{case_id}/action",
            headers={"Authorization": f"Bearer {tokens[resident_username]}"},
            json={"action": "verify"},
            timeout=10
        )
        if response.status_code == 403:
            log_pass(f"Resident correctly denied admin access ({resident_username})")
        else:
            log_fail(f"Resident admin access test", f"Expected 403, got {response.status_code}")
    except Exception as e:
        log_fail(f"Resident admin access test for {resident_username}", str(e))

def test_analytics(admin_username):
    """Test 22: Analytics endpoint"""
    if admin_username not in tokens:
        log_fail(f"Analytics for {admin_username}", "No token available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/analytics",
            headers={"Authorization": f"Bearer {tokens[admin_username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "cases" in data and "reports" in data and "trend" in data:
                log_pass(f"Analytics for {admin_username}")
            else:
                log_fail(f"Analytics for {admin_username}", f"Missing fields: {data}")
        else:
            log_fail(f"Analytics for {admin_username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Analytics for {admin_username}", str(e))

def test_media_upload(username):
    """Test 23: Media upload"""
    if username not in tokens:
        log_fail(f"Media upload for {username}", "No token available")
        return None
    
    try:
        # Create a small valid PNG (1x1 pixel red PNG)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        
        files = {'file': ('test_evidence.png', io.BytesIO(png_data), 'image/png')}
        response = requests.post(
            f"{BASE_URL}/files",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            files=files,
            timeout=30
        )
        if response.status_code == 201:
            data = response.json()
            if "id" in data:
                log_pass(f"Media upload for {username}")
                return data["id"]
            else:
                log_fail(f"Media upload for {username}", f"Missing id: {data}")
        else:
            log_fail(f"Media upload for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Media upload for {username}", str(e))
    return None

def test_media_download(username, file_id):
    """Test 24: Media download"""
    if username not in tokens or not file_id:
        log_fail(f"Media download for {username}", "No token or file_id available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=30
        )
        if response.status_code == 200:
            if len(response.content) > 0:
                log_pass(f"Media download for {username}")
            else:
                log_fail(f"Media download for {username}", "Empty file content")
        else:
            log_fail(f"Media download for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Media download for {username}", str(e))

def test_media_delete(username, file_id):
    """Test 25: Media delete unattached evidence"""
    if username not in tokens or not file_id:
        log_fail(f"Media delete for {username}", "No token or file_id available")
        return
    
    try:
        response = requests.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                log_pass(f"Media delete for {username}")
            else:
                log_fail(f"Media delete for {username}", f"Response not ok: {data}")
        else:
            log_fail(f"Media delete for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Media delete for {username}", str(e))

def test_community_endpoint(username):
    """Test 26: Community endpoint"""
    if username not in tokens:
        log_fail(f"Community endpoint for {username}", "No token available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/community",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "admins" in data and "registered_residents" in data:
                log_pass(f"Community endpoint for {username}")
            else:
                log_fail(f"Community endpoint for {username}", f"Missing fields: {data}")
        else:
            log_fail(f"Community endpoint for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Community endpoint for {username}", str(e))

def test_overview_endpoint(username):
    """Test 27: Overview endpoint"""
    if username not in tokens:
        log_fail(f"Overview endpoint for {username}", "No token available")
        return
    
    try:
        response = requests.get(
            f"{BASE_URL}/overview",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "total" in data and "active" in data and "counts" in data:
                log_pass(f"Overview endpoint for {username}")
            else:
                log_fail(f"Overview endpoint for {username}", f"Missing fields: {data}")
        else:
            log_fail(f"Overview endpoint for {username}", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail(f"Overview endpoint for {username}", str(e))

def test_create_society():
    """Test 28: Create a new society"""
    try:
        response = requests.post(
            f"{BASE_URL}/societies",
            json={
                "name": "Test Society",
                "location": "Test City",
                "address": "123 Test Street, Test City",
                "population": 5000,
                "latitude": 28.6139,
                "longitude": 77.2090,
                "admin_name": "Test Admin",
                "admin_email": "testadmin@example.com",
                "admin_capacity": 10,
                "admin_ratio": 1000
            },
            timeout=10
        )
        if response.status_code == 201:
            data = response.json()
            if "token" in data and "credentials" in data:
                log_pass("Create new society")
            else:
                log_fail("Create new society", f"Missing fields: {data}")
        else:
            log_fail("Create new society", f"Status code {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Create new society", str(e))

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    
    if test_results['failed']:
        print("\n" + "="*80)
        print("FAILED TESTS DETAILS:")
        print("="*80)
        for failure in test_results['failed']:
            print(f"\n❌ {failure['test']}")
            print(f"   Error: {failure['error']}")
    
    if test_results['warnings']:
        print("\n" + "="*80)
        print("WARNINGS:")
        print("="*80)
        for warning in test_results['warnings']:
            print(f"\n⚠️  {warning['test']}")
            print(f"   Message: {warning['message']}")

def main():
    print("="*80)
    print("CityPulse Backend Comprehensive Testing")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Society Code: {SOCIETY_CODE}")
    print("="*80 + "\n")
    
    # Test 1: Health
    print("\n--- HEALTH CHECK ---")
    test_health()
    
    # Test 2: Demo info
    print("\n--- DEMO INFO ---")
    test_demo_info()
    
    # Test 3-4: Authentication (REGRESSION TEST)
    print("\n--- AUTHENTICATION (REGRESSION: Society Code Login) ---")
    owner_data = test_login("owner", "initial_admin")
    admin_data = test_login("blockb.admin", "admin")
    admin2_data = test_login("utilities.admin", "admin")
    resident_data = test_login("elena", "resident")
    test_invalid_login()
    
    # Test 5: Session validation
    print("\n--- SESSION VALIDATION ---")
    test_session_validation("owner")
    test_session_validation("elena")
    
    # NEW FEATURE TESTS: Email-based authentication
    print("\n--- NEW FEATURE: EMAIL-BASED AUTHENTICATION ---")
    print("Testing email registration and login...")
    
    # Test: Register with unique email
    email_user = test_register_with_email()
    
    if email_user:
        # Test: Duplicate email registration
        test_register_duplicate_email(email_user["email"])
        
        # Test: Login with email
        email_token = test_login_with_email(email_user["email"], email_user["password"])
        
        # Test: Token validation
        if email_token:
            test_email_token_validation(email_token)
        
        # Test: Wrong password
        test_login_email_wrong_password(email_user["email"])
    
    # Test: Invalid email format
    test_register_invalid_email()
    
    # Test: Non-existent email
    test_login_email_nonexistent()
    
    # Test 6: Register (old test without email)
    print("\n--- REGISTRATION (Legacy without email) ---")
    new_resident = test_register_new_resident()
    
    # Test 8: Civic data
    print("\n--- CIVIC DATA ---")
    test_civic_data("elena")
    
    # Test 9-10: Problems list and detail
    print("\n--- PROBLEMS LIST & DETAIL ---")
    problems = test_list_problems("elena")
    if problems and len(problems) > 0:
        first_case_id = problems[0]["id"]
        test_problem_detail("elena", first_case_id)
    
    # Test 11: Report problem
    print("\n--- REPORT PROBLEM ---")
    new_case_id = test_report_problem("elena")
    
    # Use the new case or first existing case for further tests
    test_case_id = new_case_id if new_case_id else (first_case_id if problems and len(problems) > 0 else None)
    
    if test_case_id:
        # Test 12-14: Signals (vote, confirm, follow)
        print("\n--- SIGNALS (VOTE/CONFIRM/FOLLOW) ---")
        test_vote_on_problem("blockb.admin", test_case_id)
        test_confirm_affected("utilities.admin", test_case_id)
        test_follow_problem("elena", test_case_id)
        
        # Test 15-16: Comments
        print("\n--- COMMENTS ---")
        comment_id = test_add_comment("elena", test_case_id)
        if comment_id:
            test_mark_comment_helpful("blockb.admin", comment_id)
        
        # Test 17-20: Admin actions
        print("\n--- ADMIN ACTIONS ---")
        test_admin_verify_case("blockb.admin", test_case_id)
        if admin_data and "user" in admin_data:
            test_admin_assign_case("owner", test_case_id, admin_data["user"]["id"])
        test_admin_status_change("blockb.admin", test_case_id, "In Progress")
        test_admin_official_update("blockb.admin", test_case_id)
        
        # Test 21: Permission check
        print("\n--- PERMISSION CHECKS ---")
        test_resident_cannot_access_admin("elena", test_case_id)
    
    # Test 22: Analytics
    print("\n--- ANALYTICS ---")
    test_analytics("owner")
    
    # Test 23-25: Media
    print("\n--- MEDIA UPLOAD/DOWNLOAD/DELETE ---")
    file_id = test_media_upload("elena")
    if file_id:
        test_media_download("elena", file_id)
        test_media_delete("elena", file_id)
    
    # Test 26-27: Community and Overview
    print("\n--- COMMUNITY & OVERVIEW ---")
    test_community_endpoint("elena")
    test_overview_endpoint("elena")
    
    # Test 28: Create society
    print("\n--- CREATE SOCIETY ---")
    test_create_society()
    
    # Test 7: Logout (do this last to avoid invalidating tokens)
    print("\n--- LOGOUT ---")
    if new_resident:
        # Re-login the new resident first
        test_login(new_resident, "resident")
        test_logout(new_resident)
    
    # Print summary
    print_summary()
    
    # Return exit code based on failures
    return 0 if len(test_results['failed']) == 0 else 1

if __name__ == "__main__":
    exit(main())
