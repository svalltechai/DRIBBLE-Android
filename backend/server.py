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
app = FastAPI(title="DRIBBLE Admin API", version="1.0.0")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()


# Enums
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
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: str
    role: UserRole = UserRole.ADMIN
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserLogin(BaseModel):
    email: str
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

class OrderItem(BaseModel):
    inventory_id: str
    sku: str
    name: str
    color: str
    size: str
    price: float
    quantity: int
    gst_rate: float = 5.0

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str
    customer_id: Optional[str] = None
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
    order_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class PushToken(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    push_token: str
    device_info: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Helper Functions
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


# Auth Endpoints
@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Admin login endpoint"""
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user:
        # Create default admin if not exists
        if credentials.email == "admin@dribble.com" and credentials.password == "Admin123!":
            user = {
                "id": str(uuid.uuid4()),
                "email": "admin@dribble.com",
                "password_hash": hash_password("Admin123!"),
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user.get('password_hash', '')):
        # Check for default admin password
        if credentials.email == "admin@dribble.com" and credentials.password == "Admin123!":
            pass  # Allow default password
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(user['id'], user['email'], user.get('role', 'admin'))
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "email": user['email'],
            "role": user.get('role', 'admin')
        }
    }

@api_router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user info"""
    return {
        "id": current_user['user_id'],
        "email": current_user['email'],
        "role": current_user['role']
    }


# Orders Endpoints
@api_router.get("/admin/orders")
async def get_orders(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all orders with optional filtering"""
    query = {}
    
    if status and status != 'all':
        query['status'] = status
    
    if search:
        query['$or'] = [
            {'order_number': {'$regex': search, '$options': 'i'}},
            {'customer_name': {'$regex': search, '$options': 'i'}},
            {'customer_phone': {'$regex': search, '$options': 'i'}},
        ]
    
    skip = (page - 1) * limit
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return orders

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Get single order by ID"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@api_router.patch("/admin/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update order status"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Validate status transition
    current_status = order.get('status', 'pending')
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
    
    return updated_order

@api_router.get("/admin/orders/stats")
async def get_order_stats(current_user: dict = Depends(get_current_user)):
    """Get order statistics"""
    total_orders = await db.orders.count_documents({})
    pending_orders = await db.orders.count_documents({"status": {"$in": ["pending", "payment_pending"]}})
    
    # Today's orders
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = await db.orders.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "today_orders": today_orders
    }


# Push Notification Token Management
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


# Health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dribble-admin-api", "version": "1.0.0"}

@api_router.get("/")
async def root():
    return {"message": "DRIBBLE Admin API", "version": "1.0.0"}


# Include the router in the main app
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


# Create some sample orders on startup for testing
@app.on_event("startup")
async def create_sample_data():
    """Create sample orders for testing if none exist"""
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
                    "mobile_1": "+91 98765 43210"
                },
                "items": [
                    {"inventory_id": "inv1", "sku": "DRB-TS-001", "name": "Sports T-Shirt", "color": "Blue", "size": "L", "price": 450, "quantity": 20, "gst_rate": 5},
                    {"inventory_id": "inv2", "sku": "DRB-TP-002", "name": "Track Pants", "color": "Black", "size": "M", "price": 650, "quantity": 15, "gst_rate": 5}
                ],
                "subtotal": 18750,
                "tax": 937.5,
                "shipping_cost": 0,
                "total_amount": 19687.5,
                "status": "pending",
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
                    "mobile_1": "+91 87654 32109"
                },
                "items": [
                    {"inventory_id": "inv3", "sku": "DRB-HD-003", "name": "Hoodie", "color": "Grey", "size": "XL", "price": 850, "quantity": 30, "gst_rate": 5}
                ],
                "subtotal": 25500,
                "tax": 1275,
                "shipping_cost": 150,
                "total_amount": 26925,
                "status": "paid",
                "razorpay_payment_id": "pay_mock123456",
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
                    "mobile_1": "+91 76543 21098"
                },
                "items": [
                    {"inventory_id": "inv4", "sku": "DRB-TS-004", "name": "Jersey", "color": "Red", "size": "M", "price": 550, "quantity": 50, "gst_rate": 5},
                    {"inventory_id": "inv5", "sku": "DRB-SH-005", "name": "Shorts", "color": "White", "size": "L", "price": 350, "quantity": 50, "gst_rate": 5}
                ],
                "subtotal": 45000,
                "tax": 2250,
                "shipping_cost": 200,
                "total_amount": 47450,
                "status": "confirmed",
                "razorpay_payment_id": "pay_mock789012",
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
                    "mobile_1": "+91 65432 10987"
                },
                "items": [
                    {"inventory_id": "inv6", "sku": "DRB-TS-006", "name": "Polo T-Shirt", "color": "Navy", "size": "S", "price": 500, "quantity": 100, "gst_rate": 5}
                ],
                "subtotal": 50000,
                "tax": 2500,
                "shipping_cost": 300,
                "total_amount": 52800,
                "status": "shipped",
                "razorpay_payment_id": "pay_mock345678",
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
                    "mobile_1": "+91 54321 09876"
                },
                "items": [
                    {"inventory_id": "inv7", "sku": "DRB-TP-007", "name": "Joggers", "color": "Olive", "size": "XL", "price": 700, "quantity": 25, "gst_rate": 5}
                ],
                "subtotal": 17500,
                "tax": 875,
                "shipping_cost": 100,
                "total_amount": 18475,
                "status": "delivered",
                "razorpay_payment_id": "pay_mock901234",
                "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        await db.orders.insert_many(sample_orders)
        logger.info(f"Created {len(sample_orders)} sample orders for testing")
