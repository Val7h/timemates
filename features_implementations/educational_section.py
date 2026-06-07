"""
Educational Section - Complete Implementation
Features: Workshops, courses, learning paths, instructor profiles, certificates
Database models, API endpoints, and frontend components
"""

# ═════════════════════════════════════════════════════════════════════════════════
# DATABASE MODELS (add to database.py)
# ═════════════════════════════════════════════════════════════════════════════════

DATABASE_MODELS = '''
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Float,
    DateTime, ForeignKey, Text, JSON, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class EducationLevel(str, enum.Enum):
    """Education levels for courses."""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"

class CourseStatus(str, enum.Enum):
    """Status of a course."""
    draft = "draft"
    published = "published"
    archived = "archived"
    discontinued = "discontinued"

class EnrollmentStatus(str, enum.Enum):
    """Enrollment status for courses."""
    enrolled = "enrolled"
    in_progress = "in_progress"
    completed = "completed"
    dropped = "dropped"

class Workshop(Base):
    """Educational workshops and short courses."""
    __tablename__ = "workshops"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True)
    slug = Column(String(300), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)  # coding, design, business, etc
    level = Column(String(20), default="beginner")  # beginner, intermediate, advanced
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    city = Column(String(100), nullable=False, index=True)

    # Scheduling
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    event_date = Column(DateTime, nullable=True)  # For one-time workshops
    duration_hours = Column(Integer, nullable=True)

    # Content
    thumbnail = Column(String(500), nullable=True)
    prerequisites = Column(Text, nullable=True)
    learning_outcomes = Column(JSON, nullable=True)  # list of strings
    syllabus = Column(Text, nullable=True)

    # Format
    format = Column(String(50), nullable=False)  # online, in_person, hybrid
    location = Column(String(300), nullable=True)  # For in-person workshops
    meeting_url = Column(String(500), nullable=True)  # For online workshops
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, default=0)

    # Pricing
    price = Column(Float, default=0.0)
    currency = Column(String(5), default="BRL")
    is_free = Column(Boolean, default=True)
    has_certificate = Column(Boolean, default=True)

    # Status and engagement
    status = Column(String(20), default="published")  # draft, published, archived, discontinued
    is_featured = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Metadata
    tags = Column(JSON, nullable=True)  # list of tags
    resources = Column(JSON, nullable=True)  # list of {title, url, type}
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instructor = relationship("User", foreign_keys=[instructor_id])
    institution = relationship("Institution", foreign_keys=[institution_id])
    enrollments = relationship("WorkshopEnrollment", back_populates="workshop", cascade="all, delete-orphan")
    materials = relationship("EducationMaterial", back_populates="workshop", cascade="all, delete-orphan")
    ratings = relationship("WorkshopRating", back_populates="workshop", cascade="all, delete-orphan")
    certificates = relationship("EducationCertificate", back_populates="workshop", cascade="all, delete-orphan")


class WorkshopEnrollment(Base):
    """User enrollment in a workshop."""
    __tablename__ = "workshop_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(20), default="enrolled")  # enrolled, in_progress, completed, dropped
    progress = Column(Float, default=0.0)  # 0-100
    completion_percentage = Column(Float, default=0.0)

    # Learning tracking
    modules_completed = Column(Integer, default=0)
    total_modules = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)
    time_spent_minutes = Column(Integer, default=0)

    # Certification
    completed_at = Column(DateTime, nullable=True)
    certificate_issued_at = Column(DateTime, nullable=True)
    certificate_id = Column(String(100), nullable=True, unique=True)

    enrolled_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workshop = relationship("Workshop", back_populates="enrollments")
    user = relationship("User", foreign_keys=[user_id])


class EducationMaterial(Base):
    """Learning materials (videos, documents, links, etc) for workshops."""
    __tablename__ = "education_materials"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False, index=True)

    title = Column(String(300), nullable=False)
    material_type = Column(String(50), nullable=False)  # video, pdf, document, link, exercise, quiz
    description = Column(Text, nullable=True)

    # Content
    content_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # in bytes
    duration_minutes = Column(Integer, nullable=True)  # for videos

    # Ordering and visibility
    order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)
    is_required = Column(Boolean, default=False)
    module_name = Column(String(200), nullable=True)  # Group materials by module

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workshop = relationship("Workshop", back_populates="materials")


class WorkshopRating(Base):
    """User ratings and reviews for workshops."""
    __tablename__ = "workshop_ratings"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    rating = Column(Float, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    review = Column(Text, nullable=True)

    # Rating categories
    content_quality = Column(Float, nullable=True)
    instructor_quality = Column(Float, nullable=True)
    pacing = Column(Float, nullable=True)
    materials_quality = Column(Float, nullable=True)

    helpful_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workshop = relationship("Workshop", back_populates="ratings")
    user = relationship("User", foreign_keys=[user_id])


class EducationCertificate(Base):
    """Digital certificates issued upon course completion."""
    __tablename__ = "education_certificates"

    id = Column(Integer, primary_key=True, index=True)
    workshop_id = Column(Integer, ForeignKey("workshops.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    certificate_number = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)

    # Certificate details
    issued_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    certificate_url = Column(String(500), nullable=True)

    # Completion details
    completion_percentage = Column(Float, nullable=False)
    final_score = Column(Float, nullable=True)

    is_verified = Column(Boolean, default=True)
    verification_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workshop = relationship("Workshop", back_populates="certificates")
    user = relationship("User", foreign_keys=[user_id])


class InstructorProfile(Base):
    """Instructor/tutor profile information."""
    __tablename__ = "instructor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Professional info
    expertise_areas = Column(JSON, nullable=True)  # list of areas of expertise
    bio = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    social_media = Column(JSON, nullable=True)  # {platform: url}

    # Statistics
    total_students = Column(Integer, default=0)
    total_workshops = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)

    # Verification
    is_verified = Column(Boolean, default=False)
    verification_document = Column(String(500), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Premium instructor
    is_premium = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class LearningPath(Base):
    """Curated sequence of courses/workshops for a learning goal."""
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True)
    slug = Column(String(300), unique=True, nullable=False)
    description = Column(Text, nullable=False)

    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(100), nullable=False)
    target_level = Column(String(50), nullable=False)  # beginner, intermediate, advanced

    # Content
    learning_objectives = Column(JSON, nullable=True)  # list of strings
    estimated_duration_hours = Column(Integer, nullable=True)
    course_sequence = Column(JSON, nullable=False)  # list of workshop_ids in order

    # Engagement
    is_published = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    followers_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[creator_id])
    followers = relationship("LearningPathFollower", back_populates="path", cascade="all, delete-orphan")


class LearningPathFollower(Base):
    """Users following a learning path."""
    __tablename__ = "learning_path_followers"

    id = Column(Integer, primary_key=True, index=True)
    path_id = Column(Integer, ForeignKey("learning_paths.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    progress = Column(Float, default=0.0)  # 0-100
    followed_at = Column(DateTime, default=datetime.utcnow)

    path = relationship("LearningPath", back_populates="followers")
    user = relationship("User", foreign_keys=[user_id])
'''

