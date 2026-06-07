# 🔧 INTEGRATION GUIDE - 8 FEATURES

**Status:** ✅ All 8 features implemented  
**Location:** `features_implementations/` directory  
**Timeline:** Weeks 1-3  

---

## 📋 IMPLEMENTATION CHECKLIST

### Feature 1: Swagger Documentation ✅
**File:** `swagger_setup.py`  
**Status:** Ready for integration  
**Integration Steps:**

```python
# In main.py:
from features_implementations.swagger_setup import setup_swagger

app = FastAPI()
setup_swagger(app)

# URLs:
# - /docs (Swagger UI)
# - /redoc (ReDoc)
```

**Time to integrate:** 5 minutes  
**Dependencies:** FastAPI (built-in)  

---

### Feature 2: Push Notifications ✅
**File:** `push_notifications.py`  
**Status:** Ready for integration  
**Integration Steps:**

```python
# In main.py:
from features_implementations.push_notifications import setup_push_notifications

setup_push_notifications(app)

# Add to requirements.txt:
# - pywebpush
# - firebase-admin
```

**Database Migration:**
```sql
CREATE TABLE push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    device_token VARCHAR(500) UNIQUE,
    endpoint VARCHAR(500),
    auth VARCHAR(500),
    p256dh VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Frontend Integration:**
- Add `/public/sw.js` (Service Worker)
- Copy JavaScript code from push_notifications.py

**Time to integrate:** 1-2 hours  
**Dependencies:** Firebase Cloud Messaging (FCM)  

---

### Feature 3: Google Calendar Integration ✅
**File:** `calendar_integration.py`  
**Status:** Ready for integration  
**Integration Steps:**

```python
# In main.py:
from features_implementations.calendar_integration import setup_calendar_integration

setup_calendar_integration(app)

# Add to requirements.txt:
# - google-auth-oauthlib
# - google-auth-httplib2
# - google-api-python-client
```

**Configuration Needed:**
```
GOOGLE_CLIENT_ID = "your-client-id"
GOOGLE_CLIENT_SECRET = "your-client-secret"
GOOGLE_REDIRECT_URI = "https://timemates.onrender.com/auth/google/callback"
```

**Add OAuth endpoints:**
```python
@app.get("/auth/google")
def oauth_google(code: str, ...):
    # Exchange code for token
    # Save token in database
    pass
```

**Time to integrate:** 2-3 hours  
**Dependencies:** Google OAuth 2.0, Google Calendar API  

---

### Feature 4: Outlook Integration ✅
**File:** `calendar_integration.py` (same file)  
**Status:** Ready for integration  
**Integration Steps:**

Similar to Google Calendar, but:
```
MICROSOFT_CLIENT_ID = "your-client-id"
MICROSOFT_CLIENT_SECRET = "your-client-secret"
MICROSOFT_REDIRECT_URI = "https://timemates.onrender.com/auth/microsoft/callback"
```

**Add OAuth endpoints:**
```python
@app.get("/auth/microsoft")
def oauth_microsoft(code: str, ...):
    # Exchange code for token
    # Save token in database
    pass
```

**Time to integrate:** 2-3 hours  
**Dependencies:** Microsoft Graph API  

---

### Feature 5: Educational Section ✅
**File:** `education_section.py`  
**Status:** Ready for integration  
**Integration Steps:**

```python
# In main.py:
from features_implementations.education_section import setup_education_section

setup_education_section(app)
```

**Database Migration:**
```sql
CREATE TABLE educational_events (
    id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES cities(id),
    title VARCHAR(200),
    description TEXT,
    teacher_name VARCHAR(200),
    type VARCHAR(50),
    date VARCHAR(10),
    time VARCHAR(5),
    location VARCHAR(500),
    max_participants INTEGER,
    enrolled INTEGER DEFAULT 0,
    is_free BOOLEAN DEFAULT TRUE,
    price FLOAT,
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(200)
);

