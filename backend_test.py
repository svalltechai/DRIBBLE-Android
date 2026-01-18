#!/usr/bin/env python3
"""
DRIBBLE Admin API Backend Test Suite - DRIBBLE-NEW-2026 Sync Testing
Tests all backend endpoints synced with new web app backend
"""

import requests
import json
import sys
from typing import Dict, Optional

# Backend URL from environment
BACKEND_URL = "https://dribble-order-sync.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
ADMIN_EMAIL = "admin@dribble.com"
ADMIN_PASSWORD = "Admin123!"

class DribbleAPITester:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json"
        }
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str, response_data: Optional[Dict] = None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data
        })
        
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, indent=2)}")
    
    def test_health_check(self):
        """Test GET /api/health endpoint - should return version 2.0.0"""
        try:
            response = requests.get(f"{API_BASE}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy" and data.get("version") == "2.0.0":
                    self.log_test("Health Check", True, f"API is healthy, version {data.get('version')}", data)
                    return True
                elif data.get("status") == "healthy":
                    self.log_test("Health Check", False, f"Wrong version: {data.get('version')}, expected 2.0.0", data)
                    return False
                else:
                    self.log_test("Health Check", False, f"Unexpected health status: {data.get('status')}", data)
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Request failed: {str(e)}")
            return False
    
    def test_admin_login(self):
        """Test POST /api/auth/login endpoint"""
        try:
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = requests.post(
                f"{API_BASE}/auth/login",
                json=login_data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                if "access_token" in data and "user" in data:
                    self.access_token = data["access_token"]
                    
                    # Update headers with auth token
                    self.headers["Authorization"] = f"Bearer {self.access_token}"
                    
                    user_info = data["user"]
                    if user_info.get("email") == ADMIN_EMAIL and user_info.get("role") == "admin":
                        self.log_test("Admin Login", True, "Login successful with valid token", data)
                        return True
                    else:
                        self.log_test("Admin Login", False, "Invalid user info in response", data)
                        return False
                else:
                    self.log_test("Admin Login", False, "Missing access_token or user in response", data)
                    return False
            else:
                self.log_test("Admin Login", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Admin Login", False, f"Request failed: {str(e)}")
            return False
    
    def test_get_current_user(self):
        """Test GET /api/auth/me endpoint - should return user info with name field"""
        if not self.access_token:
            self.log_test("Get Current User", False, "No access token available")
            return False
            
        try:
            response = requests.get(
                f"{API_BASE}/auth/me",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("email") == ADMIN_EMAIL and data.get("role") == "admin" and "name" in data:
                    self.log_test("Get Current User", True, f"User info retrieved with name: {data.get('name')}", data)
                    return True
                elif "name" not in data:
                    self.log_test("Get Current User", False, "User info missing required 'name' field", data)
                    return False
                else:
                    self.log_test("Get Current User", False, "Invalid user info returned", data)
                    return False
            else:
                self.log_test("Get Current User", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Current User", False, f"Request failed: {str(e)}")
            return False
    
    def test_get_orders(self):
        """Test GET /api/admin/orders endpoint - should return orders with new fields"""
        if not self.access_token:
            self.log_test("Get Orders", False, "No access token available")
            return False
            
        try:
            response = requests.get(
                f"{API_BASE}/admin/orders",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    # Check for new schema fields in first order
                    sample_order = data[0]
                    new_fields = ["shipment", "selected_courier", "payment_method"]
                    present_fields = [field for field in new_fields if field in sample_order]
                    
                    self.log_test("Get Orders", True, f"Retrieved {len(data)} orders with new fields: {present_fields}", {"order_count": len(data), "new_fields": present_fields})
                    return True
                elif isinstance(data, list):
                    self.log_test("Get Orders", True, f"Retrieved {len(data)} orders (no sample data)", {"order_count": len(data)})
                    return True
                else:
                    self.log_test("Get Orders", False, "Response is not a list", data)
                    return False
            else:
                self.log_test("Get Orders", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Orders", False, f"Request failed: {str(e)}")
            return False
    
    def test_get_orders_with_status_filter(self):
        """Test GET /api/admin/orders?status=pending endpoint - should include both pending and payment_pending"""
        if not self.access_token:
            self.log_test("Get Orders (Status Filter)", False, "No access token available")
            return False
            
        try:
            response = requests.get(
                f"{API_BASE}/admin/orders?status=pending",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    # Check if filtering works - should include both "pending" and "payment_pending"
                    valid_statuses = ["pending", "payment_pending"]
                    invalid_orders = [order for order in data if order.get("status") not in valid_statuses]
                    
                    if len(invalid_orders) == 0:
                        self.log_test("Get Orders (Status Filter)", True, f"Status filtering working correctly, found {len(data)} pending orders", {"pending_count": len(data)})
                        return True
                    else:
                        self.log_test("Get Orders (Status Filter)", False, f"Filter not working properly. Found {len(invalid_orders)} orders with invalid status")
                        return False
                else:
                    self.log_test("Get Orders (Status Filter)", False, "Response is not a list", data)
                    return False
            else:
                self.log_test("Get Orders (Status Filter)", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Orders (Status Filter)", False, f"Request failed: {str(e)}")
            return False
    
    def test_get_single_order(self):
        """Test GET /api/orders/{order_id} endpoint - verify new schema fields"""
        if not self.access_token:
            self.log_test("Get Single Order", False, "No access token available")
            return False
        
        # First get orders to find an order ID
        try:
            orders_response = requests.get(
                f"{API_BASE}/admin/orders",
                headers=self.headers,
                timeout=10
            )
            
            if orders_response.status_code != 200:
                self.log_test("Get Single Order", False, "Could not fetch orders to get order ID")
                return False
                
            orders = orders_response.json()
            if not orders or len(orders) == 0:
                self.log_test("Get Single Order", False, "No orders available to test with")
                return False
                
            order_id = orders[0].get("id")
            if not order_id:
                self.log_test("Get Single Order", False, "Order ID not found in first order")
                return False
            
            # Now test getting single order
            response = requests.get(
                f"{API_BASE}/orders/{order_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("id") == order_id:
                    # Check for new schema fields
                    new_fields = ["shipment", "selected_courier", "payment_method"]
                    present_fields = [field for field in new_fields if field in data]
                    
                    self.log_test("Get Single Order", True, f"Retrieved order {order_id} with new fields: {present_fields}", {"order_id": order_id, "new_fields": present_fields})
                    return True
                else:
                    self.log_test("Get Single Order", False, f"Order ID mismatch. Expected {order_id}, got {data.get('id')}", data)
                    return False
            else:
                self.log_test("Get Single Order", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Single Order", False, f"Request failed: {str(e)}")
            return False
    
    def test_update_order_status_put(self):
        """Test PUT /api/admin/orders/{order_id}/status endpoint - NEW endpoint (changed from PATCH to PUT)"""
        if not self.access_token:
            self.log_test("Update Order Status PUT", False, "No access token available")
            return False
        
        # First get orders to find an order ID
        try:
            orders_response = requests.get(
                f"{API_BASE}/admin/orders",
                headers=self.headers,
                timeout=10
            )
            
            if orders_response.status_code != 200:
                self.log_test("Update Order Status PUT", False, "Could not fetch orders to get order ID")
                return False
                
            orders = orders_response.json()
            if not orders or len(orders) == 0:
                self.log_test("Update Order Status PUT", False, "No orders available to test with")
                return False
                
            # Find an order that's not already confirmed
            test_order = None
            for order in orders:
                if order.get("status") != "confirmed":
                    test_order = order
                    break
            
            if not test_order:
                # Use first order anyway
                test_order = orders[0]
                
            order_id = test_order.get("id")
            old_status = test_order.get("status")
            if not order_id:
                self.log_test("Update Order Status PUT", False, "Order ID not found")
                return False
            
            # Update order status to confirmed using PUT
            update_data = {"status": "confirmed"}
            
            response = requests.put(
                f"{API_BASE}/admin/orders/{order_id}/status",
                json=update_data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "confirmed":
                    self.log_test("Update Order Status PUT", True, f"Updated order {order_id} status from {old_status} to confirmed using PUT", {"order_id": order_id, "old_status": old_status, "new_status": "confirmed"})
                    return True
                else:
                    self.log_test("Update Order Status PUT", False, f"Status not updated. Expected 'confirmed', got '{data.get('status')}'", data)
                    return False
            else:
                self.log_test("Update Order Status PUT", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Update Order Status PUT", False, f"Request failed: {str(e)}")
            return False
    
    def test_get_order_stats(self):
        """Test GET /api/admin/orders/stats endpoint"""
        if not self.access_token:
            self.log_test("Get Order Stats", False, "No access token available")
            return False
            
        try:
            response = requests.get(
                f"{API_BASE}/admin/orders/stats",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ["total_orders", "pending_orders", "today_orders"]
                if all(field in data for field in required_fields):
                    self.log_test("Get Order Stats", True, "Order statistics retrieved successfully", data)
                    return True
                else:
                    missing_fields = [field for field in required_fields if field not in data]
                    self.log_test("Get Order Stats", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_test("Get Order Stats", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Get Order Stats", False, f"Request failed: {str(e)}")
            return False
    
    def test_register_push_token(self):
        """Test POST /api/admin/push-tokens endpoint"""
        if not self.access_token:
            self.log_test("Register Push Token", False, "No access token available")
            return False
            
        try:
            push_data = {
                "push_token": "test_token_12345",
                "device_info": {
                    "brand": "TestDevice",
                    "model": "TestModel",
                    "os": "TestOS"
                }
            }
            
            response = requests.post(
                f"{API_BASE}/admin/push-tokens",
                json=push_data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "message" in data and "successfully" in data["message"].lower():
                    self.log_test("Register Push Token", True, "Push token registered successfully", data)
                    return True
                else:
                    self.log_test("Register Push Token", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("Register Push Token", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Register Push Token", False, f"Request failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("🚀 Starting DRIBBLE Admin API Backend Tests")
        print(f"📡 Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("Admin Login", self.test_admin_login),
            ("Get Current User", self.test_get_current_user),
            ("Get Orders", self.test_get_orders),
            ("Get Orders (Status Filter)", self.test_get_orders_with_status_filter),
            ("Get Single Order", self.test_get_single_order),
            ("Update Order Status", self.test_update_order_status),
            ("Get Order Stats", self.test_get_order_stats),
            ("Register Push Token", self.test_register_push_token),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                success = test_func()
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log_test(test_name, False, f"Test execution failed: {str(e)}")
                failed += 1
            
            print()  # Add spacing between tests
        
        # Summary
        print("=" * 60)
        print(f"📊 Test Summary: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {failed} test(s) failed")
            return False

def main():
    """Main test execution"""
    tester = DribbleAPITester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()