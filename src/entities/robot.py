import random
import math
import pygame
from typing import List, Tuple, Dict, Any, Optional

from src.entities.animal import Animal
from src.entities.team import Team

class Robot(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int):
        super().__init__()
        self.x = x
        self.y = y
        self.speed = 100.0  # Further reduced for better team cohesion
        self.movement_smoothing = 0.8  # Add movement smoothing
        self.last_dx = 0
        self.last_dy = 0
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

    def update(self, dt: float, all_robots: List['Robot']) -> None:
        """Update robot behavior with recruitment cooldown."""
        current_time = pygame.time.get_ticks() / 1000.0
        
        # Update state based on conditions and cooldown
        if self.has_team:
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

    def cleanup(self):
        if hasattr(self, 'image'):
            del self.image