"""Database models and schema for weather data storage."""

# SQLite schema definitions
SCHEMA_SQL = """
-- Weather query history table
CREATE TABLE IF NOT EXISTS weather_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    country TEXT,
    query_type TEXT NOT NULL,
    temperature REAL,
    description TEXT,
    result_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Weather cache table for recent queries
CREATE TABLE IF NOT EXISTS weather_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL UNIQUE,
    data_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_weather_queries_city ON weather_queries(city);
CREATE INDEX IF NOT EXISTS idx_weather_queries_created_at ON weather_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_weather_cache_city ON weather_cache(city);
"""
