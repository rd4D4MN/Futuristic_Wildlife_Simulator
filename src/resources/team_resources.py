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
        """Gather resources from current positions."""
        # Check leader position
        if team.leader:
            grid_x = int(team.leader.x // 32)  # Assuming TILE_SIZE = 32
            grid_y = int(team.leader.y // 32)
            
            resources = resource_system.get_resources_at(grid_x, grid_y)
            for resource in resources:
                if resource['amount'] > 0:
                    # Gather resource
                    gather_amount = min(5 * dt, resource['amount'])
                    actual_gathered = resource_system.gather_resource(
                        grid_x, grid_y, resource['type'], gather_amount
                    )
                    team.inventory[resource['type']] += actual_gathered
        
        # Check member positions
        for member in team.members:
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
                        gather_amount = min(3 * dt, resource['amount'])
                        actual_gathered = resource_system.gather_resource(
                            grid_x, grid_y, resource['type'], gather_amount
                        )
                        team.inventory[resource['type']] += actual_gathered
    
    @staticmethod
    def _use_resources_for_healing(team: 'Team', dt: float):
        """Use medicinal resources to heal team members."""
        if team.inventory['medicinal'] > 0:
            # Find injured members
            injured = [m for m in team.members if hasattr(m, 'health') and 
                      m.health < getattr(m, 'max_health', 100)]
            
            if injured and len(injured) > 0:
                # Calculate healing amount
                heal_per_resource = 5
                max_heal = min(team.inventory['medicinal'], len(injured) * heal_per_resource * dt)
                heal_per_member = max_heal / len(injured)
                
                # Apply healing
                for member in injured:
                    max_health = getattr(member, 'max_health', 100)
                    heal_amount = min(heal_per_member, max_health - member.health)
                    member.health += heal_amount
                    team.inventory['medicinal'] -= heal_amount / heal_per_resource
    
    @staticmethod
    def _try_build_structures(team: 'Team'):
        """Try to build structures if we have resources."""
        # Skip if on cooldown
        if team.building_cooldown > 0:
            team.building_cooldown -= 1
            return
            
        # Check if we need a shelter
        if not any(s['type'] == 'shelter' for s in team.structures):
            requirements = team.structure_types['shelter']['requirements']
            if all(team.inventory[res] >= amount for res, amount in requirements.items()):
                # Build shelter
                for res, amount in requirements.items():
                    team.inventory[res] -= amount
                
                # Add structure near leader
                if team.leader:
                    offset_x = random.randint(-50, 50)
                    offset_y = random.randint(-50, 50)
                    team.structures.append({
                        'type': 'shelter',
                        'x': team.leader.x + offset_x,
                        'y': team.leader.y + offset_y,
                        'health': 100,
                        'built_time': 0
                    })
                    team.building_cooldown = 300  # Cooldown before next building
        
        # Check if we need a watchtower
        elif not any(s['type'] == 'watchtower' for s in team.structures):
            requirements = team.structure_types['watchtower']['requirements']
            if all(team.inventory[res] >= amount for res, amount in requirements.items()):
                # Build watchtower
                for res, amount in requirements.items():
                    team.inventory[res] -= amount
                
                # Add structure near leader
                if team.leader:
                    angle = random.random() * 2 * math.pi
                    distance = random.randint(60, 100)
                    x = team.leader.x + math.cos(angle) * distance
                    y = team.leader.y + math.sin(angle) * distance
                    
                    team.structures.append({
                        'type': 'watchtower',
                        'x': x,
                        'y': y,
                        'health': 100,
                        'built_time': 0
                    })
                    team.building_cooldown = 300  # Cooldown before next building
    
    @staticmethod
    def _update_resource_strategy(team: 'Team'):
        """Update team resource strategy based on current state."""
        # Skip if no members
        if not team.members:
            return
            
        # Assess team state
        team_health = sum(getattr(m, 'health', 0) for m in team.members) / (len(team.members) * 100)
        has_shelter = any(s['type'] == 'shelter' for s in team.structures)
        
        # Resource assessment
        food_level = (team.inventory['food_plant'] + team.inventory['food_meat']) / (len(team.members) * 50)
        building_level = (team.inventory['wood'] + team.inventory['stone']) / (len(team.members) * 100)
        
        # Decision making
        if team_health < 0.5:
            team.resource_strategy = 'survival'
        elif not has_shelter and building_level > 0.6:
            team.resource_strategy = 'establish_base'
        elif has_shelter and food_level < 0.3:
            team.resource_strategy = 'gather_food'
        elif has_shelter and team_health > 0.8 and building_level > 0.7:
            team.resource_strategy = 'expand'
        else:
            team.resource_strategy = 'balanced'
    
    @staticmethod
    def _find_resource_targets(team: 'Team', resource_system: 'ResourceSystem'):
        """Find appropriate resource targets based on current strategy."""
        if not team.leader:
            return
            
        # Determine target resource type based on strategy
        target_type = None
        
        if team.resource_strategy == 'survival':
            # Prioritize food and medicinal resources
            if team.inventory['food_plant'] + team.inventory['food_meat'] < 20:
                # Check team diet preference
                herbivores = sum(1 for m in team.members if hasattr(m, 'original_data') and 
                               m.original_data.get('Diet', '').lower() == 'herbivore')
                carnivores = sum(1 for m in team.members if hasattr(m, 'original_data') and 
                               m.original_data.get('Diet', '').lower() == 'carnivore')
                
                if herbivores > carnivores:
                    target_type = 'food_plant'
                else:
                    target_type = 'food_meat'
            elif team.inventory['medicinal'] < 10:
                target_type = 'medicinal'
            elif team.inventory['water'] < 20:
                target_type = 'water'
                
        elif team.resource_strategy == 'establish_base':
            # Prioritize building materials
            if team.inventory['wood'] < 50:
                target_type = 'wood'
            elif team.inventory['stone'] < 20:
                target_type = 'stone'
                
        elif team.resource_strategy == 'gather_food':
            # Similar to survival but focused on food
            herbivores = sum(1 for m in team.members if hasattr(m, 'original_data') and 
                           m.original_data.get('Diet', '').lower() == 'herbivore')
            carnivores = sum(1 for m in team.members if hasattr(m, 'original_data') and 
                           m.original_data.get('Diet', '').lower() == 'carnivore')
            
            if herbivores > carnivores:
                target_type = 'food_plant'
            else:
                target_type = 'food_meat'
                
        elif team.resource_strategy == 'expand':
            # Focus on minerals and advanced materials
            if team.inventory['minerals'] < 30:
                target_type = 'minerals'
            elif team.inventory['stone'] < 60:
                target_type = 'stone'
                
        else:  # balanced
            # Choose a random needed resource
            low_resources = [res for res, amount in team.inventory.items() if amount < 30]
            if low_resources:
                target_type = random.choice(low_resources)
        
        # Find nearest resource of target type
        if target_type:
            nearest_pos, distance = resource_system.find_nearest_resource(
                team.leader.x, team.leader.y, target_type, 800.0
            )
            
            if nearest_pos:
                # Set as team target
                team.resource_target = nearest_pos
                team.resource_target_type = target_type
                return
        
        # If no specific target found, find any resource
        nearest_pos, distance = resource_system.find_nearest_resource(
            team.leader.x, team.leader.y, None, 800.0
        )
        
        if nearest_pos:
            # Get the resource type at this position
            resources = resource_system.get_resources_at(*nearest_pos)
            if resources:
                team.resource_target = nearest_pos
                team.resource_target_type = resources[0]['type']
    
    @staticmethod
    def draw_team_structures(team: 'Team', screen, camera_x, camera_y):
        """Draw team structures on the screen."""
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
            
            # Draw colored background circle for the building
            pygame.draw.circle(
                screen,
                team.color,  # Use team color
                (x, y),
                15  # Size of background
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