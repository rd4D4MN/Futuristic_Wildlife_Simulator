import random
import math
import pygame
from typing import List, Tuple, Dict, Any, Optional, TYPE_CHECKING

from src.entities.team import Team

if TYPE_CHECKING:
    from src.entities.animal import Animal
    from src.resources.resource_system import ResourceSystem

class Robot(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int):
        super().__init__()
        self.x = x
        self.y = y
        self.speed = 100.0  # Further reduced for better team cohesion
        self.movement_smoothing = 0.8  # Add movement smoothing
        self.last_dx = 0
        self.last_dy = 0
        self.name = f"Robot-{id(self)%1000:03d}"  # Add consistent name
        self.image = self._load_sprite()
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)
        self.health = 100.0
        self.max_health = 100.0
        
        # Movement attributes
        self.target_x = x
        self.target_y = y
        
        # Role and scanning
        self.role = random.choice(['scout', 'defender', 'gatherer'])
        self.scan_radius = 300  # Detection radius
        
        # Memory and state
        self.memory = {
            'threats': [],
            'resources': [],
            'allies': set(),
            'enemies': set()
        }
        
        # Strategy and bounds
        self.strategy = self._init_strategy()
        self.world_bounds = {
            'x_min': 0,
            'x_max': 1200 * 8,
            'y_min': 0,
            'y_max': 800 * 8
        }
        self.world_grid = None
        
        # Timers and intervals
        self.movement_timer = 0
        self.target_update_interval = 5.0
        self.search_timer = 0
        self.search_interval = 3.0
        
        # Patrol and team attributes
        self.last_search_position = (x, y)
        self.patrol_points = []
        self.current_patrol_index = 0
        self.patrol_radius = 150  # Reduced from 300
        self.last_target_change = 0
        self.target_change_delay = 5.0
        
        # Team status
        self.has_team = False
        self.team: Optional['Team'] = None
        self.state = 'searching'
        self.nearby_animals: List['Animal'] = []

        # Add territory bounds
        self.territory_center = (x, y)
        self.territory_radius = 600  # Reduced from 1200
        self.return_threshold = 800  # Reduced from 1600

        # Add maximum team size and recruitment cooldown
        self.max_team_size = 8
        self.recruitment_cooldown = 2.0
        self.last_recruitment = 0
        
        # Resource gathering and building
        self.resource_target = None
        self.resource_target_type = None
        self.last_resource_search = 0
        self.resource_search_interval = 8.0  # Search every 8 seconds
        self.building_cooldown = 0
        self.building_target = None
        self.building_type = None
        self.resource_priority = ['food_plant', 'food_meat', 'medicinal', 'wood', 'stone', 'minerals']

    def _load_sprite(self) -> pygame.Surface:
        try:
            filename = "static/images/robot/robot.png"
            try:
                img = pygame.image.load(filename).convert_alpha()
                return pygame.transform.scale(img, (128, 128))
            except (pygame.error, FileNotFoundError) as e:
                print(f"Error loading sprite from {filename}: {e}")
                surf = pygame.Surface((128, 128), pygame.SRCALPHA)
                surf.fill((0, 255, 255))
                return surf
        except Exception as e:
            print(f"Error creating sprite for robot: {e}")
            surf = pygame.Surface((128, 128), pygame.SRCALPHA)
            surf.fill((255, 0, 255, 255))
            return surf

    def _init_strategy(self) -> Dict[str, Any]:
        strategies = {
            'scout': {
                'movement_range': 300,
                'preferred_terrain': ['grassland', 'forest'],
                'avoid_combat': True,
                'exploration_priority': 0.8
            },
            'defender': {
                'movement_range': 150,
                'preferred_terrain': ['mountain', 'forest'],
                'avoid_combat': False,
                'protection_radius': 100
            },
            'gatherer': {
                'movement_range': 200,
                'preferred_terrain': ['grassland', 'forest'],
                'avoid_combat': True,
                'resource_priority': 0.7
            }
        }
        return strategies[self.role]

    def set_team_status(self, has_team: bool) -> None:
        self.has_team = has_team
        if has_team:
            self.state = 'patrolling'
            self.patrol_radius = 200
        else:
            self.state = 'searching'
            self.patrol_radius = 300

    def update(self, dt: float, all_robots: List['Robot'], resource_system=None) -> None:
        """Update robot behavior with resource gathering and building."""
        current_time = pygame.time.get_ticks() / 1000.0
        
        # Update resource search timer
        self.last_resource_search += dt
        
        # Update building cooldown
        if self.building_cooldown > 0:
            self.building_cooldown -= dt
        
        # Update state based on conditions and cooldown
        if self.has_team:
            # If we have a team, prioritize resource gathering and building
            if self.state != 'gathering_resources' and self.state != 'building' and resource_system:
                # Check if team needs resources or should build
                if self.team and hasattr(self.team, 'inventory'):
                    # Determine if we should gather resources or build
                    if self._should_build():
                        self.state = 'building'
                    elif self._should_gather_resources():
                        self.state = 'gathering_resources'
                    else:
                        self.state = 'patrolling'
            
        elif self.nearby_animals and current_time - self.last_recruitment > self.recruitment_cooldown:
            self.state = 'recruiting'
            self.last_recruitment = current_time
        else:
            self.state = 'searching'

        # Territory check
        dx = self.x - self.territory_center[0]
        dy = self.y - self.territory_center[1]
        dist_from_center = math.sqrt(dx*dx + dy*dy)

        # Gradual territory return
        if dist_from_center > self.territory_radius:
            return_strength = min(1.0, (dist_from_center - self.territory_radius) / 
                                     (self.return_threshold - self.territory_radius))
            angle = math.atan2(dy, dx)
            self.target_x = self.territory_center[0]
            self.target_y = self.territory_center[1]
        else:
            # Normal state behavior
            if self.state == 'patrolling':
                self._patrol_territory(dt)
            elif self.state == 'recruiting':
                self._move_to_animals(dt)
            elif self.state == 'searching':
                self._search_for_animals(dt)
            elif self.state == 'gathering_resources' and resource_system:
                self._gather_resources(dt, resource_system)
            elif self.state == 'building' and resource_system:
                self._build_structure(dt, resource_system)

        # Apply smooth movement
        target_dx = self.target_x - self.x
        target_dy = self.target_y - self.y
        dist = math.sqrt(target_dx*target_dx + target_dy*target_dy)
        
        if dist > 5:
            # Smooth the movement direction
            move_dx = target_dx/dist * self.speed * dt
            move_dy = target_dy/dist * self.speed * dt
            
            # Apply smoothing
            self.last_dx = self.last_dx * self.movement_smoothing + move_dx * (1 - self.movement_smoothing)
            self.last_dy = self.last_dy * self.movement_smoothing + move_dy * (1 - self.movement_smoothing)
            
            # Update position
            self.x += self.last_dx
            self.y += self.last_dy
            
        # Update rect position
        self.rect.center = (self.x, self.y)

    def detect_nearby_animals(self, animals: List['Animal']) -> None:
        self.nearby_animals = []
        for animal in animals:
            if animal.health <= 0 or animal.team:
                continue
                
            dx = animal.x - self.x
            dy = animal.y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist <= self.scan_radius:
                self.nearby_animals.append(animal)
        
        # Only log if debug mode is enabled
        if hasattr(self, 'debug_mode') and self.debug_mode and len(self.nearby_animals) > 0:
            print(f"Robot at ({self.x:.0f},{self.y:.0f}) detected {len(self.nearby_animals)} animals")

    def _search_for_animals(self, dt: float) -> None:
        self.search_timer += dt
        if self.search_timer >= self.search_interval:
            self.search_timer = 0
            self._seek_animals()

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 10:
            self.x += (dx/dist) * self.speed * dt
            self.y += (dy/dist) * self.speed * dt

    def _seek_animals(self) -> None:
        if self.nearby_animals:
            positions = [(a.x, a.y) for a in self.nearby_animals[:5]]
            if positions:
                center_x = sum(x for x, _ in positions) / len(positions)
                center_y = sum(y for _, y in positions) / len(positions)
                
                lead_distance = 50
                dx = center_x - self.x
                dy = center_y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    self.target_x = center_x - (dx/dist * lead_distance)
                    self.target_y = center_y - (dy/dist * lead_distance)
                return

        angle = random.random() * 2 * math.pi
        self.target_x = self.x + math.cos(angle) * self.patrol_radius
        self.target_y = self.y + math.sin(angle) * self.patrol_radius

    def _move_to_animals(self, dt: float) -> None:
        if not self.nearby_animals:
            return
            
        cx = sum(a.x for a in self.nearby_animals) / len(self.nearby_animals)
        cy = sum(a.y for a in self.nearby_animals) / len(self.nearby_animals)
        
        dx = cx - self.x
        dy = cy - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 10:
            self.x += (dx/dist) * self.speed * dt
            self.y += (dy/dist) * self.speed * dt

    def _patrol_territory(self, dt: float) -> None:
        """Update patrol behavior to be more contained."""
        if not self.patrol_points or len(self.patrol_points) < 4:
            self._generate_patrol_points()

        if self.team and self.team.members:
            # Stay closer to team centroid
            positions = [(m.x, m.y) for m in self.team.members]
            avg_x = sum(x for x, _ in positions) / len(positions)
            avg_y = sum(y for y, _ in positions) / len(positions)
            
            # Adjust patrol target to stay near team
            dx = self.target_x - avg_x
            dy = self.target_y - avg_y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist > self.patrol_radius:
                self.target_x = avg_x + (dx/dist) * self.patrol_radius
                self.target_y = avg_y + (dy/dist) * self.patrol_radius
        
        # Normal patrol movement
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)

        if dist < 20:
            self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
            self.target_x, self.target_y = self.patrol_points[self.current_patrol_index]
        else:
            move_speed = self.speed * dt
            self.x += (dx/dist) * move_speed
            self.y += (dy/dist) * move_speed

    def _generate_patrol_points(self) -> None:
        """Generate patrol points within territory."""
        self.patrol_points = []
        center_x, center_y = self.territory_center
        radius = min(self.patrol_radius, self.territory_radius)
        num_points = 8

        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            self.patrol_points.append((x, y))

        if self.patrol_points:
            self.target_x, self.target_y = self.patrol_points[0]

    def _avoid_other_robots(self, dt: float, all_robots: List['Robot']) -> None:
        for robot in all_robots:
            if robot is not self:
                dx = robot.x - self.x
                dy = robot.y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if 0 < dist < 32:
                    if not self.team and not robot.team:
                        return
                        
                    my_team_strength = self.team.calculate_combat_strength() if self.team else 0
                    other_team_strength = robot.team.calculate_combat_strength() if robot.team else 0
                    
                    if my_team_strength < other_team_strength * 0.8:
                        self.x -= (dx/dist) * (dt * 50)
                        self.y -= (dy/dist) * (dt * 50)

    def _update_memory(self) -> None:
        current_time = pygame.time.get_ticks()
        self.memory['threats'] = [t for t in self.memory['threats'] 
                                if current_time - t['time'] < 30000]

    def draw(self, screen: pygame.Surface, camera_x: int = 0, camera_y: int = 0) -> None:
        screen_x = self.x - camera_x - self.rect.width // 2
        screen_y = self.y - camera_y - self.rect.height // 2
        screen.blit(self.image, (screen_x, screen_y))
        
        # Draw state indicator above robot
        self._draw_state_indicator(screen, screen_x + self.rect.width // 2, screen_y - 10)

    def _draw_state_indicator(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Draw an indicator showing the robot's current state/goal."""
        # Define colors for different states
        state_colors = {
            'searching': (200, 200, 200),      # Gray
            'recruiting': (100, 200, 255),     # Light blue
            'patrolling': (100, 255, 100),     # Light green
            'gathering_resources': (255, 215, 0),  # Gold
            'building': (255, 100, 100)        # Light red
        }
        
        # Define icons/shapes for different states
        if self.state == 'searching':
            # Draw a question mark
            font = pygame.font.SysFont('Arial', 16)
            text = font.render('?', True, (0, 0, 0))
            bg_size = max(text.get_width(), text.get_height()) + 6
            
            # Draw background circle
            pygame.draw.circle(screen, state_colors.get(self.state, (150, 150, 150)), (x, y), bg_size // 2)
            
            # Draw text
            screen.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))
            
        elif self.state == 'recruiting':
            # Draw a plus sign
            font = pygame.font.SysFont('Arial', 16)
            text = font.render('+', True, (0, 0, 0))
            bg_size = max(text.get_width(), text.get_height()) + 6
            
            # Draw background circle
            pygame.draw.circle(screen, state_colors.get(self.state, (150, 150, 150)), (x, y), bg_size // 2)
            
            # Draw text
            screen.blit(text, (x - text.get_width() // 2, y - text.get_height() // 2))
            
        elif self.state == 'patrolling':
            # Draw a shield icon
            pygame.draw.circle(screen, state_colors.get(self.state, (150, 150, 150)), (x, y), 8)
            pygame.draw.circle(screen, (0, 0, 0), (x, y), 8, 1)  # Border
            
        elif self.state == 'gathering_resources':
            # Draw a pickaxe-like shape
            color = state_colors.get(self.state, (150, 150, 150))
            
            # Draw background circle
            pygame.draw.circle(screen, color, (x, y), 8)
            
            # Draw resource type indicator if available
            if hasattr(self, 'resource_target_type') and self.resource_target_type:
                resource_colors = {
                    'food_plant': (0, 200, 0),    # Green
                    'food_meat': (200, 0, 0),     # Red
                    'wood': (139, 69, 19),        # Brown
                    'stone': (128, 128, 128),     # Gray
                    'water': (0, 0, 255),         # Blue
                    'medicinal': (255, 0, 255),   # Purple
                    'minerals': (255, 215, 0)     # Gold
                }
                
                # Draw a small colored dot indicating resource type
                resource_color = resource_colors.get(self.resource_target_type, (255, 255, 255))
                pygame.draw.circle(screen, resource_color, (x + 6, y - 6), 4)
            
        elif self.state == 'building':
            # Draw a house-like shape
            color = state_colors.get(self.state, (150, 150, 150))
            
            # Draw background circle
            pygame.draw.circle(screen, color, (x, y), 8)
            
            # Draw building type indicator if available
            if hasattr(self, 'building_type') and self.building_type:
                # Draw a small symbol based on building type
                if self.building_type == 'shelter':
                    # House shape
                    pygame.draw.polygon(screen, (0, 0, 0), [
                        (x, y - 6),       # Top
                        (x - 4, y - 2),   # Left
                        (x + 4, y - 2)    # Right
                    ])
                elif self.building_type == 'watchtower':
                    # Tower shape
                    pygame.draw.rect(screen, (0, 0, 0), (x - 2, y - 6, 4, 6))
                elif self.building_type == 'wall':
                    # Wall shape
                    pygame.draw.rect(screen, (0, 0, 0), (x - 4, y - 4, 8, 2))
                elif self.building_type == 'storage':
                    # Box shape
                    pygame.draw.rect(screen, (0, 0, 0), (x - 3, y - 3, 6, 6), 1)
        
        # Draw a line to target if applicable
        if self.state in ['gathering_resources', 'building'] and hasattr(self, 'target_x') and hasattr(self, 'target_y'):
            target_screen_x = self.target_x - camera_x
            target_screen_y = self.target_y - camera_y
            
            # Draw a dotted line to target
            pygame.draw.line(screen, state_colors.get(self.state, (150, 150, 150)), 
                           (x, y), (target_screen_x, target_screen_y), 1)

    def cleanup(self):
        if hasattr(self, 'image'):
            del self.image

    def _should_gather_resources(self) -> bool:
        """Determine if the robot should gather resources based on team needs."""
        if not self.team or not hasattr(self.team, 'inventory'):
            return False
            
        # Check if any resource is below threshold
        for resource_type, amount in self.team.inventory.items():
            if amount < 40:  # Increased threshold from 30 to 40
                return True
                
        return False
        
    def _should_build(self) -> bool:
        """Determine if the robot should build a structure."""
        if not self.team or not hasattr(self.team, 'inventory') or not hasattr(self.team, 'structures'):
            return False
            
        # Don't build if on cooldown
        if self.building_cooldown > 0:
            return False
            
        # Check if we have enough resources to build any structure
        if hasattr(self.team, 'structure_types'):
            # First prioritize shelter if we don't have one
            shelter_exists = any(s['type'] == 'shelter' for s in self.team.structures)
            if not shelter_exists:
                shelter_data = self.team.structure_types.get('shelter', {})
                requirements = shelter_data.get('requirements', {})
                if all(self.team.inventory.get(res, 0) >= amount for res, amount in requirements.items()):
                    self.building_type = 'shelter'
                    return True
            
            # Then check other structures
            for structure_type, data in self.team.structure_types.items():
                # Skip shelter as we already checked it
                if structure_type == 'shelter':
                    continue
                    
                # Check if we already have this structure
                if any(s['type'] == structure_type for s in self.team.structures):
                    continue
                    
                # Check if we have resources to build it
                requirements = data.get('requirements', {})
                if all(self.team.inventory.get(res, 0) >= amount * 0.8 for res, amount in requirements.items()):
                    # Allow building if we have at least 80% of required resources
                    self.building_type = structure_type
                    return True
                    
        return False
        
    def _gather_resources(self, dt: float, resource_system: 'ResourceSystem'):
        """Gather resources based on team needs with improved effectiveness and proper proximity checks."""
        # Find resource target if needed
        if not self.resource_target or self.last_resource_search >= self.resource_search_interval:
            self.last_resource_search = 0
            self._find_resource_target(resource_system)
            
        # Move to resource target
        if self.resource_target:
            # Calculate target position in world coordinates
            target_x, target_y = self.resource_target
            target_world_x = (target_x * 32) + 16  # Center of tile
            target_world_y = (target_y * 32) + 16
            
            # Set as movement target
            self.target_x = target_world_x
            self.target_y = target_world_y
            
            # Check if we've reached the resource
            grid_x, grid_y = int(self.x // 32), int(self.y // 32)
            if grid_x == target_x and grid_y == target_y:
                # We've reached the resource, gather it
                resources = resource_system.get_resources_at(grid_x, grid_y)
                for resource in resources:
                    if self.team and hasattr(self.team, 'inventory'):
                        # Gather the resource - increased amount
                        gather_amount = min(30, resource['amount'])  # Increased from 20
                        actual_gathered = resource_system.gather_resource(
                            grid_x, grid_y, resource['type'], gather_amount
                        )
                        
                        if actual_gathered > 0:
                            # Add to team inventory
                            self.team.inventory[resource['type']] += actual_gathered
                            
                            # Distribute food and water to team members who need it
                            if resource['type'] in ['food_plant', 'food_meat', 'water'] and self.team.members:
                                self._distribute_resources(resource['type'], actual_gathered)
                            
                            # Reset resource target after successful gathering
                            self.resource_target = None
                            self.resource_target_type = None
                            
                            # Switch to patrolling for a bit
                            self.state = 'patrolling'
                            break
        else:
            # No resource target found, switch to patrolling
            self.state = 'patrolling'
            
    def _distribute_resources(self, resource_type: str, amount: float):
        """Distribute resources like food and water to team members who need it."""
        if amount <= 0 or not self.team or not self.team.members:
            return
            
        # Find members who can use this resource
        eligible_members = []
        for member in self.team.members:
            if resource_type == 'food_plant' and hasattr(member, '_can_eat_plants') and member._can_eat_plants():
                eligible_members.append(member)
            elif resource_type == 'food_meat' and hasattr(member, '_can_eat_meat') and member._can_eat_meat():
                eligible_members.append(member)
            elif resource_type == 'water':  # All members need water
                eligible_members.append(member)
        
        if not eligible_members:
            return
            
        # Calculate how much each member gets
        amount_per_member = min(amount / len(eligible_members), 5.0)
        
        # Distribute to members
        for member in eligible_members:
            if hasattr(member, 'health') and hasattr(member, 'max_health'):
                # Convert resource to health
                health_boost = amount_per_member * 2  # 2 health points per resource unit
                
                # Apply health boost
                if member.health < member.max_health:
                    member.heal(health_boost)
                    
                    # Visual feedback
                    if hasattr(member, 'state'):
                        member.state = "seeking_resource"
                        if hasattr(member, 'resource_target_type'):
                            member.resource_target_type = resource_type

    def _build_structure(self, dt: float, resource_system: 'ResourceSystem'):
        """Build a structure using team resources with improved effectiveness."""
        if not self.team or not hasattr(self.team, 'inventory') or not hasattr(self.team, 'structures'):
            self.state = 'patrolling'
            return
            
        if not self.building_type:
            # Determine what to build
            self._should_build()
            if not self.building_type:
                self.state = 'patrolling'
                return
                
        # Check if we have the resources to build
        if hasattr(self.team, 'structure_types'):
            structure_data = self.team.structure_types.get(self.building_type, {})
            requirements = structure_data.get('requirements', {})
            
            # Allow building if we have at least 80% of required resources
            if all(self.team.inventory.get(res, 0) >= amount * 0.8 for res, amount in requirements.items()):
                # We have the resources, build the structure
                for res, amount in requirements.items():
                    # Only deduct what we have, up to the required amount
                    actual_amount = min(self.team.inventory.get(res, 0), amount)
                    self.team.inventory[res] -= actual_amount
                
                # Add structure near current position
                offset_x = random.randint(-50, 50)
                offset_y = random.randint(-50, 50)
                self.team.structures.append({
                    'type': self.building_type,
                    'x': self.x + offset_x,
                    'y': self.y + offset_y,
                    'health': 100,
                    'built_time': 0
                })
                
                # Set cooldown and reset building type
                self.building_cooldown = 180  # Reduced from 300 to 180 (3 minutes)
                self.building_type = None
                self.state = 'patrolling'
            else:
                # We don't have the resources, switch to gathering
                self.state = 'gathering_resources'
        else:
            self.state = 'patrolling'
            
    def _find_resource_target(self, resource_system: 'ResourceSystem'):
        """Find a suitable resource target based on team needs with improved search radius."""
        if not self.team or not hasattr(self.team, 'inventory'):
            return
            
        # Determine what type of resource to look for
        target_type = None
        
        # Check team inventory for low resources
        low_resources = []
        for resource_type, amount in self.team.inventory.items():
            if amount < 40:  # Increased threshold from 30 to 40
                low_resources.append(resource_type)
                
        # Prioritize resources based on team needs
        if low_resources:
            # Sort by priority
            prioritized = sorted(low_resources, 
                               key=lambda r: self.resource_priority.index(r) 
                               if r in self.resource_priority else 999)
            if prioritized:
                target_type = prioritized[0]
                
        # If no specific need, look for any resource
        if not target_type:
            target_type = random.choice(self.resource_priority)
            
        # Find nearest resource of target type with increased search radius
        nearest_pos, distance = resource_system.find_nearest_resource(
            self.x, self.y, target_type, 1200.0  # Increased from 800 to 1200
        )
        
        if nearest_pos:
            self.resource_target = nearest_pos
            self.resource_target_type = target_type
            return
            
        # If no specific resource found, look for any resource
        nearest_pos, distance = resource_system.find_nearest_resource(
            self.x, self.y, None, 1200.0  # Increased from 800 to 1200
        )
        
        if nearest_pos:
            self.resource_target = nearest_pos
            self.resource_target_type = None