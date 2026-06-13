CREATE TABLE IF NOT EXISTS match_attempt_logs (
    id SERIAL PRIMARY KEY,
    requester_id INTEGER REFERENCES users(id),
    face_id INTEGER REFERENCES tunel_faces(id),
    matches_count INTEGER DEFAULT 0,
    action_taken VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_match_logs_requester ON match_attempt_logs(requester_id);
