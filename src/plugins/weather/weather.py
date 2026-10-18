from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import os
import requests
import logging
from datetime import datetime, timedelta, timezone, date
from astral import moon, LocationInfo
from astral.sun import sun
import pytz
from io import BytesIO
import math
import json
import re

logger = logging.getLogger(__name__)
        
def get_moon_phase_name(phase_age: float) -> str:
    """Determines the name of the lunar phase based on the age of the moon."""
    PHASES_THRESHOLDS = [
        (1.0, "newmoon"),
        (7.0, "waxingcrescent"),
        (8.5, "firstquarter"),
        (14.0, "waxinggibbous"),
        (15.5, "fullmoon"),
        (22.0, "waninggibbous"),
        (23.5, "lastquarter"),
        (29.0, "waningcrescent"),
    ]

    for threshold, phase_name in PHASES_THRESHOLDS:
        if phase_age <= threshold:
            return phase_name  
    return "newmoon"

UNITS = {
    "standard": {
        "temperature": "K",
        "speed": "m/s",
        "distance":"km"
    },
    "metric": {
        "temperature": "°C",
        "speed": "m/s",
        "distance":"km"

    },
    "imperial": {
        "temperature": "°F",
        "speed": "mph",
        "distance":"mi"
    }
}

# CWA Forecast datasets mapping for 22 counties in Taiwan
CWA_COUNTY_DATASETS = {
    '宜蘭縣': {'3_day': 'F-D0047-001', '7_day': 'F-D0047-003'},
    '桃園市': {'3_day': 'F-D0047-005', '7_day': 'F-D0047-007'},
    '新竹縣': {'3_day': 'F-D0047-009', '7_day': 'F-D0047-011'},
    '苗栗縣': {'3_day': 'F-D0047-013', '7_day': 'F-D0047-015'},
    '彰化縣': {'3_day': 'F-D0047-017', '7_day': 'F-D0047-019'},
    '南投縣': {'3_day': 'F-D0047-021', '7_day': 'F-D0047-023'},
    '雲林縣': {'3_day': 'F-D0047-025', '7_day': 'F-D0047-027'},
    '嘉義縣': {'3_day': 'F-D0047-029', '7_day': 'F-D0047-031'},
    '屏東縣': {'3_day': 'F-D0047-033', '7_day': 'F-D0047-035'},
    '臺東縣': {'3_day': 'F-D0047-037', '7_day': 'F-D0047-039'},
    '花蓮縣': {'3_day': 'F-D0047-041', '7_day': 'F-D0047-043'},
    '澎湖縣': {'3_day': 'F-D0047-045', '7_day': 'F-D0047-047'},
    '基隆市': {'3_day': 'F-D0047-049', '7_day': 'F-D0047-051'},
    '新竹市': {'3_day': 'F-D0047-053', '7_day': 'F-D0047-055'},
    '嘉義市': {'3_day': 'F-D0047-057', '7_day': 'F-D0047-059'},
    '臺北市': {'3_day': 'F-D0047-061', '7_day': 'F-D0047-063'},
    '高雄市': {'3_day': 'F-D0047-065', '7_day': 'F-D0047-067'},
    '新北市': {'3_day': 'F-D0047-069', '7_day': 'F-D0047-071'},
    '臺中市': {'3_day': 'F-D0047-073', '7_day': 'F-D0047-075'},
    '臺南市': {'3_day': 'F-D0047-077', '7_day': 'F-D0047-079'},
    '連江縣': {'3_day': 'F-D0047-081', '7_day': 'F-D0047-083'},
    '金門縣': {'3_day': 'F-D0047-085', '7_day': 'F-D0047-087'},
}

WEATHER_URL = "https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={long}&units={units}&exclude=minutely&appid={api_key}"
AIR_QUALITY_URL = "http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={long}&appid={api_key}"
GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={long}&limit=1&appid={api_key}"
# URLs for CWA and MOENV data
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
MOENV_AQI_URL = "https://data.moenv.gov.tw/api/v2/aqx_p_432"

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}&hourly=weather_code,temperature_2m,precipitation,precipitation_probability,relative_humidity_2m,surface_pressure,visibility&daily=weathercode,temperature_2m_max,temperature_2m_min,sunrise,sunset&current=temperature,windspeed,winddirection,is_day,precipitation,weather_code,apparent_temperature&timezone=auto&models=best_match&forecast_days={forecast_days}"
OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={long}&hourly=european_aqi,uv_index,uv_index_clear_sky&timezone=auto"
OPEN_METEO_UNIT_PARAMS = {
    "standard": "temperature_unit=celsius&wind_speed_unit=ms&precipitation_unit=mm",  # temperature is converted to Kelvin later
    "metric":   "temperature_unit=celsius&wind_speed_unit=ms&precipitation_unit=mm",
    "imperial": "temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
}

