import os
import sys
import pygame
import random
import pandas as pd
import math
from typing import List

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


class GameState:
    def __init__(self, screen_width: int, screen_height: int):
        """Initialize the game state."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.width = WORLD_WIDTH * TILE_SIZE  # Add world dimensions
        self.height = WORLD_HEIGHT * TILE_SIZE
        self.camera_x = 0
        self.camera_y = 0
        self.camera_speed = 10
        self.frame_count = 0
        self.running = True

        # Initialize pygame and screen
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Evolution Simulation")
        self.clock = pygame.time.Clock()
        self.ui_manager = UIManager(screen_width, screen_height)

        # Load map and terrain data
        self.resampled_raster, self.new_transform = resample_raster(
            "data/Natural_Earth/NE1_HR_LC/NE1_HR_LC.tif",
            WORLD_HEIGHT,
            WORLD_WIDTH
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

        # Initialize managers
        self.combat_manager = CombatManager()
        self.event_manager = EventManager()
        self.resource_manager = ResourceManager.get_instance()
        self.environment_system = EnvironmentSystem(self.world_grid)

        # World data for UI
        self.world_data = {
            'width': WORLD_WIDTH,
            'height': WORLD_HEIGHT,
            'layout': self.world_grid,
            'colors': tile_mapping,
            'pixel_width': WORLD_WIDTH * TILE_SIZE,
            'pixel_height': WORLD_HEIGHT * TILE_SIZE
        }

        # Performance monitoring
        self.fps_history = []
        self.update_times = []
        self.draw_times = []
        self.debug_mode = False

    def _initialize_world(self) -> List[List[str]]:
        """Initialize the world grid."""
        try:
            world_grid, _ = generate_world_grid(
                raster_data=self.resampled_raster,
                transform=self.new_transform,
                land_mask=self.land_mask,
                color_classification=False
            )
            return world_grid
        except Exception as e:
            print(f"Error loading world: {e}")
            return [
                [random.choice(list(tile_mapping.keys())) for _ in range(WORLD_WIDTH)]
                for _ in range(WORLD_HEIGHT)
            ]


    def _spawn_animals(self, num_animals: int = 80) -> List[Animal]:
        """Spawn animals across the map in suitable habitats."""
        spawn_points = get_spawn_points_by_terrain(self.world_grid)
        animals = []

        species_groups = {}
        for name in self.processed_animals['Animal'].unique():
            row = self.processed_animals[self.processed_animals['Animal'] == name].iloc[0]
            habitat = row['Habitat'].lower()
            if habitat not in species_groups:
                species_groups[habitat] = []
            species_groups[habitat].append(name)

        for habitat, species_list in species_groups.items():
            terrain_type = self._get_terrain_for_habitat(habitat)
            if terrain_type not in spawn_points or not spawn_points[terrain_type]:
                continue

            spawn_x, spawn_y = random.choice(spawn_points[terrain_type])
            base_x = spawn_x * TILE_SIZE
            base_y = spawn_y * TILE_SIZE

            for species in species_list:
                if len(animals) >= num_animals:
                    break

                row = self.processed_animals[self.processed_animals['Animal'] == species].iloc[0].to_dict()
                animal = Animal(species, row)
                spread = 50
                angle = random.random() * 2 * math.pi
                distance = random.random() * spread

                animal.x = base_x + math.cos(angle) * distance
                animal.y = base_y + math.sin(angle) * distance
                animal.world_grid = self.world_grid
                animals.append(animal)

        return animals

    def _get_terrain_for_habitat(self, habitat: str) -> str:
        """Map habitat description to terrain type."""
        habitat = habitat.lower()
        if any(term in habitat for term in ['ocean', 'marine', 'water']):
            return 'aquatic'
        elif any(term in habitat for term in ['forest', 'woodland', 'jungle']):
            return 'forest'
        elif any(term in habitat for term in ['mountain', 'alpine']):
            return 'mountain'
        elif any(term in habitat for term in ['desert', 'arid']):
            return 'desert'
        elif any(term in habitat for term in ['grass', 'savanna', 'plain']):
            return 'grassland'
        return 'grassland'  # Default



    def _spawn_robots(self) -> List[Robot]:
        """Spawn robots in a grid pattern across the world."""
        robots = []
        num_robots = 24
        
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
            
        return robots

    def _form_initial_teams(self) -> List[Team]:
        """Form initial teams for robots."""
        teams = []
        for robot in self.robots:
            team = Team(robot)
            robot.team = team
            robot.set_team_status(False)
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
                    # Find or create team
                    team = next((t for t in self.teams if t.leader == robot), None)
                    if not team:
                        team = Team(robot)
                        robot.team = team
                        self.teams.append(team)

                    # Only record formation if new members are actually added
                    new_members = []
                    for animal in animals_to_add:
                        if not animal.team:  # Double-check animal is still free
                            team.add_member(animal)
                            animal.team = team
                            new_members.append(animal)

                    if new_members:  # Only record if we actually added new members
                        self.event_manager.add_team_formation(id(robot), team.members)

    def _handle_battles(self) -> None:
        """Handle battles between nearby teams."""
        battle_range = 600.0  # Increased from 400
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

                # Higher chance of battle when closer
                base_chance = 0.2  # Increased from 0.1
                proximity_bonus = max(0, (battle_range - dist) / battle_range)
                battle_chance = base_chance + (proximity_bonus * 0.3)

                if (dist < battle_range and 
                    team1.get_total_health() > 0 and 
                    team2.get_total_health() > 0 and
                    random.random() < battle_chance):
                    
                    battle_result = self.combat_manager.resolve_battle(team1, team2)
                    
                    if battle_result['result']['outcome'] != 'avoided':
                        engaged_teams.add(team1)
                        engaged_teams.add(team2)
                        
                        self.event_manager.add_event('battle', battle_result)
                        self.ui_manager.recent_battles.append(
                            (self.frame_count, battle_result['result'])
                        )
                        
                        winner = team1 if battle_result['result'].get('winner') == team1.get_leader_name() else team2
                        winner.experience += 50


    def update(self, dt: float) -> None:
        """Update game state."""
        self.event_manager.frame_count = self.frame_count
        self.environment_system.update(dt)

        # Update robots first to maintain territory control
        for robot in self.robots:
            robot.detect_nearby_animals(self.animals)
            robot.update(dt, self.robots)
            
            # Keep robot in world bounds
            self._constrain_to_world(robot)
            
            # Only mark as recruiting if not already has team
            if not robot.team or len(robot.team.members) == 0:
                robot.state = 'recruiting' if robot.nearby_animals else 'searching'

        # Then update teams and animals
        for team in self.teams:
            if team.members:  # Only update active teams
                team.update(dt)
                
        for animal in self.animals:
            if animal.health > 0:
                animal.update(dt, self.environment_system, self.world_grid, self.animals + self.robots)
                self._constrain_to_world(animal)

        self._handle_recruitment()
        self._handle_battles()
        self.teams = [t for t in self.teams if len(t.members) > 0]
        self.frame_count += 1

    def _constrain_to_world(self, entity) -> None:
        """Keep an entity within world bounds."""
        max_x = self.width - 64  # Account for entity size
        max_y = self.height - 64
        
        entity.x = max(32, min(entity.x, max_x))
        entity.y = max(32, min(entity.y, max_y))

    def draw(self) -> None:
        """Draw the game state."""
        self.screen.fill((0, 0, 0))
        self._draw_world()
        self._draw_entities()
        self.ui_manager.draw(
        self.screen, 
        self.animals, 
        self.robots, 
        self.teams, 
        camera_pos=(self.camera_x, self.camera_y),  # Pass the actual camera position
        world_data=self.world_data  # Pass the full world data
        )

        pygame.display.flip()

    def _draw_world(self) -> None:
        """Draw the visible part of the world grid."""
        start_x = max(0, self.camera_x // TILE_SIZE)
        end_x = min(WORLD_WIDTH, (self.camera_x + self.screen_width) // TILE_SIZE + 1)
        start_y = max(0, self.camera_y // TILE_SIZE)
        end_y = min(WORLD_HEIGHT, (self.camera_y + self.screen_height) // TILE_SIZE + 1)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.world_grid[y][x]
                color = self.world_data['colors'].get(tile, (100, 100, 100))
                rect = pygame.Rect(
                    x * TILE_SIZE - self.camera_x,
                    y * TILE_SIZE - self.camera_y,
                    TILE_SIZE,
                    TILE_SIZE
                )
                pygame.draw.rect(self.screen, color, rect)

    def _draw_entities(self) -> None:
        """Draw all entities."""
        for animal in self.animals:
            animal.draw(self.screen, self.camera_x, self.camera_y, self.ui_manager.show_health_bars)
        for robot in self.robots:
            robot.draw(self.screen, self.camera_x, self.camera_y)

    def cleanup(self) -> None:
        """Clean up resources when game ends."""
        self.resource_manager.cleanup()
        self.ui_manager.cleanup()
        for animal in self.animals:
            animal.cleanup()
        pygame.quit()

    def handle_input(self) -> bool:
        """Handle user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
        self._handle_camera_movement()
        return True

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle keydown events."""
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
        elif event.key == pygame.K_h:
            self.ui_manager.toggle_ui_element('health_bars')
        elif event.key == pygame.K_m:
            self.ui_manager.toggle_ui_element('minimap')
        elif event.key == pygame.K_t:
            self.ui_manager.toggle_ui_element('teams')  # Changed from 'scoreboard' to 'teams'
        elif event.key == pygame.K_F3:
            self.debug_mode = not self.debug_mode

    def _handle_camera_movement(self) -> None:
        """Handle camera movement."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.camera_x = max(0, self.camera_x - self.camera_speed)
        if keys[pygame.K_RIGHT]:
            max_x = (WORLD_WIDTH * TILE_SIZE) - self.screen_width
            self.camera_x = min(max_x, self.camera_x + self.camera_speed)
        if keys[pygame.K_UP]:
            self.camera_y = max(0, self.camera_y - self.camera_speed)
        if keys[pygame.K_DOWN]:
            max_y = (WORLD_HEIGHT * TILE_SIZE) - self.screen_height
            self.camera_y = min(max_y, self.camera_y + self.camera_speed)


def main():
    pygame.init()
    game = GameState(1280, 720)
    running = True

    try:
        while running:
            dt = min(game.clock.tick(60) / 1000.0, 0.1)
            running = game.handle_input()
            game.update(dt)
            game.draw()

        # Generate final story
        story = game.event_manager.generate_story()
        print("\nSimulation Story:")
        print(story)

    finally:
        game.cleanup()


if __name__ == "__main__":
    main()
