from typing import List, Tuple, Optional, TYPE_CHECKING
import pygame
import math

if TYPE_CHECKING:
    from src.entities.team import Team
    from src.entities.animal import Animal
    from src.entities.robot import Robot

class TeamBase:
    def __init__(self, team: 'Team', position: Tuple[float, float], radius: float = 400):
        """Initialize a team base."""
        self.team = team
        self.position = position
        self.radius = radius
        self.color = team.color
        self.structures = []  # List of structures within the base
        self.defense_bonus = 1.2  # Combat bonus when defending the base
        self.night_bonus = 1.5  # Healing/rest bonus during night
        
        # Base development stats
        self.level = 1
        self.resources = {
            'food_plant': 0,
            'food_meat': 0,
            'wood': 0,
            'stone': 0,
            'water': 0,
            'medicinal': 0,
            'minerals': 0
        }
        self.max_resource_capacity = 1000
        
        # Base boundaries
        self.boundary_points = self._calculate_boundary_points()
        
    def _calculate_boundary_points(self) -> List[Tuple[float, float]]:
        """Calculate points that define the base boundary."""
        points = []
        num_points = 32  # Number of points to define the circle
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            x = self.position[0] + math.cos(angle) * self.radius
            y = self.position[1] + math.sin(angle) * self.radius
            points.append((x, y))
        return points
        
    def is_point_inside(self, point: Tuple[float, float]) -> bool:
        """Check if a point is inside the base boundaries."""
        dx = point[0] - self.position[0]
        dy = point[1] - self.position[1]
        return math.sqrt(dx*dx + dy*dy) <= self.radius
        
    def add_resource(self, resource_type: str, amount: float) -> float:
        """Add resources to the base storage, returns amount actually stored."""
        current = self.resources[resource_type]
        space_available = self.max_resource_capacity - current
        amount_to_add = min(amount, space_available)
        self.resources[resource_type] += amount_to_add
        return amount_to_add
        
    def get_defense_bonus(self) -> float:
        """Get the defense bonus for team members inside the base."""
        return self.defense_bonus * (1 + (self.level - 1) * 0.1)
        
    def get_night_bonus(self) -> float:
        """Get the night time bonus for team members inside the base."""
        return self.night_bonus * (1 + (self.level - 1) * 0.1)
        
    def update(self, dt: float, is_night: bool) -> None:
        """Update base state."""
        if is_night:
            # Heal team members inside the base during night
            for member in self.team.members:
                if self.is_point_inside((member.x, member.y)):
                    healing = 5 * dt * self.get_night_bonus()
                    member.heal(healing)
                    
    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        """Draw the base on the screen."""
        # Draw base boundary
        points = [(x - camera_x, y - camera_y) for x, y in self.boundary_points]
        if len(points) > 2:
            # Draw semi-transparent fill
            base_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            pygame.draw.polygon(base_surface, (*self.color, 40), points)  # Alpha = 40
            screen.blit(base_surface, (0, 0))
            
            # Draw border
            pygame.draw.polygon(screen, self.color, points, 2)
            
            # Draw base center marker
            center_x = self.position[0] - camera_x
            center_y = self.position[1] - camera_y
            pygame.draw.circle(screen, self.color, (int(center_x), int(center_y)), 8)
            
            # Draw base name
            font = pygame.font.SysFont('Arial', 20)
            level_text = font.render(f"Base of {self.team.get_leader_name()}", True, self.color)
            screen.blit(level_text, (center_x - level_text.get_width()//2, center_y - 30)) 