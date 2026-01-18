"""
DRIBBLE Admin API - Synchronized with Web App Backend (DRIBBLE-NEW-2026)
Updated: June 2025
"""

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import bcrypt
import jwt
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'dribble-admin-secret-key-2026')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="DRIBBLE Admin API", version="2.0.0")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()


# ============================================
# ENUMS (Synced with new backend)
# ============================================
class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    VIEWER = "viewer"

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


# ============================================
# MODELS (Synced with new backend)
# ============================================
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    name: Optional[str] = None
    password_hash: str
    role: UserRole = UserRole.ADMIN
    is_active: bool = True
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserLogin(BaseModel):
    email: str  # Can be email or mobile
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict

class ShippingAddress(BaseModel):
    person_name: str
    business_name: Optional[str] = None
    gst_number: Optional[str] = None
    address: str
    state: str
    city: str
    pincode: str
    mobile_1: str
    mobile_2: Optional[str] = None
    email_1: Optional[str] = None
    email_2: Optional[str] = None
    country: str = "India"

class OrderItem(BaseModel):
    inventory_id: str
    sku: str
    name: str
    color: str
    size: str
    price: float
    quantity: int
    gst_rate: float = 5.0
    hsn_code: Optional[str] = None
    shipping_weight: float = 0.5

class SelectedCourier(BaseModel):
    id: str
    shipmozo_id: Optional[int] = None
    name: str
    full_name: Optional[str] = None
    mode: str
    rate: float
    estimated_days: Optional[str] = None

class Shipment(BaseModel):
    awb_number: Optional[str] = None
    carrier_name: Optional[str] = None
    carrier_mode: Optional[str] = None
    estimated_days: Optional[str] = None
    status: Optional[str] = None
    is_shipmozo_booked: bool = False
    shipmozo_order_id: Optional[str] = None
    booked_at: Optional[str] = None

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str
    customer_id: Optional[str] = None
    shop_customer_id: Optional[str] = None
    customer_email: str
    customer_name: str
    customer_phone: str
    shipping_address: ShippingAddress
    items: List[OrderItem]
    subtotal: float
    tax: float = 0.0
    shipping_cost: float = 0.0
    total_amount: float
    status: OrderStatus = OrderStatus.PENDING
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    payment_gateway: Optional[str] = None
    payment_method: Optional[str] = None
    payment_method_details: Optional[Dict] = None
    payment_mode: Optional[str] = None
    order_notes: Optional[str] = None
    selected_courier: Optional[Dict] = None
    shipment: Optional[Dict] = None
    estimated_weight: Optional[float] = None
    inventory_deducted: bool = False
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[str] = None
    cancelled_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class CancelOrderRequest(BaseModel):
    reason: Optional[str] = None

