"""Unit tests for Weather API tool."""

import pytest
from unittest.mock import patch, MagicMock

from src.tools.api_tools.weather_api.weather_api import (
    get_current_weather,
    get_weather_forecast,
)


class TestGetCurrentWeather:
    """Tests for get_current_weather function."""

    @patch('src.tools.api_tools.weather_api.weather_api.os.getenv')
    @patch('src.tools.api_tools.weather_api.weather_api.httpx.get')
    def test_successful_weather_query(self, mock_get, mock_getenv):
        """Test successful weather API response."""
        mock_getenv.return_value = 'test_api_key'
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'name': 'Seoul',
            'sys': {'country': 'KR'},
            'main': {'temp': 20.5, 'feels_like': 19.0, 'humidity': 65},
            'weather': [{'description': 'clear sky'}],
            'wind': {'speed': 3.5},
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_current_weather.invoke({'city': 'Seoul'})

        assert result['city'] == 'Seoul'
        assert result['country'] == 'KR'
        assert result['temperature'] == 20.5
        assert 'error' not in result

    @patch('src.tools.api_tools.weather_api.weather_api.os.getenv')
    def test_missing_api_key(self, mock_getenv):
        """Test error when API key is missing."""
        mock_getenv.return_value = None

        result = get_current_weather.invoke({'city': 'Seoul'})

        assert 'error' in result
        assert 'OPENWEATHER_API_KEY' in result['error']


class TestGetWeatherForecast:
    """Tests for get_weather_forecast function."""

    @patch('src.tools.api_tools.weather_api.weather_api.os.getenv')
    @patch('src.tools.api_tools.weather_api.weather_api.httpx.get')
    def test_successful_forecast_query(self, mock_get, mock_getenv):
        """Test successful forecast API response."""
        mock_getenv.return_value = 'test_api_key'
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'city': {'name': 'Tokyo', 'country': 'JP'},
            'list': [
                {
                    'dt_txt': '2024-01-01 12:00:00',
                    'main': {'temp': 10.0, 'feels_like': 8.0, 'humidity': 50},
                    'weather': [{'description': 'cloudy'}],
                    'wind': {'speed': 5.0},
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_weather_forecast.invoke({'city': 'Tokyo'})

        assert result['city'] == 'Tokyo'
        assert result['country'] == 'JP'
        assert len(result['forecasts']) > 0
        assert 'error' not in result
