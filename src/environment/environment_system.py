from typing import Dict, List, Any
import random

class EnvironmentSystem:
    def __init__(self, world_grid: List[List[str]]):
        self.world_grid = world_grid
        self.time_of_day = 0.0  # 0.0 to 24.0
        self.weather_conditions = {}  # Updated periodically
        self.season = "Spring"  # Initial season
        
        # Regional weather patterns
        self.terrain_weather_patterns = {
            'grassland': {'rain_chance': 0.3, 'temp_range': (15, 30)},
            'forest': {'rain_chance': 0.5, 'temp_range': (10, 25)},
            'desert': {'rain_chance': 0.05, 'temp_range': (25, 40)},
            'mountain': {'rain_chance': 0.2, 'temp_range': (-5, 15)},
            'aquatic': {'rain_chance': 0.4, 'temp_range': (0, 20)}
        }

        # Environment effects by terrain type
        self.terrain_effects = {
            'grassland': {'movement_speed': 1.0, 'stamina_drain': 1.0, 'visibility': 1.0},
            'forest': {'movement_speed': 0.8, 'stamina_drain': 1.2, 'visibility': 0.7},
            'desert': {'movement_speed': 0.9, 'stamina_drain': 1.5, 'visibility': 1.2},
            'mountain': {'movement_speed': 0.7, 'stamina_drain': 1.4, 'visibility': 0.9},
            'aquatic': {'movement_speed': 0.6, 'stamina_drain': 1.3, 'visibility': 0.8}
        }

        # Initialize weather for each terrain type
        self._initialize_weather()

    def _initialize_weather(self) -> None:
        """Initialize weather conditions based on terrain-specific patterns."""
        for terrain, patterns in self.terrain_weather_patterns.items():
            self.weather_conditions[terrain] = {
                'precipitation': random.uniform(0, patterns['rain_chance']),
                'temperature': random.uniform(*patterns['temp_range']),
                'wind': random.uniform(0, 20)  # Default wind speed range
            }

    def update(self, dt: float) -> None:
        """Update environment state, including time of day, weather, and season."""
        # Update time of day (complete cycle every 24 real seconds)
        self.time_of_day = (self.time_of_day + dt) % 24.0

        # Update weather more frequently with more noticeable changes
        if random.random() < 0.1:  # 10% chance each update
            self._update_weather()
            
        # Update season based on time
        if self.time_of_day < 0.1:  # Near midnight
            self._update_season()

    def _update_weather(self) -> None:
        """Update weather conditions with more dramatic changes."""
        for terrain, current_weather in self.weather_conditions.items():
            patterns = self.terrain_weather_patterns[terrain]
            
            # More dramatic weather changes
            rain_delta = random.uniform(-0.2, 0.2)  # Increased from 0.01
            temp_delta = random.uniform(-2.0, 2.0)  # Increased from 0.5
            wind_delta = random.uniform(-3.0, 3.0)  # Increased from 1.0
            
            # Calculate new values with seasonal modifications
            season_temp_modifier = {
                'Summer': 5.0,
                'Winter': -5.0,
                'Spring': 0.0,
                'Autumn': 0.0
            }.get(self.season, 0.0)
            
            # Time of day temperature modifications
            time_temp_modifier = -5.0 if 0 <= self.time_of_day <= 6 else \
                               5.0 if 12 <= self.time_of_day <= 15 else 0.0
            
            new_weather = {
                'precipitation': max(0, min(1.0, current_weather['precipitation'] + rain_delta)),
                'temperature': max(patterns['temp_range'][0],
                                 min(patterns['temp_range'][1],
                                     current_weather['temperature'] + temp_delta + 
                                     season_temp_modifier + time_temp_modifier)),
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

    def _update_season(self) -> None:
        """Cycle through seasons and apply changes."""
        if self.time_of_day == 0:  # Assume season changes occur at midnight
            seasons = ["Spring", "Summer", "Autumn", "Winter"]
            current_index = seasons.index(self.season)
            self.season = seasons[(current_index + 1) % len(seasons)]

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
