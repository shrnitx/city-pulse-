#!/usr/bin/env python3
"""
Focused testing for NEW email & password login feature in CityPulse
Tests email-based authentication + regression check for existing society login
"""
import requests
import json
import time
import random

# Base URL from frontend/.env
BASE_URL = "https://87d279e3-c0bd-4c1c-8eb4-6f0923fa9f52.preview.emergentagent.com/api"

# Demo credentials
SOCIETY_CODE = "GV-48291"
PASSWORD = "CityPulse2025!"

# Test results
results = {"passed": [], "failed": []}

def log_pass(test_name):
    results["passed"].append(test_name)
    print(f"✅ PASS: {test_name}")

def log_fail(test_name, error):
    results["failed"].append({"test": test_name, "error": str(error)})
    print(f"❌ FAIL: {test_name}")
    print(f"   Error: {error}")

def test_1_register_with_email():
    """Test 1: POST /api/auth/register with email -> expect 201"""
    print("\n--- Test 1: Register with unique email ---")
    unique_email = f"newperson{random.randint(10000, 99999)}_{int(time.time())}@example.com"
    username = f"newuser{random.randint(1000, 9999)}"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "society_code": SOCIETY_CODE,
                "name": "New Person",
                "email": unique_email,
                "username": username,
                "password": "password123",
                "area": "Block C"
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            if "token" in data and "user" in data and "society" in data:
                if data["user"].get("email") == unique_email.lower():
                    log_pass("Register with email returns 201 with token+user+society")
                    return {"email": unique_email, "password": "password123", "token": data["token"]}
                else:
                    log_fail("Register with email", f"Email not stored correctly: {data['user'].get('email')}")
            else:
                log_fail("Register with email", f"Missing required fields in response: {data}")
        else:
            log_fail("Register with email", f"Expected 201, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Register with email", str(e))
    
    return None

def test_2_login_with_email(email, password):
    """Test 2: POST /api/auth/login-email -> expect 200"""
    print("\n--- Test 2: Login with email ---")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login-email",
            json={
                "email": email,
                "password": password
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data and "society" in data:
                log_pass("Login with email returns 200 with token+user+society")
                return data["token"]
            else:
                log_fail("Login with email", f"Missing required fields: {data}")
        else:
            log_fail("Login with email", f"Expected 200, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Login with email", str(e))
    
    return None

def test_3_duplicate_email(email):
    """Test 3: Register with duplicate email -> expect 409"""
    print("\n--- Test 3: Duplicate email registration ---")
    username = f"duplicate{random.randint(1000, 9999)}"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "society_code": SOCIETY_CODE,
                "name": "Duplicate User",
                "email": email,
                "username": username,
                "password": "anotherpass123",
                "area": "Block D"
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 409:
            log_pass("Duplicate email rejected with 409")
        else:
            log_fail("Duplicate email", f"Expected 409, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Duplicate email", str(e))

def test_4_invalid_email_format():
    """Test 4: Register with invalid email format -> expect 422"""
    print("\n--- Test 4: Invalid email format ---")
    username = f"invalidemail{random.randint(1000, 9999)}"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={
                "society_code": SOCIETY_CODE,
                "name": "Invalid Email User",
                "email": "notanemail",
                "username": username,
                "password": "validpass123",
                "area": "Block E"
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 422:
            log_pass("Invalid email format rejected with 422")
        else:
            log_fail("Invalid email format", f"Expected 422, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Invalid email format", str(e))

def test_5_wrong_password(email):
    """Test 5: Login with wrong password -> expect 401"""
    print("\n--- Test 5: Wrong password ---")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login-email",
            json={
                "email": email,
                "password": "wrongpassword"
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            log_pass("Wrong password rejected with 401")
        else:
            log_fail("Wrong password", f"Expected 401, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Wrong password", str(e))

def test_6_nonexistent_email():
    """Test 6: Login with non-existent email -> expect 401"""
    print("\n--- Test 6: Non-existent email ---")
    random_email = f"nonexistent{random.randint(10000, 99999)}@example.com"
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login-email",
            json={
                "email": random_email,
                "password": "somepassword"
            },
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            log_pass("Non-existent email rejected with 401")
        else:
            log_fail("Non-existent email", f"Expected 401, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Non-existent email", str(e))

def test_7_regression_society_login():
    """Test 7: REGRESSION - Society code + username login still works"""
    print("\n--- Test 7: REGRESSION - Society code login ---")
    
    # Test owner account
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "society_code": SOCIETY_CODE,
                "username": "owner",
                "password": PASSWORD
            },
            timeout=10
        )
        
        print(f"   Owner login status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and data.get("user", {}).get("role") == "initial_admin":
                log_pass("REGRESSION: owner account login works")
            else:
                log_fail("REGRESSION: owner login", f"Invalid response: {data}")
        else:
            log_fail("REGRESSION: owner login", f"Expected 200, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("REGRESSION: owner login", str(e))
    
    # Test elena account
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "society_code": SOCIETY_CODE,
                "username": "elena",
                "password": PASSWORD
            },
            timeout=10
        )
        
        print(f"   Elena login status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data and data.get("user", {}).get("role") == "resident":
                log_pass("REGRESSION: elena account login works")
            else:
                log_fail("REGRESSION: elena login", f"Invalid response: {data}")
        else:
            log_fail("REGRESSION: elena login", f"Expected 200, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("REGRESSION: elena login", str(e))

def test_8_email_token_validation(token):
    """Test 8: Token from email login works on protected route"""
    print("\n--- Test 8: Email login token validation ---")
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "user" in data and "society" in data:
                log_pass("Email login token validated on /auth/me")
            else:
                log_fail("Email token validation", f"Missing fields: {data}")
        else:
            log_fail("Email token validation", f"Expected 200, got {response.status_code}: {response.text}")
    except Exception as e:
        log_fail("Email token validation", str(e))

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("FOCUSED EMAIL AUTH TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {len(results['passed'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    
    if results['failed']:
        print("\n" + "="*80)
        print("FAILED TESTS:")
        print("="*80)
        for failure in results['failed']:
            print(f"\n❌ {failure['test']}")
            print(f"   Error: {failure['error']}")
    
    if results['passed']:
        print("\n" + "="*80)
        print("PASSED TESTS:")
        print("="*80)
        for test in results['passed']:
            print(f"✅ {test}")

def main():
    print("="*80)
    print("CityPulse - Focused Email & Password Login Testing")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Society Code: {SOCIETY_CODE}")
    print("="*80)
    
    # Test 1: Register with email
    email_user = test_1_register_with_email()
    
    if email_user:
        # Test 2: Login with email
        email_token = test_2_login_with_email(email_user["email"], email_user["password"])
        
        # Test 3: Duplicate email
        test_3_duplicate_email(email_user["email"])
        
        # Test 5: Wrong password
        test_5_wrong_password(email_user["email"])
        
        # Test 8: Token validation
        if email_token:
            test_8_email_token_validation(email_token)
    
    # Test 4: Invalid email format
    test_4_invalid_email_format()
    
    # Test 6: Non-existent email
    test_6_nonexistent_email()
    
    # Test 7: REGRESSION - society login
    test_7_regression_society_login()
    
    # Print summary
    print_summary()
    
    return 0 if len(results['failed']) == 0 else 1

if __name__ == "__main__":
    exit(main())
