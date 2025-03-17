import random
import math
import pygame
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
import os
from src.evolution.genome import Genome

if TYPE_CHECKING:
    from src.entities.team import Team
    from src.resources.resource_system import ResourceSystem


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
        self.base_speed = float(data.get('Speed_Max', 30)) * (32 / 8)  # Scale speed based on tile size (32px vs original 8px)
        self.speed = self.base_speed  # Current speed (may be modified by terrain)
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
        self.preferred_habitat = self._parse_habitat(self.habitat)
        self.terrain_health_effect = 0.0  # Default: no effect
        self.terrain_speed_effect = 1.0   # Default: normal speed
        self.current_terrain = None
        self.terrain_effect_timer = 0.0   # Timer for periodic terrain effects
        
        # Handle combat traits with proper validation
        combat_traits = data.get('Combat_Traits', 'none')
        if isinstance(combat_traits, list):
            self.combat_traits = ','.join(combat_traits)
        else:
            self.combat_traits = str(combat_traits)
        self.natural_weapons = self._parse_natural_weapons(data.get('Natural_Weapons', ''))
        
        # Apply genome if provided
        if genome:
            self._apply_genome(genome)
            # Revalidate health after genome application
            self.max_health = max(1.0, self.max_health)
            self.health = min(self.max_health, max(0, self.health))
            
        # Apply combat traits from evolution data if provided
        if 'combat_traits' in data:
            self.combat_traits = str(data['combat_traits'])
        
        # Visual attributes
        self.color = self._parse_color(data.get('Color', 'Brown'))
        self.size = max(3, min(15, math.sqrt(float(data.get('Weight_Max', 50))) * 0.5))  # Further reduced size
        self.draw_surface = self._create_draw_surface()
        
        # General attributes
        h_max = data.get("Height_Max", 50.0)
        w_max = data.get("Weight_Max", 10.0)
        self.height = random.uniform(0.5 * h_max, h_max)
        self.weight = random.uniform(0.5 * w_max, w_max)

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
        self.is_social = 'social' in data.get('Social_Structure', '').lower()
        self.group_distance = 50 if self.is_social else 100
        self.separation_distance = 20
        self.group_members = []

        # Resource seeking behavior
        self.resource_target = None
        self.resource_target_type = None
        self.last_resource_search = 0
        self.resource_search_interval = 5.0  # Search every 5 seconds
        self.health_threshold = 0.5  # Seek resources when health below 50%

        # Visual representation
        self.image = self._load_sprite()
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

        # New attributes for animal behavior
        self.mood_points = 100  # Mood points affect behavior
        self.hunger = 0  # Hunger level
        self.thirst = 0  # Thirst level
        self.sleepiness = 0  # Sleepiness level
        self.social_needs = 0  # Social interaction needs

    #########################
    # 2. Core Behavior
    #########################
    
    def _is_valid_position(self, new_x: float, new_y: float, world_grid) -> bool:
        """Check if new position is valid based on terrain. Allows wrapping horizontally but not vertically."""
        # Check for NaN values first to prevent errors
        if math.isnan(new_x) or math.isnan(new_y):
            return False
            
        # Get world dimensions
        world_width = len(world_grid[0])
        world_height = len(world_grid)
        
        # Apply horizontal wrapping
        grid_x = int(new_x // 32) % world_width
        
        # Check vertical bounds with a safety margin
        grid_y = int(new_y // 32)
        margin = 1  # One tile margin
        if not (margin <= grid_y < world_height - margin):
            return False
        
        # Check terrain - allow movement into any terrain, but with consequences
        try:
            # We'll still check the terrain type, but we won't restrict movement
            # The consequences will be applied in _update_terrain_effects
            return True
        except IndexError:
            return False

    def update(self, dt: float, environment, world_grid, nearby_entities, resource_system=None):
        """Update animal behavior with improved resource handling."""
        # Skip if dead
        if self.health <= 0:
            return
            
        # Update terrain effects
        self._update_terrain_effects(dt, world_grid)
        
        # Update movement
        self._update_movement(dt, environment, world_grid, nearby_entities)
        
        # Handle resource gathering if we're at a resource
        if resource_system and hasattr(self, 'state') and self.state == "at_resource":
            grid_x, grid_y = int(self.x // 32), int(self.y // 32)
            resources = resource_system.get_resources_at(grid_x, grid_y)
            
            for resource in resources:
                if resource['amount'] > 0:
                    # Check if we can gather this resource
                    can_gather = False
                    
                    if resource['type'] == 'food_plant' and self._can_eat_plants():
                        can_gather = True
                    elif resource['type'] == 'food_meat' and self._can_eat_meat():
                        can_gather = True
                    elif resource['type'] in ['water', 'medicinal']:
                        can_gather = True
                    elif hasattr(self, 'team') and self.team and resource['type'] in ['wood', 'stone', 'minerals']:
                        can_gather = True
                        
                    if can_gather:
                        # Gather the resource
                        gather_amount = min(5, resource['amount'])
                        actual_gathered = resource_system.gather_resource(
                            grid_x, grid_y, resource['type'], gather_amount
                        )
                        
                        if actual_gathered > 0:
                            # If in a team, add to team inventory
                            if hasattr(self, 'team') and self.team:
                                if hasattr(self.team, 'inventory'):
                                    self.team.inventory[resource['type']] += actual_gathered
                            else:
                                # Not in a team, use resource directly
                                if resource['type'] == 'food_plant' and self._can_eat_plants():
                                    self.heal(actual_gathered * 2)
                                elif resource['type'] == 'food_meat' and self._can_eat_meat():
                                    self.heal(actual_gathered * 2)
                                elif resource['type'] == 'water':
                                    self.heal(actual_gathered)
                                elif resource['type'] == 'medicinal':
                                    self.heal(actual_gathered * 3)
                            
                            # Reset resource target after successful gathering
                            self.resource_target = None
                            self.state = "seeking_resource"
                            
                            # Look for a new resource after a delay
                            if resource_system and random.random() < 0.3:
                                self._find_resource_target(resource_system)
                            
                            break
        
        # Find new resource targets occasionally
        if resource_system and random.random() < 0.01:
            self._find_resource_target(resource_system)

        # Update new behaviors
        self.hunger += dt * 0.1  # Increase hunger over time
        self.thirst += dt * 0.1  # Increase thirst over time
        self.sleepiness += dt * 0.1  # Increase sleepiness over time
        self.social_needs += dt * 0.1  # Increase social needs over time

        # Decision-making logic
        if self.hunger > 70:
            # Find food and eat
            pass
        if self.thirst > 70:
            # Find water and drink
            pass
        if self.sleepiness > 70:
            # Find a safe place to sleep
            pass
        if self.social_needs > 70:
            # Find other animals to team up with
            pass

    def _update_terrain_effects(self, dt: float, world_grid):
        """Apply effects based on the current terrain with more noticeable effects."""
        # Validate input
        if dt <= 0 or math.isnan(dt):
            return
            
        # Get current terrain
        current_terrain = self._get_current_terrain(world_grid)
        self.current_terrain = current_terrain
        
        # Check terrain compatibility
        compatibility = self._get_terrain_compatibility(current_terrain)
        
        # Apply terrain effects based on compatibility
        if compatibility == 'optimal':
            # In optimal terrain: health regeneration and normal speed
            self.terrain_health_effect = 1.0
            self.terrain_speed_effect = 1.0
            
            # Heal slowly in optimal terrain
            self.terrain_effect_timer += dt
            if self.terrain_effect_timer >= 5.0:  # Every 5 seconds
                self.heal(self.max_health * 0.01)  # Heal 1% of max health
                self.terrain_effect_timer = 0.0
                
        elif compatibility == 'survivable':
            # In survivable terrain: no health effect, slightly reduced speed
            self.terrain_health_effect = 0.0
            self.terrain_speed_effect = 0.8
            self.terrain_effect_timer = 0.0
            
        elif compatibility == 'harmful':
            # In harmful terrain: health decrease and greatly reduced speed
            self.terrain_health_effect = -1.0
            self.terrain_speed_effect = 0.4
            
            # Take damage in harmful terrain - more damage for aquatic animals on land
            self.terrain_effect_timer += dt
            damage_multiplier = 2.0 if self.preferred_habitat == 'aquatic' and current_terrain != 'aquatic' and current_terrain != 'wetland' else 1.0
            
            if self.terrain_effect_timer >= 3.0:  # Every 3 seconds
                self.take_damage(self.max_health * 0.02 * damage_multiplier)  # Lose 2-4% of max health
                self.terrain_effect_timer = 0.0
        
        # Apply speed effect with validation
        if not math.isnan(self.base_speed) and not math.isnan(self.terrain_speed_effect):
            self.speed = self.base_speed * self.terrain_speed_effect
        else:
            # Reset to default if NaN values are detected
            self.speed = 30.0  # Default speed

    def _get_current_terrain(self, world_grid) -> str:
        """Get the current terrain type at the animal's position with horizontal wrapping."""
        try:
            # Check for NaN values first to prevent errors
            if math.isnan(self.x) or math.isnan(self.y):
                return 'grassland'  # Default if coordinates are invalid
                
            # Get world dimensions
            world_width = len(world_grid[0])
            world_height = len(world_grid)
            
            # Calculate grid position with horizontal wrapping only
            grid_x = int(self.x // 32) % world_width
            grid_y = int(self.y // 32)
            
            # Check if within vertical bounds
            if 0 <= grid_y < world_height:
                return world_grid[grid_y][grid_x]
            return 'grassland'  # Default if out of vertical bounds
        except (IndexError, TypeError):
            return 'grassland'  # Default if error

    def _update_movement(self, dt: float, environment, world_grid, nearby_entities) -> None:
        """Update animal movement based on state and surroundings."""
        # Skip movement if part of a team (team will handle movement)
        if hasattr(self, 'team') and self.team:
            return
            
        # Calculate terrain-adjusted speed
        terrain = self._get_current_terrain(world_grid)
        effective_speed = self.speed * self._get_terrain_speed_modifier(terrain)
        
        # Check for threats first
        threat = self._find_nearest_threat(nearby_entities)
        if threat:
            # Flee from threat
            self.state = "fleeing"
            self._flee(threat, effective_speed, dt)
            return
            
        # Handle resource seeking
        if self.state == "seeking_resource" and hasattr(self, 'resource_target'):
            # Move towards resource
            self._move_to_resource(dt, world_grid)
            return
            
        # Default to wandering
        self.state = "wandering"
        self._wander(world_grid, effective_speed, dt)

    def _wander(self, world_grid, effective_speed, dt):
        """Wander around randomly with terrain-adjusted speed."""
        # Change direction occasionally
        if random.random() < 0.02:
            self.direction += random.uniform(-math.pi/4, math.pi/4)
            
        # Calculate movement
        dx = math.cos(self.direction) * effective_speed * dt
        dy = math.sin(self.direction) * effective_speed * dt
        
        # Apply movement if valid position
        new_x = self.x + dx
        new_y = self.y + dy
        
        if self._is_valid_position(new_x, new_y, world_grid):
            self.x = new_x
            self.y = new_y
        else:
            # Bounce off boundaries
            self.direction += math.pi + random.uniform(-math.pi/4, math.pi/4)
    
    def _flee(self, threat, effective_speed, dt):
        """Flee from a threat with terrain-adjusted speed."""
        # Calculate direction away from threat
        dx = self.x - threat.x
        dy = self.y - threat.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 0:
            # Normalize and apply speed
            dx = dx / distance * effective_speed * dt
            dy = dy / distance * effective_speed * dt
            
            # Apply movement
            self.x += dx
            self.y += dy

    #########################
    # 3. Group and Terrain Logic
    #########################
    def _find_nearest_threat(self, nearby_entities):
        """Find the nearest threat entity."""
        threats = []
        
        for entity in nearby_entities:
            # Check if entity is a robot
            if hasattr(entity, '__class__') and entity.__class__.__name__ == 'Robot':
                threats.append(entity)
                continue
                
            # Check if entity is a predator animal
            if (hasattr(entity, 'original_data') and 
                entity.original_data.get('Diet_Type', '').lower() == 'carnivore' and
                entity != self):
                threats.append(entity)
        
        if not threats:
            return None
            
        # Find the closest threat
        closest = None
        min_dist = float('inf')
        
        for threat in threats:
            dx = threat.x - self.x
            dy = threat.y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist < min_dist:
                min_dist = dist
                closest = threat
                
        return closest

    def can_survive_in(self, terrain_type: str) -> bool:
        """Check if the animal can survive in the given terrain."""
        compatibility = self._get_terrain_compatibility(terrain_type)
        return compatibility in ['optimal', 'survivable']
    
    def _get_terrain_compatibility(self, terrain: str) -> str:
        """Determine if a terrain is optimal, survivable, or harmful for this animal."""
        if not terrain:
            return 'survivable'  # Default if no terrain
            
        # Handle transition terrains
        if terrain in ['forest_edge', 'wooded_hills']:
            if self.preferred_habitat == 'forest':
                return 'optimal'
            elif self.preferred_habitat in ['grassland', 'mountain']:
                return 'survivable'
            else:
                return 'harmful'
                
        elif terrain == 'savanna':
            if self.preferred_habitat in ['grassland', 'desert']:
                return 'optimal'
            elif self.preferred_habitat == 'forest':
                return 'survivable'
            else:
                return 'harmful'
                
        elif terrain == 'hills':
            if self.preferred_habitat in ['grassland', 'mountain']:
                return 'optimal'
            elif self.preferred_habitat == 'forest':
                return 'survivable'
            else:
                return 'harmful'
                
        elif terrain == 'wetland':
            if self.preferred_habitat in ['aquatic', 'grassland']:
                return 'optimal'
            elif self.preferred_habitat == 'forest':
                return 'survivable'
            else:
                return 'harmful'
                
        elif terrain == 'beach':
            if self.preferred_habitat in ['aquatic', 'desert']:
                return 'optimal'
            elif self.preferred_habitat == 'grassland':
                return 'survivable'
            else:
                return 'harmful'
        
        # Handle base terrains
        elif terrain == self.preferred_habitat:
            return 'optimal'
        elif (
            (self.preferred_habitat == 'forest' and terrain in ['grassland', 'wetland']) or
            (self.preferred_habitat == 'grassland' and terrain in ['forest', 'desert', 'wetland']) or
            (self.preferred_habitat == 'desert' and terrain in ['grassland']) or
            (self.preferred_habitat == 'mountain' and terrain in ['grassland', 'forest']) or
            (self.preferred_habitat == 'aquatic' and terrain in ['wetland'])
        ):
            return 'survivable'
        else:
            return 'harmful'

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
            
        # Validate position to prevent rendering issues
        if math.isnan(self.x) or math.isnan(self.y):
            return
        
        # Store camera coordinates for use in other methods
        self.camera_x = camera_x
        self.camera_y = camera_y
        
        # Draw terrain effect aura
        self._draw_terrain_effect_aura(screen, camera_x, camera_y)
        
        # Draw the animal
        screen.blit(self.image, (self.x - camera_x, self.y - camera_y))
        
        # Draw state indicator (moved above health bar)
        self._draw_state_indicator(screen, self.x - camera_x + 32, self.y - camera_y - 30)
            
        if show_health_bars:
            self._draw_health_bar(screen, camera_x, camera_y)

    def _draw_terrain_effect_aura(self, screen: pygame.Surface, camera_x: int, camera_y: int):
        """Draw an aura around the animal based on terrain effects."""
        if not hasattr(self, 'terrain_health_effect') or not hasattr(self, 'terrain_speed_effect'):
            return
            
        screen_x = self.x - camera_x + 32  # Center of sprite
        screen_y = self.y - camera_y + 32
        aura_size = 40  # Size of the aura
        
        # Health effect aura
        if self.terrain_health_effect > 0:
            # Healing aura (green)
            aura = pygame.Surface((aura_size * 2, aura_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (0, 255, 0, 50), (aura_size, aura_size), aura_size)
            screen.blit(aura, (screen_x - aura_size, screen_y - aura_size))
            
            # Add healing particles
            if random.random() < 0.1:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, 20)
                particle_x = screen_x + math.cos(angle) * distance
                particle_y = screen_y + math.sin(angle) * distance
                
                pygame.draw.circle(
                    screen,
                    (100, 255, 100),
                    (int(particle_x), int(particle_y)),
                    2
                )
                
        elif self.terrain_health_effect < 0:
            # Harmful aura (red)
            aura = pygame.Surface((aura_size * 2, aura_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (255, 0, 0, 50), (aura_size, aura_size), aura_size)
            screen.blit(aura, (screen_x - aura_size, screen_y - aura_size))
            
            # Add damage particles
            if random.random() < 0.1:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, 20)
                particle_x = screen_x + math.cos(angle) * distance
                particle_y = screen_y + math.sin(angle) * distance
                
                pygame.draw.circle(
                    screen,
                    (255, 100, 100),
                    (int(particle_x), int(particle_y)),
                    2
                )
        
        # Speed effect indicator
        if self.terrain_speed_effect != 1.0:
            if self.terrain_speed_effect > 1.0:
                # Speed boost (blue trail)
                for i in range(3):
                    offset = (i + 1) * 5
                    alpha = 150 - (i * 50)
                    trail = pygame.Surface((40, 40), pygame.SRCALPHA)
                    pygame.draw.circle(trail, (100, 100, 255, alpha), (20, 20), 20 - i)
                    screen.blit(trail, (screen_x - 20 - offset, screen_y - 20))
            else:
                # Slowed (amber glow)
                slow_indicator = pygame.Surface((aura_size * 2, aura_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(slow_indicator, (255, 200, 0, 70), (aura_size, aura_size), aura_size)
                screen.blit(slow_indicator, (screen_x - aura_size, screen_y - aura_size))

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
        
        # Arrow size and position (common for both up and down arrows)
        arrow_size = bar_height * 1.5  # Smaller arrow
        arrow_x = bar_x - arrow_size - 2  # Position left of health bar with space
        arrow_y = bar_y + (bar_height / 2) - (arrow_size / 2)  # Center vertically with health bar
        
        # Draw HP down indicator if in harmful terrain
        if hasattr(self, 'terrain_health_effect') and self.terrain_health_effect < 0:
            # Draw a downward-pointing arrow (red)
            pygame.draw.polygon(screen, (255, 0, 0), [
                (arrow_x, arrow_y + arrow_size),  # Bottom point
                (arrow_x - arrow_size/2, arrow_y),  # Top left
                (arrow_x + arrow_size/2, arrow_y)   # Top right
            ])
        # Draw HP up indicator if in optimal terrain (regenerating health)
        elif hasattr(self, 'terrain_health_effect') and self.terrain_health_effect > 0:
            # Draw an upward-pointing arrow (green)
            pygame.draw.polygon(screen, (0, 255, 0), [
                (arrow_x, arrow_y),  # Top point
                (arrow_x - arrow_size/2, arrow_y + arrow_size),  # Bottom left
                (arrow_x + arrow_size/2, arrow_y + arrow_size)   # Bottom right
            ])
        
        # Draw background (red)
        pygame.draw.rect(screen, (200, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        # Draw health (green)
        pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, fill_width, bar_height))
        # Draw border
        pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height), 1)

    def _draw_state_indicator(self, screen: pygame.Surface, x: int, y: int):
        """Draw an indicator showing the animal's current state/goal with improved visibility."""
        # Check if animal is seeking resources
        if hasattr(self, 'state') and self.state == "seeking_resource" and hasattr(self, 'resource_target'):
            # Define colors for different resource types
            resource_colors = {
                'food_plant': (0, 200, 0),    # Green
                'food_meat': (200, 0, 0),     # Red
                'wood': (139, 69, 19),        # Brown
                'stone': (128, 128, 128),     # Gray
                'water': (0, 0, 255),         # Blue
                'medicinal': (255, 0, 255),   # Purple
                'minerals': (255, 215, 0),    # Gold
                None: (255, 255, 255)         # White for any resource
            }
            
            # Get color based on resource type
            color = resource_colors.get(self.resource_target_type, (255, 255, 255))
            
            # Draw a background for better visibility
            pygame.draw.circle(screen, (0, 0, 0), (x, y), 8)
            
            # Draw a colored circle indicating resource type
            pygame.draw.circle(screen, color, (x, y), 6)
            
            # Draw a small icon based on resource type
            if self.resource_target_type == 'food_plant':
                # Draw a berry/fruit icon
                pygame.draw.circle(screen, (200, 0, 0), (x, y-2), 2)  # Red berry
                pygame.draw.circle(screen, (0, 100, 0), (x+2, y+2), 2)  # Leaf
                pygame.draw.circle(screen, (0, 100, 0), (x-2, y+2), 2)  # Leaf
            elif self.resource_target_type == 'food_meat':
                # Draw a drumstick shape
                pygame.draw.circle(screen, (150, 75, 0), (x, y), 3)  # Brown meat
                pygame.draw.line(screen, (200, 200, 200), (x, y), (x+3, y+3), 2)  # Bone
            elif self.resource_target_type == 'wood':
                # Draw a log shape
                pygame.draw.rect(screen, (101, 67, 33), (x-3, y-2, 6, 4))  # Brown log
                pygame.draw.line(screen, (50, 25, 0), (x-3, y-2), (x+3, y-2), 1)  # Wood grain
            elif self.resource_target_type == 'stone':
                # Draw a rock shape
                pygame.draw.polygon(screen, (100, 100, 100), [(x, y-3), (x+3, y), (x, y+3), (x-3, y)])
            elif self.resource_target_type == 'water':
                # Draw a water droplet
                pygame.draw.circle(screen, (0, 0, 200), (x, y), 3)  # Blue droplet
                pygame.draw.polygon(screen, (0, 0, 200), [(x, y-5), (x+3, y-1), (x-3, y-1)])
            elif self.resource_target_type == 'medicinal':
                # Draw a medical cross
                pygame.draw.rect(screen, (255, 255, 255), (x-3, y-1, 6, 2))
                pygame.draw.rect(screen, (255, 255, 255), (x-1, y-3, 2, 6))
            elif self.resource_target_type == 'minerals':
                # Draw a gold nugget
                pygame.draw.circle(screen, (255, 215, 0), (x, y), 3)  # Gold center
                pygame.draw.circle(screen, (255, 255, 200), (x-1, y-1), 1)  # Highlight
            
            # Draw a line to target if it exists
            if self.resource_target and hasattr(self, 'camera_x') and hasattr(self, 'camera_y'):
                target_x, target_y = self.resource_target
                target_screen_x = (target_x * 32) + 16 - self.camera_x  # Center of tile
                target_screen_y = (target_y * 32) + 16 - self.camera_y
                
                # Draw a dotted line to target
                for i in range(0, 100, 5):  # Draw dots every 5 pixels
                    t = i / 100.0
                    dot_x = x + (target_screen_x - x) * t
                    dot_y = y + (target_screen_y - y) * t
                    pygame.draw.circle(screen, color, (int(dot_x), int(dot_y)), 1)
        
        # Show team strategy if animal is a team leader
        if hasattr(self, 'team') and self.team and hasattr(self.team, 'leader') and self.team.leader == self:
            if hasattr(self.team, 'resource_strategy'):
                # Define colors for different strategies
                strategy_colors = {
                    'survival': (255, 0, 0),       # Red
                    'establish_base': (0, 0, 255), # Blue
                    'gather_food': (0, 255, 0),    # Green
                    'defense': (255, 165, 0),      # Orange
                    'expand': (255, 0, 255),       # Purple
                    'balanced': (255, 255, 255)    # White
                }
                
                # Get color based on strategy
                color = strategy_colors.get(self.team.resource_strategy, (255, 255, 255))
                
                # Draw strategy indicator above the resource indicator
                pygame.draw.circle(screen, (0, 0, 0), (x, y-12), 6)  # Black background
                pygame.draw.circle(screen, color, (x, y-12), 4)  # Colored circle

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
        """Parse habitat string to determine preferred terrain with improved detection."""
        habitat_str = habitat_str.lower()
        
        # More comprehensive detection for aquatic animals
        aquatic_keywords = ['water', 'marine', 'ocean', 'sea', 'lake', 'river', 'aquatic', 'fish', 'penguin', 'shark', 'whale']
        if any(keyword in habitat_str for keyword in aquatic_keywords) or 'fish' in self.name.lower() or 'penguin' in self.name.lower():
            return 'aquatic'
        elif 'forest' in habitat_str or 'jungle' in habitat_str or 'woodland' in habitat_str:
            return 'forest'
        elif 'mountain' in habitat_str or 'alpine' in habitat_str or 'highland' in habitat_str:
            return 'mountain'
        elif 'desert' in habitat_str or 'arid' in habitat_str or 'sand' in habitat_str:
            return 'desert'
        elif 'swamp' in habitat_str or 'marsh' in habitat_str or 'wetland' in habitat_str:
            return 'wetland'
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
        """Heal the animal by the specified amount."""
        if amount <= 0 or self.health <= 0:
            return
            
        self.health = min(self.health + amount, self.max_health)

    def _find_resource_target(self, resource_system: 'ResourceSystem'):
        """Find a suitable resource target with improved effectiveness."""
        # Skip if already seeking a resource
        if hasattr(self, 'resource_target') and self.resource_target and hasattr(self, 'resource_target_type'):
            # Check if we should keep the current target
            if random.random() < 0.8:  # 80% chance to keep current target
                return
        
        # Determine what type of resource to look for based on needs
        target_type = None
        search_radius = 1200.0  # Increased search radius
        
        # Check health to determine if medicinal resources are needed
        health_percent = self.health / self.max_health
        
        # Check if animal is in a team
        in_team = hasattr(self, 'team') and self.team is not None
        
        # Prioritize resources based on needs
        if health_percent < 0.5:
            # Low health - look for medicinal resources
            target_type = 'medicinal'
        elif self._can_eat_plants() and (not in_team or random.random() < 0.7):
            # Herbivore or omnivore - look for plant food
            target_type = 'food_plant'
        elif self._can_eat_meat() and (not in_team or random.random() < 0.7):
            # Carnivore or omnivore - look for meat
            target_type = 'food_meat'
        elif random.random() < 0.3:
            # Sometimes look for water
            target_type = 'water'
        elif in_team and random.random() < 0.5:
            # If in a team, sometimes look for building materials
            target_type = random.choice(['wood', 'stone', 'minerals'])
        
        # Find nearest resource of target type with increased chance of success
        nearest_pos, distance = resource_system.find_nearest_resource(
            self.x, self.y, target_type, search_radius
        )
        
        if nearest_pos:
            # Set as target
            self.resource_target = nearest_pos
            self.resource_target_type = target_type
            self.state = "seeking_resource"
            return
        
        # If no specific resource found, look for any resource
        if random.random() < 0.5:  # 50% chance to look for any resource
            nearest_pos, distance = resource_system.find_nearest_resource(
                self.x, self.y, None, search_radius
            )
            
            if nearest_pos:
                self.resource_target = nearest_pos
                self.resource_target_type = None
                self.state = "seeking_resource"

    def _move_to_resource(self, dt: float, world_grid):
        """Move towards a resource target with proper proximity checks."""
        if not hasattr(self, 'resource_target') or not self.resource_target:
            return
            
        # Calculate target position in world coordinates
        target_x, target_y = self.resource_target
        target_world_x = (target_x * 32) + 16  # Center of tile
        target_world_y = (target_y * 32) + 16
        
        # Calculate direction to target
        dx = target_world_x - self.x
        dy = target_world_y - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Check if we've reached the resource
        grid_x, grid_y = int(self.x // 32), int(self.y // 32)
        if grid_x == target_x and grid_y == target_y:
            # We've reached the resource, mark as arrived
            self.state = "at_resource"
            return
            
        # Continue moving towards the resource
        if distance > 5:
            # Calculate normalized direction
            dx /= distance
            dy /= distance
            
            # Calculate new position
            new_x = self.x + dx * self.speed * dt
            new_y = self.y + dy * self.speed * dt
            
            # Check if new position is valid
            if self._is_valid_position(new_x, new_y, world_grid):
                self.x = new_x
                self.y = new_y
            else:
                # Try to move in just x direction
                if self._is_valid_position(new_x, self.y, world_grid):
                    self.x = new_x
                # Try to move in just y direction
                elif self._is_valid_position(self.x, new_y, world_grid):
                    self.y = new_y
                else:
                    # Can't move directly towards target, try a random direction
                    self._wander(world_grid, self.speed, dt)
    
    def _can_eat_plants(self):
        """Check if the animal can eat plant-based food."""
        diet = self.original_data.get('Diet_Type', '').lower()
        return diet in ['herbivore', 'omnivore']
        
    def _can_eat_meat(self):
        """Check if the animal can eat meat-based food."""
        diet = self.original_data.get('Diet_Type', '').lower()
        return diet in ['carnivore', 'omnivore']

    def _get_terrain_speed_modifier(self, terrain: str) -> float:
        """Calculate speed modifier based on terrain and animal's adaptations."""
        # Default speed modifier
        modifier = 1.0
        
        # Apply terrain speed effect if available
        if hasattr(self, 'terrain_speed_effect'):
            modifier = self.terrain_speed_effect
            
        # Apply terrain-specific modifiers based on animal's adaptations
        if hasattr(self, 'original_data'):
            habitat = self.original_data.get('Habitat', '').lower()
            
            # Boost speed in preferred habitat
            if 'aquatic' in habitat and terrain == 'water':
                modifier *= 1.5
            elif 'forest' in habitat and terrain == 'forest':
                modifier *= 1.3
            elif 'grassland' in habitat and terrain == 'grassland':
                modifier *= 1.3
            elif 'mountain' in habitat and terrain == 'mountain':
                modifier *= 1.3
            elif 'desert' in habitat and terrain == 'desert':
                modifier *= 1.3
                
            # Reduce speed in challenging terrains
            if 'aquatic' not in habitat and terrain == 'water':
                modifier *= 0.5
            elif 'mountain' not in habitat and terrain == 'mountain':
                modifier *= 0.7
            elif 'desert' not in habitat and terrain == 'desert':
                modifier *= 0.8
                
        return max(0.2, min(modifier, 2.0))  # Clamp between 0.2 and 2.0

    def eat(self, food_type: str, amount: float):
        """Simulate eating behavior."""
        if food_type == 'plant' and self._can_eat_plants():
            self.hunger = max(0, self.hunger - amount)
            self.mood_points += amount * 2
        elif food_type == 'meat' and self._can_eat_meat():
            self.hunger = max(0, self.hunger - amount)
            self.mood_points += amount * 2

    def drink(self, amount: float):
        """Simulate drinking behavior."""
        self.thirst = max(0, self.thirst - amount)
        self.mood_points += amount

    def team_up(self, other: 'Animal'):
        """Simulate teaming up with another animal."""
        if not self.team and not other.team:
            new_team = Team(self)
            new_team.add_member(other)
            self.team = new_team
            other.team = new_team
            self.social_needs = max(0, self.social_needs - 10)
            self.mood_points += 10

    def attack(self, target: 'Animal'):
        """Simulate attacking another animal."""
        if self.hunger > 50 and target.health > 0:
            damage = min(10, target.health)
            target.health -= damage
            self.hunger = max(0, self.hunger - damage)
            self.mood_points -= 5

    def sleep(self, duration: float):
        """Simulate sleeping behavior."""
        self.sleepiness = max(0, self.sleepiness - duration)
        self.health = min(self.max_health, self.health + duration * 2)
        self.mood_points += duration

    def mate(self, partner: 'Animal'):
        """Simulate mating behavior."""
        if self.mood_points > 50 and partner.mood_points > 50:
            self.mood_points -= 20
            partner.mood_points -= 20
            # Logic to create offspring can be added here

