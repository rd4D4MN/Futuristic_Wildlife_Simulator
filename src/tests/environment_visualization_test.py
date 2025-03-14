import os
import sys
import pygame
import random
import math
from typing import Dict, List, Tuple

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.environment.environment_system import EnvironmentSystem
from src.entities.animal import Animal
from src.map.map_generator import tile_mapping

# Constants for test environment
TEST_TILE_SIZE = 64  # Much larger tiles for visibility
TEST_WORLD_WIDTH = 20  # Smaller world for testing
TEST_WORLD_HEIGHT = 15
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

class EnvironmentVisualizationTest:
    def __init__(self):
        """Initialize the test environment with larger tiles."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Environment Effects Visualization Test")
        self.clock = pygame.time.Clock()
        
        # Create a simplified world grid with distinct terrain types
        self.world_grid = self._create_test_world_grid()
        
        # Initialize environment system
        self.environment_system = EnvironmentSystem(self.world_grid)
        
        # Camera position
        self.camera_x = 0
        self.camera_y = 0
        self.camera_speed = 10
        
        # Load animal data
        self.animals = self._create_test_animals()
        
        # Font for displaying information
        self.font = pygame.font.SysFont('Arial', 16)
        self.large_font = pygame.font.SysFont('Arial', 24)
        
        # Visual effect overlays
        self.effect_overlays = {
            'rain': self._create_rain_overlay(),
            'snow': self._create_snow_overlay(),
            'heat': self._create_heat_overlay(),
            'wind': self._create_wind_overlay(),
            'night': self._create_night_overlay()
        }
        
        # Particles for weather effects
        self.particles = []
        
        # Running state
        self.running = True
        
    def _create_test_world_grid(self) -> List[List[str]]:
        """Create a test world grid with distinct terrain regions."""
        grid = []
        
        # Create terrain regions
        for y in range(TEST_WORLD_HEIGHT):
            row = []
            for x in range(TEST_WORLD_WIDTH):
                # Create distinct regions for each terrain type
                if x < 4:
                    terrain = "grassland"
                elif x < 8:
                    terrain = "forest"
                elif x < 12:
                    terrain = "desert"
                elif x < 16:
                    terrain = "mountain"
                else:
                    terrain = "aquatic"
                row.append(terrain)
            grid.append(row)
            
        return grid
    
    def _create_test_animals(self) -> List[Animal]:
        """Create test animals for each terrain type."""
        animals = []
        
        # Sample animal data
        animal_data = {
            'Animal': 'Test Animal',
            'Max_Health': 100.0,
            'Speed_Max': 30.0,
            'Attack_Multiplier': 1.0,
            'Armor_Rating': 1.0,
            'Agility_Score': 100.0,
            'Stamina_Rating': 1.0,
            'Weight_Max': 50.0,
            'Height_Max': 50.0,
            'Color': 'Brown'
        }
        
        # Create animals with different preferred habitats
        habitats = ['grassland', 'forest', 'desert', 'mountain', 'aquatic']
        
        for i, habitat in enumerate(habitats):
            # Create 2 animals for each habitat
            for j in range(2):
                animal_data_copy = animal_data.copy()
                animal_data_copy['Habitat'] = habitat
                animal_data_copy['Animal'] = f"{habitat.capitalize()} Animal {j+1}"
                
                animal = Animal(animal_data_copy['Animal'], animal_data_copy)
                
                # Position in appropriate terrain
                x = (i * 4) + 2  # Center of each terrain region
                y = 5 + (j * 4)  # Spaced vertically
                
                animal.x = x * TEST_TILE_SIZE + TEST_TILE_SIZE // 2
                animal.y = y * TEST_TILE_SIZE + TEST_TILE_SIZE // 2
                animal.world_grid = self.world_grid
                
                animals.append(animal)
        
        return animals
    
    def _create_rain_overlay(self) -> pygame.Surface:
        """Create a semi-transparent rain overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 200, 30))  # Blue tint
        return overlay
    
    def _create_snow_overlay(self) -> pygame.Surface:
        """Create a semi-transparent snow overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((200, 200, 255, 30))  # Light blue tint
        return overlay
    
    def _create_heat_overlay(self) -> pygame.Surface:
        """Create a semi-transparent heat overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 100, 0, 30))  # Orange tint
        return overlay
    
    def _create_wind_overlay(self) -> pygame.Surface:
        """Create a semi-transparent wind overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((200, 200, 200, 20))  # Gray tint
        return overlay
    
    def _create_night_overlay(self) -> pygame.Surface:
        """Create a semi-transparent night overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 50, 100))  # Dark blue tint
        return overlay
    
    def _update_particles(self, dt: float) -> None:
        """Update weather particles."""
        # Clear old particles
        self.particles = [p for p in self.particles if p['lifetime'] > 0]
        
        # Add new particles based on weather
        for terrain, conditions in self.environment_system.weather_conditions.items():
            # Rain particles - Increased number for better visibility
            if conditions['precipitation'] > 0.3:
                for _ in range(int(conditions['precipitation'] * 20)):
                    self.particles.append({
                        'type': 'rain',
                        'x': random.randint(0, SCREEN_WIDTH),
                        'y': random.randint(-10, 0),
                        'speed': random.uniform(200, 300),
                        'lifetime': random.uniform(0.5, 1.0),
                        'terrain': terrain
                    })
            
            # Snow particles (if cold) - Increased number for better visibility
            if conditions['temperature'] < 5 and conditions['precipitation'] > 0.2:
                for _ in range(int(conditions['precipitation'] * 15)):
                    self.particles.append({
                        'type': 'snow',
                        'x': random.randint(0, SCREEN_WIDTH),
                        'y': random.randint(-10, 0),
                        'speed': random.uniform(50, 100),
                        'lifetime': random.uniform(1.0, 2.0),
                        'terrain': terrain
                    })
            
            # Heat particles (if hot) - Increased number for better visibility
            if conditions['temperature'] > 30:
                for _ in range(int((conditions['temperature'] - 30) * 2)):
                    self.particles.append({
                        'type': 'heat',
                        'x': random.randint(0, SCREEN_WIDTH),
                        'y': random.randint(SCREEN_HEIGHT - 50, SCREEN_HEIGHT),
                        'speed': random.uniform(-50, -30),
                        'lifetime': random.uniform(0.5, 1.0),
                        'terrain': terrain
                    })
                    
            # Wind particles
            if conditions['wind'] > 15:
                for _ in range(int(conditions['wind'] / 2)):
                    self.particles.append({
                        'type': 'wind',
                        'x': random.randint(0, SCREEN_WIDTH),
                        'y': random.randint(0, SCREEN_HEIGHT),
                        'speed': random.uniform(100, 200),
                        'lifetime': random.uniform(0.3, 0.8),
                        'terrain': terrain
                    })
        
        # Update particle positions
        for particle in self.particles:
            if particle['type'] == 'rain':
                particle['y'] += particle['speed'] * dt
            elif particle['type'] == 'snow':
                particle['y'] += particle['speed'] * dt
                particle['x'] += math.sin(particle['y'] / 30) * 2
            elif particle['type'] == 'heat':
                particle['y'] += particle['speed'] * dt
                particle['x'] += math.sin(particle['y'] / 20) * 3
            elif particle['type'] == 'wind':
                particle['x'] += particle['speed'] * dt
                particle['y'] += math.sin(particle['x'] / 50) * 2
            
            particle['lifetime'] -= dt
    
    def update(self, dt: float) -> None:
        """Update the test environment."""
        # Update environment system
        self.environment_system.update(dt)
        
        # Update animals
        for animal in self.animals:
            animal._update_terrain_effects(dt, self.world_grid)
            
            # Move animals slowly to show speed effects
            if random.random() < 0.05:
                angle = random.uniform(0, 2 * math.pi)
                distance = animal.speed * dt
                animal.x += math.cos(angle) * distance
                animal.y += math.sin(angle) * distance
                
                # Keep within world bounds
                max_x = TEST_WORLD_WIDTH * TEST_TILE_SIZE - 32
                max_y = TEST_WORLD_HEIGHT * TEST_TILE_SIZE - 32
                animal.x = max(32, min(animal.x, max_x))
                animal.y = max(32, min(animal.y, max_y))
        
        # Update weather particles
        self._update_particles(dt)
    
    def handle_input(self) -> bool:
        """Handle user input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
        
        # Camera movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.camera_x = max(0, self.camera_x - self.camera_speed)
        if keys[pygame.K_RIGHT]:
            max_x = TEST_WORLD_WIDTH * TEST_TILE_SIZE - SCREEN_WIDTH
            self.camera_x = min(max_x, self.camera_x + self.camera_speed)
        if keys[pygame.K_UP]:
            self.camera_y = max(0, self.camera_y - self.camera_speed)
        if keys[pygame.K_DOWN]:
            max_y = TEST_WORLD_HEIGHT * TEST_TILE_SIZE - SCREEN_HEIGHT
            self.camera_y = min(max_y, self.camera_y + self.camera_speed)
        
        return True
    
    def draw(self) -> None:
        """Draw the test environment."""
        self.screen.fill((0, 0, 0))
        
        # Draw world grid
        self._draw_world_grid()
        
        # Draw animals
        for animal in self.animals:
            self._draw_animal(animal)
        
        # Draw weather effects
        self._draw_weather_effects()
        
        # Draw UI
        self._draw_ui()
        
        # Update display
        pygame.display.flip()
    
    def _draw_world_grid(self) -> None:
        """Draw the world grid with terrain types."""
        start_x = max(0, self.camera_x // TEST_TILE_SIZE)
        end_x = min(TEST_WORLD_WIDTH, (self.camera_x + SCREEN_WIDTH) // TEST_TILE_SIZE + 1)
        start_y = max(0, self.camera_y // TEST_TILE_SIZE)
        end_y = min(TEST_WORLD_HEIGHT, (self.camera_y + SCREEN_HEIGHT) // TEST_TILE_SIZE + 1)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                terrain = self.world_grid[y][x]
                color = tile_mapping.get(terrain, (100, 100, 100))
                
                # Draw terrain tile
                rect = pygame.Rect(
                    x * TEST_TILE_SIZE - self.camera_x,
                    y * TEST_TILE_SIZE - self.camera_y,
                    TEST_TILE_SIZE,
                    TEST_TILE_SIZE
                )
                pygame.draw.rect(self.screen, color, rect)
                
                # Draw grid lines
                pygame.draw.rect(self.screen, (0, 0, 0), rect, 1)
                
                # Draw terrain label
                label = self.font.render(terrain, True, (0, 0, 0))
                self.screen.blit(
                    label,
                    (rect.x + 5, rect.y + 5)
                )
    
    def _draw_animal(self, animal: Animal) -> None:
        """Draw an animal with visual indicators for environmental effects."""
        if animal.health <= 0:
            return
        
        # Draw animal
        screen_x = animal.x - self.camera_x
        screen_y = animal.y - self.camera_y
        
        # Skip if off-screen
        if (screen_x < -64 or screen_x > SCREEN_WIDTH + 64 or
            screen_y < -64 or screen_y > SCREEN_HEIGHT + 64):
            return
        
        # Draw terrain effect aura around animal
        self._draw_animal_aura(animal, screen_x, screen_y)
        
        # Draw animal circle
        color = animal.color
        pygame.draw.circle(self.screen, color, (int(screen_x), int(screen_y)), int(animal.size))
        
        # Draw animal name - Moved further up
        name_label = self.font.render(animal.name, True, (255, 255, 255))
        name_bg = pygame.Surface((name_label.get_width() + 4, name_label.get_height() + 4), pygame.SRCALPHA)
        name_bg.fill((0, 0, 0, 150))
        self.screen.blit(name_bg, (screen_x - name_label.get_width() // 2 - 2, screen_y - 60 - 2))
        self.screen.blit(
            name_label,
            (screen_x - name_label.get_width() // 2, screen_y - 60)
        )
        
        # Draw health bar - Moved closer to animal
        health_width = 60
        health_height = 8
        health_x = screen_x - health_width // 2
        health_y = screen_y - 30
        
        # Background for health bar
        health_bg = pygame.Surface((health_width + 4, health_height + 4), pygame.SRCALPHA)
        health_bg.fill((0, 0, 0, 150))
        self.screen.blit(health_bg, (health_x - 2, health_y - 2))
        
        # Background
        pygame.draw.rect(self.screen, (200, 0, 0), (health_x, health_y, health_width, health_height))
        # Health
        health_fill = (animal.health / animal.max_health) * health_width
        pygame.draw.rect(self.screen, (0, 200, 0), (health_x, health_y, health_fill, health_height))
        # Border
        pygame.draw.rect(self.screen, (0, 0, 0), (health_x, health_y, health_width, health_height), 1)
        
        # Create a background for effect indicators
        effect_panel_width = 100
        effect_panel_height = 60
        effect_panel_x = screen_x - effect_panel_width // 2
        effect_panel_y = screen_y + 20
        
        # Only create panel if there are effects to show
        has_effects = (animal.terrain_health_effect != 0 or animal.terrain_speed_effect != 1.0)
        
        if has_effects:
            effect_bg = pygame.Surface((effect_panel_width, effect_panel_height), pygame.SRCALPHA)
            effect_bg.fill((0, 0, 0, 100))
            self.screen.blit(effect_bg, (effect_panel_x, effect_panel_y))
        
        # Draw speed indicator
        speed_label = self.font.render(f"Speed: {animal.speed:.1f}", True, (255, 255, 255))
        self.screen.blit(
            speed_label,
            (screen_x - speed_label.get_width() // 2, effect_panel_y + 5)
        )
        
        # Draw terrain effect indicators
        effect_y = effect_panel_y + 25
        
        # Health effect
        if animal.terrain_health_effect > 0:
            effect_label = self.font.render("Health +", True, (0, 255, 0))
            self.screen.blit(effect_label, (screen_x - effect_label.get_width() // 2, effect_y))
            effect_y += 20
        elif animal.terrain_health_effect < 0:
            effect_label = self.font.render("Health -", True, (255, 0, 0))
            self.screen.blit(effect_label, (screen_x - effect_label.get_width() // 2, effect_y))
            effect_y += 20
        
        # Speed effect
        speed_effect = (animal.terrain_speed_effect - 1.0) * 100
        if speed_effect > 0:
            effect_label = self.font.render(f"Speed +{int(speed_effect)}%", True, (0, 255, 0))
            self.screen.blit(effect_label, (screen_x - effect_label.get_width() // 2, effect_y))
        elif speed_effect < 0:
            effect_label = self.font.render(f"Speed {int(speed_effect)}%", True, (255, 0, 0))
            self.screen.blit(effect_label, (screen_x - effect_label.get_width() // 2, effect_y))
    
    def _draw_animal_aura(self, animal, screen_x, screen_y):
        """Draw an aura around the animal based on terrain effects."""
        aura_size = int(animal.size * 1.5)
        
        # Health effect aura
        if animal.terrain_health_effect > 0:
            # Healing aura (green)
            aura = pygame.Surface((aura_size * 2, aura_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (0, 255, 0, 50), (aura_size, aura_size), aura_size)
            self.screen.blit(aura, (screen_x - aura_size, screen_y - aura_size))
            
            # Add healing particles
            if random.random() < 0.1:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, animal.size)
                particle_x = screen_x + math.cos(angle) * distance
                particle_y = screen_y + math.sin(angle) * distance
                
                pygame.draw.circle(
                    self.screen,
                    (100, 255, 100),
                    (int(particle_x), int(particle_y)),
                    2
                )
                
        elif animal.terrain_health_effect < 0:
            # Harmful aura (red)
            aura = pygame.Surface((aura_size * 2, aura_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (255, 0, 0, 50), (aura_size, aura_size), aura_size)
            self.screen.blit(aura, (screen_x - aura_size, screen_y - aura_size))
            
            # Add damage particles
            if random.random() < 0.1:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, animal.size)
                particle_x = screen_x + math.cos(angle) * distance
                particle_y = screen_y + math.sin(angle) * distance
                
                pygame.draw.circle(
                    self.screen,
                    (255, 100, 100),
                    (int(particle_x), int(particle_y)),
                    2
                )
        
        # Speed effect indicator
        if animal.terrain_speed_effect != 1.0:
            if animal.terrain_speed_effect > 1.0:
                # Speed boost (blue trail)
                for i in range(3):
                    offset = (i + 1) * 5
                    alpha = 150 - (i * 50)
                    trail = pygame.Surface((animal.size * 2, animal.size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(trail, (100, 100, 255, alpha), (animal.size, animal.size), animal.size - i)
                    self.screen.blit(trail, (screen_x - animal.size - offset, screen_y - animal.size))
            else:
                # Slowed (amber glow)
                slow_indicator = pygame.Surface((aura_size * 2, aura_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(slow_indicator, (255, 200, 0, 70), (aura_size, aura_size), aura_size)
                self.screen.blit(slow_indicator, (screen_x - aura_size, screen_y - aura_size))
    
    def _draw_weather_effects(self) -> None:
        """Draw weather effects based on environment conditions."""
        # Get current terrain at center of screen
        center_x = int((self.camera_x + SCREEN_WIDTH // 2) // TEST_TILE_SIZE)
        center_y = int((self.camera_y + SCREEN_HEIGHT // 2) // TEST_TILE_SIZE)
        
        if 0 <= center_x < TEST_WORLD_WIDTH and 0 <= center_y < TEST_WORLD_HEIGHT:
            current_terrain = self.world_grid[center_y][center_x]
            weather = self.environment_system.weather_conditions.get(current_terrain, {})
            
            # Apply weather overlays
            if weather.get('precipitation', 0) > 0.3:
                if weather.get('temperature', 20) < 5:
                    self.screen.blit(self.effect_overlays['snow'], (0, 0))
                else:
                    self.screen.blit(self.effect_overlays['rain'], (0, 0))
            
            if weather.get('temperature', 20) > 30:
                self.screen.blit(self.effect_overlays['heat'], (0, 0))
            
            if weather.get('wind', 0) > 15:
                self.screen.blit(self.effect_overlays['wind'], (0, 0))
            
            # Apply time of day overlay
            if self.environment_system.time_of_day < 6 or self.environment_system.time_of_day > 18:
                night_overlay = self.effect_overlays['night'].copy()
                # Adjust darkness based on time
                if 5 <= self.environment_system.time_of_day < 6 or 18 < self.environment_system.time_of_day <= 19:
                    # Dawn/dusk - lighter
                    night_overlay.set_alpha(50)
                else:
                    # Night - darker
                    night_overlay.set_alpha(100)
                self.screen.blit(night_overlay, (0, 0))
        
        # Draw particles
        for particle in self.particles:
            terrain_x = int(particle['x'] + self.camera_x) // TEST_TILE_SIZE
            if 0 <= terrain_x < TEST_WORLD_WIDTH:
                terrain = self.world_grid[0][terrain_x]  # Use top row for simplicity
                
                # Only draw particles for the current terrain type
                if terrain == particle['terrain']:
                    if particle['type'] == 'rain':
                        pygame.draw.line(
                            self.screen,
                            (100, 100, 255),
                            (particle['x'], particle['y']),
                            (particle['x'] - 1, particle['y'] + 10),
                            2
                        )
                    elif particle['type'] == 'snow':
                        pygame.draw.circle(
                            self.screen,
                            (255, 255, 255),
                            (int(particle['x']), int(particle['y'])),
                            2
                        )
                    elif particle['type'] == 'heat':
                        pygame.draw.circle(
                            self.screen,
                            (255, 200, 100),
                            (int(particle['x']), int(particle['y'])),
                            3
                        )
                    elif particle['type'] == 'wind':
                        pygame.draw.line(
                            self.screen,
                            (200, 200, 200),
                            (particle['x'], particle['y']),
                            (particle['x'] - 15, particle['y']),
                            1
                        )
        
        # Draw terrain effect indicators at the bottom of the screen
        self._draw_terrain_effect_indicators()
    
    def _draw_terrain_effect_indicators(self) -> None:
        """Draw indicators for terrain effects at the bottom of the screen."""
        indicator_height = 30
        indicator_y = SCREEN_HEIGHT - indicator_height - 10
        
        # Get current terrain at center of screen
        center_x = int((self.camera_x + SCREEN_WIDTH // 2) // TEST_TILE_SIZE)
        center_y = int((self.camera_y + SCREEN_HEIGHT // 2) // TEST_TILE_SIZE)
        
        if 0 <= center_x < TEST_WORLD_WIDTH and 0 <= center_y < TEST_WORLD_HEIGHT:
            current_terrain = self.world_grid[center_y][center_x]
            effects = self.environment_system.get_environment_effects(center_x, center_y)
            
            # Create indicators
            indicators = []
            
            # Movement speed indicator
            speed_effect = effects.get('movement_speed', 1.0)
            if speed_effect < 0.8:
                indicators.append(("Movement Slowed", (255, 100, 100)))
            elif speed_effect > 1.1:
                indicators.append(("Movement Boosted", (100, 255, 100)))
                
            # Stamina drain indicator
            stamina_effect = effects.get('stamina_drain', 1.0)
            if stamina_effect > 1.2:
                indicators.append(("High Stamina Drain", (255, 100, 100)))
            
            # Visibility indicator
            visibility_effect = effects.get('visibility', 1.0)
            if visibility_effect < 0.7:
                indicators.append(("Low Visibility", (255, 255, 100)))
            
            # Weather indicators
            weather = self.environment_system.weather_conditions.get(current_terrain, {})
            
            if weather.get('precipitation', 0) > 0.5:
                indicators.append(("Heavy Rain", (100, 100, 255)))
            elif weather.get('precipitation', 0) > 0.3:
                indicators.append(("Light Rain", (150, 150, 255)))
                
            if weather.get('temperature', 20) > 35:
                indicators.append(("Extreme Heat", (255, 100, 0)))
            elif weather.get('temperature', 20) > 30:
                indicators.append(("Hot", (255, 150, 50)))
            elif weather.get('temperature', 20) < 0:
                indicators.append(("Freezing", (200, 200, 255)))
            elif weather.get('temperature', 20) < 5:
                indicators.append(("Cold", (150, 150, 255)))
                
            if weather.get('wind', 0) > 25:
                indicators.append(("Strong Wind", (200, 200, 200)))
            elif weather.get('wind', 0) > 15:
                indicators.append(("Windy", (220, 220, 220)))
            
            # Draw indicators
            if indicators:
                # If we have too many indicators, use multiple rows
                max_indicators_per_row = 4
                
                if len(indicators) <= max_indicators_per_row:
                    # Single row layout
                    self._draw_indicator_row(indicators, indicator_y)
                else:
                    # Multi-row layout
                    rows = []
                    for i in range(0, len(indicators), max_indicators_per_row):
                        rows.append(indicators[i:i+max_indicators_per_row])
                    
                    # Draw each row
                    for i, row in enumerate(rows):
                        row_y = indicator_y - (len(rows) - 1 - i) * (indicator_height + 5)
                        self._draw_indicator_row(row, row_y)
    
    def _draw_indicator_row(self, indicators, y_position):
        """Draw a row of indicators at the specified y position."""
        indicator_height = 30
        
        # Calculate total width needed
        total_width = sum(self.font.size(text)[0] + 20 for text, _ in indicators)
        spacing = 10
        total_width += spacing * (len(indicators) - 1)
        
        # Start position
        start_x = (SCREEN_WIDTH - total_width) // 2
        
        for text, color in indicators:
            text_width = self.font.size(text)[0]
            indicator_width = text_width + 20
            
            # Draw indicator background
            indicator_bg = pygame.Surface((indicator_width, indicator_height), pygame.SRCALPHA)
            indicator_bg.fill((0, 0, 0, 150))
            self.screen.blit(indicator_bg, (start_x, y_position))
            
            # Draw indicator text
            text_surf = self.font.render(text, True, color)
            self.screen.blit(text_surf, (start_x + 10, y_position + (indicator_height - text_surf.get_height()) // 2))
            
            # Draw border
            pygame.draw.rect(self.screen, color, (start_x, y_position, indicator_width, indicator_height), 1)
            
            # Update start_x for next indicator
            start_x += indicator_width + spacing
    
    def _draw_ui(self) -> None:
        """Draw UI elements with environment information."""
        # Draw environment info panel
        panel_width = 300
        panel_height = 250  # Increased from 200 to 250 to fit all parameters
        panel_x = SCREEN_WIDTH - panel_width - 10
        panel_y = 10
        
        # Panel background - Fix the alpha issue
        panel_bg = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_bg.fill((0, 0, 0, 150))
        self.screen.blit(panel_bg, (panel_x, panel_y))
        pygame.draw.rect(self.screen, (255, 255, 255), (panel_x, panel_y, panel_width, panel_height), 2)
        
        # Get current terrain at center of screen
        center_x = int((self.camera_x + SCREEN_WIDTH // 2) // TEST_TILE_SIZE)
        center_y = int((self.camera_y + SCREEN_HEIGHT // 2) // TEST_TILE_SIZE)
        
        if 0 <= center_x < TEST_WORLD_WIDTH and 0 <= center_y < TEST_WORLD_HEIGHT:
            current_terrain = self.world_grid[center_y][center_x]
            
            # Draw terrain info
            title = self.large_font.render(f"Current Terrain: {current_terrain}", True, (255, 255, 255))
            self.screen.blit(title, (panel_x + 10, panel_y + 10))
            
            # Draw weather info
            weather = self.environment_system.weather_conditions.get(current_terrain, {})
            
            y_offset = 50
            weather_info = [
                f"Time: {self.environment_system.time_of_day:.1f} hours",
                f"Season: {self.environment_system.season}",
                f"Temperature: {weather.get('temperature', 0):.1f}°C",
                f"Precipitation: {weather.get('precipitation', 0):.2f}",
                f"Wind: {weather.get('wind', 0):.1f} km/h"
            ]
            
            for info in weather_info:
                info_label = self.font.render(info, True, (255, 255, 255))
                self.screen.blit(info_label, (panel_x + 10, panel_y + y_offset))
                y_offset += 25
            
            # Draw terrain effects
            effects = self.environment_system.get_environment_effects(center_x, center_y)
            
            effects_info = [
                f"Movement Speed: {effects.get('movement_speed', 1.0):.2f}x",
                f"Stamina Drain: {effects.get('stamina_drain', 1.0):.2f}x",
                f"Visibility: {effects.get('visibility', 1.0):.2f}x"
            ]
            
            y_offset += 10
            for info in effects_info:
                info_label = self.font.render(info, True, (255, 255, 255))
                self.screen.blit(info_label, (panel_x + 10, panel_y + y_offset))
                y_offset += 25
    
    def run(self) -> None:
        """Run the test environment."""
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.1)
            
            if not self.handle_input():
                self.running = False
                
            self.update(dt)
            self.draw()
        
        pygame.quit()


def main():
    """Run the environment visualization test."""
    test = EnvironmentVisualizationTest()
    test.run()


if __name__ == "__main__":
    main() 