class PushToken(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    push_token: str
    device_info: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Customer(BaseModel):
    """Customer model for creating customers from orders"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    person_name: str
    business_name: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    mobile_1: str
    mobile_2: Optional[str] = None
    email_1: Optional[str] = None
    email_2: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================
# HELPER FUNCTIONS
# ============================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(user_id: str, email: str, role: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================
# AUTH ENDPOINTS (Synced with new backend)
# ============================================
@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Admin login endpoint - supports both email and mobile login
    Synced with DRIBBLE-NEW-2026 auth.py
    """
    identifier = credentials.email
    
    # Support both email and mobile login
    user = await db.users.find_one({
        "$or": [
            {"email": identifier},
            {"mobile": identifier}
        ]
    }, {"_id": 0})
    
    if not user:
        # Create default admin if not exists (for initial setup)
        if credentials.email == "admin@dribble.com" and credentials.password == "Admin123!":
            user = {
                "id": str(uuid.uuid4()),
                "email": "admin@dribble.com",
                "name": "Admin",
                "password_hash": hash_password("Admin123!"),
                "role": "admin",
                "is_active": True,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
        else:
            raise HTTPException(status_code=401, detail="Invalid email/mobile or password")
    
    # Check if account is active (synced with new backend)
    if user.get("is_active") is False:
        raise HTTPException(status_code=401, detail="Account is deactivated. Contact admin.")
    
    if not verify_password(credentials.password, user.get('password_hash', '')):
        # Check for default admin password
        if credentials.email == "admin@dribble.com" and credentials.password == "Admin123!":
            pass  # Allow default password
        else:
            raise HTTPException(status_code=401, detail="Invalid email/mobile or password")
    
    token = create_access_token(
        user['id'], 
        user.get('email', user.get('mobile', '')), 
        user.get('role', 'admin')
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "email": user.get('email', ''),
            "name": user.get('name', ''),
            "role": user.get('role', 'admin')
        }
    }

@api_router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user info"""
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password_hash": 0})
    
    if not user_doc:
        return {
            "id": current_user['user_id'],
            "email": current_user['email'],
            "role": current_user['role']
        }
    
    return {
        "id": user_doc['id'],
        "email": user_doc.get('email', ''),
        "name": user_doc.get('name', ''),
        "role": user_doc.get('role', 'admin')
    }


# ============================================
# ORDERS ENDPOINTS (Synced with new backend)
# ============================================
@api_router.get("/admin/orders")
async def get_orders(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all orders with optional filtering
    Synced with DRIBBLE-NEW-2026 orders.py
    """
    query = {}
    
    if status and status != 'all':
        # Handle combined statuses (synced with new backend)
        if status == "refunded":
            query['status'] = {"$in": ["refunded", "partially_refunded"]}
        elif status == "pending":
            query['status'] = {"$in": ["pending", "payment_pending"]}
        else:
            query['status'] = status
    
    if search:
        query['$or'] = [
            {'order_number': {'$regex': search, '$options': 'i'}},
            {'customer_name': {'$regex': search, '$options': 'i'}},
            {'customer_phone': {'$regex': search, '$options': 'i'}},
            {'customer_email': {'$regex': search, '$options': 'i'}},
        ]
    
    skip = (page - 1) * limit
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Convert datetime strings if needed
    for order in orders:
        if isinstance(order.get("created_at"), str):
            order["created_at"] = datetime.fromisoformat(order["created_at"].replace('Z', '+00:00'))
        if isinstance(order.get("updated_at"), str):
            order["updated_at"] = datetime.fromisoformat(order["updated_at"].replace('Z', '+00:00'))
    
    return orders

@api_router.get("/admin/orders/stats")
async def get_order_stats(current_user: dict = Depends(get_current_user)):
    """Get order statistics"""
    total_orders = await db.orders.count_documents({})
    pending_orders = await db.orders.count_documents({"status": {"$in": ["pending", "payment_pending"]}})
    paid_orders = await db.orders.count_documents({"status": "paid"})
    shipped_orders = await db.orders.count_documents({"status": "shipped"})
    delivered_orders = await db.orders.count_documents({"status": "delivered"})
    cancelled_orders = await db.orders.count_documents({"status": "cancelled"})
    
    # Today's orders
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = await db.orders.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "paid_orders": paid_orders,
        "shipped_orders": shipped_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "today_orders": today_orders
    }

