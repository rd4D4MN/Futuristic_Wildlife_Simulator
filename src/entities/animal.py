import random
import math
import pygame
from typing import Dict, Any, List, Optional, Tuple
import os

class Animal(pygame.sprite.Sprite):
    #########################
    # 1. Initialization
    #########################
    def __init__(self, name: str, attributes: Dict[str, Any]):
        super().__init__()
        # General attributes
        self.name = name
        self.attributes = attributes

        # Physical attributes
        h_max = attributes.get("Height_Max", 50.0)
        w_max = attributes.get("Weight_Max", 10.0)
        self.height = random.uniform(0.5 * h_max, h_max)
        self.weight = random.uniform(0.5 * w_max, w_max)
        self.speed = max(1.0, attributes.get("Speed_Max", 5.0))

        # Combat attributes
        self.defense = 1.0 + (attributes.get("Armor_Rating", 1.0) - 1.0)
        self.attack_multiplier = attributes.get("Attack_Multiplier", 1.0)
        self.apex_bonus = attributes.get("Apex_Predator_Bonus", 1.0)
        self.pack_bonus = attributes.get("Pack_Hunter_Bonus", 1.0)

        # Position and state
        self.x, self.y = 0.0, 0.0
        self.state = "wandering"  # Default state
        self.direction_angle = random.random() * 2 * math.pi
        self.direction_timer = 2.0

        # Health and stamina
        self.health = max(50.0, (self.weight ** 0.5) * 10)
        self.max_health = self.health
        self.stamina = max(1.0, attributes.get("Stamina_Rating", 50.0))
        self.current_stamina = self.stamina
        self.stamina_recovery_rate = 5.0

        # Team affiliation
        self.team = None

        # Habitat and behavior
        self.preferred_habitat = self._parse_habitat(attributes.get('Habitat', ''))
        self.is_social = 'social' in attributes.get('Social_Structure', '').lower()
        self.group_distance = 50 if self.is_social else 100
        self.separation_distance = 20
        self.group_members = []

        # Visual representation
        self.image = self._load_sprite()
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

    #########################
    # 2. Core Behavior
    #########################
    
    def _is_valid_position(self, new_x: float, new_y: float, world_grid) -> bool:
        """Check if new position is valid based on terrain and bounds."""
        # Convert to grid coordinates
        grid_x = int(new_x // 8)
        grid_y = int(new_y // 8)
        
        # Check world boundaries with a safety margin
        margin = 1  # One tile margin
        if not (margin <= grid_x < len(world_grid[0]) - margin and 
                margin <= grid_y < len(world_grid) - margin):
            return False
            
        # Check terrain compatibility
        try:
            terrain = world_grid[grid_y][grid_x]
            if not self.can_survive_in(terrain):
                # Allow some movement in non-preferred terrain to prevent getting stuck
                current_x = int(self.x // 8)
                current_y = int(self.y // 8)
                if abs(current_x - grid_x) <= 1 and abs(current_y - grid_y) <= 1:
                    return True
                return False
            return True
        except IndexError:
            return False

    def update(self, dt: float, environment, world_grid, nearby_entities):
        """Update the animal's position and behavior based on its state."""
        if self.health <= 0:
            return

        # Get terrain effects for current position
        try:
            grid_x = max(0, min(int(self.x // 8), len(world_grid[0]) - 1))
            grid_y = max(0, min(int(self.y // 8), len(world_grid) - 1))
            terrain = world_grid[grid_y][grid_x]
            terrain_effects = environment.get_environment_effects(grid_x, grid_y)
            
            # Update health based on terrain compatibility
            self.can_survive_in(terrain)  # This updates terrain_health_effect
            health_change = self.terrain_health_effect * dt * 5  # 5 health points per second
            self.health = min(self.max_health, max(0, self.health + health_change))
            
            # Apply terrain movement modifier
            effective_speed = self.speed * terrain_effects['movement_speed']
            if terrain not in self.get_optimal_terrains():
                effective_speed *= 0.5  # Slower in non-optimal terrain
            
            # If part of a team, follow team formation
            if self.team:
                target_pos = self.team.get_target_position(self)
                if target_pos:
                    dx = target_pos[0] - self.x
                    dy = target_pos[1] - self.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    
                    if dist > 5:  # Only move if not at position
                        # Calculate movement with terrain effect
                        move_speed = effective_speed * dt
                        move_x = (dx/dist) * move_speed
                        move_y = (dy/dist) * move_speed
                        
                        # Try to move to new position
                        new_x = self.x + move_x
                        new_y = self.y + move_y
                        
                        if self._is_valid_position(new_x, new_y, world_grid):
                            self.x = new_x
                            self.y = new_y
            else:
                # Independent movement
                self._update_independent(dt, effective_speed, world_grid)

            # Clamp position to world bounds with margin
            margin = 8  # One tile margin
            max_x = (len(world_grid[0]) - 2) * 8
            max_y = (len(world_grid) - 2) * 8
            self.x = max(margin, min(self.x, max_x))
            self.y = max(margin, min(self.y, max_y))
            
            # Update sprite position
            self.rect.center = (self.x, self.y)
            
        except IndexError as e:
            print(f"Warning: Animal {self.name} at invalid position ({self.x}, {self.y}), resetting to safe position")
            # Reset to a safe position
            self.x = max(32, min(self.x, (len(world_grid[0]) - 2) * 8))
            self.y = max(32, min(self.y, (len(world_grid) - 2) * 8))
            self.rect.center = (self.x, self.y)

    def _update_independent(self, dt: float, speed: float, world_grid) -> None:
        """Handle movement when not part of a team."""
        # Update wandering direction
        self.direction_timer -= dt
        if self.direction_timer <= 0:
            self.direction_timer = random.uniform(2.0, 4.0)
            self.direction_angle = random.random() * 2 * math.pi

        # Calculate movement
        dx = math.cos(self.direction_angle) * speed * dt
        dy = math.sin(self.direction_angle) * speed * dt
        
        # Try to move
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Check if new position is valid
        if self._is_valid_position(new_x, new_y, world_grid):
            self.x = new_x
            self.y = new_y
        else:
            # If invalid, try random new direction
            self.direction_timer = 0

    def _wander(self, world_grid, effective_speed, dt):
        """Move randomly within valid bounds."""
        if self.direction_timer <= 0:
            self.direction_angle = random.random() * 2 * math.pi
            self.direction_timer = random.uniform(1.0, 3.0)

        movement_x = math.cos(self.direction_angle) * effective_speed * dt
        movement_y = math.sin(self.direction_angle) * effective_speed * dt
        new_x, new_y = self.x + movement_x, self.y + movement_y

        if self._is_valid_position(new_x, new_y, world_grid):
            self.x, self.y = new_x, new_y

        self.direction_timer -= dt

    def _flee(self, nearby_entities, effective_speed, dt):
        """Move away from the nearest threat."""
        threat = self._find_nearest_threat(nearby_entities)
        if threat:
            dx = self.x - threat.x
            dy = self.y - threat.y
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                self.x += (dx / dist) * effective_speed * dt
                self.y += (dy / dist) * effective_speed * dt

    #########################
    # 3. Group and Terrain Logic
    #########################
    def _find_nearest_threat(self, nearby_entities):
        """Find the closest predator or robot."""
        threats = [e for e in nearby_entities if e.type == "predator" or e.type == "robot"]
        return min(threats, key=lambda t: abs(t.x - self.x) + abs(t.y - self.y), default=None)

    def can_survive_in(self, terrain_type: str) -> bool:
        """Check if the animal can survive in the given terrain."""
        habitat_str = self.attributes.get('Habitat', '').lower()
        
        # Direct terrain mappings
        terrain_mappings = {
            'aquatic': ['ocean', 'water', 'marine', 'coastal', 'river', 'lake'],
            'forest': ['forest', 'woodland', 'rainforest', 'jungle'],
            'mountain': ['mountain', 'alpine', 'highland'],
            'desert': ['desert', 'arid', 'sand'],
            'grassland': ['grassland', 'savanna', 'prairie', 'plain'],
            'wetland': ['swamp', 'marsh', 'wetland', 'mangrove']
        }
        
        # Find primary terrain type from habitat
        primary_terrain = 'grassland'  # Default
        for terrain, keywords in terrain_mappings.items():
            if any(keyword in habitat_str for keyword in keywords):
                primary_terrain = terrain
                break
        
        self.preferred_habitat = primary_terrain
        
        # Define terrain compatibility levels
        terrain_compatibility = {
            'aquatic': {
                'optimal': ['aquatic'],
                'survivable': ['wetland'],
                'harmful': ['grassland', 'forest', 'desert', 'mountain']
            },
            'forest': {
                'optimal': ['forest'],
                'survivable': ['grassland', 'wetland'],
                'harmful': ['desert', 'mountain', 'aquatic']
            },
            'mountain': {
                'optimal': ['mountain'],
                'survivable': ['forest', 'grassland'],
                'harmful': ['desert', 'aquatic', 'wetland']
            },
            'desert': {
                'optimal': ['desert'],
                'survivable': ['grassland'],
                'harmful': ['forest', 'mountain', 'aquatic', 'wetland']
            },
            'grassland': {
                'optimal': ['grassland'],
                'survivable': ['forest', 'desert'],
                'harmful': ['mountain', 'aquatic', 'wetland']
            },
            'wetland': {
                'optimal': ['wetland'],
                'survivable': ['aquatic', 'grassland'],
                'harmful': ['desert', 'mountain']
            }
        }
        
        # Get compatibility for current terrain
        compatibility = terrain_compatibility.get(self.preferred_habitat, {})
        if terrain_type in compatibility.get('optimal', []):
            self.terrain_health_effect = 1.0  # Health regeneration
            return True
        elif terrain_type in compatibility.get('survivable', []):
            self.terrain_health_effect = 0.0  # No health change
            return True
        elif terrain_type in compatibility.get('harmful', []):
            self.terrain_health_effect = -1.0  # Health decrease
            return False
        
        return False

    def get_optimal_terrains(self) -> List[str]:
        """Get list of optimal terrains for this animal."""
        habitat_str = self.attributes.get('Habitat', '').lower()
        
        # Direct terrain mappings
        terrain_mappings = {
            'aquatic': ['ocean', 'water', 'marine', 'coastal', 'river', 'lake'],
            'forest': ['forest', 'woodland', 'rainforest', 'jungle'],
            'mountain': ['mountain', 'alpine', 'highland'],
            'desert': ['desert', 'arid', 'sand'],
            'grassland': ['grassland', 'savanna', 'prairie', 'plain'],
            'wetland': ['swamp', 'marsh', 'wetland', 'mangrove']
        }
        
        optimal_terrains = []
        for terrain, keywords in terrain_mappings.items():
            if any(keyword in habitat_str for keyword in keywords):
                optimal_terrains.append(terrain)
        
        return optimal_terrains if optimal_terrains else ['grassland']  # Default to grassland

    #########################
    # 4. Rendering
    #########################
    def draw(self, screen: pygame.Surface, camera_x: int = 0, camera_y: int = 0, show_health_bars: bool = False):
        """Draw the animal and its health bar if enabled."""
        if self.health <= 0:
            return
        screen.blit(self.image, (self.x - camera_x, self.y - camera_y))
        if show_health_bars:
            self._draw_health_bar(screen, camera_x, camera_y)

    def _draw_health_bar(self, screen: pygame.Surface, camera_x: int, camera_y: int):
        """Draw a health bar above the animal."""
        bar_width = 32  # Half of sprite width
        bar_height = 4
        health_ratio = self.health / self.max_health
        fill_width = int(bar_width * health_ratio)
        
        # Center the health bar above the sprite
        bar_x = self.x - camera_x - (bar_width // 2) + 32  # Add half sprite width
        bar_y = self.y - camera_y - 10  # Position above sprite
        
        # Draw background (red)
        pygame.draw.rect(screen, (200, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        # Draw health (green)
        pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, fill_width, bar_height))
        # Draw border
        pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height), 1)

    def cleanup(self):
        """Clean up resources associated with the animal."""
        if hasattr(self, 'image'):
            del self.image  # Delete the sprite image to free memory
    
    #########################
    # 5. Utility Methods
    #########################
    def _load_sprite(self):
        """Load sprite for the animal."""
        filename = self.name.lower().replace(" ", "_") + "_generated.png"
        path = os.path.join("static", "images", "animals", filename)
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (64, 64))
            return img
        else:
            surf = pygame.Surface((64, 64))
            surf.fill((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            return surf

    def _parse_habitat(self, habitat_str: str) -> str:
        """Parse habitat string to determine preferred terrain."""
        habitat_str = habitat_str.lower()
        if any(term in habitat_str for term in ['water', 'marine']):
            return 'aquatic'
        elif 'forest' in habitat_str:
            return 'forest'
        elif 'mountain' in habitat_str:
            return 'mountain'
        elif 'desert' in habitat_str:
            return 'desert'
        return 'grassland'


