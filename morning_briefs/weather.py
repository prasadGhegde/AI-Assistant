from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from .config import AppConfig
from .models import WeatherReport


WEATHER_CODES = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "light showers",
    81: "showers",
    82: "heavy showers",
    95: "thunderstorms",
    96: "thunderstorms with hail",
    99: "severe thunderstorms with hail",
}


class WeatherService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def fetch(self) -> Tuple[WeatherReport, List[str]]:
        warnings: List[str] = []
        params = {
            "latitude": self.config.weather_latitude,
            "longitude": self.config.weather_longitude,
            "current": ",".join(
                [
                    "temperature_2m",
                    "apparent_temperature",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_gusts_10m",
                    "precipitation",
                    "cloud_cover",
                ]
            ),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "temperature_unit": self.config.weather_temperature_unit,
            "wind_speed_unit": self.config.weather_wind_speed_unit,
            "forecast_days": 1,
            "timezone": "auto",
        }
        try:
            response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params=params,
                timeout=self.config.fetch_timeout,
            )
            response.raise_for_status()
            payload = response.json()
            report = self._from_payload(payload)
        except Exception as exc:
            warnings.append(f"Weather fetch failed: {exc}")
            report = self._fallback_report(warnings)
        return report, warnings

    def _from_payload(self, payload: Dict[str, object]) -> WeatherReport:
        current = payload.get("current") or {}
        current_units = payload.get("current_units") or {}
        daily = payload.get("daily") or {}
        hourly = payload.get("hourly") or {}
        code = current.get("weather_code")
        condition = WEATHER_CODES.get(code, "mixed conditions")
        precipitation_probability = _first_int(
            daily.get("precipitation_probability_max")
        )
        temperature = _number(current.get("temperature_2m"))
        apparent = _number(current.get("apparent_temperature"))
        wind_speed = _number(current.get("wind_speed_10m"))
        wind_gusts = _number(current.get("wind_gusts_10m"))
        cloud_cover = _int(current.get("cloud_cover"))
        carry, wear, advisory = weather_guidance(
            condition=condition,
            temperature=temperature,
            apparent_temperature=apparent,
            unit=current_units.get("temperature_2m")
            or self.config.weather_temperature_unit,
            wind_speed=wind_speed,
            wind_gusts=wind_gusts,
            wind_unit=current_units.get("wind_speed_10m")
            or self.config.weather_wind_speed_unit,
            precipitation_probability=precipitation_probability,
            cloud_cover=cloud_cover,
        )
        hourly_rows = self._hourly_preview(hourly)
        alerts = self._alerts(
            condition=condition,
            precipitation_probability=precipitation_probability,
            wind_gusts=wind_gusts,
            wind_unit=current_units.get("wind_speed_10m")
            or self.config.weather_wind_speed_unit,
        )
        observed_at = str(current.get("time") or datetime.now(timezone.utc).isoformat())
        return WeatherReport(
            location_name=self.config.weather_location_name,
            latitude=self.config.weather_latitude,
            longitude=self.config.weather_longitude,
            observed_at=observed_at,
            temperature=temperature,
            apparent_temperature=apparent,
            temperature_unit=str(
                current_units.get("temperature_2m")
                or self.config.weather_temperature_unit
            ),
            conditions=condition,
            weather_code=_int(code),
            wind_speed=wind_speed,
            wind_gusts=wind_gusts,
            wind_unit=str(
                current_units.get("wind_speed_10m")
                or self.config.weather_wind_speed_unit
            ),
            precipitation_probability=precipitation_probability,
            cloud_cover=cloud_cover,
            hourly=hourly_rows,
            alerts=alerts,
            carry=carry,
            wear=wear,
            advisory=advisory,
        )

    def _fallback_report(self, warnings: List[str]) -> WeatherReport:
        if self.config.use_fake_data_when_empty:
            return WeatherReport(
                location_name=self.config.weather_location_name,
                latitude=self.config.weather_latitude,
                longitude=self.config.weather_longitude,
                observed_at=datetime.now(timezone.utc).isoformat(),
                temperature=12,
                apparent_temperature=10,
                temperature_unit="°C" if "celsius" in self.config.weather_temperature_unit.lower() else self.config.weather_temperature_unit,
                conditions="partly cloudy",
                weather_code=2,
                wind_speed=14,
                wind_gusts=24,
                wind_unit=self.config.weather_wind_speed_unit,
                precipitation_probability=20,
                cloud_cover=55,
                carry=["sunglasses"],
                wear=["comfortable layers"],
                advisory="Partly cloudy and mild. Carry sunglasses and wear comfortable layers.",
                warnings=warnings,
                hourly=[
                    {"time": "08:00", "temperature": 12, "precipitation_probability": 15, "weather_code": 2},
                    {"time": "11:00", "temperature": 15, "precipitation_probability": 10, "weather_code": 2},
                    {"time": "14:00", "temperature": 17, "precipitation_probability": 20, "weather_code": 3},
                    {"time": "17:00", "temperature": 15, "precipitation_probability": 25, "weather_code": 3},
                ],
                alerts=["No active weather alerts"],
                mock=True,
            )
        return WeatherReport(
            location_name=self.config.weather_location_name,
            latitude=self.config.weather_latitude,
            longitude=self.config.weather_longitude,
            observed_at=datetime.now(timezone.utc).isoformat(),
            temperature=None,
            apparent_temperature=None,
            temperature_unit=self.config.weather_temperature_unit,
            conditions="weather unavailable",
            weather_code=None,
            wind_speed=None,
            wind_gusts=None,
            wind_unit=self.config.weather_wind_speed_unit,
            precipitation_probability=None,
            cloud_cover=None,
            carry=["check the sky before stepping out"],
            wear=["dress in adaptable layers"],
            advisory="Weather data is unavailable, so use a quick local check before you leave.",
            warnings=warnings,
            hourly=[],
            alerts=[],
        )

    def _hourly_preview(self, hourly: Dict[str, object]) -> List[Dict[str, object]]:
        times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
        temps = hourly.get("temperature_2m") if isinstance(hourly.get("temperature_2m"), list) else []
        precip = hourly.get("precipitation_probability") if isinstance(hourly.get("precipitation_probability"), list) else []
        rows: List[Dict[str, object]] = []
        for idx in range(min(len(times), len(temps), 24)):
            hour_label = "--"
            try:
                hour_label = str(times[idx])[11:16]
            except Exception:
                hour_label = str(times[idx])
            rows.append(
                {
                    "time": hour_label,
                    "temperature": _number(temps[idx]),
                    "precipitation_probability": _int(precip[idx]) if idx < len(precip) else None,
                }
            )
        return rows[:12]

    def _alerts(
        self,
        *,
        condition: str,
        precipitation_probability: Optional[int],
        wind_gusts: Optional[float],
        wind_unit: str,
    ) -> List[str]:
        alerts: List[str] = []
        cond = condition.lower()
        if "thunder" in cond or "hail" in cond:
            alerts.append("Thunderstorm risk in current forecast.")
        if precipitation_probability is not None and precipitation_probability >= 70:
            alerts.append(f"High rain probability ({precipitation_probability}%).")
        gust_kmh = _to_kmh(wind_gusts, wind_unit)
        if gust_kmh is not None and gust_kmh >= 45:
            alerts.append("Strong gusts expected; secure loose items.")
        return alerts