@api_router.get("/admin/orders/{order_id}")
async def get_admin_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Get single order by ID (admin endpoint)"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Get single order by ID"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@api_router.put("/admin/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update order status - PUT endpoint (synced with new backend)
    Changed from PATCH to PUT to match DRIBBLE-NEW-2026
    """
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.get('status', 'pending')
    new_status = status_update.status.value
    
    # Update order
    await db.orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Fetch updated order
    updated_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    # Log status change
    logger.info(f"Order {order_id} status changed from {old_status} to {new_status} by {current_user.get('email', 'unknown')}")
    
    return updated_order

# Keep PATCH for backward compatibility
@api_router.patch("/admin/orders/{order_id}/status")
async def update_order_status_patch(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update order status - PATCH endpoint (backward compatibility)"""
    return await update_order_status(order_id, status_update, current_user)

@api_router.post("/admin/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    cancel_request: CancelOrderRequest = CancelOrderRequest(),
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel an order with reason - synced with new backend
    New endpoint from DRIBBLE-NEW-2026
    """
    order = await db.orders.find_one({"id": order_id})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="Order is already cancelled")
    
    if order.get("status") == "delivered":
        raise HTTPException(status_code=400, detail="Cannot cancel a delivered order")
    
    if order.get("status") == "in_transit":
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel - shipment has already been picked up by the courier."
        )
    
    # Update order status
    update_data = {
        "status": "cancelled",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "cancellation_reason": cancel_request.reason or "Cancelled by admin",
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "cancelled_by": current_user.get("email", current_user.get("user_id")),
        "cancelled_by_type": "admin"
    }
    
    # Update shipment status if exists
    if order.get("shipment"):
        update_data["shipment.status"] = "cancelled"
        update_data["shipment.cancelled_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": update_data}
    )
    
    updated_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    return {
        "success": True,
        "message": "Order cancelled successfully",
        "order_id": order_id,
        "order_number": order.get("order_number"),
        "order": updated_order
    }


# ============================================
# PUSH NOTIFICATION TOKEN MANAGEMENT
# ============================================
@api_router.post("/admin/push-tokens")
async def register_push_token(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Register push notification token for admin"""
    push_token = data.get('push_token')
    device_info = data.get('device_info', {})
    
    if not push_token:
        raise HTTPException(status_code=400, detail="Push token is required")
    
    # Upsert token
    await db.push_tokens.update_one(
        {"push_token": push_token},
        {
            "$set": {
                "user_id": current_user['user_id'],
                "push_token": push_token,
                "device_info": device_info,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Push token registered successfully"}

@api_router.delete("/admin/push-tokens")
async def unregister_push_token(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Unregister push notification token"""
    push_token = data.get('push_token')
    
    if push_token:
        await db.push_tokens.delete_one({"push_token": push_token})
    
    return {"message": "Push token unregistered"}


# ============================================
# HEALTH CHECK
# ============================================
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dribble-admin-api", "version": "2.0.0"}

@api_router.get("/")
async def root():
    return {"message": "DRIBBLE Admin API", "version": "2.0.0", "synced_with": "DRIBBLE-NEW-2026"}


# ============================================
# APP SETUP
# ============================================
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# ============================================
# SAMPLE DATA CREATION (Updated for new schema)
# ============================================
@app.on_event("startup")
async def create_sample_data():
    """Create sample orders for testing with new schema fields"""
    order_count = await db.orders.count_documents({})
    
    if order_count == 0:
        sample_orders = [
            {
                "id": str(uuid.uuid4()),
                "order_number": "D-1-15012026-1",
                "customer_email": "customer1@example.com",
                "customer_name": "Rahul Sharma",
                "customer_phone": "+91 98765 43210",
                "shipping_address": {
                    "person_name": "Rahul Sharma",
                    "business_name": "Sharma Sports",
                    "gst_number": "29ABCDE1234F1Z5",
                    "address": "123 MG Road, Koramangala",
                    "state": "Karnataka",
                    "city": "Bangalore",
                    "pincode": "560034",
                    "mobile_1": "+91 98765 43210",
                    "country": "India"
                },
                "items": [
                    {"inventory_id": "inv1", "sku": "DRB-TS-001", "name": "Sports T-Shirt", "color": "Blue", "size": "L", "price": 450, "quantity": 20, "gst_rate": 5, "shipping_weight": 0.3},
                    {"inventory_id": "inv2", "sku": "DRB-TP-002", "name": "Track Pants", "color": "Black", "size": "M", "price": 650, "quantity": 15, "gst_rate": 5, "shipping_weight": 0.4}
                ],
                "subtotal": 18750,
                "tax": 937.5,
                "shipping_cost": 0,
                "total_amount": 19687.5,
                "status": "pending",
                "estimated_weight": 12.0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "order_number": "D-1-15012026-2",
                "customer_email": "customer2@example.com",
                "customer_name": "Priya Patel",
                "customer_phone": "+91 87654 32109",
                "shipping_address": {
                    "person_name": "Priya Patel",
                    "business_name": "Patel Athletics",
                    "address": "456 Gandhi Nagar",
                    "state": "Gujarat",
                    "city": "Ahmedabad",
                    "pincode": "380001",
                    "mobile_1": "+91 87654 32109",
                    "country": "India"
                },
                "items": [
                    {"inventory_id": "inv3", "sku": "DRB-HD-003", "name": "Hoodie", "color": "Grey", "size": "XL", "price": 850, "quantity": 30, "gst_rate": 5, "shipping_weight": 0.6}
                ],
                "subtotal": 25500,
                "tax": 1275,
                "shipping_cost": 150,
                "total_amount": 26925,
                "status": "paid",
                "razorpay_payment_id": "pay_mock123456",
                "payment_gateway": "Razorpay",
                "payment_method": "UPI",
                "payment_mode": "live",
                "inventory_deducted": True,
                "estimated_weight": 18.0,
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "order_number": "D-1-14012026-1",
                "customer_email": "customer3@example.com",
                "customer_name": "Amit Kumar",
                "customer_phone": "+91 76543 21098",
                "shipping_address": {
                    "person_name": "Amit Kumar",
                    "business_name": "Kumar Sports Store",
                    "address": "789 Nehru Place",
                    "state": "Delhi",
                    "city": "New Delhi",
                    "pincode": "110019",
                    "mobile_1": "+91 76543 21098",
                    "country": "India"
                },
                "items": [
                    {"inventory_id": "inv4", "sku": "DRB-TS-004", "name": "Jersey", "color": "Red", "size": "M", "price": 550, "quantity": 50, "gst_rate": 5, "shipping_weight": 0.35},
                    {"inventory_id": "inv5", "sku": "DRB-SH-005", "name": "Shorts", "color": "White", "size": "L", "price": 350, "quantity": 50, "gst_rate": 5, "shipping_weight": 0.25}
                ],
                "subtotal": 45000,
                "tax": 2250,
                "shipping_cost": 200,
                "total_amount": 47450,
                "status": "confirmed",
                "razorpay_payment_id": "pay_mock789012",
                "payment_gateway": "Razorpay",
                "payment_method": "NETBANKING",
                "payment_mode": "live",
                "inventory_deducted": True,
                "estimated_weight": 30.0,
                "selected_courier": {
                    "id": "1",
                    "name": "Delhivery",
                    "full_name": "Delhivery Surface",
                    "mode": "Surface",
                    "rate": 200,
                    "estimated_days": "5-7 days"
                },
                "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "order_number": "D-1-13012026-1",
                "customer_email": "customer4@example.com",
                "customer_name": "Sneha Reddy",
                "customer_phone": "+91 65432 10987",
                "shipping_address": {
                    "person_name": "Sneha Reddy",
                    "business_name": "Reddy Sports Academy",
                    "address": "321 Banjara Hills",
                    "state": "Telangana",
                    "city": "Hyderabad",
                    "pincode": "500034",
                    "mobile_1": "+91 65432 10987",
                    "country": "India"
                },
                "items": [
                    {"inventory_id": "inv6", "sku": "DRB-TS-006", "name": "Polo T-Shirt", "color": "Navy", "size": "S", "price": 500, "quantity": 100, "gst_rate": 5, "shipping_weight": 0.3}
                ],
                "subtotal": 50000,
                "tax": 2500,
                "shipping_cost": 300,
                "total_amount": 52800,
                "status": "shipped",
                "razorpay_payment_id": "pay_mock345678",
                "payment_gateway": "Razorpay",
                "payment_method": "CARD",
                "payment_mode": "live",
                "inventory_deducted": True,
                "estimated_weight": 30.0,
                "selected_courier": {
                    "id": "2",
                    "name": "BlueDart",
                    "full_name": "BlueDart Express",
                    "mode": "Air",
                    "rate": 300,
                    "estimated_days": "2-3 days"
                },
                "shipment": {
                    "awb_number": "BD123456789",
                    "carrier_name": "BlueDart",
                    "carrier_mode": "Air",
                    "estimated_days": "2-3 days",
                    "status": "shipped",
                    "is_shipmozo_booked": True,
                    "shipmozo_order_id": "SM123456",
                    "booked_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
                },
                "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "order_number": "D-1-10012026-1",
                "customer_email": "customer5@example.com",
                "customer_name": "Vikram Singh",
                "customer_phone": "+91 54321 09876",
                "shipping_address": {
                    "person_name": "Vikram Singh",
                    "business_name": "Singh Sports Hub",
                    "address": "567 Civil Lines",
                    "state": "Punjab",
                    "city": "Ludhiana",
                    "pincode": "141001",
                    "mobile_1": "+91 54321 09876",
                    "country": "India"
                },
                "items": [
                    {"inventory_id": "inv7", "sku": "DRB-TP-007", "name": "Joggers", "color": "Olive", "size": "XL", "price": 700, "quantity": 25, "gst_rate": 5, "shipping_weight": 0.4}
                ],
                "subtotal": 17500,
                "tax": 875,
                "shipping_cost": 100,
                "total_amount": 18475,
                "status": "delivered",
                "razorpay_payment_id": "pay_mock901234",
                "payment_gateway": "Razorpay",
                "payment_method": "UPI",
                "payment_mode": "live",
                "inventory_deducted": True,
                "estimated_weight": 10.0,
                "selected_courier": {
                    "id": "1",
                    "name": "Delhivery",
                    "full_name": "Delhivery Surface",
                    "mode": "Surface",
                    "rate": 100,
                    "estimated_days": "5-7 days"
                },
                "shipment": {
                    "awb_number": "DV987654321",
                    "carrier_name": "Delhivery",
                    "carrier_mode": "Surface",
                    "estimated_days": "5-7 days",
                    "status": "delivered",
                    "is_shipmozo_booked": True,
                    "shipmozo_order_id": "SM789012",
                    "booked_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
                },
                "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        await db.orders.insert_many(sample_orders)
        logger.info(f"Created {len(sample_orders)} sample orders for testing (schema synced with DRIBBLE-NEW-2026)")