# ═════════════════════════════════════════════════════════════════════════════════
# BACKEND API ENDPOINTS (add to main.py)
# ═════════════════════════════════════════════════════════════════════════════════

BACKEND_ENDPOINTS = '''
# ═══════════════════════════════════════════════════════════════════════════
# WORKSHOPS - CRUD & MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/education/workshops")
@limiter.limit("30/minute")
def list_workshops(
    request: Request,
    city: str = "",
    category: str = "",
    level: str = "",
    search: str = "",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """📚 List all workshops with filters."""
    query = db.query(Workshop).filter(Workshop.status == "published", Workshop.is_active == True)

    if city:
        query = query.filter(Workshop.city.ilike(f"%{city}%"))
    if category:
        query = query.filter(Workshop.category == category)
    if level:
        query = query.filter(Workshop.level == level)
    if search:
        query = query.filter(
            (Workshop.title.ilike(f"%{search}%")) |
            (Workshop.description.ilike(f"%{search}%"))
        )

    total = query.count()
    workshops = query.order_by(Workshop.start_date.asc()).offset(skip).limit(limit).all()

    result = []
    for w in workshops:
        enrollment_count = db.query(WorkshopEnrollment).filter(
            WorkshopEnrollment.workshop_id == w.id,
            WorkshopEnrollment.status.in_(["enrolled", "in_progress"])
        ).count()

        result.append({
            "id": w.id,
            "title": w.title,
            "slug": w.slug,
            "description": w.description[:200],
            "category": w.category,
            "level": w.level,
            "city": w.city,
            "start_date": w.start_date.isoformat(),
            "end_date": w.end_date.isoformat() if w.end_date else None,
            "duration_hours": w.duration_hours,
            "format": w.format,
            "location": w.location,
            "price": w.price,
            "is_free": w.is_free,
            "thumbnail": w.thumbnail,
            "instructor": w.instructor.full_name if w.instructor else "Unknown",
            "instructor_id": w.instructor_id,
            "rating": w.rating,
            "total_ratings": w.total_ratings,
            "enrollment_count": enrollment_count,
            "current_participants": w.current_participants,
            "max_participants": w.max_participants,
            "is_featured": w.is_featured,
            "has_certificate": w.has_certificate,
            "tags": w.tags or [],
        })

    return {
        "success": True,
        "data": result,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.get("/api/education/workshops/{workshop_id}")
def get_workshop_detail(workshop_id: int, db: Session = Depends(get_db)):
    """📖 Get detailed workshop information."""
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        return {"success": False, "error": "Workshop not found"}

    materials = db.query(EducationMaterial).filter(
        EducationMaterial.workshop_id == workshop_id,
        EducationMaterial.is_visible == True
    ).order_by(EducationMaterial.order.asc()).all()

    enrollments = db.query(WorkshopEnrollment).filter(
        WorkshopEnrollment.workshop_id == workshop_id
    ).count()

    completed = db.query(WorkshopEnrollment).filter(
        WorkshopEnrollment.workshop_id == workshop_id,
        WorkshopEnrollment.status == "completed"
    ).count()

    ratings = db.query(WorkshopRating).filter(
        WorkshopRating.workshop_id == workshop_id
    ).all()

    return {
        "success": True,
        "data": {
            "id": workshop.id,
            "title": workshop.title,
            "slug": workshop.slug,
            "description": workshop.description,
            "category": workshop.category,
            "level": workshop.level,
            "city": workshop.city,
            "start_date": workshop.start_date.isoformat(),
            "end_date": workshop.end_date.isoformat() if workshop.end_date else None,
            "duration_hours": workshop.duration_hours,
            "format": workshop.format,
            "location": workshop.location,
            "meeting_url": workshop.meeting_url,
            "price": workshop.price,
            "is_free": workshop.is_free,
            "currency": workshop.currency,
            "thumbnail": workshop.thumbnail,
            "prerequisites": workshop.prerequisites,
            "learning_outcomes": workshop.learning_outcomes or [],
            "syllabus": workshop.syllabus,
            "resources": workshop.resources or [],
            "instructor": {
                "id": workshop.instructor_id,
                "name": workshop.instructor.full_name if workshop.instructor else "Unknown",
                "bio": workshop.instructor.bio if workshop.instructor else "",
            },
            "has_certificate": workshop.has_certificate,
            "rating": workshop.rating,
            "total_ratings": workshop.total_ratings,
            "enrollments": enrollments,
            "completed": completed,
            "materials": [
                {
                    "id": m.id,
                    "title": m.title,
                    "type": m.material_type,
                    "description": m.description,
                    "url": m.content_url,
                    "module": m.module_name,
                    "order": m.order,
                    "duration_minutes": m.duration_minutes,
                    "is_required": m.is_required,
                } for m in materials
            ],
            "reviews": [
                {
                    "id": r.id,
                    "rating": r.rating,
                    "title": r.title,
                    "review": r.review,
                    "author": r.user.full_name if r.user else "Anonymous",
                    "created_at": r.created_at.isoformat(),
                } for r in ratings[:5]  # Latest 5 reviews
            ]
        }
    }


@app.post("/api/education/workshops")
@limiter.limit("10/minute")
def create_workshop(
    request: Request,
    title: str = "",
    description: str = "",
    category: str = "",
    level: str = "beginner",
    start_date: str = "",
    city: str = "",
    format: str = "hybrid",
    duration_hours: int = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """✍️ Create a new workshop (instructor only)."""
    # Check if user is an instructor
    instructor_profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == current_user.id
    ).first()

    if not instructor_profile and not current_user.is_system_admin:
        return {"success": False, "error": "Only instructors can create workshops"}

    if not all([title, description, category, city, start_date]):
        return {"success": False, "error": "Missing required fields"}

    try:
        from datetime import datetime as dt
        start = dt.fromisoformat(start_date)
    except:
        return {"success": False, "error": "Invalid start_date format (use ISO format)"}

    # Create slug
    slug = title.lower().replace(" ", "-")[:50]
    slug_count = db.query(Workshop).filter(Workshop.slug.ilike(f"{slug}%")).count()
    if slug_count > 0:
        slug = f"{slug}-{slug_count}"

    workshop = Workshop(
        title=title,
        slug=slug,
        description=description,
        category=category,
        level=level,
        instructor_id=current_user.id,
        city=city,
        start_date=start,
        format=format,
        duration_hours=duration_hours,
        status="draft",
        is_free=True,
    )

    db.add(workshop)
    db.commit()
    db.refresh(workshop)

    return {
        "success": True,
        "message": "Workshop created successfully",
        "data": {
            "id": workshop.id,
            "slug": workshop.slug,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# WORKSHOP ENROLLMENT
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/education/workshops/{workshop_id}/enroll")
@limiter.limit("20/minute")
def enroll_workshop(
    request: Request,
    workshop_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """📝 Enroll in a workshop."""
    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        return {"success": False, "error": "Workshop not found"}

    # Check if already enrolled
    existing = db.query(WorkshopEnrollment).filter(
        WorkshopEnrollment.workshop_id == workshop_id,
        WorkshopEnrollment.user_id == current_user.id
    ).first()

    if existing:
        return {"success": False, "error": "Already enrolled in this workshop"}

    # Check max participants
    if workshop.max_participants and workshop.current_participants >= workshop.max_participants:
        return {"success": False, "error": "Workshop is full"}

    enrollment = WorkshopEnrollment(
        workshop_id=workshop_id,
        user_id=current_user.id,
        status="enrolled",
        total_modules=len([m for m in workshop.materials if m.is_required]),
    )

    workshop.current_participants = (workshop.current_participants or 0) + 1

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return {
        "success": True,
        "message": "Successfully enrolled in workshop",
        "data": {
            "enrollment_id": enrollment.id,
            "status": enrollment.status,
        }
    }


@app.get("/api/education/my-workshops")
def get_my_workshops(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """📚 Get user's enrolled workshops."""
    enrollments = db.query(WorkshopEnrollment).filter(
        WorkshopEnrollment.user_id == current_user.id
    ).order_by(WorkshopEnrollment.enrolled_at.desc()).all()

    result = []
    for e in enrollments:
        w = e.workshop
        result.append({
            "enrollment_id": e.id,
            "workshop_id": w.id,
            "title": w.title,
            "slug": w.slug,
            "status": e.status,
            "progress": e.progress,
            "modules_completed": e.modules_completed,
            "total_modules": e.total_modules,
            "last_accessed": e.last_accessed.isoformat() if e.last_accessed else None,
            "enrolled_at": e.enrolled_at.isoformat(),
            "thumbnail": w.thumbnail,
            "instructor": w.instructor.full_name if w.instructor else "Unknown",
            "category": w.category,
        })

    return {"success": True, "data": result}


# ═══════════════════════════════════════════════════════════════════════════
# RATINGS & REVIEWS
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/education/workshops/{workshop_id}/rate")
@limiter.limit("10/minute")
def rate_workshop(
    request: Request,
    workshop_id: int,
    rating: float = 5.0,
    title: str = "",
    review: str = "",
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """⭐ Rate and review a workshop."""
    if rating < 1 or rating > 5:
        return {"success": False, "error": "Rating must be between 1 and 5"}

    workshop = db.query(Workshop).filter(Workshop.id == workshop_id).first()
    if not workshop:
        return {"success": False, "error": "Workshop not found"}

    # Check if user completed the workshop
    enrollment = db.query(WorkshopEnrollment).filter(
        WorkshopEnrollment.workshop_id == workshop_id,
        WorkshopEnrollment.user_id == current_user.id,
    ).first()

    if not enrollment:
        return {"success": False, "error": "You must be enrolled to rate this workshop"}

    # Check for existing rating
    existing_rating = db.query(WorkshopRating).filter(
        WorkshopRating.workshop_id == workshop_id,
        WorkshopRating.user_id == current_user.id
    ).first()

    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating
        existing_rating.title = title
        existing_rating.review = review
        existing_rating.updated_at = datetime.utcnow()
    else:
        # Create new rating
        existing_rating = WorkshopRating(
            workshop_id=workshop_id,
            user_id=current_user.id,
            rating=rating,
            title=title,
            review=review,
        )
        db.add(existing_rating)

    # Update workshop rating
    all_ratings = db.query(WorkshopRating).filter(
        WorkshopRating.workshop_id == workshop_id
    ).all()
    total_ratings = len(all_ratings)
    avg_rating = sum(r.rating for r in all_ratings) / total_ratings if total_ratings > 0 else 0

    workshop.rating = avg_rating
    workshop.total_ratings = total_ratings

    db.commit()

    return {
        "success": True,
        "message": "Rating submitted successfully",
        "data": {
            "rating": rating,
            "workshop_rating": workshop.rating,
            "total_ratings": workshop.total_ratings,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# INSTRUCTOR PROFILE
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/education/instructor/profile")
def setup_instructor_profile(
    request: Request,
    bio: str = "",
    expertise_areas: list = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """👨‍🏫 Setup or update instructor profile."""
    profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = InstructorProfile(
            user_id=current_user.id,
            bio=bio,
            expertise_areas=expertise_areas or [],
        )
        db.add(profile)
    else:
        profile.bio = bio
        profile.expertise_areas = expertise_areas or profile.expertise_areas

    db.commit()
    db.refresh(profile)

    return {
        "success": True,
        "message": "Instructor profile updated",
        "data": {
            "id": profile.id,
            "bio": profile.bio,
            "expertise_areas": profile.expertise_areas,
        }
    }


@app.get("/api/education/instructor/{instructor_id}")
def get_instructor_profile(instructor_id: int, db: Session = Depends(get_db)):
    """👨‍🏫 Get instructor profile and statistics."""
    profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == instructor_id
    ).first()

    if not profile:
        return {"success": False, "error": "Instructor profile not found"}

    user = profile.user
    workshops = db.query(Workshop).filter(Workshop.instructor_id == instructor_id).all()

    return {
        "success": True,
        "data": {
            "id": profile.id,
            "name": user.full_name,
            "photo": user.profile_photo,
            "bio": profile.bio,
            "expertise_areas": profile.expertise_areas,
            "website": profile.website,
            "total_students": profile.total_students,
            "total_workshops": len(workshops),
            "rating": profile.rating,
            "is_verified": profile.is_verified,
            "is_premium": profile.is_premium,
            "workshops": [
                {
                    "id": w.id,
                    "title": w.title,
                    "category": w.category,
                    "students": db.query(WorkshopEnrollment).filter(
                        WorkshopEnrollment.workshop_id == w.id
                    ).count(),
                } for w in workshops[:10]
            ]
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# CERTIFICATES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/education/my-certificates")
def get_my_certificates(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🏆 Get user's earned certificates."""
    certificates = db.query(EducationCertificate).filter(
        EducationCertificate.user_id == current_user.id
    ).order_by(EducationCertificate.issued_at.desc()).all()

    result = []
    for cert in certificates:
        result.append({
            "id": cert.id,
            "certificate_number": cert.certificate_number,
            "title": cert.title,
            "workshop": cert.workshop.title if cert.workshop else "Unknown",
            "workshop_id": cert.workshop_id,
            "issued_at": cert.issued_at.isoformat(),
            "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
            "completion_percentage": cert.completion_percentage,
            "final_score": cert.final_score,
            "certificate_url": cert.certificate_url,
            "verification_url": cert.verification_url,
            "is_verified": cert.is_verified,
        })

    return {"success": True, "data": result}


@app.get("/api/education/certificates/{certificate_id}")
def verify_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """✅ Verify a certificate by ID."""
    cert = db.query(EducationCertificate).filter(
        EducationCertificate.certificate_number == certificate_id
    ).first()

    if not cert:
        return {"success": False, "error": "Certificate not found"}

    return {
        "success": True,
        "data": {
            "certificate_number": cert.certificate_number,
            "title": cert.title,
            "student": cert.user.full_name if cert.user else "Unknown",
            "workshop": cert.workshop.title if cert.workshop else "Unknown",
            "issued_at": cert.issued_at.isoformat(),
            "expires_at": cert.expires_at.isoformat() if cert.expires_at else None,
            "is_verified": cert.is_verified,
            "completion_percentage": cert.completion_percentage,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# LEARNING PATHS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/education/learning-paths")
def list_learning_paths(
    search: str = "",
    category: str = "",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """🗺️ List learning paths."""
    query = db.query(LearningPath).filter(LearningPath.is_published == True)

    if search:
        query = query.filter(LearningPath.title.ilike(f"%{search}%"))
    if category:
        query = query.filter(LearningPath.category == category)

    total = query.count()
    paths = query.order_by(LearningPath.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for path in paths:
        result.append({
            "id": path.id,
            "title": path.title,
            "slug": path.slug,
            "description": path.description[:200],
            "category": path.category,
            "target_level": path.target_level,
            "estimated_duration_hours": path.estimated_duration_hours,
            "followers_count": path.followers_count,
            "rating": path.rating,
            "creator": path.creator.full_name if path.creator else "Unknown",
            "courses_count": len(path.course_sequence) if path.course_sequence else 0,
        })

    return {
        "success": True,
        "data": result,
        "total": total,
    }


@app.post("/api/education/my-workshops/batch")
@limiter.limit("5/minute")
def get_batch_progress(
    request: Request,
    enrollment_ids: list = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """📊 Get progress for multiple enrollments."""
    if not enrollment_ids:
        enrollment_ids = []

    enrollments = db.query(WorkshopEnrollment).filter(
        WorkshopEnrollment.user_id == current_user.id,
        WorkshopEnrollment.id.in_(enrollment_ids) if enrollment_ids else True
    ).all()

    result = []
    for e in enrollments:
        result.append({
            "enrollment_id": e.id,
            "workshop_id": e.workshop_id,
            "progress": e.progress,
            "modules_completed": e.modules_completed,
            "total_modules": e.total_modules,
            "status": e.status,
            "time_spent_minutes": e.time_spent_minutes,
        })

    return {"success": True, "data": result}
'''


