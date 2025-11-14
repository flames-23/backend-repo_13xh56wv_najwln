import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Course, Lesson, Order

app = FastAPI(title="Course Selling API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class CourseOut(Course):
    id: str


class LessonOut(Lesson):
    id: str


class OrderIn(BaseModel):
    course_id: str
    buyer_name: str
    buyer_email: str


@app.get("/")
def root():
    return {"message": "Course Selling API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# Courses
@app.post("/api/courses", response_model=dict)
def create_course(course: Course):
    course_id = create_document("course", course)
    return {"id": course_id}


@app.get("/api/courses", response_model=List[CourseOut])
def list_courses(published: Optional[bool] = None):
    filter_query = {}
    if published is not None:
        filter_query["published"] = published
    docs = get_documents("course", filter_query)
    result: List[CourseOut] = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        result.append(CourseOut(**d))
    return result


@app.get("/api/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: str):
    try:
        obj_id = ObjectId(course_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid course id")
    doc = db["course"].find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Course not found")
    doc["id"] = str(doc.pop("_id"))
    return CourseOut(**doc)


@app.patch("/api/courses/{course_id}")
def update_course(course_id: str, course: Course):
    try:
        obj_id = ObjectId(course_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid course id")
    update_data = course.model_dump()
    update_data["updated_at"] = __import__("datetime").datetime.utcnow()
    res = db["course"].update_one({"_id": obj_id}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"status": "ok"}


@app.delete("/api/courses/{course_id}")
def delete_course(course_id: str):
    try:
        obj_id = ObjectId(course_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid course id")
    res = db["course"].delete_one({"_id": obj_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"status": "ok"}


# Lessons
@app.post("/api/courses/{course_id}/lessons", response_model=dict)
def create_lesson(course_id: str, lesson: Lesson):
    # override course_id from path
    data = lesson.model_dump()
    data["course_id"] = course_id
    lesson_id = create_document("lesson", data)
    return {"id": lesson_id}


@app.get("/api/courses/{course_id}/lessons", response_model=List[LessonOut])
def list_lessons(course_id: str):
    docs = get_documents("lesson", {"course_id": course_id})
    result: List[LessonOut] = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        result.append(LessonOut(**d))
    # sort by order
    result.sort(key=lambda x: x.order)
    return result


# Orders (mock checkout)
@app.post("/api/orders", response_model=dict)
def create_order(order: OrderIn):
    # Normally integrate with Stripe/PayPal; here we just store as paid
    course = db["course"].find_one({"_id": ObjectId(order.course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    amount = float(course.get("price", 0))
    order_doc = Order(
        course_id=order.course_id,
        buyer_name=order.buyer_name,
        buyer_email=order.buyer_email,
        amount=amount,
        status="paid",
    )
    order_id = create_document("order", order_doc)
    return {"id": order_id, "status": "paid"}


# Admin summary
class AdminSummary(BaseModel):
    total_courses: int
    published_courses: int
    total_lessons: int
    total_sales: int
    revenue: float


@app.get("/api/admin/summary", response_model=AdminSummary)
def admin_summary():
    total_courses = db["course"].count_documents({})
    published_courses = db["course"].count_documents({"published": True})
    total_lessons = db["lesson"].count_documents({})
    total_sales = db["order"].count_documents({"status": "paid"})
    revenue = 0.0
    for o in db["order"].find({"status": "paid"}, {"amount": 1}):
        revenue += float(o.get("amount", 0))
    return AdminSummary(
        total_courses=total_courses,
        published_courses=published_courses,
        total_lessons=total_lessons,
        total_sales=total_sales,
        revenue=round(revenue, 2),
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
