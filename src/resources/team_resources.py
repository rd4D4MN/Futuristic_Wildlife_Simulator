from typing import Dict, List, Tuple, Optional, Union, TYPE_CHECKING
import random
import math
import pygame

if TYPE_CHECKING:
    from src.entities.team import Team
    from src.entities.animal import Animal
    from src.entities.robot import Robot
    from src.resources.resource_system import ResourceSystem

class TeamResourceExtension:
    """Extension class to add resource functionality to teams."""
    
    @staticmethod
    def initialize_team_resources(team: 'Team'):
        """Initialize resource-related attributes for a team."""
        # Add inventory to store resources
        team.inventory = {
            'food_plant': 0,
            'food_meat': 0,
            'wood': 0,
            'stone': 0,
            'water': 0,
            'medicinal': 0,
            'minerals': 0
        }
        
        # Add structures list
        team.structures = []
        
        # Add resource-related strategy attributes
        team.resource_strategy = 'balanced'  # Default strategy
        team.resource_target = None  # Current resource gathering target
        team.resource_target_type = None  # Type of resource being targeted
        team.last_resource_search = 0  # Timer for resource searching
        team.resource_search_interval = 3.0  # Search every 3 seconds
        
        # Add building-related attributes
        team.building_cooldown = 0  # Cooldown for building structures
        team.building_in_progress = None  # Current building being constructed
        
        # Structure definitions
        team.structure_types = {
            'shelter': {
                'requirements': {'wood': 50, 'stone': 20},
                'emoji': '🏠',
                'benefits': {'protection': 0.5, 'healing': 0.1}
            },
            'watchtower': {
                'requirements': {'wood': 30},
                'emoji': '🗼',
                'benefits': {'visibility': 1.5, 'defense': 0.2}
            },
            'storage': {
                'requirements': {'wood': 40, 'stone': 10},
                'emoji': '🏪',
                'benefits': {'capacity': 2.0}
            },
            'wall': {
                'requirements': {'stone': 60},
                'emoji': '🧱',
                'benefits': {'defense': 0.5}
            }
        }
    
    @staticmethod
    def update_team_resources(team: 'Team', dt: float, resource_system: 'ResourceSystem'):
        """Update resource-related behaviors for a team."""
        # Skip if team is disbanding
        if hasattr(team, 'disbanding') and team.disbanding:
            return
            
        # Make sure team has all required resource attributes
        if not hasattr(team, 'inventory') or not hasattr(team, 'resource_strategy'):
            # Re-initialize if attributes are missing
            TeamResourceExtension.initialize_team_resources(team)
            
        # Update resource search timer
        team.last_resource_search += dt
        
        # Gather resources from current positions
        TeamResourceExtension._gather_resources(team, dt, resource_system)
        
        # Use resources for healing
        TeamResourceExtension._use_resources_for_healing(team, dt)
        
        # Try to build structures
        TeamResourceExtension._try_build_structures(team)
        
        # Update resource strategy
        TeamResourceExtension._update_resource_strategy(team)
        
        # Find new resource targets if needed
        if team.last_resource_search >= team.resource_search_interval:
            team.last_resource_search = 0
            TeamResourceExtension._find_resource_targets(team, resource_system)
    
    @staticmethod
    def _gather_resources(team: 'Team', dt: float, resource_system: 'ResourceSystem'):
        """Gather resources from current positions with proper proximity checks and team distribution."""
        gathered_resources = {}  # Track resources gathered by the team
        
        # Check leader position - leader can gather any resource
        if team.leader:
            grid_x = int(team.leader.x // 32)  # Assuming TILE_SIZE = 32
            grid_y = int(team.leader.y // 32)
            
            resources = resource_system.get_resources_at(grid_x, grid_y)
            for resource in resources:
                if resource['amount'] > 0:
                    # Gather resource - only when in the same tile
                    gather_amount = min(8 * dt, resource['amount'])
                    actual_gathered = resource_system.gather_resource(
                        grid_x, grid_y, resource['type'], gather_amount
                    )
                    
                    # Add to gathered resources
                    if resource['type'] not in gathered_resources:
                        gathered_resources[resource['type']] = 0
                    gathered_resources[resource['type']] += actual_gathered
                    
                    # Set leader state for visual indicators
                    if hasattr(team.leader, 'state') and hasattr(team.leader, 'resource_target_type'):
                        team.leader.state = "seeking_resource"
                        team.leader.resource_target_type = resource['type']
        
        # Check member positions - members can only gather resources they're compatible with
        for member in team.members:
            if member == team.leader:
                continue  # Skip leader as we already processed them
                
            grid_x = int(member.x // 32)
            grid_y = int(member.y // 32)
            
            resources = resource_system.get_resources_at(grid_x, grid_y)
            for resource in resources:
                if resource['amount'] > 0:
                    # Check if member can gather this resource type
                    can_gather = False
                    
                    # Check member type if it's an animal
                    if hasattr(member, 'original_data'):
                        diet = member.original_data.get('Diet', 'omnivore').lower()
                        if resource['type'] == 'food_plant' and diet in ['herbivore', 'omnivore']:
                            can_gather = True
                        elif resource['type'] == 'food_meat' and diet in ['carnivore', 'omnivore']:
                            can_gather = True
                        elif resource['type'] in ['wood', 'stone', 'water', 'medicinal', 'minerals']:
                            can_gather = True
                    else:
                        # Robots can gather any resource
                        can_gather = True
                            
                    if can_gather:
                        # Gather resource - only when in the same tile
                        gather_amount = min(5 * dt, resource['amount'])
                        actual_gathered = resource_system.gather_resource(
                            grid_x, grid_y, resource['type'], gather_amount
                        )
                        
                        # Add to gathered resources
                        if resource['type'] not in gathered_resources:
                            gathered_resources[resource['type']] = 0
                        gathered_resources[resource['type']] += actual_gathered
                        
                        # Set member state for visual indicators
                        if hasattr(member, 'state') and hasattr(member, 'resource_target_type'):
                            member.state = "seeking_resource"
                            member.resource_target_type = resource['type']
        
        # Distribute gathered resources to team inventory
        for resource_type, amount in gathered_resources.items():
            team.inventory[resource_type] += amount
            
            # Distribute food and water to team members who need it
            if resource_type in ['food_plant', 'food_meat', 'water'] and amount > 0:
                TeamResourceExtension._distribute_resources(team, resource_type, amount)
    
    @staticmethod
    def _distribute_resources(team: 'Team', resource_type: str, amount: float):
        """Distribute resources like food and water to team members who need it."""
        if amount <= 0:
            return
            
        # Find members who can use this resource
        eligible_members = []
        for member in team.members:
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
    
    @staticmethod
    def _use_resources_for_healing(team: 'Team', dt: float):
        """Use medicinal resources to heal team members with improved efficiency."""
        if team.inventory['medicinal'] <= 0:
            return
            
        # Find injured members and sort by health percentage (most injured first)
        injured = []
        for member in team.members:
            if hasattr(member, 'health') and hasattr(member, 'max_health'):
                health_percent = member.health / member.max_health
                if health_percent < 0.95:  # Consider anyone below 95% as needing healing
                    injured.append((member, health_percent))
        
        # Sort by health percentage (ascending)
        injured.sort(key=lambda x: x[1])
        
        # Determine healing strategy based on team state
        if hasattr(team, 'strategy_context'):
            team_health_avg = team.strategy_context.get('team_health_avg', 0.5)
            
            # Critical situation - heal everyone a little
            if team_health_avg < 0.3 and len(injured) > 1:
                # Distribute healing among all injured members
                healing_per_member = min(team.inventory['medicinal'] / len(injured), 2.0)
                
                for member, _ in injured:
                    if team.inventory['medicinal'] >= healing_per_member:
                        # Apply healing
                        heal_amount = healing_per_member * 5  # 5 health points per resource unit
                        member.heal(heal_amount)
                        team.inventory['medicinal'] -= healing_per_member
            
            # Normal situation - focus on most injured first
            else:
                # Heal the most injured members first
                for member, health_percent in injured:
                    # Calculate healing needed based on how injured they are
                    healing_needed = (1.0 - health_percent) * 10
                    healing_to_use = min(healing_needed, team.inventory['medicinal'], 5.0)
                    
                    if healing_to_use > 0:
                        # Apply healing
                        heal_amount = healing_to_use * 5  # 5 health points per resource unit
                        member.heal(heal_amount)
                        team.inventory['medicinal'] -= healing_to_use
                        
                        # Stop if we're out of medicinal resources
                        if team.inventory['medicinal'] <= 0:
                            break
        else:
            # Fallback if strategy context is not available
            if injured:
                # Simple healing for the most injured member
                member = injured[0][0]
                healing_to_use = min(5.0, team.inventory['medicinal'])
                heal_amount = healing_to_use * 5
                member.heal(heal_amount)
                team.inventory['medicinal'] -= healing_to_use
    
    @staticmethod
    def _try_build_structures(team: 'Team'):
        """Try to build structures with improved strategic decision making."""
        # Skip if no leader or on cooldown
        if not team.leader or team.building_cooldown > 0:
            return
            
        # Get structure counts
        structure_counts = {}
        for s in team.structures:
            structure_counts[s['type']] = structure_counts.get(s['type'], 0) + 1
            
        # Determine what to build based on team strategy and needs
        structure_to_build = None
        
        # Shelter is highest priority if we don't have one
        if structure_counts.get('shelter', 0) == 0:
            structure_to_build = 'shelter'
            
        # If we have a shelter, consider other structures based on strategy
        elif team.resource_strategy == 'defense':
            if structure_counts.get('watchtower', 0) == 0:
                structure_to_build = 'watchtower'
            elif structure_counts.get('wall', 0) < 2:  # Allow multiple walls
                structure_to_build = 'wall'
                
        elif team.resource_strategy == 'expand':
            if structure_counts.get('storage', 0) == 0:
                structure_to_build = 'storage'
            elif structure_counts.get('watchtower', 0) == 0:
                structure_to_build = 'watchtower'
                
        elif team.resource_strategy == 'balanced':
            # Build a balanced set of structures
            if structure_counts.get('watchtower', 0) == 0:
                structure_to_build = 'watchtower'
            elif structure_counts.get('storage', 0) == 0:
                structure_to_build = 'storage'
            elif structure_counts.get('wall', 0) < 2:
                structure_to_build = 'wall'
        
        # Check if we have resources to build the selected structure
        if structure_to_build and hasattr(team, 'structure_types'):
            requirements = team.structure_types[structure_to_build]['requirements']
            
            # Allow building if we have at least 80% of required resources
            if all(team.inventory[res] >= amount * 0.8 for res, amount in requirements.items()):
                # Deduct resources - only what we have
                for res, amount in requirements.items():
                    actual_amount = min(team.inventory[res], amount)
                    team.inventory[res] -= actual_amount
                
                # Add structure near leader
                if team.leader:
                    # Place structure strategically based on type
                    if structure_to_build == 'shelter':
                        # Place shelter at center of territory
                        offset_x = random.randint(-20, 20)
                        offset_y = random.randint(-20, 20)
                    elif structure_to_build == 'watchtower':
                        # Place watchtower at perimeter for visibility
                        angle = random.random() * 2 * math.pi
                        distance = random.randint(80, 120)
                        offset_x = math.cos(angle) * distance
                        offset_y = math.sin(angle) * distance
                    elif structure_to_build == 'wall':
                        # Place walls in a defensive perimeter
                        angle = random.random() * 2 * math.pi
                        distance = random.randint(60, 100)
                        offset_x = math.cos(angle) * distance
                        offset_y = math.sin(angle) * distance
                    else:  # storage or other
                        # Place storage near shelter
                        offset_x = random.randint(-50, 50)
                        offset_y = random.randint(-50, 50)
                    
                    # Add the structure
                    team.structures.append({
                        'type': structure_to_build,
                        'x': team.leader.x + offset_x,
                        'y': team.leader.y + offset_y,
                        'health': 100,
                        'built_time': 0
                    })
                    
                    # Set cooldown - reduced for faster building
                    team.building_cooldown = 120  # 2 minutes cooldown (reduced from 3)
    
    @staticmethod
    def _update_resource_strategy(team: 'Team'):
        """Update team resource strategy based on current state with improved decision making."""
        # Skip if no members
        if not team.members:
            return
            
        # Assess team state with more detailed metrics
        team_health_values = [getattr(m, 'health', 0) / getattr(m, 'max_health', 100) for m in team.members]
        team_health_avg = sum(team_health_values) / len(team_health_values)
        team_health_min = min(team_health_values)
        
        # Count structures by type
        structure_counts = {}
        for s in team.structures:
            structure_counts[s['type']] = structure_counts.get(s['type'], 0) + 1
            
        # Resource assessment with more detailed metrics
        food_plant_per_member = team.inventory['food_plant'] / max(1, len(team.members))
        food_meat_per_member = team.inventory['food_meat'] / max(1, len(team.members))
        medicinal_per_member = team.inventory['medicinal'] / max(1, len(team.members))
        wood_amount = team.inventory['wood']
        stone_amount = team.inventory['stone']
        minerals_amount = team.inventory['minerals']
        
        # Enhanced decision making with priority system
        priorities = []
        
        # Critical health situation - highest priority
        if team_health_min < 0.3:
            priorities.append(('survival', 10))
        elif team_health_avg < 0.5:
            priorities.append(('survival', 8))
            
        # Base establishment - high priority if no shelter
        if structure_counts.get('shelter', 0) == 0:
            if wood_amount >= 40 and stone_amount >= 15:
                # We have enough resources to build a shelter
                priorities.append(('establish_base', 9))
            else:
                # Need to gather resources for shelter
                priorities.append(('establish_base', 7))
                
        # Food security - medium-high priority
        if food_plant_per_member < 5 and food_meat_per_member < 5:
            priorities.append(('gather_food', 6))
            
        # Defense - medium priority if we have a base but no defenses
        if (structure_counts.get('shelter', 0) > 0 and 
            structure_counts.get('watchtower', 0) == 0 and 
            structure_counts.get('wall', 0) == 0):
            priorities.append(('defense', 5))
            
        # Expansion - lower priority when other needs are met
        if (team_health_avg > 0.7 and 
            structure_counts.get('shelter', 0) > 0 and 
            food_plant_per_member + food_meat_per_member > 15):
            priorities.append(('expand', 3))
            
        # Balanced approach - lowest priority as fallback
        priorities.append(('balanced', 1))
        
        # Sort by priority (highest first) and select the top strategy
        priorities.sort(key=lambda x: x[1], reverse=True)
        team.resource_strategy = priorities[0][0]
        
        # Store additional context for more nuanced behavior
        team.strategy_context = {
            'team_health_avg': team_health_avg,
            'team_health_min': team_health_min,
            'structure_counts': structure_counts,
            'food_per_member': food_plant_per_member + food_meat_per_member,
            'medicinal_per_member': medicinal_per_member,
            'priorities': priorities
        }
    
    @staticmethod
    def _find_resource_targets(team: 'Team', resource_system: 'ResourceSystem'):
        """Find appropriate resource targets based on current strategy with improved decision making."""
        if not team.leader:
            return
            
        # Determine target resource type based on strategy
        target_type = None
        
        # Get team composition for diet-based decisions
        herbivores = sum(1 for m in team.members if hasattr(m, 'original_data') and 
                       m.original_data.get('Diet_Type', '').lower() == 'herbivore')
        carnivores = sum(1 for m in team.members if hasattr(m, 'original_data') and 
                       m.original_data.get('Diet_Type', '').lower() == 'carnivore')
        omnivores = sum(1 for m in team.members if hasattr(m, 'original_data') and 
                       m.original_data.get('Diet_Type', '').lower() == 'omnivore')
        
        # Enhanced strategy-based targeting
        if team.resource_strategy == 'survival':
            # Critical survival needs - medicinal first, then food
            if team.inventory['medicinal'] < 15:  # Increased from 10
                target_type = 'medicinal'
            elif team.inventory['food_plant'] + team.inventory['food_meat'] < 30:  # Increased from 20
                # Choose food type based on team composition
                if herbivores > carnivores + omnivores:
                    target_type = 'food_plant'
                elif carnivores > herbivores + omnivores:
                    target_type = 'food_meat'
                else:
                    # Mixed diet team - choose the resource with lower inventory
                    target_type = 'food_plant' if team.inventory['food_plant'] < team.inventory['food_meat'] else 'food_meat'
            elif team.inventory['water'] < 30:  # Increased from 20
                target_type = 'water'
                
        elif team.resource_strategy == 'establish_base':
            # Building a base - prioritize wood then stone
            if team.inventory['wood'] < 50:
                target_type = 'wood'
            elif team.inventory['stone'] < 20:
                target_type = 'stone'
                
        elif team.resource_strategy == 'gather_food':
            # Food gathering - choose based on team composition and current inventory
            plant_need = max(0, 15 * (herbivores + omnivores) - team.inventory['food_plant'])  # Increased from 10
            meat_need = max(0, 15 * (carnivores + omnivores) - team.inventory['food_meat'])   # Increased from 10
            
            if plant_need > meat_need:
                target_type = 'food_plant'
            else:
                target_type = 'food_meat'
                
        elif team.resource_strategy == 'defense':
            # Defense focus - stone for walls, wood for watchtowers
            if team.inventory['stone'] < 60:
                target_type = 'stone'
            elif team.inventory['wood'] < 30:
                target_type = 'wood'
                
        elif team.resource_strategy == 'expand':
            # Expansion - focus on advanced materials
            if team.inventory['minerals'] < 30:
                target_type = 'minerals'
            elif team.inventory['stone'] < 60:
                target_type = 'stone'
            elif team.inventory['wood'] < 40:
                target_type = 'wood'
                
        else:  # balanced
            # Balanced approach - identify the most needed resource
            resource_needs = {
                'food_plant': max(0, 15 - team.inventory['food_plant'] / max(1, herbivores + omnivores)),  # Increased from 10
                'food_meat': max(0, 15 - team.inventory['food_meat'] / max(1, carnivores + omnivores)),    # Increased from 10
                'medicinal': max(0, 8 - team.inventory['medicinal'] / max(1, len(team.members))),          # Increased from 5
                'wood': max(0, 30 - team.inventory['wood']),                                               # Increased from 20
                'stone': max(0, 30 - team.inventory['stone']),                                             # Increased from 20
                'water': max(0, 15 - team.inventory['water']),                                             # Increased from 10
                'minerals': max(0, 15 - team.inventory['minerals'])                                        # Increased from 10
            }
            
            # Find the resource with highest need
            max_need = 0
            for res, need in resource_needs.items():
                if need > max_need:
                    max_need = need
                    target_type = res
        
        # Find nearest resource of target type with increased search radius
        if target_type:
            nearest_pos, distance = resource_system.find_nearest_resource(
                team.leader.x, team.leader.y, target_type, 1200.0  # Increased from 800
            )
            
            if nearest_pos:
                # Set as team target
                team.resource_target = nearest_pos
                team.resource_target_type = target_type
                
                # Update team members' states for visual indicators
                for member in team.members:
                    if hasattr(member, 'state'):
                        member.state = "seeking_resource"
                        if hasattr(member, 'resource_target_type'):
                            member.resource_target_type = target_type
                        if hasattr(member, 'resource_target'):
                            member.resource_target = nearest_pos
                return
        
        # If no specific target found, find any resource
        nearest_pos, distance = resource_system.find_nearest_resource(
            team.leader.x, team.leader.y, None, 1200.0  # Increased from 800
        )
        
        if nearest_pos:
            team.resource_target = nearest_pos
            team.resource_target_type = None
            
            # Update team members' states for visual indicators
            for member in team.members:
                if hasattr(member, 'state'):
                    member.state = "seeking_resource"
                    if hasattr(member, 'resource_target'):
                        member.resource_target = nearest_pos
    
    @staticmethod
    def draw_team_structures(team: 'Team', screen, camera_x, camera_y):
        """Draw team structures on the screen with improved visibility."""
        # Skip if no structures or missing attributes
        if not hasattr(team, 'structures') or not team.structures:
            return
            
        # Make sure team has structure_types
        if not hasattr(team, 'structure_types'):
            # Re-initialize if attributes are missing
            TeamResourceExtension.initialize_team_resources(team)
            
        # Initialize font for rendering emojis if not already done
        if not hasattr(team, 'emoji_font'):
            try:
                # Try to use a font that supports emojis
                team.emoji_font = pygame.font.SysFont('Segoe UI Emoji', 24)  # Windows emoji font
            except:
                # Fallback to default font
                team.emoji_font = pygame.font.SysFont('Arial', 24)
        
        # Draw structures with emojis
        for structure in team.structures:
            x = structure['x'] - camera_x
            y = structure['y'] - camera_y
            
            # Skip if off-screen
            if x < -50 or y < -50 or x > screen.get_width() + 50 or y > screen.get_height() + 50:
                continue
            
            # Draw colored background circle for the building
            pygame.draw.circle(
                screen,
                team.color,  # Use team color
                (x, y),
                20  # Increased size for better visibility
            )
            
            # Draw building emoji
            emoji = team.structure_types.get(structure['type'], {}).get('emoji', '?')
            try:
                emoji_surface = team.emoji_font.render(emoji, True, (0, 0, 0))
                screen.blit(
                    emoji_surface,
                    (x - emoji_surface.get_width() // 2, 
                     y - emoji_surface.get_height() // 2)
                )
            except Exception as e:
                # Fallback to text if emoji rendering fails
                fallback = structure['type'][0].upper()  # First letter
                text_surface = team.emoji_font.render(fallback, True, (0, 0, 0))
                screen.blit(
                    text_surface,
                    (x - text_surface.get_width() // 2, 
                     y - text_surface.get_height() // 2)
                )
                
            # Draw structure type label below
            small_font = pygame.font.SysFont('Arial', 12)
            label = small_font.render(structure['type'].capitalize(), True, (255, 255, 255))
            screen.blit(
                label,
                (x - label.get_width() // 2, y + 22)
            )
            
            # Draw a border around the structure
            pygame.draw.circle(
                screen,
                (0, 0, 0),  # Black border
                (x, y),
                20,  # Same as background size
                2    # Border width
            )
        
        # Draw team resource target if available
        if hasattr(team, 'resource_target') and team.resource_target and hasattr(team, 'resource_target_type'):
            target_x, target_y = team.resource_target
            screen_x = (target_x * 32) + 16 - camera_x  # Center of tile
            screen_y = (target_y * 32) + 16 - camera_y
            
            # Skip if off-screen
            if screen_x < -50 or screen_y < -50 or screen_x > screen.get_width() + 50 or screen_y > screen.get_height() + 50:
                return
                
            # Define colors for different resource types
            resource_colors = {
                'food_plant': (0, 200, 0),    # Green
                'food_meat': (200, 0, 0),     # Red
                'wood': (139, 69, 19),        # Brown
                'stone': (128, 128, 128),     # Gray
                'water': (0, 0, 255),         # Blue
                'medicinal': (255, 0, 255),   # Purple
                'minerals': (255, 215, 0)     # Gold
            }
            
            # Get color based on resource type
            color = resource_colors.get(team.resource_target_type, (255, 255, 255))
            
            # Draw a target indicator
            pygame.draw.circle(screen, color, (screen_x, screen_y), 10, 2)
            pygame.draw.line(screen, color, (screen_x - 15, screen_y), (screen_x + 15, screen_y), 2)
            pygame.draw.line(screen, color, (screen_x, screen_y - 15), (screen_x, screen_y + 15), 2)
            
            # Draw a line from leader to target
            if team.leader:
                leader_x = team.leader.x - camera_x
                leader_y = team.leader.y - camera_y
                pygame.draw.line(screen, color, (leader_x, leader_y), (screen_x, screen_y), 1)
                
        # Draw team strategy indicator near leader
        if team.leader and hasattr(team, 'resource_strategy'):
            leader_x = team.leader.x - camera_x
            leader_y = team.leader.y - camera_y - 30  # Position above leader
            
            # Skip if off-screen
            if leader_x < -50 or leader_y < -50 or leader_x > screen.get_width() + 50 or leader_y > screen.get_height() + 50:
                return
                
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
            color = strategy_colors.get(team.resource_strategy, (255, 255, 255))
            
            # Draw strategy indicator
            pygame.draw.circle(screen, color, (leader_x, leader_y), 8)
            pygame.draw.circle(screen, (0, 0, 0), (leader_x, leader_y), 8, 1)  # Border
            
            # Draw strategy label
            small_font = pygame.font.SysFont('Arial', 12)
            label = small_font.render(team.resource_strategy.replace('_', ' ').capitalize(), True, (255, 255, 255))
            
            # Draw background for text
            text_bg = pygame.Surface((label.get_width() + 4, label.get_height() + 4))
            text_bg.fill((0, 0, 0))
            text_bg.set_alpha(150)
            screen.blit(text_bg, (leader_x - label.get_width() // 2 - 2, leader_y - 25))
            
            # Draw text
            screen.blit(label, (leader_x - label.get_width() // 2, leader_y - 23)) 