# 🎓 EDUCATIONAL SECTION
# Workshops, cursos, webinars por cidade

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from fastapi import FastAPI, Depends

# DATABASE MODELS
class EducationalEvent:
    """Eventos educacionais (workshops, webinars, cursos)"""
    __tablename__ = "educational_events"

    id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey("cities.id"))
    title = Column(String(200))
    description = Column(String(2000))
    teacher_name = Column(String(200))
    type = Column(String(50))  # webinar, workshop, course, lecture
    date = Column(String(10))  # YYYY-MM-DD
    time = Column(String(5))   # HH:MM
    location = Column(String(500))
    max_participants = Column(Integer)
    enrolled = Column(Integer, default=0)
    is_free = Column(Boolean, default=True)
    price = Column(Float, nullable=True)
    image_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(200))  # Teacher name


# ENDPOINTS
def setup_education_section(app: FastAPI):
    """Setup educational events endpoints"""

    @app.get("/api/education/workshops")
    def get_workshops(
        city_id: int = None,
        db: Session = Depends(get_db)
    ):
        """Listar workshops e cursos"""
        query = db.query(EducationalEvent).filter(
            EducationalEvent.type.in_(["workshop", "course"])
        )

        if city_id:
            query = query.filter(EducationalEvent.city_id == city_id)

        workshops = query.order_by(
            EducationalEvent.date.desc()
        ).all()

        return {
            "success": True,
            "data": [{
                "id": w.id,
                "title": w.title,
                "teacher": w.teacher_name,
                "city_id": w.city_id,
                "type": w.type,
                "date": w.date,
                "time": w.time,
                "location": w.location,
                "enrolled": w.enrolled,
                "max": w.max_participants,
                "is_free": w.is_free,
                "price": w.price
            } for w in workshops]
        }

    @app.get("/api/education/webinars")
    def get_webinars(db: Session = Depends(get_db)):
        """Listar webinars"""
        webinars = db.query(EducationalEvent).filter(
            EducationalEvent.type == "webinar"
        ).order_by(EducationalEvent.date.desc()).all()

        return {
            "success": True,
            "data": webinars
        }

    @app.post("/api/education/create")
    def create_educational_event(
        title: str,
        description: str,
        teacher_name: str,
        event_type: str,  # webinar, workshop, course
        date: str,
        time: str,
        location: str,
        max_participants: int,
        city_id: int,
        is_free: bool = True,
        price: float = None,
        current_user = Depends(get_current_user_required),
        db: Session = Depends(get_db)
    ):
        """Criar novo evento educacional (apenas professores/admin)"""

        # Validar permissão
        if not current_user.is_teacher and not current_user.is_system_admin:
            raise HTTPException(status_code=403, detail="Only teachers can create events")

        event = EducationalEvent(
            city_id=city_id,
            title=title,
            description=description,
            teacher_name=teacher_name,
            type=event_type,
            date=date,
            time=time,
            location=location,
            max_participants=max_participants,
            is_free=is_free,
            price=price,
            created_by=current_user.full_name
        )

        db.add(event)
        db.commit()

        return {
            "success": True,
            "event_id": event.id,
            "message": "Educational event created"
        }

    @app.post("/api/education/{event_id}/enroll")
    def enroll_in_event(
        event_id: int,
        current_user = Depends(get_current_user_required),
        db: Session = Depends(get_db)
    ):
        """Inscrever em evento educacional"""
        event = db.query(EducationalEvent).filter(
            EducationalEvent.id == event_id
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        if event.enrolled >= event.max_participants:
            raise HTTPException(status_code=400, detail="Event is full")

        # Criar enrollment
        enrollment = EducationalEnrollment(
            event_id=event_id,
            user_id=current_user.id
        )

        event.enrolled += 1
        db.add(enrollment)
        db.commit()

        return {
            "success": True,
            "message": "Successfully enrolled in event",
            "spots_remaining": event.max_participants - event.enrolled
        }


# DADOS SEED
educational_events_seed = [
    {
        "city": "São Paulo",
        "title": "Workshop: Python avançado",
        "teacher": "João Silva",
        "type": "workshop",
        "date": "2026-06-20",
        "time": "14:00",
        "location": "Tech Hub SP",
        "max": 30,
        "free": True
    },
    {
        "city": "Rio de Janeiro",
        "title": "Webinar: Desenvolvimento Web",
        "teacher": "Maria Costa",
        "type": "webinar",
        "date": "2026-06-22",
        "time": "19:00",
        "location": "Online",
        "max": 500,
        "free": True
    },
    # ... mais eventos
]
