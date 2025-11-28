"""Weather Database Tool - SQLite operations for weather history."""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from langchain_core.tools import tool

from observability import trace_tool

from .models import SCHEMA_SQL


def get_db_path() -> str:
    """Get the database file path."""
    db_dir = Path(os.getenv('WEATHER_DB_DIR', './data'))
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / 'weather.db')


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database with required tables."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


@tool
@trace_tool(name="db.save_weather_query")
def save_weather_query(
    city: str,
    query_type: str,
    result: dict,
) -> dict:
    """Save a weather query to the history database.

    Args:
        city: The city name that was queried.
        query_type: Type of query - "current" or "forecast".
        result: The weather result dictionary to save.

    Returns:
        A confirmation message with the saved record ID.
    """
    init_db()
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO weather_queries
            (city, country, query_type, temperature, description, result_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                city,
                result.get('country'),
                query_type,
                result.get('temperature'),
                result.get('description'),
                json.dumps(result),
            ),
        )
        conn.commit()
        return {
            'success': True,
            'message': f'Weather query saved with ID {cursor.lastrowid}',
            'id': cursor.lastrowid,
        }
    except sqlite3.Error as e:
        return {'error': f'Database error: {e}'}
    finally:
        conn.close()


@tool
@trace_tool(name="db.get_weather_history")
def get_weather_history(
    city: str = '',
    limit: int = 10,
) -> dict:
    """Get weather query history from the database.

    Args:
        city: Optional city name to filter by. If empty, returns all cities.
        limit: Maximum number of records to return. Defaults to 10.

    Returns:
        A dictionary containing the query history records.
    """
    init_db()
    conn = get_connection()
    try:
        if city:
            cursor = conn.execute(
                """
                SELECT city, country, query_type, temperature, description, created_at
                FROM weather_queries
                WHERE city LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f'%{city}%', limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT city, country, query_type, temperature, description, created_at
                FROM weather_queries
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cursor.fetchall()
        history = [
            {
                'city': row['city'],
                'country': row['country'],
                'query_type': row['query_type'],
                'temperature': row['temperature'],
                'description': row['description'],
                'queried_at': row['created_at'],
            }
            for row in rows
        ]

        return {
            'total': len(history),
            'history': history,
        }
    except sqlite3.Error as e:
        return {'error': f'Database error: {e}'}
    finally:
        conn.close()


def cache_weather(city: str, data: dict) -> None:
    """Cache weather data for a city.

    Args:
        city: The city name.
        data: Weather data to cache.
    """
    init_db()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO weather_cache (city, data_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (city.lower(), json.dumps(data)),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_weather(city: str, max_age_minutes: int = 30) -> dict | None:
    """Get cached weather data if not expired.

    Args:
        city: The city name.
        max_age_minutes: Maximum age of cache in minutes.

    Returns:
        Cached weather data or None if expired/not found.
    """
    init_db()
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT data_json, updated_at
            FROM weather_cache
            WHERE city = ?
            """,
            (city.lower(),),
        )
        row = cursor.fetchone()

        if row:
            updated_at = datetime.fromisoformat(row['updated_at'])
            if datetime.now() - updated_at < timedelta(minutes=max_age_minutes):
                return json.loads(row['data_json'])

        return None
    except sqlite3.Error:
        return None
    finally:
        conn.close()
