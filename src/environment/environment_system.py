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

        # Periodically update weather and season
        self._update_weather()
        self._update_season()

    def _update_weather(self) -> None:
        """Gradually update weather conditions with continuity."""
        for terrain, current_weather in self.weather_conditions.items():
            patterns = self.terrain_weather_patterns[terrain]
            rain_delta = random.uniform(-0.01, 0.01)  # Smaller changes for readability
            temp_delta = random.uniform(-0.5, 0.5)  # Smaller changes for readability
            self.weather_conditions[terrain] = {
                'precipitation': max(0, min(patterns['rain_chance'], current_weather['precipitation'] + rain_delta)),
                'temperature': max(patterns['temp_range'][0], min(patterns['temp_range'][1], current_weather['temperature'] + temp_delta)),
                'wind': max(0, min(30, current_weather['wind'] + random.uniform(-1, 1)))  # Smaller changes for readability
            }

    def _update_season(self) -> None:
        """Cycle through seasons and apply changes."""
        if self.time_of_day == 0:  # Assume season changes occur at midnight
            seasons = ["Spring", "Summer", "Autumn", "Winter"]
            current_index = seasons.index(self.season)
            self.season = seasons[(current_index + 1) % len(seasons)]

    def get_environment_effects(self, tile_x: int, tile_y: int) -> Dict[str, float]:
        """Get current environmental effects for a specific tile."""
        try:
            terrain_type = self.world_grid[tile_y][tile_x]
        except IndexError:
            # Return default effects if coordinates are invalid
            return {'movement_speed': 1.0, 'stamina_drain': 1.0, 'visibility': 1.0}

        base_effects = self.terrain_effects.get(terrain_type, {'movement_speed': 1.0, 'stamina_drain': 1.0, 'visibility': 1.0})
        weather = self.weather_conditions.get(terrain_type, {'precipitation': 0, 'temperature': 20, 'wind': 0})

        # Apply weather modifications
        modified_effects = base_effects.copy()

        # Heavy rain reduces movement speed and visibility
        if weather['precipitation'] > 0.7:
            modified_effects['movement_speed'] *= 0.8
            modified_effects['visibility'] *= 0.6

        # Extreme temperatures increase stamina drain
        if weather['temperature'] > 35 or weather['temperature'] < 0:
            modified_effects['stamina_drain'] *= 1.3

        # Strong winds affect movement speed
        if weather['wind'] > 20:
            modified_effects['movement_speed'] *= 0.9

        # Time of day effects
        if self.time_of_day < 6 or self.time_of_day > 18:  # Night time
            modified_effects['visibility'] *= 0.6
            modified_effects['movement_speed'] *= 0.9

        return modified_effects
