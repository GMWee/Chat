CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    sub_type INTEGER NOT NULL DEFAULT 0,
    sub_time REAL NOT NULL DEFAULT 0,
    role INTEGER NOT NULL DEFAULT 0,
    setting_model INTEGER NOT NULL DEFAULT 12,
    credits INTEGER NOT NULL DEFAULT 10,
    next_credits_time REAL NOT NULL DEFAULT 0,
    setting_system TEXT NOT NULL DEFAULT '',
    setting_temperature FLOAT NOT NULL DEFAULT 1.0,
    setting_max_tokens INTEGER NOT NULL DEFAULT 2048,
    ban INTEGER DEFAULT 0,
    balance INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    hour_credits INTEGER NOT NULL,
    image_cost INTEGER NOT NULL,
    show_in_shop INTEGER NOT NULL DEFAULT 1,
    price FLOAT NOT NULL,
    context_length INTEGER NOT NULL,
    voice_cost INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS s_models (
    sub_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    internal_name TEXT NOT NULL,
    provider TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS u_context (
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    image_data TEXT,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_key (
    client TEXT NOT NULL,
    api_key TEXT NOT NULL
);