"""Weather API Tool - OpenWeatherMap integration."""

import os

import httpx
from langchain_core.tools import tool


@tool
def get_current_weather(
    city: str,
    units: str = 'metric',
) -> dict:
    """Get current weather for a city.

    Args:
        city: The city name (e.g., "Seoul", "Tokyo", "New York").
        units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit).
            Defaults to "metric".

    Returns:
        A dictionary containing weather data including temperature, humidity,
        description, and more. Returns an error message if the request fails.
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return {'error': 'OPENWEATHER_API_KEY environment variable not set.'}

    try:
        response = httpx.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={
                'q': city,
                'appid': api_key,
                'units': units,
            },
            timeout=10.0,
        )
        response.raise_for_status()

        data = response.json()
        return {
            'city': data.get('name'),
            'country': data.get('sys', {}).get('country'),
            'temperature': data.get('main', {}).get('temp'),
            'feels_like': data.get('main', {}).get('feels_like'),
            'humidity': data.get('main', {}).get('humidity'),
            'description': data.get('weather', [{}])[0].get('description'),
            'wind_speed': data.get('wind', {}).get('speed'),
            'units': units,
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {'error': f'City "{city}" not found.'}
        return {'error': f'API request failed: {e}'}
    except httpx.HTTPError as e:
        return {'error': f'API request failed: {e}'}
    except ValueError:
        return {'error': 'Invalid JSON response from API.'}


@tool
def get_weather_forecast(
    city: str,
    units: str = 'metric',
) -> dict:
    """Get 5-day weather forecast for a city.

    Args:
        city: The city name (e.g., "Seoul", "Tokyo", "New York").
        units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit).
            Defaults to "metric".

    Returns:
        A dictionary containing forecast data for the next 5 days.
        Returns an error message if the request fails.
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return {'error': 'OPENWEATHER_API_KEY environment variable not set.'}

    try:
        response = httpx.get(
            'https://api.openweathermap.org/data/2.5/forecast',
            params={
                'q': city,
                'appid': api_key,
                'units': units,
            },
            timeout=10.0,
        )
        response.raise_for_status()

        data = response.json()
        forecasts = []

        # Group by day (API returns 3-hour intervals)
        seen_dates = set()
        for item in data.get('list', []):
            date = item.get('dt_txt', '').split(' ')[0]
            if date and date not in seen_dates:
                seen_dates.add(date)
                forecasts.append({
                    'date': date,
                    'temperature': item.get('main', {}).get('temp'),
                    'feels_like': item.get('main', {}).get('feels_like'),
                    'humidity': item.get('main', {}).get('humidity'),
                    'description': item.get('weather', [{}])[0].get('description'),
                    'wind_speed': item.get('wind', {}).get('speed'),
                })
                if len(forecasts) >= 5:
                    break

        return {
            'city': data.get('city', {}).get('name'),
            'country': data.get('city', {}).get('country'),
            'forecasts': forecasts,
            'units': units,
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {'error': f'City "{city}" not found.'}
        return {'error': f'API request failed: {e}'}
    except httpx.HTTPError as e:
        return {'error': f'API request failed: {e}'}
    except ValueError:
        return {'error': 'Invalid JSON response from API.'}
