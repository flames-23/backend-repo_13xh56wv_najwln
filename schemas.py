"""
Database Schemas for Course Selling App

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercased class name. For example, Course -> "course" collection.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class Course(BaseModel):
    """
    Courses collection schema
    Collection name: "course"
    """
    title: str = Field(..., description="Course title")
    subtitle: Optional[str] = Field(None, description="Short subtitle")
    description: Optional[str] = Field(None, description="Detailed description")
    price: float = Field(..., ge=0, description="Price in USD")
    thumbnail_url: Optional[str] = Field(None, description="Poster/thumbnail image URL")
    category: Optional[str] = Field(None, description="Course category")
    level: Optional[str] = Field(None, description="Beginner / Intermediate / Advanced")
    published: bool = Field(False, description="Whether this course is visible to users")
    tags: Optional[List[str]] = Field(default_factory=list, description="Search tags")


class Lesson(BaseModel):
    """
    Lessons collection schema
    Collection name: "lesson"
    """
    course_id: str = Field(..., description="Related course ObjectId as string")
    title: str = Field(..., description="Lesson title")
    content: Optional[str] = Field(None, description="Lesson text/content (could be markdown)")
    video_url: Optional[str] = Field(None, description="Optional video URL")
    order: int = Field(0, ge=0, description="Display order within the course")
    free_preview: bool = Field(False, description="Whether this lesson is free to preview")


class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    course_id: str = Field(..., description="Purchased course ObjectId as string")
    buyer_name: str = Field(..., description="Customer full name")
    buyer_email: str = Field(..., description="Customer email")
    amount: float = Field(..., ge=0, description="Amount charged in USD")
    status: str = Field("paid", description="paid, refunded, failed, pending")


class User(BaseModel):
    """
    Users collection schema (optional, not used for auth in this demo)
    Collection name: "user"
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    is_active: bool = Field(True, description="Whether user is active")
