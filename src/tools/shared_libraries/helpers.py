"""Shared helper functions for weather tools."""

from datetime import datetime


def format_temperature(temp: float, units: str = 'metric') -> str:
    """Format temperature with unit symbol.

    Args:
        temp: Temperature value.
        units: "metric" for Celsius, "imperial" for Fahrenheit.

    Returns:
        Formatted temperature string.
    """
    unit_symbol = 'C' if units == 'metric' else 'F'
    return f'{temp:.1f}{unit_symbol}'


def get_timestamp() -> str:
    """Get current timestamp in ISO format.

    Returns:
        ISO formatted timestamp string.
    """
    return datetime.now().isoformat()


def format_weather_summary(weather_data: dict) -> str:
    """Format weather data into a human-readable summary.

    Args:
        weather_data: Weather data dictionary.

    Returns:
        Formatted weather summary string.
    """
    if 'error' in weather_data:
        return f"Error: {weather_data['error']}"

    city = weather_data.get('city', 'Unknown')
    country = weather_data.get('country', '')
    temp = weather_data.get('temperature', 'N/A')
    desc = weather_data.get('description', 'N/A')
    humidity = weather_data.get('humidity', 'N/A')
    units = weather_data.get('units', 'metric')

    location = f'{city}, {country}' if country else city
    temp_str = format_temperature(temp, units) if isinstance(temp, (int, float)) else temp

    return (
        f'{location}: {temp_str}, {desc}, '
        f'Humidity: {humidity}%'
    )