CREATE TABLE educational_enrollments (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES educational_events(id),
    user_id INTEGER REFERENCES users(id),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Frontend:**
- Add `/education` route
- Create `public/education-dashboard.html`

**Time to integrate:** 3-4 hours  
**Dependencies:** None (uses existing User model)  

---

### Feature 6: Tourism Data ✅
**File:** `tourism_data.py`  
**Status:** Ready for integration  
**Integration Steps:**

```python
# In main.py:
from features_implementations.tourism_data import setup_tourism_section

setup_tourism_section(app)
```

**Database Migration:**
```sql
CREATE TABLE tourist_attractions (
    id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES cities(id),
    name VARCHAR(200),
    type VARCHAR(50),
    description TEXT,
    rating FLOAT,
    address VARCHAR(500),
    phone VARCHAR(20),
    website VARCHAR(500),
    image_url VARCHAR(500),
    latitude FLOAT,
    longitude FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Seed Tourism Data:**
- Run `seed_tourism_data.py` with 50+ attractions across 27 cities

**Frontend:**
- Add `/tourism` route
- Create `public/tourism-dashboard.html`

**Time to integrate:** 4-5 hours  
**Dependencies:** None  

---

### Feature 7: Social Sharing ✅
**File:** `social_sharing.py`  
**Status:** Ready for integration  
**Integration Steps:**

```python
# In main.py:
from features_implementations.social_sharing import setup_social_sharing

setup_social_sharing(app)
```

**Database Migration (for analytics):**
```sql
CREATE TABLE share_analytics (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50),
    content_id INTEGER,
    platform VARCHAR(50),
    user_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Frontend:**
- Add share buttons to news-dashboard.html
- Add share buttons to events-dashboard.html
- Copy JavaScript code from social_sharing.py

**Time to integrate:** 2 hours  
**Dependencies:** None (uses built-in urllib)  

---

### Feature 8: Distance Calculation ✅
**File:** `tourism_data.py` (same file)  
**Status:** Ready for integration  

**Integration:**
- Already integrated in `tourism_data.py`
- No additional database needed
- Uses Haversine formula with city coordinates

**Endpoints:**
- `GET /api/distance/{city1}/{city2}` - Distance between cities
- `GET /api/tourism/recommended-routes` - Pre-built routes

**Time to integrate:** < 1 hour  
**Dependencies:** None (math library built-in)  

---

## 📦 REQUIREMENTS TO ADD

```
# Calendar Integration
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.2.0
google-api-python-client==2.90.0

# Outlook Integration
requests-oauthlib==1.3.0

# Push Notifications
pywebpush==1.14.0
firebase-admin==6.2.0

# Existing (already have)
fastapi==0.104.0
sqlalchemy==2.0.0
psycopg2-binary==2.9.9
```

---

## 🗄️ DATABASE MIGRATIONS

**Total new tables:** 4
- push_subscriptions
- educational_events
- educational_enrollments
- tourist_attractions
- share_analytics (optional, for analytics)

**Run migrations:**
```sql
-- Create all tables
-- Copy SQL from each feature section above
-- Or run migration script
```

---

## 🧪 TESTING CHECKLIST

- [ ] Swagger docs accessible at /docs
- [ ] Push notification subscription working
- [ ] Google Calendar export functional
- [ ] Outlook Calendar export functional
- [ ] Create educational event working
- [ ] Enroll in educational event working
- [ ] Tourism attractions loading
- [ ] Distance calculation accurate
- [ ] Social sharing links generate correctly
- [ ] Share analytics tracking

---

## 📊 INTEGRATION TIMELINE

```
Week 1 (Days 1-3):
  ✅ Swagger Documentation
  ✅ Push Notifications (partial - Firebase setup needed)

Week 1 (Days 4-7):
  ✅ Google Calendar Integration
  ✅ Outlook Integration

Week 2 (Days 8-10):
  ✅ Educational Section
  ✅ Tourism Data

Week 2 (Days 11-14):
  ✅ Social Sharing
  ✅ Distance Calculation

Week 3 (Days 15-21):
  ✅ Final integration & testing
  ✅ Bug fixes
```

---

## ✅ FINAL INTEGRATION STEPS

1. **Copy all files** from `features_implementations/` to appropriate locations
2. **Update main.py** with all imports and setup calls
3. **Run database migrations**
4. **Add requirements.txt**
5. **Create frontend files**
6. **Test all endpoints**
7. **Commit to GitHub**

---

## 📝 NOTES

- All features are modular and independent
- Can be integrated one at a time
- Frontend components can be created in parallel
- Testing should happen after each feature integration
- Beta testing with 50+ users in Week 4

---

**Total Implementation Time: 15-20 hours**  
**All code ready to use - just needs integration!**
