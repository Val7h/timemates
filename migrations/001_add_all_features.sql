-- Migration: Add 8 Features Tables
-- Description: Creates tables for: Push Subscriptions, OAuth Tokens, Educational Events, Tourist Attractions, Share Analytics

-- Create user_oauth_tokens table
CREATE TABLE IF NOT EXISTS user_oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,
    access_token VARCHAR(1000) NOT NULL,
    refresh_token VARCHAR(1000),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user ON user_oauth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_provider ON user_oauth_tokens(provider);

-- Create educational_events table
CREATE TABLE IF NOT EXISTS educational_events (
    id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES cities(id),
    title VARCHAR(200) NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_educational_events_city ON educational_events(city_id);
CREATE INDEX IF NOT EXISTS idx_educational_events_type ON educational_events(type);
CREATE INDEX IF NOT EXISTS idx_educational_events_date ON educational_events(date);

-- Create educational_enrollments table
CREATE TABLE IF NOT EXISTS educational_enrollments (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES educational_events(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_educational_enrollments_event ON educational_enrollments(event_id);
CREATE INDEX IF NOT EXISTS idx_educational_enrollments_user ON educational_enrollments(user_id);

-- Create tourist_attractions table
CREATE TABLE IF NOT EXISTS tourist_attractions (
    id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES cities(id),
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50),
    description TEXT,
    rating FLOAT DEFAULT 0.0,
    address VARCHAR(500),
    phone VARCHAR(20),
    website VARCHAR(500),
    image_url VARCHAR(500),
    latitude FLOAT,
    longitude FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tourist_attractions_city ON tourist_attractions(city_id);
CREATE INDEX IF NOT EXISTS idx_tourist_attractions_type ON tourist_attractions(type);
CREATE INDEX IF NOT EXISTS idx_tourist_attractions_rating ON tourist_attractions(rating);

-- Create share_analytics table
CREATE TABLE IF NOT EXISTS share_analytics (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50),
    content_id INTEGER,
    platform VARCHAR(50),
    user_id INTEGER REFERENCES users(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_share_analytics_content ON share_analytics(content_type, content_id);
CREATE INDEX IF NOT EXISTS idx_share_analytics_platform ON share_analytics(platform);
CREATE INDEX IF NOT EXISTS idx_share_analytics_user ON share_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_share_analytics_timestamp ON share_analytics(timestamp);
