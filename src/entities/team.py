from typing import List, Tuple, Union, Optional, TYPE_CHECKING
import pygame
import random
import math
from src.entities.team_base import TeamBase

if TYPE_CHECKING:
    from src.entities.animal import Animal
    from src.entities.robot import Robot

class Team:
    def __init__(self, leader: Union['Robot', 'Animal']):
        """Initialize team with a leader."""
        # Basic attributes
        self.leader = leader
        self.members: List['Animal'] = []
        
        # Team appearance and formation first (needed by base)
        self.color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255)
        )
        self.formation = random.choice(['aggressive', 'defensive', 'scout'])
        
        # Base attributes
        self.base = TeamBase(self, (leader.x, leader.y))
        self.base_established = True
        
        # Timing and cooldowns
        self.battle_cooldown = 180
        self.last_battle_frame = -self.battle_cooldown
        self.search_timer = 0
        self.search_interval = 5
        self.last_cohesion_check = 0
        self.cohesion_check_interval = 0.5
        self.last_debug_time = 0
        self.debug_interval = 5.0
        
        # Combat and stats
        self.team_level = 1
        self.experience = 0
        self.specializations = set()
        self.battle_stats = {'wins': 0, 'losses': 0, 'members_lost': 0}
        self.aggression = random.uniform(0.8, 2.0)
        
        # Movement and positioning
        self.max_distance_from_leader = 300
        self.base_formation_radius = 50
        self.max_formation_radius = 200
        self.formation_positions = {}
        self.patrol_points = []
        self.current_patrol_index = 0
        self.target_x, self.target_y = self.leader.x, self.leader.y
        
        # Territory attributes
        self.territory_radius = 800
        self.min_territory_radius = 800
        self.territory_center = (leader.x, leader.y)
        self.territory_expansion_rate = 1.2
        self.last_territory_update = 0
        self.territory_update_interval = 1.0
        
        # Team state
        self.disbanding = False
        self.disband_timer = 0
        self.max_disband_time = 10.0
        self.max_spread = 400
        
        # Debug and tracking
        self.debug_logs = []
        self.movement_history = []
        self.max_history = 10
        self.cohesion_violations = 0

    def get_total_health(self) -> float:
        """Calculate total health of team including leader and active members."""
        total = 0.0
        
        # Add leader health if present
        if self.leader:
            if isinstance(self.leader, Robot):
                total += 100  # Robots have fixed health
            else:
                total += self.leader.health
                
        # Add health of active members
        total += sum(member.health for member in self.members if member.health > 0)
        
        return total

    def get_leader_name(self) -> str:
        """Return name of team leader."""
        if not self.leader:
            return "No Leader"
            
        if isinstance(self.leader, Robot):
            return self.leader.name
        
        # Animal leader
        return self.leader.name

    def _update_formation(self) -> None:
        """Update team formation type based on situation and strategy."""
        if len(self.members) <= 2:
            self.formation = 'defensive'
        elif any(m.health < m.max_health * 0.3 for m in self.members):
            self.formation = 'defensive'
        else:
            total_strength = self.calculate_combat_strength()
            if total_strength > 500:
                self.formation = 'aggressive'
            elif random.random() < self.aggression * 0.3:
                self.formation = random.choice(['aggressive', 'defensive', 'scout'])

    def calculate_combat_strength(self) -> float:
        """Calculate the total combat strength of the team."""
        base_strength = sum(member.attack_multiplier for member in self.members if member.health > 0)
        
        # Formation multiplier
        formation_multipliers = {
            'defensive': 1.0,  # Reduced from 1.2
            'aggressive': 1.5,  # Increased from 1.3
            'scout': 1.2
        }
        formation_multiplier = formation_multipliers.get(self.formation, 1.0)

        # Team level and specializations bonuses
        level_bonus = 1.0 + (self.team_level - 1) * 0.1
        spec_bonus = 1.0 + len(self.specializations) * 0.1

        base_strength = base_strength * formation_multiplier * level_bonus * spec_bonus
        
        # Add size scaling
        size_factor = min(2.0, math.sqrt(len(self.members)) / 2)
        
        # Add health factor
        health_ratio = self.get_total_health() / (len(self.members) * 100)
        health_factor = max(0.5, min(1.5, health_ratio))
        
        # Add aggression modifier
        aggression_bonus = self.aggression * (1.5 if self.formation == 'aggressive' else 1.0)
        
        return base_strength * size_factor * health_factor * aggression_bonus * formation_multiplier

    def add_member(self, animal: 'Animal') -> None:
        """Add a new member to the team."""
        animal.team = self
        # Only set world_grid if leader has it
        if hasattr(self.leader, 'world_grid'):
            animal.world_grid = self.leader.world_grid
        self.members.append(animal)

    def remove_member(self, animal: 'Animal') -> None:
        """Remove a member from the team."""
        if animal in self.members:
            if not hasattr(animal, '_being_removed'):
                animal.cleanup()  # Call the cleanup method when removing the animal
            animal.team = None
            self.members.remove(animal)

    def update(self, dt: float) -> None:
        """Update team behavior with base management."""
        # Update base first
        is_night = self._is_night_time()
        self.base.update(dt, is_night)
        
        # Check if night time and enforce return to base
        if is_night and self.base_established:
            self._return_to_base()
        
        # Rest of the update logic
        self.last_territory_update += dt
        if self.last_territory_update >= self.territory_update_interval:
            self.last_territory_update = 0
            self._update_territory_center()

        self.last_cohesion_check += dt
        if self.last_cohesion_check >= self.cohesion_check_interval:
            self.last_cohesion_check = 0
            cohesion_result = self._check_team_cohesion()
            if not cohesion_result and not self.disbanding:
                self.disbanding = True
            else:
                if self.disbanding:
                    self.disbanding = False
                    self.disband_timer = 0

        if self.disbanding:
            self.disband_timer += dt
            if self.disband_timer >= self.max_disband_time:
                if self._check_team_cohesion():
                    self.disbanding = False
                    self.disband_timer = 0
                else:
                    self._disband_team()
                    return

        self._update_formation_positions()

        if self.members:
            base_speed = min(member.speed for member in self.members)
            for member in self.members:
                if member in self.formation_positions:
                    target_x, target_y = self.formation_positions[member]
                    dx = target_x - member.x
                    dy = target_y - member.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    
                    if dist > 5:
                        speed_mult = min(2.0, dist / 50)
                        move_speed = base_speed * speed_mult * dt
                        move_x = (dx/dist) * move_speed
                        move_y = (dy/dist) * move_speed
                        new_x = member.x + move_x
                        new_y = member.y + move_y
                        if member._is_valid_position(new_x, new_y, member.world_grid):
                            member.x = new_x
                            member.y = new_y

        if self.experience >= self.team_level * 100:
            self._level_up()

    def _is_night_time(self) -> bool:
        """Check if it's night time based on environment system."""
        if hasattr(self.leader, 'world_grid') and hasattr(self.leader.world_grid, 'environment_system'):
            time_of_day = self.leader.world_grid.environment_system.time_of_day
            return time_of_day < 6 or time_of_day > 18
        return False

    def _return_to_base(self) -> None:
        """Direct all team members to return to base during night."""
        if not self.base_established:
            return
            
        # Update leader's target to base center
        if isinstance(self.leader, Robot):
            self.leader.target_x = self.base.position[0]
            self.leader.target_y = self.base.position[1]
            
        # Update formation positions to be within base
        for member in self.members:
            angle = random.random() * 2 * math.pi
            distance = random.random() * (self.base.radius * 0.8)  # Stay within 80% of base radius
            target_x = self.base.position[0] + math.cos(angle) * distance
            target_y = self.base.position[1] + math.sin(angle) * distance
            self.formation_positions[member] = (target_x, target_y)

    def handle_intruder(self, intruder: Union['Animal', 'Robot']) -> bool:
        """Handle an intruder in the team's base."""
        if not self.base_established:
            return False
            
        # Check if intruder is in base
        if not self.base.is_point_inside((intruder.x, intruder.y)):
            return False
            
        # Calculate defense bonus
        defense_bonus = self.base.get_defense_bonus()
        
        # Increase aggression temporarily
        old_aggression = self.aggression
        self.aggression *= defense_bonus
        
        # Set all members to attack intruder
        for member in self.members:
            if hasattr(member, 'target'):
                member.target = intruder
                
        # Reset aggression after delay
        self.aggression = old_aggression
        
        return True

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        """Draw team and base."""
        # Draw base first
        if self.base_established:
            self.base.draw(screen, camera_x, camera_y)
            
        # Draw territory and other team visuals
        if len(self.members) > 0:
            # Draw lines between members
            for i, member in enumerate(self.members[:-1]):
                next_member = self.members[i + 1]
                start_pos = (int(member.x - camera_x), int(member.y - camera_y))
                end_pos = (int(next_member.x - camera_x), int(next_member.y - camera_y))
                pygame.draw.line(screen, self.color, start_pos, end_pos, 1)
                
            # Draw line to leader
            if self.members:
                start_pos = (int(self.leader.x - camera_x), int(self.leader.y - camera_y))
                end_pos = (int(self.members[0].x - camera_x), int(self.members[0].y - camera_y))
                pygame.draw.line(screen, self.color, start_pos, end_pos, 1)

    def _apply_team_bonuses(self) -> None:
        """Apply team-based bonuses to all members."""
        if not self.members:
            return
            
        # Base bonuses from team level
        level_bonus = 0.1 * self.team_level
        
        # Formation bonuses
        formation_bonus = {
            'defensive': {'defense': 0.2},
            'aggressive': {'attack': 0.2},
            'scattered': {'speed': 0.2}
        }.get(self.formation, {})
        
        # Specialization bonuses based on team's focus
        spec_bonus = len(self.specializations) * 0.05
        
        # Apply bonuses to each member
        for member in self.members:
            # Apply level bonus
            member.defense *= (1 + level_bonus)
            member.attack_multiplier *= (1 + level_bonus)
            
            # Apply formation bonus
            for stat, value in formation_bonus.items():
                if hasattr(member, stat):
                    current = getattr(member, stat)
                    setattr(member, stat, current * (1 + value))
            
            # Apply specialization bonus
            member.attack_multiplier *= (1 + spec_bonus)
            member.defense *= (1 + spec_bonus)

    def _level_up(self) -> None:
        """Handle team level up."""
        self.team_level += 1
        self.experience = 0
        
        # Add random specialization on level up
        possible_specs = ['offensive', 'defensive', 'mobility', 'tactical']
        if len(self.specializations) < len(possible_specs):
            new_spec = random.choice([s for s in possible_specs if s not in self.specializations])
            self.specializations.add(new_spec)

    def _update_formation_positions(self) -> None:
        """Update team formation positions based on leader's position."""
        if not self.members:
            return

        # Adjust formation radius based on team size
        self.formation_radius = 100 + (len(self.members) * 10)  # Increased base radius
        angle_step = 2 * math.pi / len(self.members)
        
        # Calculate base formation point ahead of leader's movement
        if isinstance(self.leader, Robot):
            # Use leader's target position to anticipate movement
            lead_x = self.leader.x + (self.leader.target_x - self.leader.x) * 0.5
            lead_y = self.leader.y + (self.leader.target_y - self.leader.y) * 0.5
        else:
            lead_x, lead_y = self.leader.x, self.leader.y

        # Assign positions in formation
        for i, member in enumerate(self.members):
            angle = angle_step * i
            ideal_x = lead_x + math.cos(angle) * self.formation_radius
            ideal_y = lead_y + math.sin(angle) * self.formation_radius
            
            if member._is_valid_position(ideal_x, ideal_y, member.world_grid):
                self.formation_positions[member] = (ideal_x, ideal_y)
    
    def get_member_count(self) -> int:
        """Return total number of team members including leader."""
        active_members = len([m for m in self.members if m.health > 0])
        # Add leader if present (Robot always counts as alive)
        if self.leader:
            if isinstance(self.leader, Robot) or self.leader.health > 0:
                return active_members + 1
        return active_members

    def get_active_members(self) -> list:
        """Return list of active (alive) members."""
        return [m for m in self.members if m.health > 0]

    def is_active(self) -> bool:
        """Check if team has any active members or living leader."""
        return self.get_member_count() > 0
    def _distance_to_leader(self, member: 'Animal') -> float:
        """Calculate distance between member and leader."""
        dx = member.x - self.leader.x
        dy = member.y - self.leader.y
        return math.sqrt(dx * dx + dy * dy)

    def get_target_position(self, member: 'Animal') -> Tuple[float, float]:
        """Get ideal position for a team member."""
        return self.formation_positions.get(member, (self.leader.x, self.leader.y))

    def get_average_position(self) -> Tuple[float, float]:
        """Calculate average position of team including leader and members."""
        if not self.members and not self.leader:
            return (0, 0)
            
        # Start with leader position
        total_x = self.leader.x 
        total_y = self.leader.y
        count = 1
        
        # Add member positions
        for member in self.members:
            total_x += member.x
            total_y += member.y
            count += 1
            
        # Return average
        return (total_x / count, total_y / count)

    def is_ready_for_battle(self, current_frame: int) -> bool:
        """Check if team is ready for another battle."""
        # More permissive battle readiness
        return (
            current_frame - self.last_battle_frame > self.battle_cooldown and
            len(self.members) >= 2 and
            self.get_total_health() > len(self.members) * 30  # Reduced from 200
        )

    def _check_team_cohesion(self) -> bool:
        """Check if team is still cohesive."""
        if not self.members:
            return False

        # Calculate team centroid including leader
        positions = [(m.x, m.y) for m in self.members if m.health > 0]
        positions.append((self.leader.x, self.leader.y))
        
        if len(positions) < 2:
            return False

        # Calculate average position
        avg_x = sum(x for x, _ in positions) / len(positions)
        avg_y = sum(y for y, _ in positions) / len(positions)

        # Track position history
        self.movement_history.append((avg_x, avg_y))
        if len(self.movement_history) > self.max_history:
            self.movement_history.pop(0)

        # Check if team is moving
        is_stationary = len(self.movement_history) > 5 and all(
            abs(p1[0] - p2[0]) < 1 and abs(p1[1] - p2[1]) < 1
            for p1, p2 in zip(self.movement_history[:-1], self.movement_history[1:])
        )

        # Check spread from centroid
        max_distance = 0
        for i, (x, y) in enumerate(positions):
            dist = math.sqrt((x - avg_x)**2 + (y - avg_y)**2)
            if dist > max_distance:
                max_distance = dist

        # Team is cohesive if not too spread out
        return max_distance <= self.max_spread

    def _disband_team(self) -> None:
        """Handle team disbanding."""
        for member in self.members:
            member.team = None
        self.members.clear()

    def _update_territory_center(self) -> None:
        """Update the team's territory center and radius based on leader and member positions."""
        if not self.leader:
            return

        # Leader (robot) is always the territory center
        self.territory_center = (self.leader.x, self.leader.y)

        if not self.members:
            self.territory_radius = self.min_territory_radius
            return
            
        # Get active members (health > 0)
        active_members = [m for m in self.members if m.health > 0]
        
        # If no active members, use minimum radius
        if not active_members:
            self.territory_radius = self.min_territory_radius
            return

        # Calculate maximum distance from leader to any member
        max_distance = max(
            math.sqrt((m.x - self.leader.x)**2 + (m.y - self.leader.y)**2)
            for m in active_members
        )

        # Calculate maximum distance between any two members
        max_member_distance = 0
        for i, member1 in enumerate(active_members):
            for member2 in active_members[i+1:]:
                dist = math.sqrt((member1.x - member2.x)**2 + (member1.y - member2.y)**2)
                max_member_distance = max(max_member_distance, dist)

        # Territory radius is the larger of:
        # 1. Distance to furthest member plus buffer
        # 2. Half the maximum distance between members plus buffer
        # 3. Minimum territory radius
        new_radius = max(
            self.min_territory_radius,
            max_distance * 1.2,  # 20% buffer for leader-member connections
            (max_member_distance / 2) * 1.2  # 20% buffer for member-member connections
        )

        # Smooth transition for radius changes
        self.territory_radius = new_radius

    def get_territory_points(self) -> List[Tuple[float, float]]:
        """Get points that define the territory boundary for visualization."""
        points = []
        num_points = 32  # Number of points to define the circle
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            x = self.territory_center[0] + math.cos(angle) * self.territory_radius
            y = self.territory_center[1] + math.sin(angle) * self.territory_radius
            points.append((x, y))
        return points

    def _graham_scan(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Calculate convex hull of points using Graham Scan algorithm."""
        if len(points) < 3:
            return points
            
        # Find the bottommost point (and leftmost if tied)
        bottom_point = min(points, key=lambda p: (p[1], p[0]))
        
        def sort_key(p):
            return (
                math.atan2(p[1] - bottom_point[1], p[0] - bottom_point[0]),
                (p[0] - bottom_point[0]) ** 2 + (p[1] - bottom_point[1]) ** 2
            )
        
        # Sort points based on polar angle and distance from bottom_point
        sorted_points = sorted(
            [p for p in points if p != bottom_point],
            key=sort_key
        )
        
        # Initialize hull with first three points
        hull = [bottom_point]
        
        # Process remaining points
        for point in sorted_points:
            while len(hull) >= 2 and self._cross_product(
                hull[-2],
                hull[-1],
                point
            ) <= 0:
                hull.pop()
            hull.append(point)
            
        return hull

    def _cross_product(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                      p3: Tuple[float, float]) -> float:
        """Calculate cross product to determine turn direction."""
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

    def is_in_territory(self, point: Tuple[float, float]) -> bool:
        """Check if a point is within the team's territory based on leader-centric model."""
        if not self.leader:
            return False

        # First check if point is within radius of leader
        dx = point[0] - self.leader.x
        dy = point[1] - self.leader.y
        if math.sqrt(dx*dx + dy*dy) <= self.territory_radius:
            return True

        # Get all active member positions
        member_positions = [(m.x, m.y) for m in self.members if m.health > 0]
        if not member_positions:
            return False

        # If we have at least 3 points (including leader), use convex hull
        if len(member_positions) >= 2:
            hull_points = self._graham_scan([(self.leader.x, self.leader.y)] + member_positions)
            if len(hull_points) >= 3:
                # Check if point is inside the polygon using ray casting
                x, y = point
                inside = False
                j = len(hull_points) - 1
                
                for i in range(len(hull_points)):
                    if (((hull_points[i][1] > y) != (hull_points[j][1] > y)) and
                        (x < (hull_points[j][0] - hull_points[i][0]) * (y - hull_points[i][1]) /
                             (hull_points[j][1] - hull_points[i][1]) + hull_points[i][0])):
                        inside = not inside
                    j = i
                
                return inside

        # For fewer points, check if point is within radius of any member
        for pos in member_positions:
            dx = point[0] - pos[0]
            dy = point[1] - pos[1]
            if math.sqrt(dx*dx + dy*dy) <= self.territory_radius:
                return True

        return False

    def check_territory_conflict(self, other_team: 'Team') -> bool:
        """Check if there's a territory conflict with another team."""
        if not self.members or not other_team.members:
            return False

        # Calculate distance between territory centers
        dx = self.territory_center[0] - other_team.territory_center[0]
        dy = self.territory_center[1] - other_team.territory_center[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if territories overlap
        return distance < (self.territory_radius + other_team.territory_radius)

# Import at bottom to avoid circular dependencies
from .robot import Robot
from .animal import Animal