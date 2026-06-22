-- Migration 018: Reuniao Photos (Flywheel Closer)
-- Photos uploaded after a turma reunião — closes the social loop:
-- vote → confirm → attend → share photos → revive nostalgia → next reunião
-- Only confirmed RSVPs can upload; verified turma members can view.

CREATE TABLE IF NOT EXISTS reuniao_photos (
    id SERIAL PRIMARY KEY,
    reuniao_id INTEGER REFERENCES turma_reunioes(id),
    uploader_user_id INTEGER REFERENCES users(id),
    file_path VARCHAR(500),
    caption VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reuniao_photos_reuniao_id ON reuniao_photos(reuniao_id);
