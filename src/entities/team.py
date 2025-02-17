from typing import List, Tuple, Union, Optional
import pygame
import random
import math

class Team:
    def __init__(self, leader: Union['Robot', 'Animal']):
        """Initialize team with a leader."""
        # Basic attributes
        self.leader = leader
        self.members: List['Animal'] = []
        
        # Timing and cooldowns first
        self.battle_cooldown = 180
        self.last_battle_frame = -self.battle_cooldown
        self.search_timer = 0
        self.search_interval = 5
        self.last_cohesion_check = 0
        self.cohesion_check_interval = 0.5  # More frequent checks
        self.last_debug_time = 0
        self.debug_interval = 5.0
        
        # Team appearance and formation
        self.color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255)
        )
        self.formation = random.choice(['aggressive', 'defensive', 'scout'])
        
        # Combat and stats
        self.team_level = 1
        self.experience = 0
        self.specializations = set()
        self.battle_stats = {'wins': 0, 'losses': 0, 'members_lost': 0}
        self.aggression = random.uniform(0.8, 2.0)
        
        # Movement and positioning
        self.max_distance_from_leader = 300  # Reduced from 400
        self.base_formation_radius = 50  # Base radius for formation
        self.max_formation_radius = 200  # Maximum formation radius
        self.formation_positions = {}
        self.patrol_points = []
        self.current_patrol_index = 0
        self.target_x, self.target_y = self.leader.x, self.leader.y
        self.territory_center = (leader.x, leader.y)
        
        # Team state
        self.disbanding = False
        self.disband_timer = 0
        self.max_disband_time = 10.0
        self.max_spread = 400  # Reduced back to 400
        
        # Debug and tracking
        self.debug_logs = []
        self.movement_history = []
        self.max_history = 10
        self.cohesion_violations = 0  # Track consecutive cohesion violations
        
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
            return f"Robot-{id(self.leader)%1000:03d}"
        
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
        """Update team behavior with enhanced debugging."""
        # Check cohesion periodically
        self.last_cohesion_check += dt
        if self.last_cohesion_check >= self.cohesion_check_interval:
            self.last_cohesion_check = 0
            cohesion_result = self._check_team_cohesion()
            if not cohesion_result and not self.disbanding:
                self.disbanding = True
                self._log_debug("Starting disband countdown due to failed cohesion check")
            else:
                if self.disbanding:
                    self._log_debug("Team regained cohesion - canceling disband")
                    self.disbanding = False
                    self.disband_timer = 0

        # Handle disbanding with grace period
        if self.disbanding:
            self.disband_timer += dt
            self._log_debug(f"Disband timer: {self.disband_timer:.1f}/{self.max_disband_time}")
            
            if self.disband_timer >= self.max_disband_time:
                if self._check_team_cohesion():
                    self.disbanding = False
                    self.disband_timer = 0
                    self._log_debug("Team recovered from disbanding state")
                else:
                    self._log_debug("Final disband: Team could not recover cohesion")
                    self._disband_team()
                    return

        # Update positions
        self._update_formation_positions()

        # Move members toward their formation positions
        if self.members:
            base_speed = min(member.speed for member in self.members)
            
            for member in self.members:
                if member in self.formation_positions:
                    target_x, target_y = self.formation_positions[member]
                    dx = target_x - member.x
                    dy = target_y - member.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    
                    if dist > 5:  # Only move if not at position
                        speed_mult = min(2.0, dist / 50)  # Faster catch-up when far
                        move_speed = base_speed * speed_mult * dt
                        
                        # Calculate movement with collision avoidance
                        move_x = (dx/dist) * move_speed
                        move_y = (dy/dist) * move_speed
                        
                        # Apply movement if valid
                        new_x = member.x + move_x
                        new_y = member.y + move_y
                        
                        if member._is_valid_position(new_x, new_y, member.world_grid):
                            member.x = new_x
                            member.y = new_y

        # Level up check
        if self.experience >= self.team_level * 100:
            self._level_up()

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
        """Check if team is still cohesive with detailed logging."""
        if not self.members:
            self._log_debug("Team disbanded: No members remaining")
            return False

        # Calculate team centroid including leader
        positions = [(m.x, m.y) for m in self.members if m.health > 0]
        positions.append((self.leader.x, self.leader.y))
        
        if len(positions) < 2:
            self._log_debug("Team disbanded: Not enough active members")
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

        if is_stationary:
            self._log_debug("Team is stationary - checking if stuck")

        # Check spread from centroid
        max_distance = 0
        furthest_member = None
        for i, (x, y) in enumerate(positions):
            dist = math.sqrt((x - avg_x)**2 + (y - avg_y)**2)
            if dist > max_distance:
                max_distance = dist
                furthest_member = i

        # if max_distance > self.max_spread:
        #     entity_type = "Leader" if furthest_member == len(positions) - 1 else f"Member {furthest_member}"
        #     self._log_debug(f"Team spread check failed: {entity_type} at distance {max_distance:.2f} > {self.max_spread}")
        #     return False

        return True

    def _log_debug(self, message: str) -> None:
        """Add timestamped debug message for critical events only."""
        # Only log critical events and reduce frequency
        critical_keywords = ['disbanded', 'failed', 'recovered']
        
        if not any(keyword in message.lower() for keyword in critical_keywords):
            return
            
        current_time = pygame.time.get_ticks() / 1000.0
        if current_time - self.last_debug_time >= self.debug_interval:
            self.last_debug_time = current_time
            # Only log if spread is significantly over the limit
            if 'spread check failed' in message:
                distance = float(message.split('distance ')[1].split(' >')[0])
                if distance > self.max_spread * 1.5:  # Only log if significantly over limit
                    print(f"[{current_time:.1f}s] Team {self.get_leader_name()}: {message}")
            else:
                print(f"[{current_time:.1f}s] Team {self.get_leader_name()}: {message}")
            
    def _disband_team(self) -> None:
        """Handle team disbanding."""
        for member in self.members:
            member.team = None
        self.members.clear()

# Import at bottom to avoid circular dependencies
from .robot import Robot
from .animal import Animal