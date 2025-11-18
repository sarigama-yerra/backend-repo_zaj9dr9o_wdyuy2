"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Booking schema for the booking app
class Booking(BaseModel):
    """
    Bookings collection schema
    Collection name: "booking"
    """
    guest_name: str = Field(..., description="Name of the guest")
    email: Optional[str] = Field(None, description="Contact email")
    start_date: date = Field(..., description="Check-in date (YYYY-MM-DD)")
    duration_days: int = Field(..., ge=1, le=60, description="Number of nights")
    rooms: int = Field(..., ge=1, le=20, description="Number of rooms")
    room_type: Optional[str] = Field("standard", description="Room type")
    notes: Optional[str] = Field(None, description="Additional notes")
    status: str = Field("confirmed", description="Booking status")
    total_price: float = Field(..., ge=0, description="Computed total price")

# Add your own schemas here:
# --------------------------------------------------

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
