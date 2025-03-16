from typing import Dict, List, Any
import random
import math

class EnvironmentSystem:
    def __init__(self, world_grid: List[List[str]]):
        self.world_grid = world_grid
        
        # Time system with calendar
        self.time_of_day = 8.0  # Start at 8:00 AM (0.0 to 24.0)
        self.day = 1
        self.month = 3  # Start in March (1-12)
        self.year = 1
        self.time_scale = 0.05  # 0.05 means 1 real second = 0.05 game hours (20x slower than before)
        self.days_per_month = 30
        self.months_per_year = 12
        
        # Time zone configuration
        self.time_zones = 24  # 24 time zones across the world
        self.reference_longitude = 0  # Prime meridian (reference point for time)
        
        # Weather and seasons
        self.weather_conditions = {}  # Updated periodically
        self.season = self._get_season_from_month(self.month)  # Initial season based on month
        
        # Regional weather patterns
        self.terrain_weather_patterns = {
            'grassland': {'rain_chance': 0.3, 'temp_range': (15, 30)},
            'forest': {'rain_chance': 0.5, 'temp_range': (10, 25)},
            'desert': {'rain_chance': 0.05, 'temp_range': (25, 40)},
            'mountain': {'rain_chance': 0.2, 'temp_range': (-5, 15)},
            'aquatic': {'rain_chance': 0.4, 'temp_range': (0, 20)},
            # Add transition terrains
            'forest_edge': {'rain_chance': 0.4, 'temp_range': (12, 28)},
            'savanna': {'rain_chance': 0.2, 'temp_range': (20, 35)},
            'hills': {'rain_chance': 0.25, 'temp_range': (5, 25)},
            'wooded_hills': {'rain_chance': 0.35, 'temp_range': (5, 20)},
            'wetland': {'rain_chance': 0.6, 'temp_range': (10, 25)},
            'beach': {'rain_chance': 0.3, 'temp_range': (15, 35)}
        }

        # Environment effects by terrain type
        self.terrain_effects = {
            'grassland': {'movement_speed': 1.0, 'stamina_drain': 1.0, 'visibility': 1.0},
            'forest': {'movement_speed': 0.8, 'stamina_drain': 1.2, 'visibility': 0.7},
            'desert': {'movement_speed': 0.9, 'stamina_drain': 1.5, 'visibility': 1.2},
            'mountain': {'movement_speed': 0.7, 'stamina_drain': 1.4, 'visibility': 0.9},
            'aquatic': {'movement_speed': 0.6, 'stamina_drain': 1.3, 'visibility': 0.8},
            # Add transition terrains with blended effects
            'forest_edge': {'movement_speed': 0.9, 'stamina_drain': 1.1, 'visibility': 0.85},
            'savanna': {'movement_speed': 0.95, 'stamina_drain': 1.25, 'visibility': 1.1},
            'hills': {'movement_speed': 0.85, 'stamina_drain': 1.2, 'visibility': 1.0},
            'wooded_hills': {'movement_speed': 0.75, 'stamina_drain': 1.3, 'visibility': 0.8},
            'wetland': {'movement_speed': 0.7, 'stamina_drain': 1.2, 'visibility': 0.9},
            'beach': {'movement_speed': 0.8, 'stamina_drain': 1.3, 'visibility': 1.1}
        }

        # Month names for display
        self.month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # Initialize weather for each terrain type
        self._initialize_weather()

    def _get_season_from_month(self, month: int) -> str:
        """Determine season based on month (Northern Hemisphere)."""
        if 3 <= month <= 5:  # March to May
            return "Spring"
        elif 6 <= month <= 8:  # June to August
            return "Summer"
        elif 9 <= month <= 11:  # September to November
            return "Autumn"
        else:  # December, January, February
            return "Winter"

    def _initialize_weather(self) -> None:
        """Initialize weather conditions based on terrain-specific patterns."""
        for terrain, patterns in self.terrain_weather_patterns.items():
            # Apply seasonal adjustments to initial weather
            season_temp_modifier = self._get_season_temperature_modifier()
            
            base_temp = random.uniform(*patterns['temp_range'])
            adjusted_temp = base_temp + season_temp_modifier
            
            self.weather_conditions[terrain] = {
                'precipitation': random.uniform(0, patterns['rain_chance']),
                'temperature': adjusted_temp,
                'wind': random.uniform(0, 20)  # Default wind speed range
            }

    def _get_season_temperature_modifier(self) -> float:
        """Get temperature modifier based on current season."""
        return {
            'Summer': 5.0,
            'Winter': -5.0,
            'Spring': 0.0,
            'Autumn': 0.0
        }.get(self.season, 0.0)

    def update(self, dt: float) -> None:
        """Update environment state, including time of day, weather, and season."""
        # Update time of day with configurable time scale
        old_time = self.time_of_day
        self.time_of_day = (self.time_of_day + dt * self.time_scale) % 24.0
        
        # Check if a day has passed
        if old_time > self.time_of_day:  # We've wrapped around to a new day
            self._advance_day()
        
        # Update weather more frequently with more noticeable changes
        if random.random() < 0.1 * dt:  # Scale chance with dt
            self._update_weather()

    def _advance_day(self) -> None:
        """Advance to the next day and update calendar."""
        self.day += 1
        
        # Check if month has changed
        if self.day > self.days_per_month:
            self.day = 1
            self.month += 1
            
            # Check if year has changed
            if self.month > self.months_per_year:
                self.month = 1
                self.year += 1
            
            # Update season when month changes
            new_season = self._get_season_from_month(self.month)
            if new_season != self.season:
                self.season = new_season
                # Apply seasonal changes to weather
                self._apply_seasonal_weather_changes()

    def _apply_seasonal_weather_changes(self) -> None:
        """Apply seasonal changes to weather patterns."""
        season_temp_modifier = self._get_season_temperature_modifier()
        
        for terrain, weather in self.weather_conditions.items():
            patterns = self.terrain_weather_patterns[terrain]
            
            # Adjust base temperature for season
            base_temp = (patterns['temp_range'][0] + patterns['temp_range'][1]) / 2
            weather['temperature'] = base_temp + season_temp_modifier + random.uniform(-3.0, 3.0)
            
            # Adjust precipitation based on season
            if self.season == "Spring":
                weather['precipitation'] = min(1.0, patterns['rain_chance'] * 1.3)  # More rain in spring
            elif self.season == "Summer":
                if terrain in ['desert', 'savanna']:
                    weather['precipitation'] = patterns['rain_chance'] * 0.5  # Drier in summer for hot areas
                else:
                    weather['precipitation'] = patterns['rain_chance'] * 0.8
            elif self.season == "Autumn":
                weather['precipitation'] = patterns['rain_chance'] * 1.1  # Slightly more rain
            elif self.season == "Winter":
                if terrain in ['mountain', 'hills', 'wooded_hills']:
                    weather['precipitation'] = min(1.0, patterns['rain_chance'] * 1.2)  # More snow in mountains
                else:
                    weather['precipitation'] = patterns['rain_chance'] * 0.9

    def _update_weather(self) -> None:
        """Update weather conditions with more dramatic changes."""
        for terrain, current_weather in self.weather_conditions.items():
            patterns = self.terrain_weather_patterns[terrain]
            
            # More dramatic weather changes
            rain_delta = random.uniform(-0.2, 0.2)  # Increased from 0.01
            temp_delta = random.uniform(-2.0, 2.0)  # Increased from 0.5
            wind_delta = random.uniform(-3.0, 3.0)  # Increased from 1.0
            
            # Calculate new values with seasonal modifications
            season_temp_modifier = self._get_season_temperature_modifier()
            
            # Time of day temperature modifications
            time_temp_modifier = -5.0 if 0 <= self.time_of_day <= 6 else \
                               5.0 if 12 <= self.time_of_day <= 15 else 0.0
            
            new_weather = {
                'precipitation': max(0, min(1.0, current_weather['precipitation'] + rain_delta)),
                'temperature': max(patterns['temp_range'][0],
                                 min(patterns['temp_range'][1],
                                     current_weather['temperature'] + temp_delta + 
                                     time_temp_modifier)),
                'wind': max(0, min(40, current_weather['wind'] + wind_delta))
            }
            
            # Add weather events
            if random.random() < 0.05:  # 5% chance of weather events
                if self.season == 'Summer':
                    new_weather['temperature'] += random.uniform(2.0, 5.0)  # Heat wave
                elif self.season == 'Winter':
                    new_weather['temperature'] -= random.uniform(2.0, 5.0)  # Cold snap
                elif random.random() < 0.5:
                    new_weather['precipitation'] = min(1.0, new_weather['precipitation'] + 0.3)  # Storm
                else:
                    new_weather['wind'] = min(40, new_weather['wind'] + random.uniform(5.0, 10.0))  # Wind gust
            
            self.weather_conditions[terrain] = new_weather

    def get_environment_effects(self, tile_x: int, tile_y: int) -> Dict[str, float]:
        """Get current environmental effects for a specific tile with more impactful modifiers."""
        try:
            terrain_type = self.world_grid[tile_y][tile_x]
        except IndexError:
            return {'movement_speed': 1.0, 'stamina_drain': 1.0, 'visibility': 1.0}

        base_effects = self.terrain_effects.get(terrain_type, 
            {'movement_speed': 1.0, 'stamina_drain': 1.0, 'visibility': 1.0})
        weather = self.weather_conditions.get(terrain_type, 
            {'precipitation': 0, 'temperature': 20, 'wind': 0})

        # Apply more impactful weather modifications
        modified_effects = base_effects.copy()

        # Precipitation effects
        if weather['precipitation'] > 0.3:  # Lowered threshold
            modified_effects['movement_speed'] *= max(0.5, 1.0 - weather['precipitation'])
            modified_effects['visibility'] *= max(0.4, 1.0 - weather['precipitation'])

        # Temperature effects
        temp = weather['temperature']
        if temp > 30 or temp < 5:
            modified_effects['stamina_drain'] *= 1.5
            modified_effects['movement_speed'] *= 0.8
        
        # Wind effects
        if weather['wind'] > 15:  # Lowered threshold
            wind_factor = min(1.0, weather['wind'] / 40.0)
            modified_effects['movement_speed'] *= max(0.6, 1.0 - wind_factor)
            modified_effects['visibility'] *= max(0.7, 1.0 - wind_factor)

        # Time of day effects (more pronounced)
        hour = self.time_of_day
        if hour < 6 or hour > 18:  # Night time
            modified_effects['visibility'] *= 0.4  # Darker nights
            modified_effects['movement_speed'] *= 0.7  # Slower at night
        elif 6 <= hour < 8 or 16 <= hour <= 18:  # Dawn/Dusk
            modified_effects['visibility'] *= 0.7  # Reduced visibility during twilight

        # Seasonal effects
        if self.season == 'Winter':
            modified_effects['movement_speed'] *= 0.8
            modified_effects['stamina_drain'] *= 1.3
        elif self.season == 'Summer':
            modified_effects['stamina_drain'] *= 1.2

        return modified_effects
        
    def get_local_time(self, longitude: int) -> float:
        """
        Calculate local time based on longitude (x-coordinate).
        
        Args:
            longitude: The x-coordinate in the world grid (0 to WORLD_WIDTH-1)
            
        Returns:
            Local time of day (0.0 to 24.0)
        """
        # Calculate time zone offset (how many hours from prime meridian)
        # Map longitude to -12 to +12 hours range
        from src.map.map_generator import WORLD_WIDTH
        
        # Calculate the offset in hours
        # Each time zone is WORLD_WIDTH / time_zones tiles wide
        zone_width = WORLD_WIDTH / self.time_zones
        
        # Calculate which time zone this longitude is in
        time_zone = int(longitude / zone_width)
        
        # Calculate hours offset from reference meridian (0)
        # Map from 0-23 to -12 to +12 range
        if time_zone > self.time_zones / 2:
            hours_offset = time_zone - self.time_zones
        else:
            hours_offset = time_zone
            
        # Apply offset to base time
        local_time = (self.time_of_day + hours_offset) % 24.0
        
        return local_time
    
    def get_formatted_time(self, longitude: int = None) -> str:
        """Return a formatted time string (HH:MM) for the given longitude."""
        if longitude is not None:
            # Get local time for the specified longitude
            time_to_format = self.get_local_time(longitude)
        else:
            # Use global time if no longitude specified
            time_to_format = self.time_of_day
            
        hours = int(time_to_format)
        minutes = int((time_to_format % 1) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def get_formatted_date(self) -> str:
        """Return a formatted date string."""
        month_name = self.month_names[self.month - 1]
        return f"{month_name} {self.day}, Year {self.year}"
    
    def get_time_data(self, longitude: int = None) -> Dict[str, Any]:
        """Get complete time and calendar data for the given longitude."""
        if longitude is not None:
            local_time = self.get_local_time(longitude)
            formatted_time = self.get_formatted_time(longitude)
        else:
            local_time = self.time_of_day
            formatted_time = self.get_formatted_time()
            
        return {
            'time_of_day': local_time,
            'formatted_time': formatted_time,
            'day': self.day,
            'month': self.month,
            'month_name': self.month_names[self.month - 1],
            'year': self.year,
            'formatted_date': self.get_formatted_date(),
            'season': self.season,
            'time_scale': self.time_scale
        }
    
    def set_time_scale(self, scale: float) -> None:
        """Set the time scale factor (how fast time passes)."""
        self.time_scale = max(0.001, min(1.0, scale))  # Clamp between 0.001 and 1.0
