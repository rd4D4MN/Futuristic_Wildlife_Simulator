import os
import sys
import pygame
import random
import pandas as pd
import math
from typing import List, Any, Dict
import time

# Import modules for map, entities, UI, and utilities
from map.map_generator import (
    get_spawn_points_by_terrain,
    resample_raster,
    load_land_shapefile,
    rasterize_land,
    generate_world_grid,
    tile_mapping,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    TILE_SIZE
)
from entities.animal import Animal
from entities.robot import Robot
from entities.team import Team
from ui.ui_manager import UIManager
from utils.helpers import generate_battle_story, generate_simulation_story
from combat.combat_manager import CombatManager
from events.event_manager import EventManager
from utils.resource_manager import ResourceManager
from environment.environment_system import EnvironmentSystem
from evolution.evolution_manager import EvolutionManager
from resources.resource_system import ResourceSystem
from resources.team_resources import TeamResourceExtension
from setup.game_setup import setup_player_robot, is_player_robot


class GameState:
    def __init__(self, screen_width: int, screen_height: int):
        """Initialize the game state."""
        # Debug and performance monitoring first
        self.debug_mode = False
        self.fps_history = []
        self.update_times = []
        self.draw_times = []

        # Spectator mode
        self.spectating = False
        self.spectated_robot_index = -1
        
        # Basic dimensions
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.width = WORLD_WIDTH * TILE_SIZE
        self.height = WORLD_HEIGHT * TILE_SIZE
        self.camera_x = 0
        self.camera_y = 0
        self.camera_speed = int(WORLD_WIDTH * TILE_SIZE / 100)  # Proportional to world size
        self.frame_count = 0
        self.running = True
        self.TILE_SIZE = TILE_SIZE  # Add TILE_SIZE as class attribute

        # Initialize pygame and screen
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Evolution Simulation")
        self.clock = pygame.time.Clock()
        self.ui_manager = UIManager(screen_width, screen_height)

        # Weather and environment visualization
        self.particles = []
        self.effect_overlays = self._create_effect_overlays()
        
        # Load map and terrain data
        self.resampled_raster, self.new_transform = resample_raster(
            "data/Natural_Earth/NE1_HR_LC/NE1_HR_LC.tif",
            WORLD_HEIGHT,
            WORLD_WIDTH,
            debug=self.debug_mode
        )
        self.land_gdf = load_land_shapefile("data/Natural_Earth/10m_physical/ne_10m_land.shp")
        self.land_mask = rasterize_land(
            self.land_gdf, (WORLD_HEIGHT, WORLD_WIDTH), self.new_transform
        )
        self.world_grid = self._initialize_world()

        # Load animal data
        self.processed_animals = pd.read_csv('data/processed_animals.csv')

        # Spawn entities
        self.animals = self._spawn_animals()
        self.robots = self._spawn_robots()
        self.teams = self._form_initial_teams()
        
        # Set up player's robot as first robot if not in spectator mode
        self.player_robot = None
        if not self.spectating:
            self.player_robot = self.robots[0] if self.robots else None
            if self.player_robot:
                self.spectated_robot_index = 0

        # Initialize managers
        self.combat_manager = CombatManager()
        self.event_manager = EventManager()
        self.resource_manager = ResourceManager.get_instance()
        self.environment_system = EnvironmentSystem(self.world_grid)
        self.evolution_manager = EvolutionManager(self.processed_animals)
        self.evolution_manager.world_grid = self.world_grid  # Add world grid reference

        # World data for UI
        self.world_data = {
            'width': WORLD_WIDTH,
            'height': WORLD_HEIGHT,
            'layout': self.world_grid,
            'colors': tile_mapping,
            'pixel_width': WORLD_WIDTH * TILE_SIZE,
            'pixel_height': WORLD_HEIGHT * TILE_SIZE
        }

        # Initialize resource system
        self.resource_system = ResourceSystem(self.world_grid)

    def _initialize_world(self) -> List[List[str]]:
        """Initialize the world grid."""
        try:
            world_grid, _ = generate_world_grid(
                raster_data=self.resampled_raster,
                transform=self.new_transform,
                land_mask=self.land_mask,
                color_classification=False,
                debug=self.debug_mode
            )
            return world_grid
        except Exception as e:
            print(f"Error loading world: {e}")
            return [
                [random.choice(list(tile_mapping.keys())) for _ in range(WORLD_WIDTH)]
                for _ in range(WORLD_HEIGHT)
            ]

    def _create_effect_overlays(self) -> Dict[str, pygame.Surface]:
        """Create semi-transparent overlays for weather and time effects."""
        overlays = {}
        
        # Rain overlay (blue tint)
        rain_overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        rain_overlay.fill((0, 0, 200, 30))
        overlays['rain'] = rain_overlay
        
        # Snow overlay (light blue tint)
        snow_overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        snow_overlay.fill((200, 200, 255, 30))
        overlays['snow'] = snow_overlay
        
        # Heat overlay (orange tint)
        heat_overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        heat_overlay.fill((255, 100, 0, 30))
        overlays['heat'] = heat_overlay
        
        # Wind overlay (gray tint)
        wind_overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        wind_overlay.fill((200, 200, 200, 20))
        overlays['wind'] = wind_overlay
        
        # Night overlay (dark blue tint)
        night_overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        night_overlay.fill((0, 0, 50, 100))
        overlays['night'] = night_overlay
        
        return overlays

    def _update_weather_particles(self, dt: float) -> None:
        """Update weather particles based on environment conditions with horizontal wrapping only."""
        # Clear old particles
        self.particles = [p for p in self.particles if p['lifetime'] > 0]
        
        # Get current terrain at center of screen with horizontal wrapping
        center_x = int((self.camera_x + self.screen_width // 2) // self.TILE_SIZE) % WORLD_WIDTH
        center_y = int((self.camera_y + self.screen_height // 2) // self.TILE_SIZE)
        
        # Check if within vertical bounds
        if 0 <= center_y < WORLD_HEIGHT:
            current_terrain = self.world_grid[center_y][center_x]
            weather = self.environment_system.weather_conditions.get(current_terrain, {})
            
            # Get time and season data
            hour = self.environment_system.time_of_day
            season = self.environment_system.season
            
            # Calculate particle spawn rates based on weather, time, and season
            rain_rate = 0
            snow_rate = 0
            heat_rate = 0
            wind_rate = 0
            
            # Base rates from weather conditions
            precipitation = weather.get('precipitation', 0)
            temperature = weather.get('temperature', 20)
            wind_speed = weather.get('wind', 0)
            
            # Adjust for time of day
            is_daytime = 6 <= hour <= 18
            
            # Precipitation particles (rain or snow)
            if precipitation > 0.3:
                if temperature < 5:  # Snow
                    # Snow is more visible during day, but still present at night
                    snow_base_rate = int(precipitation * 20)
                    snow_rate = snow_base_rate if is_daytime else snow_base_rate // 2
                    
                    # More snow in winter
                    if season == 'Winter':
                        snow_rate = int(snow_rate * 1.5)
                else:  # Rain
                    # Rain is more visible at night due to contrast
                    rain_base_rate = int(precipitation * 25)
                    rain_rate = rain_base_rate
                    
                    # More rain in spring
                    if season == 'Spring':
                        rain_rate = int(rain_rate * 1.3)
            
            # Heat particles (more during day, especially in summer)
            if temperature > 30:
                heat_base_rate = int((temperature - 30) * 2)
                heat_rate = heat_base_rate if is_daytime else heat_base_rate // 3
                
                # More heat waves in summer
                if season == 'Summer':
                    heat_rate = int(heat_rate * 1.5)
            
            # Wind particles
            if wind_speed > 15:
                wind_base_rate = int(wind_speed / 2)
                wind_rate = wind_base_rate
                
                # More visible wind in autumn
                if season == 'Autumn':
                    wind_rate = int(wind_rate * 1.3)
            
            # Add new particles based on calculated rates
            # Rain particles
            for _ in range(rain_rate):
                self.particles.append({
                    'type': 'rain',
                    'x': random.randint(0, self.screen_width),
                    'y': random.randint(-10, 0),
                    'speed': random.uniform(200, 300),
                    'lifetime': random.uniform(0.5, 1.0),
                    'weather': weather  # Store weather reference for this particle
                })
            
            # Snow particles
            for _ in range(snow_rate):
                self.particles.append({
                    'type': 'snow',
                    'x': random.randint(0, self.screen_width),
                    'y': random.randint(-10, 0),
                    'speed': random.uniform(50, 100),
                    'lifetime': random.uniform(1.0, 2.0),
                    'weather': weather  # Store weather reference for this particle
                })
            
            # Heat particles
            for _ in range(heat_rate):
                self.particles.append({
                    'type': 'heat',
                    'x': random.randint(0, self.screen_width),
                    'y': random.randint(self.screen_height - 50, self.screen_height),
                    'speed': random.uniform(-50, -30),
                    'lifetime': random.uniform(0.5, 1.0),
                    'weather': weather  # Store weather reference for this particle
                })
            
            # Wind particles
            for _ in range(wind_rate):
                self.particles.append({
                    'type': 'wind',
                    'x': random.randint(0, self.screen_width),
                    'y': random.randint(0, self.screen_height),
                    'speed': random.uniform(100, 200),
                    'lifetime': random.uniform(0.3, 0.8),
                    'weather': weather  # Store weather reference for this particle
                })
        else:
            # Default weather if out of bounds
            weather = {'precipitation': 0, 'temperature': 20, 'wind': 0}
        
        # Update particle positions with more realistic physics
        for particle in self.particles:
            # Get weather data from the particle itself
            particle_weather = particle.get('weather', {})
            
            if particle['type'] == 'rain':
                # Rain falls straight down, slightly affected by wind
                wind_effect = particle_weather.get('wind', 0) * 0.1
                particle['y'] += particle['speed'] * dt
                particle['x'] -= wind_effect * dt
            elif particle['type'] == 'snow':
                # Snow falls more slowly and drifts with sine wave pattern
                wind_effect = particle_weather.get('wind', 0) * 0.2
                particle['y'] += particle['speed'] * dt
                particle['x'] += math.sin(particle['y'] / 30) * 2 - wind_effect * dt
            elif particle['type'] == 'heat':
                # Heat rises with wavering motion
                particle['y'] += particle['speed'] * dt
                particle['x'] += math.sin(particle['y'] / 20) * 3
            elif particle['type'] == 'wind':
                # Wind moves horizontally with slight vertical variation
                particle['x'] += particle['speed'] * dt
                particle['y'] += math.sin(particle['x'] / 50) * 2
            
            # Apply horizontal wrapping to particles
            if particle['x'] < 0:
                particle['x'] += self.screen_width
            elif particle['x'] >= self.screen_width:
                particle['x'] -= self.screen_width
                
            # Reduce lifetime
            particle['lifetime'] -= dt

    def _spawn_animals(self, num_animals: int = 100) -> List[Animal]:
        """Spawn animals across the map, prioritizing their preferred habitats."""
        spawn_points = get_spawn_points_by_terrain(self.world_grid)
        animals = []

        # Calculate world boundaries in pixels
        world_width_px = len(self.world_grid[0]) * TILE_SIZE
        world_height_px = len(self.world_grid) * TILE_SIZE
        safe_margin = TILE_SIZE * 2  # Keep animals away from edges

        # Create valid spawn locations dictionary
        valid_spawn_locations = {}
        for terrain_type, locations in spawn_points.items():
            valid_spawn_locations[terrain_type] = [
                (x, y) for x, y in locations
                if (safe_margin <= x * TILE_SIZE <= world_width_px - safe_margin and
                    safe_margin <= y * TILE_SIZE <= world_height_px - safe_margin)
            ]

        # Group animals by their primary habitat and diet type
        habitat_groups = {}
        diet_groups = {'carnivore': [], 'herbivore': [], 'omnivore': []}
        animal_habitat_map = {}  # Maps animal name to preferred habitat
        
        # First, categorize all animals
        for _, row in self.processed_animals.iterrows():
            if pd.isna(row['Animal']) or pd.isna(row['Habitat']):
                continue
                
            animal_data = row.to_dict()
            animal_name = animal_data['Animal']
            habitat_str = str(animal_data['Habitat']).lower()
            diet = str(animal_data['Diet_Type']).lower()
            
            # Determine preferred habitat with improved detection
            preferred_habitat = self._get_terrain_for_habitat(habitat_str)
            
            # Store animal's preferred habitat
            animal_habitat_map[animal_name] = preferred_habitat
            
            # Group by habitat
            if preferred_habitat not in habitat_groups:
                habitat_groups[preferred_habitat] = []
            habitat_groups[preferred_habitat].append(animal_data)
            
            # Group by diet
            if diet in diet_groups:
                diet_groups[diet].append(animal_data)

        # Calculate target numbers for each diet type
        total_spawns = {
            'carnivore': max(1, int(num_animals * 0.2)),  # At least 1 of each type
            'herbivore': max(1, int(num_animals * 0.5)),
            'omnivore': max(1, int(num_animals * 0.3))
        }
        
        # Ensure we don't exceed the total
        total = sum(total_spawns.values())
        if total < num_animals:
            # Distribute remaining animals proportionally
            remaining = num_animals - total
            total_spawns['herbivore'] += remaining // 2
            total_spawns['carnivore'] += remaining // 4
            total_spawns['omnivore'] += remaining - (remaining // 2) - (remaining // 4)

        # Track spawning statistics
        spawned_per_terrain = {terrain: 0 for terrain in spawn_points.keys()}
        total_spawned = 0
        spawn_attempts = 0
        max_attempts = num_animals * 10
        
        # Create a list of all animal data sorted by diet to ensure balanced ecosystem
        all_animals_by_diet = []
        for diet, count in total_spawns.items():
            diet_animals = [a for a in diet_groups.get(diet, []) if a['Animal'] in animal_habitat_map]
            if diet_animals:
                # Add animals of this diet type according to target count
                for _ in range(count):
                    if diet_animals:  # Check again in case we ran out
                        all_animals_by_diet.append(random.choice(diet_animals))

        # Shuffle to avoid patterns
        random.shuffle(all_animals_by_diet)
        
        # Main spawning loop - try to spawn each animal in its preferred habitat
        while all_animals_by_diet and total_spawned < num_animals and spawn_attempts < max_attempts:
            spawn_attempts += 1
            
            # Get next animal to spawn
            animal_data = all_animals_by_diet.pop(0)
            animal_name = animal_data['Animal']
            preferred_habitat = animal_habitat_map.get(animal_name, 'grassland')
            
            # Try to spawn in preferred habitat first
            spawned = False
            
            # Define habitat priority: preferred first, then survivable, then any
            habitat_priority = [preferred_habitat]
            
            # Add survivable habitats as fallback
            # This is a simplified version - in a real implementation, you'd use the
            # terrain compatibility logic from the Animal class
            if preferred_habitat == 'aquatic':
                habitat_priority.append('wetland')
            elif preferred_habitat == 'forest':
                habitat_priority.extend(['grassland', 'wetland'])
            elif preferred_habitat == 'mountain':
                habitat_priority.extend(['forest', 'grassland'])
            elif preferred_habitat == 'desert':
                habitat_priority.append('grassland')
            elif preferred_habitat == 'grassland':
                habitat_priority.extend(['forest', 'desert'])
            elif preferred_habitat == 'wetland':
                habitat_priority.extend(['aquatic', 'grassland'])
            
            # Try each habitat in priority order
            for habitat in habitat_priority:
                if habitat in valid_spawn_locations and valid_spawn_locations[habitat]:
                    # Found a valid location in this habitat
                    spawn_x, spawn_y = random.choice(valid_spawn_locations[habitat])
                    base_x = spawn_x * TILE_SIZE
                    base_y = spawn_y * TILE_SIZE
                    
                    # Create the animal
                    animal = Animal(animal_data['Animal'], animal_data)
                    
                    # Add position variation within the tile
                    spread = TILE_SIZE // 2
                    angle = random.random() * 2 * math.pi
                    distance = random.random() * spread
                    animal.x = base_x + math.cos(angle) * distance
                    animal.y = base_y + math.sin(angle) * distance
                    
                    # Ensure position is within bounds
                    animal.x = max(safe_margin, min(animal.x, world_width_px - safe_margin))
                    animal.y = max(safe_margin, min(animal.y, world_height_px - safe_margin))
                    
                    animal.world_grid = self.world_grid
                    animals.append(animal)
                    
                    # Update counters
                    spawned_per_terrain[habitat] += 1
                    total_spawned += 1
                    spawned = True
                    
                    # Remove the used spawn point to avoid overcrowding
                    valid_spawn_locations[habitat].remove((spawn_x, spawn_y))
                    
                    break  # Successfully spawned, move to next animal
            
            # If we couldn't spawn in any preferred or survivable habitat, try any available habitat
            if not spawned:
                # Try any terrain with available spawn points
                available_terrains = [t for t in valid_spawn_locations if valid_spawn_locations[t]]
                if available_terrains:
                    terrain = random.choice(available_terrains)
                    spawn_x, spawn_y = random.choice(valid_spawn_locations[terrain])
                    base_x = spawn_x * TILE_SIZE
                    base_y = spawn_y * TILE_SIZE
                    
                    # Create the animal
                    animal = Animal(animal_data['Animal'], animal_data)
                    
                    # Add position variation within the tile
                    spread = TILE_SIZE // 2
                    angle = random.random() * 2 * math.pi
                    distance = random.random() * spread
                    animal.x = base_x + math.cos(angle) * distance
                    animal.y = base_y + math.sin(angle) * distance
                    
                    # Ensure position is within bounds
                    animal.x = max(safe_margin, min(animal.x, world_width_px - safe_margin))
                    animal.y = max(safe_margin, min(animal.y, world_height_px - safe_margin))
                    
                    animal.world_grid = self.world_grid
                    animals.append(animal)
                    
                    # Update counters
                    spawned_per_terrain[terrain] += 1
                    total_spawned += 1
                    
                    # Remove the used spawn point
                    valid_spawn_locations[terrain].remove((spawn_x, spawn_y))
            
            # If we've reached our target number, stop spawning
            if total_spawned >= num_animals:
                break
                
        # If we still need more animals, add them in any available terrain
        while total_spawned < num_animals and spawn_attempts < max_attempts:
            spawn_attempts += 1
            
            # Find any terrain with available spawn points
            available_terrains = [t for t in valid_spawn_locations if valid_spawn_locations[t]]
            if not available_terrains:
                break  # No more spawn points available
                
            terrain = random.choice(available_terrains)
            spawn_x, spawn_y = random.choice(valid_spawn_locations[terrain])
            
            # Find animals that can survive in this terrain
            suitable_animals = []
            for diet, animals_list in diet_groups.items():
                if total_spawns.get(diet, 0) > 0:  # If we still need animals of this diet
                    suitable_animals.extend(animals_list)
            
            if not suitable_animals:
                # If no suitable animals, use any animal
                suitable_animals = [a for diet_list in diet_groups.values() for a in diet_list]
            
            if not suitable_animals:
                break  # No suitable animals found
                
            # Select and create animal
            animal_data = random.choice(suitable_animals)
            animal = Animal(animal_data['Animal'], animal_data)
            
            # Set position
            base_x = spawn_x * TILE_SIZE
            base_y = spawn_y * TILE_SIZE
            
            # Add position variation
            spread = TILE_SIZE // 2
            angle = random.random() * 2 * math.pi
            distance = random.random() * spread
            animal.x = base_x + math.cos(angle) * distance
            animal.y = base_y + math.sin(angle) * distance
            
            # Ensure position is within bounds
            animal.x = max(safe_margin, min(animal.x, world_width_px - safe_margin))
            animal.y = max(safe_margin, min(animal.y, world_height_px - safe_margin))
            
            animal.world_grid = self.world_grid
            animals.append(animal)
            
            # Update counters
            diet = str(animal_data.get('Diet_Type', '')).lower()
            if diet in total_spawns:
                total_spawns[diet] -= 1
            spawned_per_terrain[terrain] += 1
            total_spawned += 1
            
            # Remove the used spawn point
            valid_spawn_locations[terrain].remove((spawn_x, spawn_y))

        if self.debug_mode:
            print(f"\nSpawn Summary:")
            print(f"Successfully spawned {len(animals)} animals after {spawn_attempts} attempts")
            print(f"Animals per terrain: {spawned_per_terrain}")
            
        return animals

    def _get_terrain_for_habitat(self, habitat: str) -> str:
        """Map habitat description to terrain type with improved matching."""
        habitat = habitat.lower()
        
        # Aquatic habitats
        if any(term in habitat for term in ['ocean', 'marine', 'water', 'aquatic', 'sea', 'river', 'lake']):
            return 'aquatic'
        
        # Forest habitats
        elif any(term in habitat for term in ['forest', 'woodland', 'jungle', 'rainforest', 'tropical']):
            return 'forest'
        
        # Mountain habitats
        elif any(term in habitat for term in ['mountain', 'alpine', 'highland', 'cliff', 'rocky']):
            return 'mountain'
        
        # Desert habitats
        elif any(term in habitat for term in ['desert', 'arid', 'sand', 'dune']):
            return 'desert'
        
        # Grassland habitats (default if no other match)
        elif any(term in habitat for term in ['grass', 'savanna', 'plain', 'meadow', 'prairie']):
            return 'grassland'
        
        # Default to grassland if no clear match
        return 'grassland'

    def _spawn_robots(self) -> List[Robot]:
        """Spawn robots in a grid pattern across the world with player robot."""
        robots = []
        num_robots = 47  # Reduced by 1 to make room for player robot
        
        # Run player setup to get customized robot
        player_robot = setup_player_robot(self.screen)
        
        # Calculate grid dimensions to get a roughly square arrangement
        grid_size = int(math.sqrt(num_robots))  # e.g., 5x5 grid for 24 robots
        spacing_x = self.width / (grid_size + 1)  # +1 to create margin from edges
        spacing_y = self.height / (grid_size + 1)
        
        # Generate positions in a grid with some randomness
        positions = []
        for row in range(grid_size):
            for col in range(grid_size):
                # Base position in grid
                x = spacing_x * (col + 1)  # +1 to skip the edge
                y = spacing_y * (row + 1)
                
                # Add controlled randomness
                rand_x = random.uniform(-spacing_x/4, spacing_x/4)
                rand_y = random.uniform(-spacing_y/4, spacing_y/4)
                
                # Store position if we still need more robots
                if len(positions) < num_robots:
                    positions.append((
                        max(100, min(self.width - 100, x + rand_x)),
                        max(100, min(self.height - 100, y + rand_y))
                    ))
        
        # Shuffle positions to avoid predictable patterns
        random.shuffle(positions)
        
        # Create robots at positions
        for x, y in positions:
            robot = Robot(x, y)
            robot.world_grid = self.world_grid
            robot.territory_center = (x, y)
            robots.append(robot)
        
        # Add player robot with special position (closest to center)
        if player_robot:
            # Find center of the world
            center_x = self.width / 2
            center_y = self.height / 2
            
            # Select the position closest to the center for the player
            center_position = min(positions, key=lambda pos: math.sqrt((pos[0] - center_x)**2 + (pos[1] - center_y)**2))
            
            # Place player robot
            player_robot.x = center_position[0]
            player_robot.y = center_position[1]
            player_robot.world_grid = self.world_grid
            player_robot.territory_center = (player_robot.x, player_robot.y)
            
            # Add player robot to the front of the list
            robots.insert(0, player_robot)
            
            # Start following the player's robot
            self.spectating = True
            self.spectated_robot_index = 0
            
            # Log player creation
            print(f"Player robot '{player_robot.name}' created with ideology: {player_robot.ideology}, archetype: {player_robot.archetype}")
        
        return robots

    def _form_initial_teams(self) -> List[Team]:
        """Form initial teams for robots."""
        teams = []
        for robot in self.robots:
            team = Team(robot)
            robot.team = team
            robot.set_team_status(False)
            
            # Initialize team resources
            TeamResourceExtension.initialize_team_resources(team)
            
            teams.append(team)
        return teams

    def _handle_recruitment(self) -> None:
        """Handle the recruitment of animals into teams."""
        recruitment_radius = 300

        for robot in self.robots:
            if robot.state == 'recruiting':
                # Skip if robot already has a full team
                if robot.team and len(robot.team.members) >= robot.max_team_size:
                    continue

                animals_to_add = []
                current_team_ids = {id(m) for m in robot.team.members} if robot.team else set()

                for animal in self.animals:
                    if not animal.team and animal.health > 0:
                        # Skip if animal was already in this team
                        if id(animal) in current_team_ids:
                            continue
                            
                        dist = math.sqrt((animal.x - robot.x) ** 2 + (animal.y - robot.y) ** 2)
                        if dist < recruitment_radius:
                            animals_to_add.append(animal)

                if animals_to_add:
                    # Create team if robot doesn't have one
                    if not robot.team:
                        robot.team = Team(robot)
                        self.teams.append(robot.team)
                        # Initialize team resources
                        TeamResourceExtension.initialize_team_resources(robot.team)
                        
                    # Add animals to team
                    for animal in animals_to_add[:robot.max_team_size - len(robot.team.members)]:
                        robot.team.add_member(animal)
                        
                    # Update robot state if team is full
                    if len(robot.team.members) >= robot.max_team_size:
                        robot.state = 'leading'
                        robot.set_team_status(True)

    def _handle_battles(self) -> None:
        """Handle battles between nearby teams and territory conflicts."""
        battle_range = 600.0
        min_team_size = 2

        # Track engaged teams to prevent multiple battles per frame
        engaged_teams = set()

        for i, team1 in enumerate(self.teams):
            if (team1 in engaged_teams or 
                len(team1.members) < min_team_size or 
                not team1.is_ready_for_battle(self.frame_count)):
                continue

            team1_pos = team1.get_average_position()

            for team2 in self.teams[i + 1:]:
                if (team2 in engaged_teams or 
                    len(team2.members) < min_team_size or 
                    not team2.is_ready_for_battle(self.frame_count)):
                    continue

                team2_pos = team2.get_average_position()
                dx = team2_pos[0] - team1_pos[0]
                dy = team2_pos[1] - team1_pos[1]
                dist = math.sqrt(dx**2 + dy**2)

                # Check for base invasion
                base_invasion = False
                if team1.base_established:
                    for member in team2.members + [team2.leader]:
                        if team1.base.is_point_inside((member.x, member.y)):
                            team1.handle_intruder(member)
                            base_invasion = True
                            break
                            
                if team2.base_established:
                    for member in team1.members + [team1.leader]:
                        if team2.base.is_point_inside((member.x, member.y)):
                            team2.handle_intruder(member)
                            base_invasion = True
                            break

                # Check for territory conflict
                territory_conflict = False
                for member in team1.members:
                    if team2.is_in_territory((member.x, member.y)):
                        territory_conflict = True
                        break
                if not territory_conflict:
                    for member in team2.members:
                        if team1.is_in_territory((member.x, member.y)):
                            territory_conflict = True
                            break

                # Higher chance of battle when closer, in territory conflict, or base invasion
                base_chance = 0.2
                proximity_bonus = max(0, (battle_range - dist) / battle_range)
                territory_bonus = 0.4 if territory_conflict else 0.0
                base_invasion_bonus = 0.6 if base_invasion else 0.0
                battle_chance = base_chance + (proximity_bonus * 0.3) + territory_bonus + base_invasion_bonus

                if ((dist < battle_range or territory_conflict or base_invasion) and 
                    team1.get_total_health() > 0 and 
                    team2.get_total_health() > 0 and
                    random.random() < battle_chance):
                    
                    battle_result = self.combat_manager.resolve_battle(team1, team2)
                    
                    if battle_result['result']['outcome'] != 'avoided':
                        engaged_teams.add(team1)
                        engaged_teams.add(team2)
                        
                        # Add territory and base context to battle result
                        battle_result['result']['context'] = []
                        if territory_conflict:
                            battle_result['result']['context'].append('territory_conflict')
                        if base_invasion:
                            battle_result['result']['context'].append('base_invasion')
                        
                        self.event_manager.add_event('battle', battle_result)
                        self.ui_manager.add_battle(self.frame_count, battle_result['result'])
                        
                        winner = team1 if battle_result['result'].get('winner') == team1.get_leader_name() else team2
                        winner.experience += 50
                        if territory_conflict:
                            winner.experience += 25
                        if base_invasion:
                            winner.experience += 50  # Extra XP for successful base defense/invasion

    def update(self, dt: float) -> None:
        """Update game state with base management."""
        self.event_manager.frame_count = self.frame_count
        
        # Update systems
        self.environment_system.update(dt)
        self.combat_manager.update(dt)
        self.resource_system.update(dt)
        
        # Update weather particles
        if self.frame_count % 2 == 0:
            self._update_weather_particles(dt)
        
        # Determine if we should do a full update
        do_full_update = True
        if len(self.fps_history) > 5:
            avg_fps = sum(self.fps_history[-5:]) / 5
            if avg_fps < 15:
                do_full_update = (self.frame_count % 2 == 0)
        
        # Always update robots
        for robot in self.robots:
            robot.detect_nearby_animals(self.animals)
            robot.update(dt, self.robots, self.resource_system)
            self._constrain_to_world(robot)
            if not robot.team or len(robot.team.members) == 0:
                robot.state = 'recruiting' if robot.nearby_animals else 'searching'
        
        # Update teams and evolution less frequently if FPS is low
        if do_full_update:
            # Update evolution manager
            self.evolution_manager.update(dt)
            
            # Update teams
            for team in self.teams:
                if team.members:
                    team.update(dt)
                    TeamResourceExtension.update_team_resources(team, dt, self.resource_system)
                    
            # Update animals and handle breeding
            for i, animal1 in enumerate(self.animals):
                if animal1.health > 0:
                    animal1.update(dt, self.environment_system, self.world_grid, self.animals + self.robots, self.resource_system)
                    self._constrain_to_world(animal1)
                    
                    # Check for breeding opportunities
                    if not animal1.team and self.frame_count % 10 == 0:
                        for animal2 in self.animals[i+1:]:
                            if (animal2.health > 0 and not animal2.team and 
                                self._are_animals_close(animal1, animal2, 50)):
                                current_pop = sum(1 for a in self.animals 
                                              if a.name == animal1.name and a.health > 0)
                                if self.evolution_manager.should_reproduce(animal1, animal2, current_pop):
                                    self._handle_reproduction(animal1, animal2)

                    # New behavior logic
                    if animal1.hunger > 70:
                        # Find food and eat
                        animal1.eat('plant', 10)  # Example action
                    if animal1.thirst > 70:
                        # Find water and drink
                        animal1.drink(10)  # Example action
                    if animal1.sleepiness > 70:
                        # Find a safe place to sleep
                        animal1.sleep(5)  # Example action
                    if animal1.social_needs > 70:
                        # Find other animals to team up with
                        for animal2 in self.animals[i+1:]:
                            if animal2.health > 0 and not animal2.team:
                                animal1.team_up(animal2)
                                break
        else:
            # Simplified update for animals when FPS is low
            for animal in self.animals:
                if animal.health > 0:
                    animal.x += animal.dx * dt
                    animal.y += animal.dy * dt
                    self._constrain_to_world(animal)

        # These operations should run every frame for gameplay consistency
        self._handle_recruitment()
        self._handle_battles()
        self.teams = [t for t in self.teams if len(t.members) > 0]
        self.frame_count += 1

    def _constrain_to_world(self, entity) -> None:
        """Wrap entity horizontally but constrain vertically to create a cylindrical world."""
        # Get world dimensions
        world_width_px = self.width
        world_height_px = self.height
        
        # Wrap around horizontally (left/right)
        if entity.x < 0:
            entity.x += world_width_px
        elif entity.x >= world_width_px:
            entity.x -= world_width_px
            
        # Constrain vertically (top/bottom)
        entity.y = max(32, min(entity.y, world_height_px - 64))

    def _handle_reproduction(self, parent1: 'Animal', parent2: 'Animal') -> None:
        """Handle reproduction between two animals."""
        # Get offspring traits from evolution manager
        offspring_data = self.evolution_manager.create_offspring(parent1, parent2)
        
        # Create new animal with evolved genome
        animal_data = next((row for _, row in self.processed_animals.iterrows() 
                         if row['Animal'] == parent1.name), None)
        if animal_data is not None:
            # Calculate spawn position
            spawn_x = (parent1.x + parent2.x) / 2 + random.uniform(-20, 20)
            spawn_y = (parent1.y + parent2.y) / 2 + random.uniform(-20, 20)
            
            # Create offspring
            offspring = Animal(
                parent1.name,
                animal_data.to_dict(),
                genome=offspring_data['genome'],
                generation=offspring_data['generation']
            )
            
            # Set position
            offspring.x = spawn_x
            offspring.y = spawn_y
            offspring.world_grid = self.world_grid
            
            # Add to simulation
            self.animals.append(offspring)
            
            # Update species stats
            species_pop = sum(1 for a in self.animals if a.name == parent1.name)
            if parent1.name in self.evolution_manager.species_stats:
                self.evolution_manager.species_stats[parent1.name]['population_history'].append(species_pop)

    def _are_animals_close(self, animal1: 'Animal', animal2: 'Animal', distance: float) -> bool:
        """Check if two animals are within breeding distance."""
        dx = animal1.x - animal2.x
        dy = animal1.y - animal2.y
        return math.sqrt(dx*dx + dy*dy) <= distance

    def handle_input(self) -> bool:
        """Handle user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
                
            # Let UI handle events first
            ui_result = self.ui_manager.handle_event(event)
            if isinstance(ui_result, Robot):  # If a robot was clicked in team overview
                # Find the index of the clicked robot
                if ui_result in self.robots:
                    self.spectating = True
                    self.spectated_robot_index = self.robots.index(ui_result)
                continue
            elif ui_result:  # Other UI event was handled
                continue
                
            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
                
            elif event.type == pygame.MOUSEMOTION:
                # Update tooltip for entities under cursor
                self._handle_mouse_motion(event)
                
        self._handle_camera_movement()
        return True

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        """Handle mouse motion for UI interactions"""
        # Update tooltip for entities under cursor
        mouse_x, mouse_y = event.pos
        world_x = mouse_x + self.camera_x
        world_y = mouse_y + self.camera_y
        
        # Check for entities under cursor
        for animal in self.animals:
            if animal.health > 0:
                dx = world_x - animal.x
                dy = world_y - animal.y
                if math.sqrt(dx*dx + dy*dy) < 32:  # Radius for interaction
                    tooltip_text = self._get_entity_tooltip(animal)
                    self.ui_manager.active_tooltip = {
                        'text': tooltip_text,
                        'entity': animal
                    }
                    return
                    
        for robot in self.robots:
            dx = world_x - robot.x
            dy = world_y - robot.y
            if math.sqrt(dx*dx + dy*dy) < 32:
                tooltip_text = self._get_entity_tooltip(robot)
                self.ui_manager.active_tooltip = {
                    'text': tooltip_text,
                    'entity': robot
                }
                return
        
        self.ui_manager.active_tooltip = None

    def _get_entity_tooltip(self, entity: Any) -> str:
        """Get tooltip text for an entity"""
        if hasattr(entity, 'name'):  # Animal
            tooltip_lines = [
                f"{entity.name}",
                f"Health: {int(entity.health)}/{int(entity.max_health)}"
            ]
            
            # Add terrain information and effects
            if hasattr(entity, 'current_terrain') and entity.current_terrain:
                terrain_compatibility = entity._get_terrain_compatibility(entity.current_terrain)
                
                # Add terrain info
                tooltip_lines.append(f"Current Terrain: {entity.current_terrain}")
                tooltip_lines.append(f"Preferred Habitat: {entity.preferred_habitat}")
                
                # Add compatibility and effects
                if terrain_compatibility == 'optimal':
                    tooltip_lines.append("Terrain: Optimal (Health +)")
                elif terrain_compatibility == 'survivable':
                    tooltip_lines.append("Terrain: Survivable")
                elif terrain_compatibility == 'harmful':
                    tooltip_lines.append("Terrain: Harmful (Health -)")
                
                # Add speed effect if not normal
                if entity.terrain_speed_effect != 1.0:
                    speed_effect = int((entity.terrain_speed_effect - 1.0) * 100)
                    if speed_effect < 0:
                        tooltip_lines.append(f"Speed: {speed_effect}%")
                    else:
                        tooltip_lines.append(f"Speed: +{speed_effect}%")
            
            if entity.team:
                tooltip_lines.extend([
                    f"Team: {entity.team.get_leader_name()}",
                    f"Role: {'Leader' if entity.team.leader == entity else 'Member'}"
                ])
            return "\n".join(tooltip_lines)
        else:  # Robot
            tooltip_lines = [entity.name]  # Use robot's name property
            if entity.team:
                tooltip_lines.extend([
                    f"Team Size: {len(entity.team.members)}",
                    f"Formation: {entity.team.formation}",
                    f"Base Level: {entity.team.base.level}",
                    f"Defense Bonus: +{int((entity.team.base.get_defense_bonus() - 1) * 100)}%",
                    f"Night Bonus: +{int((entity.team.base.get_night_bonus() - 1) * 100)}%"
                ])
            tooltip_lines.append(f"State: {entity.state}")
            return "\n".join(tooltip_lines)

    def draw(self) -> None:
        """Draw the game state with base visualization."""
        self.screen.fill((0, 0, 0))
        
        # Draw world and entities
        self._draw_world()
        
        # Draw resources
        self.resource_system.draw(self.screen, self.camera_x, self.camera_y, TILE_SIZE)
        
        # Draw weather effects
        self._draw_weather_effects()
        
        # Calculate visible area for entity culling
        visible_min_x = self.camera_x - TILE_SIZE
        visible_max_x = self.camera_x + self.screen_width + TILE_SIZE
        visible_min_y = self.camera_y - TILE_SIZE
        visible_max_y = self.camera_y + self.screen_height + TILE_SIZE
        
        # Draw team bases first (so they appear behind entities)
        for team in self.teams:
            if team.base_established:
                team.base.draw(self.screen, self.camera_x, self.camera_y)
        
        # Draw visible animals
        visible_animals = []
        for animal in self.animals:
            if animal.health > 0:
                animal_x = animal.x
                if abs(animal_x - self.camera_x) > self.width / 2:
                    if animal_x > self.camera_x:
                        animal_x -= self.width
                    else:
                        animal_x += self.width
                    
                if (visible_min_x <= animal_x <= visible_max_x and 
                    visible_min_y <= animal.y <= visible_max_y):
                    visible_animals.append(animal)
        
        for animal in visible_animals:
            animal.draw(self.screen, self.camera_x, self.camera_y, self.ui_manager.show_health_bars)
        
        # Draw robots
        for robot in self.robots:
            robot_x = robot.x
            if abs(robot_x - self.camera_x) > self.width / 2:
                if robot_x > self.camera_x:
                    robot_x -= self.width
                else:
                    robot_x += self.width
                
            if (visible_min_x <= robot_x <= visible_max_x and 
                visible_min_y <= robot.y <= visible_max_y):
                robot.draw(self.screen, self.camera_x, self.camera_y)
        
        # Draw team structures
        visible_teams = []
        for team in self.teams:
            if team.leader:
                leader_x = team.leader.x
                if abs(leader_x - self.camera_x) > self.width / 2:
                    if leader_x > self.camera_x:
                        leader_x -= self.width
                    else:
                        leader_x += self.width
                    
                if (visible_min_x <= leader_x <= visible_max_x and 
                    visible_min_y <= team.leader.y <= visible_max_y):
                    visible_teams.append(team)
        
        for team in visible_teams:
            TeamResourceExtension.draw_team_structures(team, self.screen, self.camera_x, self.camera_y)
        
        # Draw combat effects
        self.combat_manager.draw(self.screen, self.camera_x, self.camera_y)
        
        # Get current terrain and environment data
        current_terrain, current_longitude = self._get_current_terrain()
        environment_data = {
            'time_of_day': self.environment_system.time_of_day,
            'weather_conditions': self.environment_system.weather_conditions,
            'season': self.environment_system.season,
            'current_terrain': current_terrain,
            'time_data': self.environment_system.get_time_data(current_longitude),
            'current_longitude': current_longitude,
            'world_width': WORLD_WIDTH
        }
        
        # Store current time for UI
        self.ui_manager.current_time_of_day = self.environment_system.get_local_time(current_longitude)
        
        # Draw UI
        self.ui_manager.draw(
            self.screen,
            self.animals,
            self.robots,
            self.teams,
            camera_pos=(self.camera_x, self.camera_y),
            world_data=self.world_data,
            environment_data=environment_data
        )
        
        # Update display
        pygame.display.flip()

    def _draw_world(self) -> None:
        """Draw the visible part of the world grid with horizontal wrapping only."""
        # Calculate visible tile range
        start_x_raw = int(self.camera_x // TILE_SIZE)
        end_x_raw = int((self.camera_x + self.screen_width) // TILE_SIZE + 1)
        start_y_raw = max(0, int(self.camera_y // TILE_SIZE))
        end_y_raw = min(WORLD_HEIGHT, int((self.camera_y + self.screen_height) // TILE_SIZE + 1))
        
        # Get world dimensions in tiles
        world_width_tiles = WORLD_WIDTH
        
        # Draw tiles in the visible range, wrapping horizontally but not vertically
        for y in range(start_y_raw, end_y_raw):
            for x_offset in range(start_x_raw, end_x_raw):
                # Apply horizontal wrapping
                x = x_offset % world_width_tiles
                
                # Get tile and color
                tile = self.world_grid[y][x]
                color = self.world_data['colors'].get(tile, (100, 100, 100))
                
                # Calculate screen position, accounting for wrapping
                screen_x = int(x_offset * TILE_SIZE - self.camera_x)
                screen_y = int(y * TILE_SIZE - self.camera_y)
                
                # Draw the tile
                rect = pygame.Rect(screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.screen, color, rect)

    def _draw_weather_effects(self) -> None:
        """Draw weather effects based on environment conditions with horizontal wrapping only."""
        # Get current terrain at center of screen with horizontal wrapping
        center_x = int((self.camera_x + self.screen_width // 2) // self.TILE_SIZE) % WORLD_WIDTH
        center_y = int((self.camera_y + self.screen_height // 2) // self.TILE_SIZE)
        
        # Check if within vertical bounds
        if 0 <= center_y < WORLD_HEIGHT:
            current_terrain = self.world_grid[center_y][center_x]
            weather = self.environment_system.weather_conditions.get(current_terrain, {})
            
            # Get time of day for more realistic lighting
            hour = self.environment_system.time_of_day
            season = self.environment_system.season
            
            # Apply weather overlays
            if weather.get('precipitation', 0) > 0.3:
                if weather.get('temperature', 20) < 5:
                    # Snow effect - more intense in winter
                    snow_overlay = self.effect_overlays['snow'].copy()
                    if season == 'Winter':
                        snow_overlay.set_alpha(60)  # More intense in winter
                    else:
                        snow_overlay.set_alpha(40)
                    self.screen.blit(snow_overlay, (0, 0))
                else:
                    # Rain effect - varies by intensity
                    rain_overlay = self.effect_overlays['rain'].copy()
                    rain_intensity = min(80, int(weather.get('precipitation', 0) * 100))
                    rain_overlay.set_alpha(rain_intensity)
                    self.screen.blit(rain_overlay, (0, 0))
            
            # Heat effect - more intense in summer
            if weather.get('temperature', 20) > 30:
                heat_overlay = self.effect_overlays['heat'].copy()
                heat_intensity = min(60, int((weather.get('temperature', 20) - 30) * 10))
                if season == 'Summer':
                    heat_intensity += 10  # More intense in summer
                heat_overlay.set_alpha(heat_intensity)
                self.screen.blit(heat_overlay, (0, 0))
            
            # Wind effect - varies by intensity
            if weather.get('wind', 0) > 15:
                wind_overlay = self.effect_overlays['wind'].copy()
                wind_intensity = min(50, int(weather.get('wind', 0) * 2))
                wind_overlay.set_alpha(wind_intensity)
                self.screen.blit(wind_overlay, (0, 0))
            
            # Apply time of day overlay with more realistic transitions
            # Define day phases with realistic timing
            dawn_start = 5.0
            dawn_end = 7.0
            dusk_start = 18.0
            dusk_end = 20.0
            
            # Adjust for seasonal variations
            if season == 'Summer':
                dawn_start -= 1.0  # Earlier sunrise
                dusk_end += 1.0    # Later sunset
            elif season == 'Winter':
                dawn_start += 1.0  # Later sunrise
                dusk_end -= 1.0    # Earlier sunset
            
            # Night time (full darkness)
            if hour < dawn_start or hour > dusk_end:
                night_overlay = self.effect_overlays['night'].copy()
                night_overlay.set_alpha(120)  # Darker nights
                self.screen.blit(night_overlay, (0, 0))
            
            # Dawn transition (gradually getting lighter)
            elif dawn_start <= hour < dawn_end:
                night_overlay = self.effect_overlays['night'].copy()
                # Calculate alpha based on position in dawn transition
                progress = (hour - dawn_start) / (dawn_end - dawn_start)
                alpha = int(120 * (1 - progress))
                night_overlay.set_alpha(alpha)
                self.screen.blit(night_overlay, (0, 0))
            
            # Dusk transition (gradually getting darker)
            elif dusk_start <= hour < dusk_end:
                night_overlay = self.effect_overlays['night'].copy()
                # Calculate alpha based on position in dusk transition
                progress = (hour - dusk_start) / (dusk_end - dusk_start)
                alpha = int(120 * progress)
                night_overlay.set_alpha(alpha)
                self.screen.blit(night_overlay, (0, 0))
        
            # Draw particles with improved effects
            for particle in self.particles:
                if particle['type'] == 'rain':
                    # Rain drops - longer when heavier precipitation
                    rain_length = 10 + int(weather.get('precipitation', 0) * 10)
                    pygame.draw.line(
                        self.screen,
                        (100, 100, 255),
                        (particle['x'], particle['y']),
                        (particle['x'] - 1, particle['y'] + rain_length),
                        2
                    )
                elif particle['type'] == 'snow':
                    # Snow flakes - larger in winter
                    snow_size = 2
                    if self.environment_system.season == 'Winter':
                        snow_size = 3
                    pygame.draw.circle(
                        self.screen,
                        (255, 255, 255),
                        (int(particle['x']), int(particle['y'])),
                        snow_size
                    )
                elif particle['type'] == 'heat':
                    # Heat waves - more intense in summer
                    heat_size = 3
                    if self.environment_system.season == 'Summer':
                        heat_size = 4
                    pygame.draw.circle(
                        self.screen,
                        (255, 200, 100),
                        (int(particle['x']), int(particle['y'])),
                        heat_size
                    )
                elif particle['type'] == 'wind':
                    # Wind streaks - longer with stronger wind
                    wind_length = 15 + int(weather.get('wind', 0) / 2)
                    pygame.draw.line(
                        self.screen,
                        (200, 200, 200),
                        (particle['x'], particle['y']),
                        (particle['x'] - wind_length, particle['y']),
                        1
                    )

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle keydown events with improved UI feedback."""
        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_h:
            self.ui_manager.toggle_ui_element('health_bars')
            self.ui_manager.add_notification(
                "Health bars " + ("shown" if self.ui_manager.show_health_bars else "hidden"),
                'info'
            )
        elif event.key == pygame.K_m:
            self.ui_manager.toggle_ui_element('minimap')
            self.ui_manager.add_notification(
                "Minimap " + ("shown" if self.ui_manager.show_minimap else "hidden"),
                'info'
            )
        elif event.key == pygame.K_t:
            self.ui_manager.toggle_ui_element('teams')
            self.ui_manager.add_notification(
                "Team overview " + ("shown" if self.ui_manager.show_team_overview else "hidden"),
                'info'
            )
        elif event.key == pygame.K_F3:
            self.debug_mode = not self.debug_mode
            self.ui_manager.add_notification(
                "Debug mode " + ("enabled" if self.debug_mode else "disabled"),
                'info'
            )
        elif event.key == pygame.K_TAB:
            # Toggle spectator mode with notification
            self.spectating = not self.spectating
            if self.spectating:
                if is_player_robot(self.robots[0]) and self.spectated_robot_index != 0:
                    # Return to player robot
                    self.spectated_robot_index = 0
                    self.ui_manager.add_notification(f"Following your robot: {self.robots[0].name}", 'info')
                elif self.spectated_robot_index < 0:
                    self.spectated_robot_index = 0
            else:
                self.ui_manager.add_notification("Exited spectator mode", 'info')
        elif event.key == pygame.K_LEFT and self.spectating:
            # Previous robot
            if self.robots:
                self.spectated_robot_index = (self.spectated_robot_index - 1) % len(self.robots)
                self.ui_manager.add_notification(f"Following: {self.robots[self.spectated_robot_index].name}", 'info')
        elif event.key == pygame.K_RIGHT and self.spectating:
            # Next robot
            if self.robots:
                self.spectated_robot_index = (self.spectated_robot_index + 1) % len(self.robots)
                self.ui_manager.add_notification(f"Following: {self.robots[self.spectated_robot_index].name}", 'info')
        # Add time scale controls
        elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
            # Increase time scale
            current_scale = self.environment_system.time_scale
            new_scale = min(1.0, current_scale * 1.5)  # Increase by 50%, max 1.0
            self.environment_system.set_time_scale(new_scale)
            self.ui_manager.add_notification(
                f"Time scale: {new_scale:.3f}x",
                'info'
            )
        elif event.key == pygame.K_MINUS:
            # Decrease time scale
            current_scale = self.environment_system.time_scale
            new_scale = max(0.001, current_scale / 1.5)  # Decrease by 33%, min 0.001
            self.environment_system.set_time_scale(new_scale)
            self.ui_manager.add_notification(
                f"Time scale: {new_scale:.3f}x",
                'info'
            )
        elif event.key == pygame.K_0:
            # Reset time scale to default
            self.environment_system.set_time_scale(0.05)  # Default time scale
            self.ui_manager.add_notification(
                "Time scale reset to default (0.05x)",
                'info'
            )

    def _handle_camera_movement(self) -> None:
        """Handle camera movement with horizontal wrapping but vertical constraints."""
        world_width_px = self.width
        world_height_px = self.height
        
        if self.spectating and 0 <= self.spectated_robot_index < len(self.robots):
            # Follow the spectated robot with smooth camera
            robot = self.robots[self.spectated_robot_index]
            target_x = robot.x - self.screen_width // 2
            target_y = robot.y - self.screen_height // 2
            
            # Smooth camera movement with easing
            self.camera_x += (target_x - self.camera_x) * 0.1
            self.camera_y += (target_y - self.camera_y) * 0.1
            
            # Apply horizontal wrapping to camera position
            self.camera_x = self.camera_x % world_width_px
            # Constrain vertically
            self.camera_y = max(0, min(self.camera_y, world_height_px - self.screen_height))
        else:
            # Handle manual camera movement
            keys = pygame.key.get_pressed()
            if not self.spectating:
                move_x = 0
                move_y = 0
                
                if keys[pygame.K_LEFT]:
                    move_x -= self.camera_speed
                if keys[pygame.K_RIGHT]:
                    move_x += self.camera_speed
                if keys[pygame.K_UP]:
                    move_y -= self.camera_speed
                if keys[pygame.K_DOWN]:
                    move_y += self.camera_speed
                    
                # Apply movement with horizontal wrapping and vertical constraints
                if move_x != 0 or move_y != 0:
                    self.camera_x = (self.camera_x + move_x) % world_width_px
                    self.camera_y = max(0, min(self.camera_y + move_y, world_height_px - self.screen_height))

    def _get_current_terrain(self) -> tuple:
        """
        Get the terrain type and longitude at the center of the viewport with horizontal wrapping only.
        Returns a tuple of (terrain_type, longitude)
        """
        # Get world dimensions
        world_width_tiles = WORLD_WIDTH
        world_height_tiles = WORLD_HEIGHT
        
        # Calculate center position with horizontal wrapping only
        center_x = int((self.camera_x + self.screen_width/2) // self.TILE_SIZE) % world_width_tiles
        center_y = int((self.camera_y + self.screen_height/2) // self.TILE_SIZE)
        
        try:
            # Check if within vertical bounds
            if 0 <= center_y < world_height_tiles:
                return self.world_grid[center_y][center_x], center_x
            return 'grassland', center_x  # Default if out of vertical bounds
        except IndexError:
            return 'grassland', center_x  # Default if out of bounds

    def cleanup(self) -> None:
        """Clean up resources when game ends."""
        try:
            # Clean up teams first
            for team in self.teams:
                if hasattr(team, '_disband_team'):
                    team._disband_team()
            
            # Clean up animals
            for animal in self.animals:
                if hasattr(animal, 'cleanup'):
                    animal.cleanup()
            
            # Clean up managers
            if hasattr(self, 'resource_manager'):
                self.resource_manager.cleanup()
            if hasattr(self, 'ui_manager'):
                self.ui_manager.cleanup()
            
            # Quit pygame last
            pygame.quit()
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    pygame.init()
    
    # Get the screen info to use full screen dimensions
    screen_info = pygame.display.Info()
    screen_width = screen_info.current_w
    screen_height = screen_info.current_h
    
    # Create game with screen dimensions
    game = GameState(screen_width, screen_height)
    running = True
    
    # FPS tracking
    fps_font = pygame.font.SysFont('Arial', 24)
    fps_history = []
    fps_update_time = 0
    fps_display = "FPS: --"

    try:
        while game.running:  # Use game.running instead of separate running variable
            # Start timing this frame
            frame_start = time.time()
            
            # Calculate dt with a maximum to prevent physics issues
            dt = min(game.clock.tick(60) / 1000.0, 0.1)
            
            # Update FPS tracking
            current_time = time.time()
            if current_time - fps_update_time > 0.5:  # Update FPS display twice per second
                if fps_history:
                    avg_fps = sum(fps_history) / len(fps_history)
                    fps_display = f"FPS: {avg_fps:.1f}"
                fps_history = []
                fps_update_time = current_time
            
            # Calculate instantaneous FPS
            if dt > 0:
                fps_history.append(1.0 / dt)
            
            # Game update
            if not game.handle_input():  # If handle_input returns False, break the loop
                break
            game.update(dt)
            game.draw()
            
            # Draw FPS counter
            fps_surface = fps_font.render(fps_display, True, (255, 255, 0))
            game.screen.blit(fps_surface, (10, 10))
            pygame.display.flip()
            
            # Store frame time for performance monitoring
            frame_time = time.time() - frame_start
            game.fps_history.append(1.0 / frame_time if frame_time > 0 else 0)
            if len(game.fps_history) > 100:
                game.fps_history = game.fps_history[-100:]

        # Generate final story
        story = game.event_manager.generate_story()
        print("\nSimulation Story:")
        print(story)

    finally:
        game.cleanup()


if __name__ == "__main__":
    main()