class Weather(BasePlugin):
    def __init__(self, config=None, **dependencies):
        super().__init__(config, **dependencies)
        self._stations_cache = None

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['api_key'] = {
            "required": True,
            "service": "CWA / OpenWeatherMap",
            "expected_key": "CWA_API_KEY / OPEN_WEATHER_MAP_SECRET"
        }
        template_params['style_settings'] = True
        return template_params

    def generate_image(self, settings, device_config):
        lat = float(settings.get('latitude'))
        long = float(settings.get('longitude'))
        county = settings.get('county')
        district = settings.get('district')
        if not lat or not long:
            raise RuntimeError("Latitude and Longitude are required.")

        units = settings.get('units')
        if not units or units not in ['metric', 'imperial', 'standard']:
            raise RuntimeError("Units are required.")

        weather_provider = settings.get('weatherProvider', 'OpenWeatherMap')
        title = settings.get('customTitle', '')

        timezone = device_config.get_config("timezone", default="Asia/Taipei")
        time_format = device_config.get_config("time_format", default="12h")
        tz = pytz.timezone(timezone)

        try:
            if weather_provider == "OpenWeatherMap":
                api_key = device_config.load_env_key("OPEN_WEATHER_MAP_SECRET")
                if not api_key:
                    raise RuntimeError("Open Weather Map API Key not configured.")
                weather_data = self.get_weather_data(api_key, units, lat, long)
                aqi_data = self.get_air_quality(api_key, lat, long)
                if settings.get('titleSelection', 'location') == 'location':
                    title = self.get_location(api_key, lat, long)
                if settings.get('weatherTimeZone', 'locationTimeZone') == 'locationTimeZone':
                    logger.info("Using location timezone for OpenWeatherMap data.")
                    wtz = self.parse_timezone(weather_data)
                    template_params = self.parse_weather_data(weather_data, aqi_data, wtz, units, time_format, lat)
                else:
                    logger.info("Using configured timezone for OpenWeatherMap data.")
                    template_params = self.parse_weather_data(weather_data, aqi_data, tz, units, time_format, lat)
            elif weather_provider == "OpenMeteo":
                forecast_days = 7
                weather_data = self.get_open_meteo_data(lat, long, units, forecast_days + 1)
                aqi_data = self.get_open_meteo_air_quality(lat, long)
                template_params = self.parse_open_meteo_data(weather_data, aqi_data, tz, units, time_format, lat)
            elif weather_provider == "CWA":
                cwa_api = device_config.load_env_key("CWA_API_KEY")
                moe_api = device_config.load_env_key("MOE_API_KEY")
                if not cwa_api:
                    raise RuntimeError("CWA API Key not configured. Please set CWA_API_KEY in the API Keys page.")

                # If county or district not explicitly set, find nearest station from coordinates
                if not county or not district:
                    nearest_st = self.get_nearest_station(lat, long)
                    if nearest_st:
                        county = county or nearest_st.get('城市')
                        addr = nearest_st.get('地址', '')
                        m_dist = re.search(r'([^\d\s]+?[市區鄉鎮])', addr)
                        if m_dist and not district:
                            district = m_dist.group(1)

                if settings.get('titleSelection', 'location') == 'location' or not title:
                    title = f"{county or ''} {district or ''}".strip() or "Taiwan"

                template_params = self.get_and_parse_cwa_data(
                    cwa_api=cwa_api,
                    moe_api=moe_api,
                    county=county,
                    district=district,
                    lat=lat,
                    long=long,
                    units=units,
                    tz=tz,
                    time_format=time_format,
                    settings=settings
                )
            else:
                raise RuntimeError(f"Unknown weather provider: {weather_provider}")

            template_params['title'] = title
        except Exception as e:
            logger.error(f"{weather_provider} request failed: {str(e)}")
            raise RuntimeError(f"{weather_provider} request failure, please check logs.")
       
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params["plugin_settings"] = settings

        # Add last refresh time
        now = datetime.now(tz)
        if time_format == "24h":
            last_refresh_time = now.strftime("%Y-%m-%d %H:%M")
        else:
            last_refresh_time = now.strftime("%Y-%m-%d %I:%M %p")
        template_params["last_refresh_time"] = last_refresh_time

        image = self.render_image(dimensions, "weather.html", "weather.css", template_params)

        if not image:
            raise RuntimeError("Failed to take screenshot, please check logs.")
        return image

    def parse_weather_data(self, weather_data, aqi_data, tz, units, time_format, lat):
        current = weather_data.get("current")
        daily_forecast = weather_data.get("daily", [])
        dt = datetime.fromtimestamp(current.get('dt'), tz=timezone.utc).astimezone(tz)
        current_icon = current.get("weather")[0].get("icon")
        icon_codes_to_preserve = ["01", "02", "10"]
        icon_code = current_icon[:2]
        current_suffix = current_icon[-1]

        if icon_code not in icon_codes_to_preserve:
            if current_icon.endswith('n'):
                current_icon = current_icon.replace("n", "d")
        data = {
            "current_date": dt.strftime("%A, %B %d"),
            "current_day_icon": self.get_plugin_dir(f'icons/{current_icon}.png'),
            "current_temperature": str(round(current.get("temp"))),
            "feels_like": str(round(current.get("feels_like"))),
            "temperature_unit": UNITS[units]["temperature"],
            "units": units,
            "time_format": time_format
        }
        data['forecast'] = self.parse_forecast(weather_data.get('daily'), tz, current_suffix, lat)
        data['data_points'] = self.parse_data_points(weather_data, aqi_data, tz, units, time_format)

        data['hourly_forecast'] = self.parse_hourly(weather_data.get('hourly'), tz, time_format, units, daily_forecast)
        return data

    def parse_open_meteo_data(self, weather_data, aqi_data, tz, units, time_format, lat):
        current = weather_data.get("current", {})
        daily = weather_data.get('daily', {})
        dt = datetime.fromisoformat(current.get('time')).astimezone(tz) if current.get('time') else datetime.now(tz)
        weather_code = current.get("weather_code", 0)
        is_day = current.get("is_day", 1)
        current_icon = self.map_weather_code_to_icon(weather_code, is_day)
        
        temperature_conversion = 273.15 if units == "standard" else 0.

        data = {
            "current_date": dt.strftime("%A, %B %d"),
            "current_day_icon": self.get_plugin_dir(f'icons/{current_icon}.png'),
            "current_temperature": str(round(current.get("temperature", 0) + temperature_conversion)),
            "feels_like": str(round(current.get("apparent_temperature", current.get("temperature", 0)) + temperature_conversion)),
            "temperature_unit": UNITS[units]["temperature"],
            "units": units,
            "time_format": time_format
        }

        data['forecast'] = self.parse_open_meteo_forecast(weather_data.get('daily', {}), units, tz, is_day, lat)
        data['data_points'] = self.parse_open_meteo_data_points(weather_data, aqi_data, units, tz, time_format)
        
        data['hourly_forecast'] = self.parse_open_meteo_hourly(weather_data.get('hourly', {}), units, tz, time_format, daily.get('sunrise', []), daily.get('sunset', []))
        return data
    

    
    def map_weather_code_to_icon(self, weather_code, is_day):

        icon = "01d" # Default to clear day icon
        
        if weather_code in [0]:   # Clear sky
            icon = "01d"
        elif weather_code in [1]: # Mainly clear
            icon = "022d"
        elif weather_code in [2]: # Partly cloudy
            icon = "02d"
        elif weather_code in [3]: # Overcast
            icon = "04d"
        elif weather_code in [51, 61, 80]: # Drizzle, showers, rain: Light
            icon = "51d"          
        elif weather_code in [53, 63, 81]: # Drizzle, showers, rain: Moderatr
            icon = "53d"
        elif weather_code in [55, 65, 82]: # Drizzle, showers, rain: Heavy
            icon = "09d"
        elif weather_code in [45]: # Fog
            icon = "50d"                       
        elif weather_code in [48]: # Icy fog
            icon = "48d"
        elif weather_code in [56, 66]: # Light freezing Drizzle
            icon = "56d"            
        elif weather_code in [57, 67]: # Freezing Drizzle
            icon = "57d"            
        elif weather_code in [71, 85]: # Snow fall: Slight
            icon = "71d"
        elif weather_code in [73]:     # Snow fall: Moderate
            icon = "73d"
        elif weather_code in [75, 86]: # Snow fall: Heavy
            icon = "13d"
        elif weather_code in [77]:     # Snow grain
            icon = "77d"
        elif weather_code in [95]: # Thunderstorm
            icon = "11d"
        elif weather_code in [96, 99]: # Thunderstorm with slight and heavy hail
            icon = "11d"

        if is_day == 0:
            if icon == "01d":
                icon = "01n"      # Clear sky night
            elif icon == "022d":
                icon = "022n"     # Mainly clear night
            elif icon == "02d":
                icon = "02n"      # Partly cloudy night                
            elif icon == "10d":
                icon = "10n"      # Rain night

        return icon

    def get_moon_phase_icon_path(self, phase_name: str, lat: float) -> str:
        """Determines the path to the moon icon, inverting it if the location is in the Southern Hemisphere."""
        # Waxing, Waning, First and Last quarter phases are inverted between hemispheres.
        if lat < 0: # Southern Hemisphere
            if phase_name == "waxingcrescent":
                phase_name = "waningcrescent"
            elif phase_name == "waxinggibbous":
                phase_name = "waninggibbous"
            elif phase_name == "waningcrescent":
                phase_name = "waxingcrescent"
            elif phase_name == "waninggibbous":
                phase_name = "waxinggibbous"
            elif phase_name == "firstquarter":
                phase_name = "lastquarter"
            elif phase_name == "lastquarter":
                phase_name = "firstquarter"
        
        return self.get_plugin_dir(f"icons/{phase_name}.png")

    def parse_forecast(self, daily_forecast, tz, current_suffix, lat):
        """
        - daily_forecast: list of daily entries from One‑Call v3 (each has 'dt', 'weather', 'temp', 'moon_phase')
        - tz: your target tzinfo (e.g. from zoneinfo or pytz)
        """
        PHASES = [
            (0.0, "newmoon"),
            (0.25, "firstquarter"),
            (0.5, "fullmoon"),
            (0.75, "lastquarter"),
            (1.0, "newmoon"),
        ]

        def choose_phase_name(phase: float) -> str:
            for target, name in PHASES:
                if math.isclose(phase, target, abs_tol=1e-3):
                    return name
            if 0.0 < phase < 0.25:
                return "waxingcrescent"
            elif 0.25 < phase < 0.5:
                return "waxinggibbous"
            elif 0.5 < phase < 0.75:
                return "waninggibbous"
            else:
                return "waningcrescent"

        forecast = []
        icon_codes_to_apply_current_suffix = ["01", "02", "10"]
        for day in daily_forecast:
            # --- weather icon ---
            weather_icon = day["weather"][0]["icon"]  # e.g. "10d", "01n"
            icon_code = weather_icon[:2]
            if icon_code in icon_codes_to_apply_current_suffix:
                weather_icon_base = weather_icon[:-1]
                weather_icon = weather_icon_base + current_suffix
            else:
                if weather_icon.endswith('n'):
                    weather_icon = weather_icon.replace("n", "d")
            weather_icon = f"{icon_code}d"        
            weather_icon_path = self.get_plugin_dir(f"icons/{weather_icon}.png")

            # --- moon phase & icon ---
            moon_phase = float(day["moon_phase"])  # [0.0–1.0]
            phase_name_north_hemi = choose_phase_name(moon_phase)
            moon_icon_path = self.get_moon_phase_icon_path(phase_name_north_hemi, lat)
            # --- true illumination percent, no decimals ---
            illum_fraction = (1 - math.cos(2 * math.pi * moon_phase)) / 2
            moon_pct = f"{illum_fraction * 100:.0f}"

            # --- date & temps ---
            dt = datetime.fromtimestamp(day["dt"], tz=timezone.utc).astimezone(tz)
            day_label = dt.strftime("%a")

            forecast.append(
                {
                    "day": day_label,
                    "high": int(day["temp"]["max"]),
                    "low": int(day["temp"]["min"]),
                    "icon": weather_icon_path,
                    "moon_phase_pct": moon_pct,
                    "moon_phase_icon": moon_icon_path,
                }
            )

        return forecast
        
    def parse_open_meteo_forecast(self, daily_data, units, tz, is_day, lat):
        """
        Parse the daily forecast from Open-Meteo API and calculate moon phase and illumination using the local 'astral' library.
        """
        times = daily_data.get('time', [])
        weather_codes = daily_data.get('weathercode', [])
        temp_max = daily_data.get('temperature_2m_max', [])
        temp_min = daily_data.get('temperature_2m_min', [])
        if units == "standard":
            temp_max = [T + 273.15 for T in temp_max]
            temp_min = [T + 273.15 for T in temp_min]

        forecast = []

        for i in range(0, len(times)): 
            dt = datetime.fromisoformat(times[i]).replace(tzinfo=timezone.utc).astimezone(tz)
            day_label = dt.strftime("%a")

            code = weather_codes[i] if i < len(weather_codes) else 0
            weather_icon = self.map_weather_code_to_icon(code, is_day=1)
            weather_icon_path = self.get_plugin_dir(f"icons/{weather_icon}.png")

            timestamp = int(dt.replace(hour=12, minute=0, second=0).timestamp())
            target_date: date = dt.date() + timedelta(days=1)

            try:
                phase_age = moon.phase(target_date)
                phase_name_north_hemi = get_moon_phase_name(phase_age)
                LUNAR_CYCLE_DAYS = 29.530588853
                phase_fraction = phase_age / LUNAR_CYCLE_DAYS
                illum_pct = (1 - math.cos(2 * math.pi * phase_fraction)) / 2 * 100
            except Exception as e:
                logger.error(f"Error calculating moon phase for {target_date}: {e}")
                illum_pct = 0
                phase_name_north_hemi = "newmoon"
            moon_icon_path = self.get_moon_phase_icon_path(phase_name_north_hemi, lat)

            forecast.append({
                "day": day_label,
                "high": int(temp_max[i]) if i < len(temp_max) else 0,
                "low": int(temp_min[i]) if i < len(temp_min) else 0,
                "icon": weather_icon_path,
                "moon_phase_pct": f"{illum_pct:.0f}",
                "moon_phase_icon": moon_icon_path
            })

        return forecast




    def parse_hourly(self, hourly_forecast, tz, time_format, units, daily_forecast):
        hourly = []
        icon_codes_to_preserve = ["01", "02", "10"]
        
        sun_map = {}
        for day in daily_forecast:
            day_date = datetime.fromtimestamp(day['dt'], tz=timezone.utc).astimezone(tz).date()
            sun_map[day_date] = (day['sunrise'], day['sunset'])
        
        for hour in hourly_forecast[:24]:
            dt_epoch = hour.get('dt')
            dt = datetime.fromtimestamp(dt_epoch, tz=timezone.utc).astimezone(tz)
            rain_mm = hour.get("rain", {}).get("1h", 0.0)
            snow_mm = hour.get("snow", {}).get("1h", 0.0)
            total_precip_mm = rain_mm + snow_mm
            sunrise, sunset = sun_map.get(dt.date(), (0, 0))
        
            is_day = sunrise <= dt_epoch < sunset
            suffix = 'd' if is_day else 'n'
        
            raw_icon = hour.get("weather", [{}])[0].get("icon", "01d")
            icon_base = raw_icon[:2]
            icon_name = f"{icon_base}{suffix}" if icon_base in icon_codes_to_preserve else f"{icon_base}d"
            
            if units == "imperial":
                precip_value = total_precip_mm / 25.4
            else:
                precip_value = total_precip_mm 
            hour_forecast = {
                "time": self.format_time(dt, time_format, hour_only=True),
                "temperature": int(hour.get("temp")),
                "precipitation": hour.get("pop"),
                "rain": round(precip_value, 2),
                "icon": self.get_plugin_dir(f'icons/{icon_name}.png')
            }
            hourly.append(hour_forecast)
        return hourly

    def parse_open_meteo_hourly(self, hourly_data, units, tz, time_format, sunrises, sunsets):
        hourly = []
        times = hourly_data.get('time', [])
        temperatures = hourly_data.get('temperature_2m', [])
        if units == "standard":
            temperatures = [temperature + 273.15 for temperature in temperatures]
        precipitation_probabilities = hourly_data.get('precipitation_probability', [])
        rain = hourly_data.get('precipitation', [])
        codes = hourly_data.get('weather_code', [])
        
        sun_map = {}
        for sr_s, ss_s in zip(sunrises, sunsets):
            sr_dt = datetime.fromisoformat(sr_s).astimezone(tz)
            ss_dt = datetime.fromisoformat(ss_s).astimezone(tz)
            sun_map[sr_dt.date()] = (sr_dt, ss_dt)
        
        current_time_in_tz = datetime.now(tz)
        start_index = 0
        for i, time_str in enumerate(times):
            try:
                dt_hourly = datetime.fromisoformat(time_str).astimezone(tz)
                if dt_hourly.date() == current_time_in_tz.date() and dt_hourly.hour >= current_time_in_tz.hour:
                    start_index = i
                    break
                if dt_hourly.date() > current_time_in_tz.date():
                    break
            except ValueError:
                logger.warning(f"Could not parse time string {time_str} in hourly data.")
                continue

        sliced_times = times[start_index:]
        sliced_temperatures = temperatures[start_index:]
        sliced_precipitation_probabilities = precipitation_probabilities[start_index:]
        sliced_rain = rain[start_index:]
        sliced_codes = codes[start_index:]

        for i in range(min(24, len(sliced_times))):
            dt = datetime.fromisoformat(sliced_times[i]).astimezone(tz)
            sunrise, sunset = sun_map.get(dt.date(), (None, None))
            is_day = 0
            if sunrise and sunset:
                is_day = 1 if sunrise <= dt < sunset else 0
            code = sliced_codes[i] if i < len(sliced_codes) else 0
            icon_name = self.map_weather_code_to_icon(code, is_day)
            hour_forecast = {
                "time": self.format_time(dt, time_format, True),
                "temperature": int(sliced_temperatures[i]) if i < len(sliced_temperatures) else 0,
                "precipitation": (sliced_precipitation_probabilities[i] / 100) if i < len(sliced_precipitation_probabilities) else 0,
                "rain": (sliced_rain[i]) if i < len(sliced_rain) else 0,
                "icon": self.get_plugin_dir(f"icons/{icon_name}.png")
            }
            hourly.append(hour_forecast)
        return hourly

    def parse_data_points(self, weather, air_quality, tz, units, time_format):
        data_points = []
        sunrise_epoch = weather.get('current', {}).get("sunrise")

        if sunrise_epoch:
            sunrise_dt = datetime.fromtimestamp(sunrise_epoch, tz=timezone.utc).astimezone(tz)
            data_points.append({
                "label": "Sunrise",
                "measurement": self.format_time(sunrise_dt, time_format, include_am_pm=False),
                "unit": "" if time_format == "24h" else sunrise_dt.strftime('%p'),
                "icon": self.get_plugin_dir('icons/sunrise.png')
            })
        else:
            logger.error(f"Sunrise not found in OpenWeatherMap response, this is expected for polar areas in midnight sun and polar night periods.")

        sunset_epoch = weather.get('current', {}).get("sunset")
        if sunset_epoch:
            sunset_dt = datetime.fromtimestamp(sunset_epoch, tz=timezone.utc).astimezone(tz)
            data_points.append({
                "label": "Sunset",
                "measurement": self.format_time(sunset_dt, time_format, include_am_pm=False),
                "unit": "" if time_format == "24h" else sunset_dt.strftime('%p'),
                "icon": self.get_plugin_dir('icons/sunset.png')
            })
        else:
            logger.error(f"Sunset not found in OpenWeatherMap response, this is expected for polar areas in midnight sun and polar night periods.")

        wind_deg = weather.get('current', {}).get("wind_deg", 0)
        wind_arrow = self.get_wind_arrow(wind_deg)
        data_points.append({
            "label": "Wind",
            "measurement": weather.get('current', {}).get("wind_speed"),
            "unit": UNITS[units]["speed"],
            "icon": self.get_plugin_dir('icons/wind.png'),
            "arrow": wind_arrow
        })

        data_points.append({
            "label": "Humidity",
            "measurement": weather.get('current', {}).get("humidity"),
            "unit": '%',
            "icon": self.get_plugin_dir('icons/humidity.png')
        })

        data_points.append({
            "label": "Pressure",
            "measurement": weather.get('current', {}).get("pressure"),
            "unit": 'hPa',
            "icon": self.get_plugin_dir('icons/pressure.png')
        })

        data_points.append({
            "label": "UV Index",
            "measurement": weather.get('current', {}).get("uvi"),
            "unit": '',
            "icon": self.get_plugin_dir('icons/uvi.png')
        })

        visibility = weather.get('current', {}).get("visibility")
        if units == "imperial":
            # convert from m to mi
            visibility /= 1609.
            at_max_visibility = visibility >= 6.2
        else:
            # convert from m to km
            visibility /= 1000.
            at_max_visibility = visibility >= 10
        visibility_str = f"{visibility:.1f}"
        if at_max_visibility:
            visibility_str = u"\u2265" + visibility_str
        data_points.append({
            "label": "Visibility",
            "measurement": visibility_str,
            "unit": UNITS[units]["distance"],
            "icon": self.get_plugin_dir('icons/visibility.png')
        })

        aqi = air_quality.get('list', [])[0].get("main", {}).get("aqi")
        data_points.append({
            "label": "Air Quality",
            "measurement": aqi,
            "unit": ["Good", "Fair", "Moderate", "Poor", "Very Poor"][int(aqi)-1],
            "icon": self.get_plugin_dir('icons/aqi.png')
        })

        return data_points

    def parse_open_meteo_data_points(self, weather_data, aqi_data, units, tz, time_format):
        """Parses current data points from Open-Meteo API response."""
        data_points = []
        daily_data = weather_data.get('daily', {})
        current_data = weather_data.get('current', {})
        hourly_data = weather_data.get('hourly', {})

        current_time = datetime.now(tz)

        # Sunrise
        sunrise_times = daily_data.get('sunrise', [])
        if sunrise_times:
            sunrise_dt = datetime.fromisoformat(sunrise_times[0]).astimezone(tz)
            data_points.append({
                "label": "Sunrise",
                "measurement": self.format_time(sunrise_dt, time_format, include_am_pm=False),
                "unit": "" if time_format == "24h" else sunrise_dt.strftime('%p'),
                "icon": self.get_plugin_dir('icons/sunrise.png')
            })
        else:
            logger.error(f"Sunrise not found in Open-Meteo response, this is expected for polar areas in midnight sun and polar night periods.")

        # Sunset
        sunset_times = daily_data.get('sunset', [])
        if sunset_times:
            sunset_dt = datetime.fromisoformat(sunset_times[0]).astimezone(tz)
            data_points.append({
                "label": "Sunset",
                "measurement": self.format_time(sunset_dt, time_format, include_am_pm=False),
                "unit": "" if time_format == "24h" else sunset_dt.strftime('%p'),
                "icon": self.get_plugin_dir('icons/sunset.png')
            })
        else:
            logger.error(f"Sunset not found in Open-Meteo response, this is expected for polar areas in midnight sun and polar night periods.")

        # Wind
        wind_speed = current_data.get("windspeed", 0)
        wind_deg = current_data.get("winddirection", 0)
        wind_arrow = self.get_wind_arrow(wind_deg)
        wind_unit = UNITS[units]["speed"]
        data_points.append({
            "label": "Wind", "measurement": wind_speed, "unit": wind_unit,
            "icon": self.get_plugin_dir('icons/wind.png'), "arrow": wind_arrow
        })

        # Humidity
        current_humidity = "N/A"
        humidity_hourly_times = hourly_data.get('time', [])
        humidity_values = hourly_data.get('relative_humidity_2m', [])
        for i, time_str in enumerate(humidity_hourly_times):
            try:
                if datetime.fromisoformat(time_str).astimezone(tz).hour == current_time.hour:
                    current_humidity = int(humidity_values[i])
                    break
            except ValueError:
                logger.warning(f"Could not parse time string {time_str} for humidity.")
                continue
        data_points.append({
            "label": "Humidity", "measurement": current_humidity, "unit": '%',
            "icon": self.get_plugin_dir('icons/humidity.png')
        })

        # Pressure
        current_pressure = "N/A"
        pressure_hourly_times = hourly_data.get('time', [])
        pressure_values = hourly_data.get('surface_pressure', [])
        for i, time_str in enumerate(pressure_hourly_times):
            try:
                if datetime.fromisoformat(time_str).astimezone(tz).hour == current_time.hour:
                    current_pressure = int(pressure_values[i])
                    break
            except ValueError:
                logger.warning(f"Could not parse time string {time_str} for pressure.")
                continue
        data_points.append({
            "label": "Pressure", "measurement": current_pressure, "unit": 'hPa',
            "icon": self.get_plugin_dir('icons/pressure.png')
        })

        # UV Index
        uv_index_hourly_times = aqi_data.get('hourly', {}).get('time', [])
        uv_index_values = aqi_data.get('hourly', {}).get('uv_index', [])
        current_uv_index = "N/A"
        for i, time_str in enumerate(uv_index_hourly_times):
            try:
                if datetime.fromisoformat(time_str).astimezone(tz).hour == current_time.hour:
                    current_uv_index = uv_index_values[i]
                    break
            except ValueError:
                logger.warning(f"Could not parse time string {time_str} for UV Index.")
                continue
        data_points.append({
            "label": "UV Index", "measurement": current_uv_index, "unit": '',
            "icon": self.get_plugin_dir('icons/uvi.png')
        })

        # Visibility
        current_visibility = "N/A"
        visibility_hourly_times = hourly_data.get('time', [])
        visibility_values = hourly_data.get('visibility', [])
        if units == "imperial":
            visibility_conversion = 1/5280.     # ft to mi
            visibility_max = 6.2                # mi
        else:
            visibility_conversion = 0.001       # m to km
            visibility_max = 10.                # km
        for i, time_str in enumerate(visibility_hourly_times):
            try:
                if datetime.fromisoformat(time_str).astimezone(tz).hour == current_time.hour:
                    current_visibility = visibility_values[i]*visibility_conversion
                    at_max_visibility = current_visibility >= visibility_max
                    break
            except ValueError:
                logger.warning(f"Could not parse time string {time_str} for visibility.")
                continue
        visibility_str = f"{current_visibility:.1f}"
        if at_max_visibility:
            visibility_str = u"\u2265" + visibility_str
        data_points.append({
            "label": "Visibility", 
            "measurement": visibility_str, 
            "unit": UNITS[units]["distance"],
            "icon": self.get_plugin_dir('icons/visibility.png')
        })

        # Air Quality
        aqi_hourly_times = aqi_data.get('hourly', {}).get('time', [])
        aqi_values = aqi_data.get('hourly', {}).get('european_aqi', [])
        current_aqi = "N/A"
        for i, time_str in enumerate(aqi_hourly_times):
            try:
                if datetime.fromisoformat(time_str).astimezone(tz).hour == current_time.hour:
                    current_aqi = round(aqi_values[i], 1)
                    break
            except ValueError:
                logger.warning(f"Could not parse time string {time_str} for AQI.")
                continue
        scale = ""
        if current_aqi and current_aqi != "N/A":
            scale = ["Good","Fair","Moderate","Poor","Very Poor","Ext Poor"][min(current_aqi//20,5)]
        data_points.append({
            "label": "Air Quality", "measurement": current_aqi,
            "unit": scale, "icon": self.get_plugin_dir('icons/aqi.png')
        })

        return data_points

    def get_wind_arrow(self, wind_deg: float) -> str:
        DIRECTIONS = [
            ("↓", 22.5),    # North (N)
            ("↙", 67.5),    # North-East (NE)
            ("←", 112.5),   # East (E)
            ("↖", 157.5),   # South-East (SE)
            ("↑", 202.5),   # South (S)
            ("↗", 247.5),   # South-West (SW)
            ("→", 292.5),   # West (W)
            ("↘", 337.5),   # North-West (NW)
            ("↓", 360.0)    # Wrap back to North
        ]
        wind_deg = wind_deg % 360
        for arrow, upper_bound in DIRECTIONS:
            if wind_deg < upper_bound:
                return arrow

        return "↑"

    def get_weather_data(self, api_key, units, lat, long):
        url = WEATHER_URL.format(lat=lat, long=long, units=units, api_key=api_key)
        response = requests.get(url, timeout=30)
        if not 200 <= response.status_code < 300:
            logger.error(f"Failed to retrieve weather data: {response.content}")
            raise RuntimeError("Failed to retrieve weather data.")

        return response.json()

    def get_air_quality(self, api_key, lat, long):
        url = AIR_QUALITY_URL.format(lat=lat, long=long, api_key=api_key)
        response = requests.get(url, timeout=30)

        if not 200 <= response.status_code < 300:
            logger.error(f"Failed to get air quality data: {response.content}")
            raise RuntimeError("Failed to retrieve air quality data.")

        return response.json()

    def get_location(self, api_key, lat, long):
        url = GEOCODING_URL.format(lat=lat, long=long, api_key=api_key)
        response = requests.get(url, timeout=30)

        if not 200 <= response.status_code < 300:
            logger.error(f"Failed to get location: {response.content}")
            raise RuntimeError("Failed to retrieve location.")

        location_data = response.json()[0]
        location_str = f"{location_data.get('name')}, {location_data.get('state', location_data.get('country'))}"

        return location_str

    def get_open_meteo_data(self, lat, long, units, forecast_days):
        unit_params = OPEN_METEO_UNIT_PARAMS[units]
        url = OPEN_METEO_FORECAST_URL.format(lat=lat, long=long, forecast_days=forecast_days) + f"&{unit_params}"
        response = requests.get(url, timeout=30)

        if not 200 <= response.status_code < 300:
            logger.error(f"Failed to retrieve Open-Meteo weather data: {response.content}")
            raise RuntimeError("Failed to retrieve Open-Meteo weather data.")
        
        return response.json()

    def get_open_meteo_air_quality(self, lat, long):
        url = OPEN_METEO_AIR_QUALITY_URL.format(lat=lat, long=long)
        response = requests.get(url, timeout=30)
        if not 200 <= response.status_code < 300:
            logger.error(f"Failed to retrieve Open-Meteo air quality data: {response.content}")
            raise RuntimeError("Failed to retrieve Open-Meteo air quality data.")
        
        return response.json()
    
    def normalize_county_name(self, county):
        """Normalizes Taiwan county name and resolves common aliases."""
        if not county:
            return '臺北市'
        c = county.replace('台北', '臺北').replace('台中', '臺中').replace('台南', '臺南').replace('台東', '臺東')
        for k in CWA_COUNTY_DATASETS:
            if k in c or c in k:
                return k
        return '臺北市'

    def get_nearest_station(self, lat, lon):
        """Finds nearest active weather station using station.geojson with in-memory caching."""
        if self._stations_cache is None:
            geojson_path = os.path.join(self.get_plugin_dir('shp/station.geojson'))
            if os.path.exists(geojson_path):
                try:
                    with open(geojson_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self._stations_cache = data.get('features', [])
                except Exception as e:
                    logger.error(f"Error loading station.geojson: {e}")
                    self._stations_cache = []
            else:
                self._stations_cache = []

        best_dist = float('inf')
        best_station = None
        for feat in self._stations_cache:
            props = feat.get('properties', {})
            # Skip decommissioned stations
            if props.get('撤站日期'):
                continue
            coords = feat.get('geometry', {}).get('coordinates', [])
            if len(coords) >= 2:
                # coords: [lon, lat]
                d = (coords[1] - lat)**2 + (coords[0] - lon)**2
                if d < best_dist:
                    best_dist = d
                    best_station = props
        return best_station

    def get_cwa_dataset(self, api_key, dataset_id, location_name=None):
        """Fetches dataset from CWA datastore API."""
        url = f"{CWA_BASE_URL}/{dataset_id}"
        params = {
            "Authorization": api_key,
            "format": "JSON"
        }
        if location_name:
            params["LocationName"] = location_name

        response = requests.get(url, params=params, timeout=30)
        if not 200 <= response.status_code < 300:
            logger.error(f"Failed to retrieve CWA dataset {dataset_id}: {response.content}")
            raise RuntimeError(f"Failed to retrieve CWA dataset {dataset_id}")
        return response.json()

    def get_cwa_station_observation(self, api_key, station_id=None):
        """Fetches station observation data from CWA O-A0001-001."""
        url = f"{CWA_BASE_URL}/O-A0001-001"
        params = {
            "Authorization": api_key,
            "format": "JSON"
        }
        if station_id:
            params["StationId"] = station_id

        response = requests.get(url, params=params, timeout=30)
        if not 200 <= response.status_code < 300:
            logger.warning(f"Failed to retrieve CWA station observation: {response.content}")
            return None
        return response.json()

    def get_cwa_or_moe_air_quality(self, moe_api, county, lat, lon):
        """Retrieves air quality data from MOENV or falls back to Open-Meteo."""
        if moe_api:
            try:
                response = requests.get(
                    MOENV_AQI_URL,
                    params={"api_key": moe_api, "limit": 1000, "sort": "ImportDate desc", "format": "json"},
                    timeout=15
                )
                if 200 <= response.status_code < 300:
                    data = response.json()
                    records = data.get("records", [])
                    # Match by county
                    for rec in records:
                        if rec.get("county") and (rec.get("county") in county or county in rec.get("county")):
                            aqi_str = rec.get("aqi")
                            if aqi_str and aqi_str.isdigit():
                                return {"aqi": int(aqi_str), "status": rec.get("status", "")}
            except Exception as e:
                logger.warning(f"Failed to fetch MOENV AQI data: {e}")

        # Fallback to Open-Meteo Air Quality
        try:
            return self.get_open_meteo_air_quality(lat, lon)
        except Exception as e:
            logger.warning(f"Failed to fetch Open-Meteo AQI fallback: {e}")
            return {}

    def map_cwa_weather_code_to_icon(self, code, text="", is_day=1):
        """Maps CWA weather code (01-42) or Chinese weather description to icon name."""
        try:
            code_num = int(code)
        except (ValueError, TypeError):
            code_num = None

        icon = "01d"
        if code_num is not None:
            if code_num in [1]:
                icon = "01d"
            elif code_num in [2]:
                icon = "022d"
            elif code_num in [3]:
                icon = "02d"
            elif code_num in [4, 5, 6]:
                icon = "02d"
            elif code_num in [7]:
                icon = "04d"
            elif code_num in [8, 9, 10, 11, 12, 13, 14, 19, 20, 21, 22]:
                icon = "10d"
            elif code_num in [15, 16, 17, 18, 23, 24, 25, 26, 27, 28, 33, 34, 35, 36]:
                icon = "11d"
            elif code_num in [31, 32, 38, 39]:
                icon = "50d"
            elif code_num in [37, 41, 42]:
                icon = "13d"
        elif text:
            if "雷" in text:
                icon = "11d"
            elif "雪" in text or "雹" in text:
                icon = "13d"
            elif "雨" in text:
                icon = "10d"
            elif "霧" in text:
                icon = "50d"
            elif "陰" in text:
                icon = "04d"
            elif "多雲" in text:
                icon = "02d"
            elif "晴" in text:
                icon = "01d"

        if is_day == 0:
            if icon == "01d":
                icon = "01n"
            elif icon == "022d":
                icon = "022n"
            elif icon == "02d":
                icon = "02n"
            elif icon == "10d":
                icon = "10n"

        return icon

    def get_and_parse_cwa_data(self, cwa_api, moe_api, county, district, lat, long, units, tz, time_format, settings):
        """Fetches CWA forecast & observation data and parses into template parameters."""
        normalized_county = self.normalize_county_name(county)
        dataset_info = CWA_COUNTY_DATASETS.get(normalized_county, CWA_COUNTY_DATASETS['臺北市'])

        # 1. Fetch 3-day forecast (3-hour intervals)
        forecast_3_day_data = self.get_cwa_dataset(cwa_api, dataset_info['3_day'], district)

        # 2. Fetch 7-day forecast (daily intervals)
        forecast_7_day_data = self.get_cwa_dataset(cwa_api, dataset_info['7_day'], district)

        # 3. Fetch station observation
        nearest_station = self.get_nearest_station(lat, long)
        station_id = nearest_station.get('站號') if nearest_station else None
        current_station_data = self.get_cwa_station_observation(cwa_api, station_id) if station_id else None

        # 4. Fetch air quality
        aqi_data = self.get_cwa_or_moe_air_quality(moe_api, normalized_county, lat, long)

        # 5. Parse and assemble
        now = datetime.now(tz)

        # Helper to extract location dictionary
        def extract_location(records):
            locs = records.get("locations") or records.get("Locations") or []
            if not locs:
                return {}
            loc_list = locs[0].get("location") or locs[0].get("Location") or []
            if not loc_list:
                return {}
            if district:
                for loc in loc_list:
                    name = loc.get("locationName") or loc.get("LocationName") or ""
                    if name == district or district in name or name in district:
                        return loc
            return loc_list[0]

        loc_3d = extract_location(forecast_3_day_data.get("records", {}))
        el_map_3d = {el.get("elementName"): el.get("time", []) for el in loc_3d.get("weatherElement", [])}

        loc_7d = extract_location(forecast_7_day_data.get("records", {}))
        el_map_7d = {el.get("elementName"): el.get("time", []) for el in loc_7d.get("weatherElement", [])}

        station_elem = {}
        stations = current_station_data.get("records", {}).get("Station", []) if current_station_data else []
        if stations:
            station_elem = stations[0].get("WeatherElement", {})

        # Sun times via Astral
        loc_info = LocationInfo(latitude=lat, longitude=long)
        try:
            s = sun(loc_info.observer, date=now.date(), tzinfo=tz)
            sunrise_dt = s['sunrise']
            sunset_dt = s['sunset']
        except Exception:
            sunrise_dt = now.replace(hour=6, minute=0, second=0)
            sunset_dt = now.replace(hour=18, minute=0, second=0)

        is_day = 1 if sunrise_dt <= now < sunset_dt else 0

        def safe_float(val, min_valid=-90):
            if val is None:
                return None
            try:
                f = float(val)
                return None if f <= min_valid else f
            except (ValueError, TypeError):
                return None

        def convert_temp(celsius):
            if celsius is None:
                return 0
            if units == "imperial":
                return round(celsius * 9 / 5 + 32)
            elif units == "standard":
                return round(celsius + 273.15)
            return round(celsius)

        def convert_speed(ms):
            if ms is None:
                return 0
            if units == "imperial":
                return round(ms * 2.23694, 1)
            return round(ms, 1)

        def extract_wx(val_list):
            text, code = "", ""
            for item in val_list:
                if not isinstance(item, dict):
                    continue
                if "weatherCode" in item:
                    code = str(item["weatherCode"])
                measures = item.get("measures", "")
                val = item.get("value", "")
                if "代碼" in measures or "code" in measures.lower():
                    code = str(val)
                elif "現象" in measures:
                    text = str(val)
                elif not text:
                    text = str(val)
            if not code and len(val_list) > 1 and str(val_list[1].get("value", "")).isdigit():
                code = str(val_list[1]["value"])
            return text, code

        # Current temperature & condition
        st_temp = safe_float(station_elem.get("AirTemperature"))
        st_humidity = safe_float(station_elem.get("RelativeHumidity"))
        st_pressure = safe_float(station_elem.get("AirPressure"))
        st_wind_speed = safe_float(station_elem.get("WindSpeed"))
        st_wind_deg = safe_float(station_elem.get("WindDirection"), min_valid=-1)
        st_weather_text = station_elem.get("Weather", "")

        fc_temp_slot = el_map_3d.get("溫度", [{}])[0].get("elementValue", [{}])[0].get("value") if el_map_3d.get("溫度") else None
        fc_temp = safe_float(fc_temp_slot)

        fc_at_slot = el_map_3d.get("體感溫度", [{}])[0].get("elementValue", [{}])[0].get("value") if el_map_3d.get("體感溫度") else None
        fc_at = safe_float(fc_at_slot)

        fc_wx_list = el_map_3d.get("天氣現象", [{}])[0].get("elementValue", []) if el_map_3d.get("天氣現象") else []
        fc_wx_text, fc_wx_code = extract_wx(fc_wx_list)

        current_celsius = st_temp if st_temp is not None else (fc_temp if fc_temp is not None else 25.0)
        current_temp_val = convert_temp(current_celsius)

        feels_like_celsius = fc_at if fc_at is not None else current_celsius
        feels_like_val = convert_temp(feels_like_celsius)

        current_icon = self.map_cwa_weather_code_to_icon(fc_wx_code, st_weather_text or fc_wx_text, is_day)

        # 6. Daily forecast
        daily_groups = {}
        for t_item in el_map_7d.get("最高溫度", []):
            st_str = t_item.get("startTime", "")
            if not st_str: continue
            d_val = datetime.fromisoformat(st_str).astimezone(tz).date()
            v = safe_float(t_item.get("elementValue", [{}])[0].get("value"))
            if v is not None:
                if d_val not in daily_groups: daily_groups[d_val] = {}
                daily_groups[d_val]["high"] = max(daily_groups[d_val].get("high", -999), v)

        for t_item in el_map_7d.get("最低溫度", []):
            st_str = t_item.get("startTime", "")
            if not st_str: continue
            d_val = datetime.fromisoformat(st_str).astimezone(tz).date()
            v = safe_float(t_item.get("elementValue", [{}])[0].get("value"))
            if v is not None:
                if d_val not in daily_groups: daily_groups[d_val] = {}
                daily_groups[d_val]["low"] = min(daily_groups[d_val].get("low", 999), v)

        for t_item in el_map_7d.get("天氣現象", []):
            st_str = t_item.get("startTime", "")
            if not st_str: continue
            dt_val = datetime.fromisoformat(st_str).astimezone(tz)
            d_val = dt_val.date()
            txt, code = extract_wx(t_item.get("elementValue", []))
            if d_val not in daily_groups: daily_groups[d_val] = {}
            if 6 <= dt_val.hour < 18 or "icon" not in daily_groups[d_val]:
                daily_groups[d_val]["icon"] = self.map_cwa_weather_code_to_icon(code, txt, is_day=1)

        today_uvi = "N/A"
        for t_item in el_map_7d.get("紫外線指數", []):
            st_str = t_item.get("startTime", "")
            if not st_str: continue
            dt_val = datetime.fromisoformat(st_str).astimezone(tz)
            if dt_val.date() == now.date():
                today_uvi = t_item.get("elementValue", [{}])[0].get("value", "N/A")
                break

        forecast_list = []
        sorted_dates = sorted(daily_groups.keys())
        if not sorted_dates:
            sorted_dates = [now.date() + timedelta(days=i) for i in range(8)]

        for d_val in sorted_dates:
            g = daily_groups.get(d_val, {})
            d_high = convert_temp(g.get("high", current_celsius + 3))
            d_low = convert_temp(g.get("low", current_celsius - 3))
            d_icon = g.get("icon", "01d")

            try:
                phase_age = moon.phase(d_val)
                phase_name = get_moon_phase_name(phase_age)
                LUNAR_CYCLE = 29.530588853
                illum_pct = (1 - math.cos(2 * math.pi * (phase_age / LUNAR_CYCLE))) / 2 * 100
            except Exception:
                phase_name = "newmoon"
                illum_pct = 0

            forecast_list.append({
                "day": d_val.strftime("%a"),
                "high": int(d_high),
                "low": int(d_low),
                "icon": self.get_plugin_dir(f"icons/{d_icon}.png"),
                "moon_phase_pct": f"{illum_pct:.0f}",
                "moon_phase_icon": self.get_moon_phase_icon_path(phase_name, lat)
            })

        while len(forecast_list) < 8:
            last_d = now.date() + timedelta(days=len(forecast_list))
            forecast_list.append({
                "day": last_d.strftime("%a"),
                "high": int(current_temp_val + 2),
                "low": int(current_temp_val - 2),
                "icon": self.get_plugin_dir("icons/01d.png"),
                "moon_phase_pct": "50",
                "moon_phase_icon": self.get_moon_phase_icon_path("fullmoon", lat)
            })

        # 7. Hourly forecast (24 hours)
        raw_hourly = []
        temp_slots = el_map_3d.get("溫度", [])
        pop_slots = el_map_3d.get("3小時降雨機率", [])
        wx_slots = el_map_3d.get("天氣現象", [])

        for i, t_slot in enumerate(temp_slots):
            dt_str = t_slot.get("dataTime") or t_slot.get("startTime")
            if not dt_str: continue
            dt_pt = datetime.fromisoformat(dt_str).astimezone(tz)
            t_c = safe_float(t_slot.get("elementValue", [{}])[0].get("value"))

            pop_val = 0.0
            if i < len(pop_slots):
                pop_s = pop_slots[i].get("elementValue", [{}])[0].get("value")
                try:
                    pop_val = float(pop_s) / 100.0
                except (ValueError, TypeError):
                    pop_val = 0.0

            txt, code = "", ""
            if i < len(wx_slots):
                txt, code = extract_wx(wx_slots[i].get("elementValue", []))

            raw_hourly.append({
                "dt": dt_pt,
                "celsius": t_c if t_c is not None else current_celsius,
                "pop": pop_val,
                "wx_code": code,
                "wx_text": txt
            })

        hourly_forecast = []
        start_hour = now.replace(minute=0, second=0, microsecond=0)
        for h_offset in range(24):
            target_dt = start_hour + timedelta(hours=h_offset)
            best_pt = None
            min_diff = timedelta(days=999)
            for pt in raw_hourly:
                diff = abs(pt["dt"] - target_dt)
                if diff < min_diff:
                    min_diff = diff
                    best_pt = pt

            if best_pt:
                pt_celsius = best_pt["celsius"]
                pt_pop = best_pt["pop"]
                pt_code = best_pt["wx_code"]
                pt_txt = best_pt["wx_text"]
            else:
                pt_celsius = current_celsius
                pt_pop = 0.0
                pt_code = ""
                pt_txt = ""

            try:
                pt_s = sun(loc_info.observer, date=target_dt.date(), tzinfo=tz)
                pt_is_day = 1 if pt_s['sunrise'] <= target_dt < pt_s['sunset'] else 0
            except Exception:
                pt_is_day = 1 if 6 <= target_dt.hour < 18 else 0

            icon_name = self.map_cwa_weather_code_to_icon(pt_code, pt_txt, pt_is_day)
            temp_out = convert_temp(pt_celsius)

            hourly_forecast.append({
                "time": self.format_time(target_dt, time_format, hour_only=True),
                "temperature": int(temp_out),
                "precipitation": pt_pop,
                "rain": 0.0,
                "icon": self.get_plugin_dir(f"icons/{icon_name}.png")
            })

        # 8. Data Points
        data_points = []

        data_points.append({
            "label": "Sunrise",
            "measurement": self.format_time(sunrise_dt, time_format, include_am_pm=False),
            "unit": "" if time_format == "24h" else sunrise_dt.strftime('%p'),
            "icon": self.get_plugin_dir('icons/sunrise.png')
        })

        data_points.append({
            "label": "Sunset",
            "measurement": self.format_time(sunset_dt, time_format, include_am_pm=False),
            "unit": "" if time_format == "24h" else sunset_dt.strftime('%p'),
            "icon": self.get_plugin_dir('icons/sunset.png')
        })

        wind_spd = convert_speed(st_wind_speed if st_wind_speed is not None else 1.5)
        wind_arrow = self.get_wind_arrow(st_wind_deg if st_wind_deg is not None else 0)
        data_points.append({
            "label": "Wind",
            "measurement": wind_spd,
            "unit": UNITS[units]["speed"],
            "icon": self.get_plugin_dir('icons/wind.png'),
            "arrow": wind_arrow
        })

        hum_val = int(st_humidity) if st_humidity is not None else 70
        data_points.append({
            "label": "Humidity",
            "measurement": hum_val,
            "unit": "%",
            "icon": self.get_plugin_dir('icons/humidity.png')
        })

        press_val = round(st_pressure) if st_pressure is not None else 1013
        data_points.append({
            "label": "Pressure",
            "measurement": press_val,
            "unit": "hPa",
            "icon": self.get_plugin_dir('icons/pressure.png')
        })

        data_points.append({
            "label": "UV Index",
            "measurement": today_uvi,
            "unit": "",
            "icon": self.get_plugin_dir('icons/uvi.png')
        })

        vis_val = 10.0 if units != "imperial" else 6.2
        data_points.append({
            "label": "Visibility",
            "measurement": f"≥{vis_val:.1f}",
            "unit": UNITS[units]["distance"],
            "icon": self.get_plugin_dir('icons/visibility.png')
        })

        aqi_val = 35
        aqi_scale = "Good"
        if isinstance(aqi_data, dict):
            if "aqi" in aqi_data:
                aqi_val = aqi_data["aqi"]
                aqi_scale = aqi_data.get("status") or ["Good", "Fair", "Moderate", "Poor", "Very Poor", "Ext Poor"][min(int(aqi_val) // 20, 5)]
            elif "hourly" in aqi_data:
                aqi_list = aqi_data.get("hourly", {}).get("european_aqi", [])
                if aqi_list:
                    aqi_val = round(aqi_list[0], 1)
                    scales = ["Good", "Fair", "Moderate", "Poor", "Very Poor", "Ext Poor"]
                    aqi_scale = scales[min(int(aqi_val) // 20, 5)]

        data_points.append({
            "label": "Air Quality",
            "measurement": aqi_val,
            "unit": aqi_scale,
            "icon": self.get_plugin_dir('icons/aqi.png')
        })

        return {
            "current_date": now.strftime("%A, %B %d"),
            "current_day_icon": self.get_plugin_dir(f"icons/{current_icon}.png"),
            "current_temperature": str(round(current_temp_val)),
            "feels_like": str(round(feels_like_val)),
            "temperature_unit": UNITS[units]["temperature"],
            "units": units,
            "time_format": time_format,
            "forecast": forecast_list,
            "data_points": data_points,
            "hourly_forecast": hourly_forecast
        }

    def format_time(self, dt, time_format, hour_only=False, include_am_pm=True):
        """Format datetime based on 12h or 24h preference"""
        if time_format == "24h":
            return dt.strftime("%H:00" if hour_only else "%H:%M")
        
        if include_am_pm:
            fmt = "%I %p" if hour_only else "%I:%M %p"
        else:
            fmt = "%I" if hour_only else "%I:%M"

        return dt.strftime(fmt).lstrip("0")
    
    def parse_timezone(self, weatherdata):
        """Parse timezone from weather data"""
        if 'timezone' in weatherdata:
            logger.info(f"Using timezone from weather data: {weatherdata['timezone']}")
            return pytz.timezone(weatherdata['timezone'])
        else:
            logger.error("Failed to retrieve Timezone from weather data")
            raise RuntimeError("Timezone not found in weather data.")
