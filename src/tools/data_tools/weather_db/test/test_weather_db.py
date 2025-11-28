"""Unit tests for Weather DB tool."""

import os
import pytest
import tempfile

from src.tools.data_tools.weather_db.weather_db import (
    init_db,
    save_weather_query,
    get_weather_history,
    cache_weather,
    get_cached_weather,
    get_db_path,
)


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['WEATHER_DB_DIR'] = tmpdir
        yield tmpdir
        # Cleanup
        if 'WEATHER_DB_DIR' in os.environ:
            del os.environ['WEATHER_DB_DIR']


class TestWeatherDb:
    """Tests for weather database operations."""

    def test_init_db(self, temp_db_dir):
        """Test database initialization."""
        init_db()
        db_path = get_db_path()
        assert os.path.exists(db_path)

    def test_save_and_get_history(self, temp_db_dir):
        """Test saving and retrieving weather history."""
        test_result = {
            'city': 'Seoul',
            'country': 'KR',
            'temperature': 20.5,
            'description': 'clear sky',
        }

        # Save weather query
        save_result = save_weather_query.invoke({
            'city': 'Seoul',
            'query_type': 'current',
            'result': test_result,
        })
        assert save_result['success'] is True

        # Get history
        history = get_weather_history.invoke({'city': 'Seoul', 'limit': 10})
        assert history['total'] > 0
        assert history['history'][0]['city'] == 'Seoul'

    def test_cache_weather(self, temp_db_dir):
        """Test weather data caching."""
        test_data = {
            'city': 'Tokyo',
            'temperature': 15.0,
            'description': 'cloudy',
        }

        # Cache weather data
        cache_weather('Tokyo', test_data)

        # Retrieve cached data
        cached = get_cached_weather('Tokyo', max_age_minutes=30)
        assert cached is not None
        assert cached['city'] == 'Tokyo'

    def test_get_history_empty(self, temp_db_dir):
        """Test getting history when database is empty."""
        history = get_weather_history.invoke({'city': '', 'limit': 10})
        assert history['total'] == 0
        assert history['history'] == []