def weather_guidance(
    *,
    condition: str,
    temperature: Optional[float],
    apparent_temperature: Optional[float],
    unit: str,
    wind_speed: Optional[float],
    wind_gusts: Optional[float],
    wind_unit: str,
    precipitation_probability: Optional[int],
    cloud_cover: Optional[int],
) -> Tuple[List[str], List[str], str]:
    carry: List[str] = []
    wear: List[str] = []
    condition_text = condition.lower()
    temp_c = _to_celsius(
        apparent_temperature if apparent_temperature is not None else temperature,
        unit,
    )

    rain_risk = (
        "rain" in condition_text
        or "drizzle" in condition_text
        or "showers" in condition_text
        or (precipitation_probability is not None and precipitation_probability >= 35)
    )
    if rain_risk:
        carry.append("umbrella")
    if "snow" in condition_text:
        carry.append("shoes with grip")

    if temp_c is None:
        wear.append("adaptable layers")
    elif temp_c < 4:
        wear.append("proper coat")
    elif temp_c < 12:
        wear.append("light jacket")
    elif temp_c > 24:
        wear.append("breathable clothes")
    else:
        wear.append("comfortable layers")

    if (
        ("clear" in condition_text or "cloudy" not in condition_text)
        and (cloud_cover is None or cloud_cover < 45)
        and not rain_risk
    ):
        carry.append("sunglasses")

    wind_kmh = _to_kmh(
        wind_gusts if wind_gusts is not None else wind_speed,
        wind_unit,
    )
    wind_note = ""
    if wind_kmh is not None and wind_kmh >= 38:
        wind_note = " Watch the gusts; it may feel sharper than the headline temperature."
        carry.append("secure loose layers")

    carry = carry or ["phone and keys"]
    temperature_phrase = (
        "temperature data is not available"
        if temperature is None
        else f"it is {round(temperature)} degrees"
    )
    advisory = (
        f"{condition.capitalize()} in the forecast, {temperature_phrase}. "
        f"Carry {', '.join(carry)} and wear {', '.join(wear)}.{wind_note}"
    )
    return carry, wear, advisory


def _number(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_int(value) -> Optional[int]:
    if isinstance(value, list) and value:
        return _int(value[0])
    return _int(value)


def _to_celsius(value: Optional[float], unit: str) -> Optional[float]:
    if value is None:
        return None
    if "f" in unit.lower():
        return (value - 32) * 5 / 9
    return value


def _to_kmh(value: Optional[float], unit: str) -> Optional[float]:
    if value is None:
        return None
    normalized = unit.lower()
    if "mph" in normalized:
        return value * 1.60934
    if "ms" in normalized or "m/s" in normalized:
        return value * 3.6
    return value
