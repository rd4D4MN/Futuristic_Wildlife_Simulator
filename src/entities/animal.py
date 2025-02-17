import random
import math
import pygame
from typing import Dict, Any, List, Optional, Tuple
import os
from evolution.genome import Genome
from src.entities.team import Team


class Animal(pygame.sprite.Sprite):
    #########################
    # 1. Initialization
    #########################
    def __init__(self, name: str, data: Dict, genome: Optional[Genome] = None, generation: int = 1):
        """Initialize animal with optional genome for evolved instances."""
        super().__init__()
        self.name = name
        self.original_data = data
        self.generation = generation
        self.age = 0
        
        # Basic attributes - ensure valid health values
        self.max_health = max(1.0, float(data.get('Max_Health', 100.0)))
        self.health = self.max_health
        self.team: Optional['Team'] = None
        self.target = None
        self.world_grid = None
        
        # Position and movement
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0
        self.speed = float(data.get('Speed_Max', 30))
        self.direction = random.uniform(0, 2 * math.pi)
        
        # Combat attributes
        self.attack_multiplier = float(data.get('Attack_Multiplier', 1.0))
        self.armor_rating = float(data.get('Armor_Rating', 1.0))
        self.agility_score = float(data.get('Agility_Score', 100.0))
        self.stamina_rating = float(data.get('Stamina_Rating', 0.0))
        
        # Evolution attributes
        self.genome = genome  # Store the provided genome
        self.maturity_score = float(data.get('Maturity_Score', 0.0))
        self.reproduction_rate = float(data.get('Reproduction_Rate', 1.0))
        self.social_score = float(data.get('Social_Score', 0.5))
        self.generation_time = float(data.get('Generation_Time', 100.0))
        self.predator_pressure = float(data.get('Predator_Pressure', 0.4))
        
        # Environmental attributes
        self.habitat = str(data.get('Habitat', 'Grassland'))
        self.combat_traits = str(data.get('Combat_Traits', 'none'))
        self.natural_weapons = self._parse_natural_weapons(data.get('Natural_Weapons', ''))
        
        # Apply genome if provided
        if genome:
            self._apply_genome(genome)
            # Revalidate health after genome application
            self.max_health = max(1.0, self.max_health)
            self.health = min(self.max_health, max(0, self.health))
        
        # Visual attributes
        self.color = self._parse_color(data.get('Color', 'Brown'))
        self.size = max(10, min(30, math.sqrt(float(data.get('Weight_Max', 50)))))
        self.draw_surface = self._create_draw_surface()
        
        # General attributes
        h_max = data.get("Height_Max", 50.0)
        w_max = data.get("Weight_Max", 10.0)
        self.height = random.uniform(0.5 * h_max, h_max)
        self.weight = random.uniform(0.5 * w_max, w_max)
        self.speed = max(1.0, data.get("Speed_Max", 5.0))

        # Combat attributes
        self.defense = 1.0 + (self.armor_rating - 1.0)
        self.apex_bonus = data.get("Apex_Predator_Bonus", 1.0)
        self.pack_bonus = data.get("Pack_Hunter_Bonus", 1.0)

        # Position and state
        self.state = "wandering"  # Default state
        self.direction_angle = random.random() * 2 * math.pi
        self.direction_timer = 2.0

        # Health and stamina
        self.stamina = max(1.0, data.get("Stamina_Rating", 50.0))
        self.current_stamina = self.stamina
        self.stamina_recovery_rate = 5.0

        # Team affiliation
        self.team = None

        # Habitat and behavior
        self.preferred_habitat = self._parse_habitat(data.get('Habitat', ''))
        self.is_social = 'social' in data.get('Social_Structure', '').lower()
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

        self.age += dt

        if self.team:
            # Team behavior takes precedence
            return
            
        # Solo behavior
        self._update_movement(dt, environment, world_grid, nearby_entities)

    def _update_movement(self, dt: float, environment, world_grid, nearby_entities) -> None:
        """Update movement based on environment and nearby entities."""
        # Random movement with persistence
        if random.random() < 0.02:  # Change direction occasionally
            self.direction += random.uniform(-math.pi/4, math.pi/4)
            
        # Calculate movement
        self.dx = math.cos(self.direction) * self.speed * dt
        self.dy = math.sin(self.direction) * self.speed * dt
        
        # Apply movement if valid position
        new_x = self.x + self.dx
        new_y = self.y + self.dy
        
        if self._is_valid_position(new_x, new_y, world_grid):
            self.x = new_x
            self.y = new_y
        else:
            # Bounce off boundaries
            self.direction += math.pi + random.uniform(-math.pi/4, math.pi/4)
            
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
        habitat_str = self.original_data.get('Habitat', '').lower()
        
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
        habitat_str = self.original_data.get('Habitat', '').lower()
        
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
        """Draw a health bar above the animal with safety checks."""
        # Safety checks for health values
        if not hasattr(self, 'health') or not hasattr(self, 'max_health'):
            return
            
        if self.health is None or self.max_health is None or self.max_health <= 0:
            return
            
        bar_width = 32  # Half of sprite width
        bar_height = 4
        
        # Ensure health values are valid
        health = max(0, min(self.health, self.max_health))
        max_health = max(1, self.max_health)  # Prevent division by zero
        health_ratio = health / max_health
        
        # Ensure ratio is valid
        if not (0 <= health_ratio <= 1):
            health_ratio = 0
            
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
        if self.team and not hasattr(self, '_being_removed'):
            self._being_removed = True  # Mark that we're being removed to prevent recursion
            self.team.remove_member(self)
            delattr(self, '_being_removed')
        self.team = None
    
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

    def _parse_natural_weapons(self, weapons_str: str) -> List[str]:
        """Parse natural weapons string into list."""
        if not weapons_str or weapons_str == 'none':
            return []
        return [w.strip() for w in weapons_str.split(',')]
        
    def _parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """Convert color string to RGB tuple."""
        color_map = {
            'Red': (255, 0, 0),
            'Green': (0, 255, 0),
            'Blue': (0, 0, 255),
            'Yellow': (255, 255, 0),
            'Brown': (139, 69, 19),
            'Black': (0, 0, 0),
            'White': (255, 255, 255),
            'Gray': (128, 128, 128),
            'Orange': (255, 165, 0),
            'Purple': (128, 0, 128)
        }
        
        # Handle multiple colors
        if ',' in color_str:
            colors = color_str.split(',')
            color_str = colors[0].strip()
            
        return color_map.get(color_str, (139, 69, 19))  # Default to brown
        
    def _create_draw_surface(self) -> pygame.Surface:
        """Create the surface for drawing the animal."""
        size = int(self.size * 2)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Base shape
        pygame.draw.circle(surface, self.color, (size//2, size//2), self.size)
        
        # Generation indicator (darker with higher generation)
        if self.generation > 1:
            darkness = min(200, self.generation * 20)
            pygame.draw.circle(
                surface,
                (0, 0, 0, darkness),
                (size//2, size//2),
                self.size//2
            )
        
        return surface
        
    def _apply_genome(self, genome: Genome) -> None:
        """Apply genome traits with safety checks."""
        if not genome or not genome.genes:
            return
            
        # Apply genome traits with validation
        if 'max_health' in genome.genes:
            self.max_health = max(1.0, genome.genes['max_health'].value * 100.0)
            self.health = min(self.max_health, self.health)  # Ensure health doesn't exceed max
        
        # Update attributes from genes
        self.attack_multiplier = genome.genes['attack_multiplier'].value
        self.armor_rating = genome.genes['armor_rating'].value
        self.agility_score = genome.genes['agility_score'].value
        self.stamina_rating = genome.genes['stamina_rating'].value
        self.social_score = genome.genes['social_score'].value
        self.maturity_score = genome.genes['maturity_score'].value
        
        # Recalculate derived attributes
        self.max_health = 100.0 * (1 + self.stamina_rating * 0.5)
        self.health = self.max_health
        
    def take_damage(self, amount: float) -> None:
        """Take damage with safety checks."""
        if not isinstance(amount, (int, float)) or math.isnan(amount):
            return
            
        self.health = max(0, min(self.max_health, self.health - amount))
        
    def heal(self, amount: float) -> None:
        """Heal with safety checks."""
        if not isinstance(amount, (int, float)) or math.isnan(amount):
            return
            
        self.health = max(0, min(self.max_health, self.health + amount))
        