# ═════════════════════════════════════════════════════════════════════════════════
# FRONTEND HTML DASHBOARD (create as public/education-dashboard.html)
# ═════════════════════════════════════════════════════════════════════════════════

FRONTEND_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Educação - TimeMates</title>
    <meta name="theme-color" content="#1E3A5F">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #1E3A5F 0%, #2A5080 100%);
            color: #333;
            min-height: 100vh;
            padding-bottom: 80px;
        }

        .navbar {
            background: rgba(30, 58, 95, 0.98);
            color: white;
            padding: 1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .navbar-title {
            font-size: 1.5rem;
            font-weight: bold;
            color: #D4A853;
        }

        .navbar-menu {
            display: flex;
            gap: 1rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }

        .btn-primary {
            background: #D4A853;
            color: #1E3A5F;
        }

        .btn-primary:hover {
            background: #e8c868;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(212, 168, 83, 0.3);
        }

        .btn-secondary {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
        }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.3);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* HERO SECTION */
        /* ═══════════════════════════════════════════════════════════════════ */

        .hero {
            background: linear-gradient(135deg, #1E3A5F 0%, #2A5080 100%);
            color: white;
            padding: 3rem 1rem;
            text-align: center;
            border-radius: 12px;
            margin-bottom: 3rem;
        }

        .hero h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            color: #D4A853;
        }

        .hero p {
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }

        .search-box {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            margin-top: 2rem;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            justify-content: center;
        }

        .search-box input,
        .search-box select {
            padding: 0.75rem 1rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 1rem;
            flex: 1;
            min-width: 150px;
        }

        .search-box button {
            padding: 0.75rem 2rem;
            background: #D4A853;
            color: #1E3A5F;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: 0.3s;
        }

        .search-box button:hover {
            background: #e8c868;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* TABS */
        /* ═══════════════════════════════════════════════════════════════════ */

        .tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid rgba(255,255,255,0.2);
            overflow-x: auto;
        }

        .tab {
            padding: 1rem 1.5rem;
            background: transparent;
            border: none;
            color: rgba(255,255,255,0.7);
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            border-bottom: 3px solid transparent;
            transition: 0.3s;
            white-space: nowrap;
        }

        .tab.active {
            color: #D4A853;
            border-bottom-color: #D4A853;
        }

        .tab:hover {
            color: white;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* WORKSHOPS GRID */
        /* ═══════════════════════════════════════════════════════════════════ */

        .workshops-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }

        .workshop-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            display: flex;
            flex-direction: column;
        }

        .workshop-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 20px rgba(0,0,0,0.15);
        }

        .workshop-thumbnail {
            width: 100%;
            height: 200px;
            background: linear-gradient(135deg, #D4A853 0%, #c98e3f 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3rem;
            font-weight: bold;
        }

        .workshop-content {
            padding: 1.5rem;
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .workshop-category {
            display: inline-block;
            background: #f0f0f0;
            color: #666;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
            width: fit-content;
        }

        .workshop-title {
            font-size: 1.3rem;
            font-weight: bold;
            color: #1E3A5F;
            margin-bottom: 0.5rem;
        }

        .workshop-description {
            color: #666;
            font-size: 0.95rem;
            margin-bottom: 1rem;
            line-height: 1.4;
            flex: 1;
        }

        .workshop-meta {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            font-size: 0.9rem;
            color: #999;
        }

        .workshop-meta span {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .workshop-rating {
            color: #D4A853;
            font-weight: bold;
            margin-bottom: 1rem;
        }

        .workshop-footer {
            display: flex;
            gap: 1rem;
            align-items: center;
            justify-content: space-between;
        }

        .workshop-price {
            font-size: 1.3rem;
            font-weight: bold;
            color: #1E3A5F;
        }

        .workshop-price.free {
            color: #4CAF50;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* MY WORKSHOPS SECTION */
        /* ═══════════════════════════════════════════════════════════════════ */

        .my-workshops {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .my-workshops h2 {
            color: #1E3A5F;
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }

        .enrollment-card {
            background: #f9f9f9;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border-left: 4px solid #D4A853;
        }

        .enrollment-progress {
            margin-top: 1rem;
        }

        .progress-bar {
            background: #e0e0e0;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }

        .progress-fill {
            background: linear-gradient(90deg, #D4A853 0%, #c98e3f 100%);
            height: 100%;
            transition: width 0.3s ease;
        }

        .progress-text {
            font-size: 0.9rem;
            color: #666;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* CERTIFICATES SECTION */
        /* ═══════════════════════════════════════════════════════════════════ */

        .certificates-section {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
        }

        .certificates-section h2 {
            color: #1E3A5F;
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
        }

        .certificate-item {
            background: linear-gradient(135deg, #1E3A5F 0%, #D4A853 100%);
            color: white;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .certificate-info h3 {
            margin-bottom: 0.5rem;
            font-size: 1.2rem;
        }

        .certificate-number {
            font-size: 0.9rem;
            opacity: 0.9;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* INSTRUCTORS SECTION */
        /* ═══════════════════════════════════════════════════════════════════ */

        .instructors-section {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
        }

        .instructors-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 2rem;
        }

        .instructor-card {
            text-align: center;
            background: #f9f9f9;
            padding: 2rem;
            border-radius: 8px;
            transition: 0.3s;
        }

        .instructor-card:hover {
            background: #f0f0f0;
            transform: translateY(-4px);
        }

        .instructor-avatar {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: linear-gradient(135deg, #D4A853 0%, #c98e3f 100%);
            margin: 0 auto 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.5rem;
            font-weight: bold;
        }

        .instructor-name {
            font-size: 1.1rem;
            font-weight: bold;
            color: #1E3A5F;
            margin-bottom: 0.5rem;
        }

        .instructor-expertise {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }

        .instructor-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }

        .stat {
            background: white;
            padding: 0.75rem;
            border-radius: 6px;
        }

        .stat-number {
            font-weight: bold;
            color: #D4A853;
        }

        .stat-label {
            color: #999;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* LOADING & EMPTY STATES */
        /* ═══════════════════════════════════════════════════════════════════ */

        .loading {
            text-align: center;
            padding: 3rem 1rem;
            color: white;
        }

        .loading-spinner {
            border: 4px solid rgba(255,255,255,0.2);
            border-top: 4px solid #D4A853;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .empty-state {
            text-align: center;
            padding: 3rem 1rem;
            color: rgba(255,255,255,0.7);
        }

        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* MODAL */
        /* ═══════════════════════════════════════════════════════════════════ */

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            max-width: 600px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 1rem;
        }

        .modal-title {
            font-size: 1.5rem;
            font-weight: bold;
            color: #1E3A5F;
        }

        .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #999;
        }

        .modal-close:hover {
            color: #333;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #1E3A5F;
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 1rem;
            font-family: inherit;
        }

        .form-group textarea {
            resize: vertical;
            min-height: 100px;
        }

        /* ═══════════════════════════════════════════════════════════════════ */
        /* RESPONSIVE */
        /* ═══════════════════════════════════════════════════════════════════ */

        @media (max-width: 768px) {
            .navbar {
                flex-direction: column;
                gap: 1rem;
            }

            .hero h1 {
                font-size: 2rem;
            }

            .search-box {
                flex-direction: column;
            }

            .search-box input,
            .search-box select {
                min-width: 100%;
            }

            .workshops-grid {
                grid-template-columns: 1fr;
            }

            .instructor-stats {
                grid-template-columns: 1fr;
            }

            .certificate-item {
                flex-direction: column;
                text-align: center;
            }
        }

        @media (max-width: 480px) {
            .container {
                padding: 1rem;
            }

            .hero {
                padding: 2rem 1rem;
            }

            .hero h1 {
                font-size: 1.5rem;
            }

            .workshop-footer {
                flex-direction: column;
            }

            .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <!-- NAVBAR -->
    <div class="navbar">
        <div class="navbar-title">📚 Educação TimeMates</div>
        <div class="navbar-menu">
            <button class="btn btn-secondary" onclick="showAuthCheck()">Meus Cursos</button>
            <button class="btn btn-primary" onclick="openCreateModal()">+ Criar Workshop</button>
        </div>
    </div>

    <!-- CONTAINER -->
    <div class="container">
        <!-- HERO SECTION -->
        <div class="hero">
            <h1>Aprenda & Ensine</h1>
            <p>Explore workshops, cursos e caminhos de aprendizado criados por especialistas da comunidade</p>

            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Buscar workshops...">
                <select id="categoryFilter">
                    <option value="">Todas as categorias</option>
                    <option value="coding">Programação</option>
                    <option value="design">Design</option>
                    <option value="business">Negócios</option>
                    <option value="languages">Idiomas</option>
                    <option value="art">Artes</option>
                    <option value="health">Saúde</option>
                </select>
                <select id="levelFilter">
                    <option value="">Todos os níveis</option>
                    <option value="beginner">Iniciante</option>
                    <option value="intermediate">Intermediário</option>
                    <option value="advanced">Avançado</option>
                </select>
                <button onclick="filterWorkshops()">🔍 Buscar</button>
            </div>
        </div>

        <!-- TABS -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('discover')">Descobrir</button>
            <button class="tab" onclick="switchTab('my-workshops')">Meus Cursos</button>
            <button class="tab" onclick="switchTab('certificates')">Certificados</button>
            <button class="tab" onclick="switchTab('instructors')">Instrutores</button>
        </div>

        <!-- DISCOVER TAB -->
        <div id="discover-tab" class="tab-content">
            <div id="workshops-container" class="workshops-grid">
                <div class="loading">
                    <div class="loading-spinner"></div>
                    Carregando workshops...
                </div>
            </div>
        </div>

        <!-- MY WORKSHOPS TAB -->
        <div id="my-workshops-tab" class="tab-content" style="display: none;">
            <div class="my-workshops">
                <h2>Meus Cursos</h2>
                <div id="my-workshops-container">
                    <div class="empty-state">
                        <div class="empty-state-icon">📚</div>
                        <p>Você ainda não está inscrito em nenhum workshop.</p>
                        <p style="margin-top: 1rem;">
                            <button class="btn btn-primary" onclick="switchTab('discover')">Explorar Workshops</button>
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <!-- CERTIFICATES TAB -->
        <div id="certificates-tab" class="tab-content" style="display: none;">
            <div class="certificates-section">
                <h2>🏆 Meus Certificados</h2>
                <div id="certificates-container">
                    <div class="empty-state">
                        <div class="empty-state-icon">📜</div>
                        <p>Você ainda não obteve nenhum certificado.</p>
                        <p style="margin-top: 1rem;">Complete um workshop para ganhar um certificado!</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- INSTRUCTORS TAB -->
        <div id="instructors-tab" class="tab-content" style="display: none;">
            <div class="instructors-section">
                <h2>Instrutores Destacados</h2>
                <div id="instructors-container" class="instructors-grid">
                    <div class="loading">
                        <div class="loading-spinner"></div>
                        Carregando instrutores...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- CREATE WORKSHOP MODAL -->
    <div id="createModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Criar novo Workshop</h2>
                <button class="modal-close" onclick="closeCreateModal()">✕</button>
            </div>
            <form onsubmit="submitCreateWorkshop(event)">
                <div class="form-group">
                    <label for="workshopTitle">Título *</label>
                    <input type="text" id="workshopTitle" required>
                </div>
                <div class="form-group">
                    <label for="workshopDescription">Descrição *</label>
                    <textarea id="workshopDescription" required></textarea>
                </div>
                <div class="form-group">
                    <label for="workshopCategory">Categoria *</label>
                    <select id="workshopCategory" required>
                        <option value="">Selecione...</option>
                        <option value="coding">Programação</option>
                        <option value="design">Design</option>
                        <option value="business">Negócios</option>
                        <option value="languages">Idiomas</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="workshopLevel">Nível</label>
                    <select id="workshopLevel">
                        <option value="beginner">Iniciante</option>
                        <option value="intermediate">Intermediário</option>
                        <option value="advanced">Avançado</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="workshopDate">Data de Início *</label>
                    <input type="datetime-local" id="workshopDate" required>
                </div>
                <div class="form-group">
                    <label for="workshopCity">Cidade *</label>
                    <input type="text" id="workshopCity" required>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Criar Workshop</button>
            </form>
        </div>
    </div>

    <!-- WORKSHOP DETAIL MODAL -->
    <div id="detailModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="detailTitle">Workshop Details</h2>
                <button class="modal-close" onclick="closeDetailModal()">✕</button>
            </div>
            <div id="detailContent"></div>
        </div>
    </div>

    <script>
        const API_URL = "/api";
        const EDUCATION_API = "/api/education";
        let currentUser = null;

        // ═══════════════════════════════════════════════════════════════════════════
        // INITIALIZATION
        // ═══════════════════════════════════════════════════════════════════════════

        async function init() {
            // Check authentication
            try {
                const res = await fetch(`${API_URL}/auth/me`);
                if (res.ok) {
                    currentUser = await res.json();
                    document.querySelector(".navbar-menu").style.display = "flex";
                } else {
                    document.querySelector(".navbar-menu").innerHTML =
                        '<button class="btn btn-primary" onclick="window.location.href=\\"/\\">Login</button>';
                }
            } catch (e) {
                console.log("Not logged in");
            }

            // Load workshops
            loadWorkshops();
            loadInstructors();
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // WORKSHOPS
        // ═══════════════════════════════════════════════════════════════════════════

        async function loadWorkshops() {
            try {
                const city = currentUser?.city || "São Paulo";
                const res = await fetch(`${EDUCATION_API}/workshops?city=${encodeURIComponent(city)}&limit=20`);
                const data = await res.json();

                if (data.success && data.data.length > 0) {
                    renderWorkshops(data.data);
                } else {
                    document.getElementById("workshops-container").innerHTML = `
                        <div class="empty-state" style="grid-column: 1/-1;">
                            <div class="empty-state-icon">🎓</div>
                            <p>Nenhum workshop encontrado.</p>
                        </div>
                    `;
                }
            } catch (e) {
                console.error("Error loading workshops:", e);
                document.getElementById("workshops-container").innerHTML = `
                    <div class="empty-state" style="grid-column: 1/-1;">
                        <p>Erro ao carregar workshops. Tente novamente.</p>
                    </div>
                `;
            }
        }

        function renderWorkshops(workshops) {
            const container = document.getElementById("workshops-container");
            container.innerHTML = workshops.map(w => `
                <div class="workshop-card" onclick="showWorkshopDetail(${w.id})">
                    <div class="workshop-thumbnail">
                        ${w.category === "coding" ? "💻" :
                          w.category === "design" ? "🎨" :
                          w.category === "business" ? "💼" :
                          w.category === "languages" ? "🌍" : "📚"}
                    </div>
                    <div class="workshop-content">
                        <span class="workshop-category">${w.category}</span>
                        <h3 class="workshop-title">${w.title}</h3>
                        <p class="workshop-description">${w.description}</p>
                        <div class="workshop-meta">
                            <span>⏱️ ${w.duration_hours || "N/A"} horas</span>
                            <span>👥 ${w.enrollment_count} alunos</span>
                        </div>
                        <div class="workshop-rating">
                            ${"⭐".repeat(Math.round(w.rating || 0))} ${(w.rating || 0).toFixed(1)}
                        </div>
                        <div class="workshop-footer">
                            <span class="workshop-price ${w.is_free ? "free" : ""}">
                                ${w.is_free ? "Grátis" : `R$ ${w.price}`}
                            </span>
                            <button class="btn btn-primary" onclick="event.stopPropagation(); enrollWorkshop(${w.id})">
                                Inscrever
                            </button>
                        </div>
                    </div>
                </div>
            `).join("");
        }

        async function filterWorkshops() {
            const search = document.getElementById("searchInput").value;
            const category = document.getElementById("categoryFilter").value;
            const level = document.getElementById("levelFilter").value;

            try {
                let url = `${EDUCATION_API}/workshops?`;
                if (search) url += `search=${encodeURIComponent(search)}&`;
                if (category) url += `category=${category}&`;
                if (level) url += `level=${level}&`;

                const res = await fetch(url);
                const data = await res.json();

                if (data.success) {
                    renderWorkshops(data.data);
                }
            } catch (e) {
                console.error("Error filtering:", e);
            }
        }

        async function enrollWorkshop(workshopId) {
            if (!currentUser) {
                alert("Faça login para se inscrever");
                return;
            }

            try {
                const res = await fetch(`${EDUCATION_API}/workshops/${workshopId}/enroll`, {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${localStorage.getItem("token")}`,
                        "Content-Type": "application/json"
                    }
                });

                const data = await res.json();
                if (data.success) {
                    alert("Inscrição realizada com sucesso!");
                    loadMyWorkshops();
                } else {
                    alert("Erro: " + (data.error || "Falha na inscrição"));
                }
            } catch (e) {
                console.error("Error enrolling:", e);
            }
        }

        async function showWorkshopDetail(workshopId) {
            try {
                const res = await fetch(`${EDUCATION_API}/workshops/${workshopId}`);
                const data = await res.json();

                if (data.success) {
                    const w = data.data;
                    document.getElementById("detailTitle").textContent = w.title;
                    document.getElementById("detailContent").innerHTML = `
                        <div style="margin-bottom: 1.5rem;">
                            <h3>${w.title}</h3>
                            <p style="color: #666; margin: 1rem 0;">${w.description}</p>

                            <div style="background: #f9f9f9; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                                <p><strong>Instrutor:</strong> ${w.instructor.name}</p>
                                <p><strong>Categoria:</strong> ${w.category}</p>
                                <p><strong>Nível:</strong> ${w.level}</p>
                                <p><strong>Data:</strong> ${new Date(w.start_date).toLocaleDateString("pt-BR")}</p>
                                <p><strong>Duração:</strong> ${w.duration_hours} horas</p>
                                <p><strong>Inscritos:</strong> ${w.enrollments} / ${w.max_participants || "Ilimitado"}</p>
                            </div>

                            ${w.learning_outcomes.length > 0 ? `
                                <h4>Objetivos de Aprendizado:</h4>
                                <ul style="margin-bottom: 1rem;">
                                    ${w.learning_outcomes.map(o => `<li>${o}</li>`).join("")}
                                </ul>
                            ` : ""}

                            ${w.materials.length > 0 ? `
                                <h4>Materiais:</h4>
                                <ul>
                                    ${w.materials.map(m => `<li>${m.type}: ${m.title}</li>`).join("")}
                                </ul>
                            ` : ""}
                        </div>

                        <button class="btn btn-primary" style="width: 100%;" onclick="enrollWorkshop(${w.id})">
                            ${w.is_free ? "Inscrever Grátis" : `Pagar R$ ${w.price}`}
                        </button>
                    `;
                    document.getElementById("detailModal").classList.add("active");
                }
            } catch (e) {
                console.error("Error loading detail:", e);
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // MY WORKSHOPS
        // ═══════════════════════════════════════════════════════════════════════════

        async function loadMyWorkshops() {
            if (!currentUser) return;

            try {
                const res = await fetch(`${EDUCATION_API}/my-workshops`, {
                    headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}
                });
                const data = await res.json();

                if (data.success && data.data.length > 0) {
                    document.getElementById("my-workshops-container").innerHTML =
                        data.data.map(e => `
                            <div class="enrollment-card">
                                <h3>${e.title}</h3>
                                <p style="color: #666; margin: 0.5rem 0;">
                                    Instrutor: ${e.instructor}
                                </p>
                                <div class="enrollment-progress">
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${e.progress}%"></div>
                                    </div>
                                    <div class="progress-text">
                                        ${e.modules_completed}/${e.total_modules} módulos | ${e.progress}% concluído
                                    </div>
                                </div>
                                <p style="margin-top: 0.5rem; color: #999; font-size: 0.9rem;">
                                    Status: ${e.status}
                                </p>
                            </div>
                        `).join("");
                } else {
                    document.getElementById("my-workshops-container").innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">📚</div>
                            <p>Você ainda não está inscrito em nenhum workshop.</p>
                        </div>
                    `;
                }
            } catch (e) {
                console.error("Error loading my workshops:", e);
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // CERTIFICATES
        // ═══════════════════════════════════════════════════════════════════════════

        async function loadCertificates() {
            if (!currentUser) return;

            try {
                const res = await fetch(`${EDUCATION_API}/my-certificates`, {
                    headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}
                });
                const data = await res.json();

                if (data.success && data.data.length > 0) {
                    document.getElementById("certificates-container").innerHTML =
                        data.data.map(c => `
                            <div class="certificate-item">
                                <div class="certificate-info">
                                    <h3>${c.title}</h3>
                                    <p>Workshop: ${c.workshop}</p>
                                    <p class="certificate-number">
                                        Certificado #${c.certificate_number}
                                    </p>
                                    <p style="margin-top: 0.5rem; opacity: 0.9;">
                                        Emitido em: ${new Date(c.issued_at).toLocaleDateString("pt-BR")}
                                    </p>
                                </div>
                                <button class="btn btn-secondary" onclick="window.open('${c.certificate_url}')">
                                    Baixar
                                </button>
                            </div>
                        `).join("");
                }
            } catch (e) {
                console.error("Error loading certificates:", e);
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // INSTRUCTORS
        // ═══════════════════════════════════════════════════════════════════════════

        async function loadInstructors() {
            try {
                const res = await fetch(`${EDUCATION_API}/workshops?limit=100`);
                const data = await res.json();

                if (data.success && data.data.length > 0) {
                    const instructors = [...new Map(
                        data.data.map(w => [w.instructor_id, w])
                    ).values()];

                    document.getElementById("instructors-container").innerHTML =
                        instructors.slice(0, 6).map(w => `
                            <div class="instructor-card">
                                <div class="instructor-avatar">
                                    ${w.instructor.charAt(0).toUpperCase()}
                                </div>
                                <h3 class="instructor-name">${w.instructor}</h3>
                                <p class="instructor-expertise">Especialista em ${w.category}</p>
                                <div class="instructor-stats">
                                    <div class="stat">
                                        <div class="stat-number">5</div>
                                        <div class="stat-label">Cursos</div>
                                    </div>
                                    <div class="stat">
                                        <div class="stat-number">⭐ ${w.rating || 5}</div>
                                        <div class="stat-label">Rating</div>
                                    </div>
                                </div>
                                <button class="btn btn-secondary" style="width: 100%;">Ver Perfil</button>
                            </div>
                        `).join("");
                }
            } catch (e) {
                console.error("Error loading instructors:", e);
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // TAB SWITCHING
        // ═══════════════════════════════════════════════════════════════════════════

        function switchTab(tabName) {
            // Hide all tabs
            document.querySelectorAll(".tab-content").forEach(t => t.style.display = "none");

            // Deactivate all tab buttons
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));

            // Show selected tab
            document.getElementById(`${tabName}-tab`).style.display = "block";

            // Activate selected tab button
            event.target.classList.add("active");

            // Load data if needed
            if (tabName === "my-workshops") {
                loadMyWorkshops();
            } else if (tabName === "certificates") {
                loadCertificates();
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // MODALS
        // ═══════════════════════════════════════════════════════════════════════════

        function openCreateModal() {
            if (!currentUser) {
                alert("Faça login para criar um workshop");
                return;
            }
            document.getElementById("createModal").classList.add("active");
        }

        function closeCreateModal() {
            document.getElementById("createModal").classList.remove("active");
        }

        function closeDetailModal() {
            document.getElementById("detailModal").classList.remove("active");
        }

        async function submitCreateWorkshop(e) {
            e.preventDefault();

            const title = document.getElementById("workshopTitle").value;
            const description = document.getElementById("workshopDescription").value;
            const category = document.getElementById("workshopCategory").value;
            const level = document.getElementById("workshopLevel").value;
            const startDate = document.getElementById("workshopDate").value;
            const city = document.getElementById("workshopCity").value;

            try {
                const res = await fetch(`${EDUCATION_API}/workshops`, {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${localStorage.getItem("token")}`,
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    body: new URLSearchParams({
                        title, description, category, level,
                        start_date: startDate, city
                    })
                });

                const data = await res.json();
                if (data.success) {
                    alert("Workshop criado com sucesso!");
                    closeCreateModal();
                    loadWorkshops();
                    document.querySelector("form").reset();
                } else {
                    alert("Erro: " + (data.error || "Falha ao criar workshop"));
                }
            } catch (e) {
                console.error("Error creating workshop:", e);
                alert("Erro ao criar workshop");
            }
        }

        function showAuthCheck() {
            if (!currentUser) {
                alert("Faça login para acessar seus cursos");
                window.location.href = "/";
            } else {
                switchTab("my-workshops");
            }
        }

        // Initialize on page load
        window.addEventListener("DOMContentLoaded", init);
    </script>
</body>
</html>
'''

print("✅ Educational Section implementation complete!")
