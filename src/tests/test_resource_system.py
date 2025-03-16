import pygame
import random
import math
import time
from typing import Dict, List, Tuple, Any

# Constants for testing
TILE_SIZE = 32
WORLD_WIDTH = 50
WORLD_HEIGHT = 30

class TestResourceSystem:
    def __init__(self, world_grid):
        self.world_grid = world_grid
        self.resources = {}  # Map of position to resource
        self.resource_types = {
            'food_plant': {'terrain': ['grassland', 'forest'], 'regrowth_rate': 0.01, 'color': (0, 255, 0)},
            'food_meat': {'terrain': ['grassland'], 'regrowth_rate': 0.005, 'color': (255, 0, 0)},
            'wood': {'terrain': ['forest'], 'regrowth_rate': 0.008, 'color': (139, 69, 19)},
            'stone': {'terrain': ['mountain'], 'regrowth_rate': 0.003, 'color': (128, 128, 128)},
            'water': {'terrain': ['aquatic', 'wetland'], 'regrowth_rate': 0.02, 'color': (0, 0, 255)},
            'medicinal': {'terrain': ['forest', 'wetland'], 'regrowth_rate': 0.004, 'color': (255, 0, 255)},
            'minerals': {'terrain': ['mountain'], 'regrowth_rate': 0.001, 'color': (255, 215, 0)}
        }
        self._initialize_resources()
        
    def _initialize_resources(self):
        """Generate initial resources based on terrain"""
        for y, row in enumerate(self.world_grid):
            for x, terrain in enumerate(row):
                for resource_type, data in self.resource_types.items():
                    if terrain in data['terrain'] and random.random() < 0.2:
                        pos = (x, y)
                        if pos not in self.resources:
                            self.resources[pos] = []
                        self.resources[pos].append({
                            'type': resource_type,
                            'amount': random.randint(10, 100),
                            'max_amount': 100,
                            'last_update': time.time()
                        })
    
    def update(self, dt):
        """Update resources (regrowth)"""
        current_time = time.time()
        
        # Process regrowth for existing resources
        for pos, resources in self.resources.items():
            for resource in resources:
                if resource['amount'] < resource['max_amount']:
                    time_diff = current_time - resource['last_update']
                    regrowth_rate = self.resource_types[resource['type']]['regrowth_rate']
                    resource['amount'] += regrowth_rate * time_diff * 100  # Scale for testing
                    resource['amount'] = min(resource['amount'], resource['max_amount'])
                resource['last_update'] = current_time
        
        # Occasionally add new resources
        if random.random() < 0.01:
            y = random.randint(0, len(self.world_grid) - 1)
            x = random.randint(0, len(self.world_grid[0]) - 1)
            terrain = self.world_grid[y][x]
            
            possible_resources = [r for r, data in self.resource_types.items() 
                                if terrain in data['terrain']]
            
            if possible_resources:
                resource_type = random.choice(possible_resources)
                pos = (x, y)
                if pos not in self.resources:
                    self.resources[pos] = []
                
                # Check if this resource type already exists at this position
                if not any(r['type'] == resource_type for r in self.resources[pos]):
                    self.resources[pos].append({
                        'type': resource_type,
                        'amount': random.randint(10, 50),
                        'max_amount': 100,
                        'last_update': current_time
                    })
    
    def draw(self, screen, camera_x, camera_y):
        """Draw resources on screen using emojis"""
        # Initialize font for rendering emojis if not already done
        if not hasattr(self, 'emoji_font'):
            try:
                # Try to use a font that supports emojis
                self.emoji_font = pygame.font.SysFont('Segoe UI Emoji', 24)  # Windows emoji font
            except:
                # Fallback to default font
                self.emoji_font = pygame.font.SysFont('Arial', 24)
        
        # Define emoji symbols for each resource type
        emoji_symbols = {
            'food_plant': '🍎',  # Apple
            'food_meat': '🍖',   # Meat
            'wood': '🌲',        # Tree
            'stone': '🗿',       # Moai statue
            'water': '💧',       # Water Drop
            'medicinal': '💊',   # Pill
            'minerals': '💎'     # Gem
        }
        
        # Fallback symbols in case emojis don't render properly
        fallback_symbols = {
            'food_plant': 'F',
            'food_meat': 'M',
            'wood': 'W',
            'stone': 'S',
            'water': 'H',
            'medicinal': '+',
            'minerals': '$'
        }
        
        for pos, resources in self.resources.items():
            x, y = pos
            screen_x = x * TILE_SIZE - camera_x
            screen_y = y * TILE_SIZE - camera_y
            
            # Skip if off screen
            if (screen_x < -TILE_SIZE or screen_x > screen.get_width() or
                screen_y < -TILE_SIZE or screen_y > screen.get_height()):
                continue
            
            # Center of the tile
            center_x = screen_x + TILE_SIZE // 2
            center_y = screen_y + TILE_SIZE // 2
            
            for resource in resources:
                if resource['amount'] > 5:  # Only draw if significant amount
                    # Calculate size based on amount
                    size_factor = resource['amount'] / resource['max_amount']
                    base_size = 5 + int(10 * size_factor)
                    color = self.resource_types[resource['type']]['color']
                    
                    # Draw background circle with resource color - make it larger for wood and stone
                    circle_size = base_size * 1.2
                    if resource['type'] in ['wood', 'stone']:
                        circle_size = base_size * 1.8  # Even larger background for wood and stone
                        
                    # Draw a more visible background for wood
                    if resource['type'] == 'wood':
                        # Draw a brown rectangle for wood
                        rect_width = circle_size * 1.5
                        rect_height = circle_size
                        pygame.draw.rect(
                            screen,
                            (101, 67, 33),  # Brown
                            (center_x - rect_width//2, center_y - rect_height//2, rect_width, rect_height),
                            border_radius=3
                        )
                        # Add wood grain lines
                        for i in range(2):
                            line_y = center_y - rect_height//4 + i * rect_height//2
                            pygame.draw.line(
                                screen,
                                (139, 69, 19),  # Darker brown
                                (center_x - rect_width//2 + 2, line_y),
                                (center_x + rect_width//2 - 2, line_y),
                                1
                            )
                    else:
                        # Draw regular circle for other resources
                        pygame.draw.circle(
                            screen,
                            color,
                            (center_x, center_y),
                            circle_size
                        )
                    
                    # Add white outline for stone to make it more visible
                    if resource['type'] == 'stone':
                        pygame.draw.circle(
                            screen,
                            (255, 255, 255),  # White outline
                            (center_x, center_y),
                            circle_size,
                            2  # Line width
                        )
                    
                    # Try to render emoji
                    try:
                        # Get the appropriate emoji for this resource type
                        emoji = emoji_symbols.get(resource['type'], '?')
                        
                        # Render the emoji
                        emoji_surface = self.emoji_font.render(emoji, True, (0, 0, 0))
                        
                        # Scale emoji based on resource amount - make wood and stone emojis larger
                        scale_factor = 0.5 + (size_factor * 0.5)  # Scale between 0.5 and 1.0
                        if resource['type'] in ['wood', 'stone']:
                            scale_factor *= 1.5  # Make wood and stone emojis 50% larger
                            
                        scaled_width = int(emoji_surface.get_width() * scale_factor)
                        scaled_height = int(emoji_surface.get_height() * scale_factor)
                        
                        # Only scale if dimensions are valid
                        if scaled_width > 0 and scaled_height > 0:
                            emoji_surface = pygame.transform.scale(emoji_surface, (scaled_width, scaled_height))
                        
                        # Draw the emoji centered on the resource
                        screen.blit(
                            emoji_surface,
                            (center_x - emoji_surface.get_width() // 2, 
                             center_y - emoji_surface.get_height() // 2)
                        )
                    except Exception as e:
                        # Fallback to text symbol if emoji rendering fails
                        fallback = fallback_symbols.get(resource['type'], '?')
                        text_surface = self.emoji_font.render(fallback, True, (0, 0, 0))
                        screen.blit(
                            text_surface,
                            (center_x - text_surface.get_width() // 2, 
                             center_y - text_surface.get_height() // 2)
                        )

class TestTeam:
    def __init__(self, leader_x, leader_y):
        self.leader_x = leader_x
        self.leader_y = leader_y
        self.members = []  # Would be animals in the real implementation
        self.inventory = {
            'food_plant': 0,
            'food_meat': 0,
            'wood': 0,
            'stone': 0,
            'water': 0,
            'medicinal': 0,
            'minerals': 0
        }
        self.structures = []
        self.strategy = 'balanced'
        self.color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255)
        )
        self.territory_radius = 200
        self.health = 100
        self.max_health = 100
        
        # Add some test members
        for _ in range(random.randint(3, 6)):
            angle = random.random() * 2 * math.pi
            distance = random.random() * 100
            self.members.append({
                'x': leader_x + math.cos(angle) * distance,
                'y': leader_y + math.sin(angle) * distance,
                'health': random.randint(50, 100),
                'max_health': 100,
                'type': random.choice(['herbivore', 'carnivore', 'omnivore'])
            })
    
    def gather_resources(self, resource_system, dt):
        """Gather resources from current positions"""
        # Check leader position
        grid_x = int(self.leader_x // TILE_SIZE)
        grid_y = int(self.leader_y // TILE_SIZE)
        pos = (grid_x, grid_y)
        
        if pos in resource_system.resources and resource_system.resources[pos]:
            for resource in resource_system.resources[pos]:
                if resource['amount'] > 0:
                    # Gather resource
                    gather_amount = min(5 * dt, resource['amount'])
                    resource['amount'] -= gather_amount
                    self.inventory[resource['type']] += gather_amount
        
        # Check member positions
        for member in self.members:
            grid_x = int(member['x'] // TILE_SIZE)
            grid_y = int(member['y'] // TILE_SIZE)
            pos = (grid_x, grid_y)
            
            if pos in resource_system.resources and resource_system.resources[pos]:
                for resource in resource_system.resources[pos]:
                    if resource['amount'] > 0:
                        # Check if member can gather this resource type
                        can_gather = False
                        if resource['type'] == 'food_plant' and member['type'] in ['herbivore', 'omnivore']:
                            can_gather = True
                        elif resource['type'] == 'food_meat' and member['type'] in ['carnivore', 'omnivore']:
                            can_gather = True
                        elif resource['type'] in ['wood', 'stone', 'water', 'medicinal', 'minerals']:
                            can_gather = True
                            
                        if can_gather:
                            gather_amount = min(3 * dt, resource['amount'])
                            resource['amount'] -= gather_amount
                            self.inventory[resource['type']] += gather_amount
    
    def update(self, dt, resource_system):
        """Update team behavior"""
        # Move members randomly for testing
        for member in self.members:
            angle = random.random() * 2 * math.pi
            distance = random.random() * 5 * dt
            member['x'] += math.cos(angle) * distance
            member['y'] += math.sin(angle) * distance
            
            # Keep members within territory
            dx = member['x'] - self.leader_x
            dy = member['y'] - self.leader_y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > self.territory_radius:
                # Move back toward leader
                member['x'] = self.leader_x + (dx/dist) * self.territory_radius * 0.9
                member['y'] = self.leader_y + (dy/dist) * self.territory_radius * 0.9
        
        # Gather resources
        self.gather_resources(resource_system, dt)
        
        # Use resources for healing
        self._heal_members(dt)
        
        # Try to build structures
        self._try_build_structures()
        
        # Update strategy
        self._update_strategy()
    
    def _heal_members(self, dt):
        """Use medicinal resources to heal members"""
        if self.inventory['medicinal'] > 0:
            # Find injured members
            injured = [m for m in self.members if m['health'] < m['max_health']]
            
            if injured:
                # Calculate healing amount
                heal_per_resource = 5
                max_heal = min(self.inventory['medicinal'], len(injured) * heal_per_resource * dt)
                heal_per_member = max_heal / len(injured)
                
                # Apply healing
                for member in injured:
                    heal_amount = min(heal_per_member, member['max_health'] - member['health'])
                    member['health'] += heal_amount
                    self.inventory['medicinal'] -= heal_amount / heal_per_resource
    
    def _try_build_structures(self):
        """Try to build structures if we have resources"""
        # Structure requirements
        required_resources = {
            'shelter': {'wood': 50, 'stone': 20},
            'watchtower': {'wood': 30},
            'storage': {'wood': 40, 'stone': 10},
            'wall': {'stone': 60}
        }
        
        # Check if we need a shelter
        if not any(s['type'] == 'shelter' for s in self.structures):
            if (self.inventory['wood'] >= required_resources['shelter']['wood'] and 
                self.inventory['stone'] >= required_resources['shelter']['stone']):
                
                # Build shelter
                self.inventory['wood'] -= required_resources['shelter']['wood']
                self.inventory['stone'] -= required_resources['shelter']['stone']
                
                # Add structure near leader
                offset_x = random.randint(-50, 50)
                offset_y = random.randint(-50, 50)
                self.structures.append({
                    'type': 'shelter',
                    'x': self.leader_x + offset_x,
                    'y': self.leader_y + offset_y,
                    'health': 100,
                    'built_time': time.time()
                })
                print(f"Team built a shelter at ({self.leader_x + offset_x}, {self.leader_y + offset_y})")
        
        # Check if we need a watchtower
        elif not any(s['type'] == 'watchtower' for s in self.structures):
            if self.inventory['wood'] >= required_resources['watchtower']['wood']:
                # Build watchtower
                self.inventory['wood'] -= required_resources['watchtower']['wood']
                
                # Add structure near leader
                angle = random.random() * 2 * math.pi
                distance = random.randint(60, 100)
                x = self.leader_x + math.cos(angle) * distance
                y = self.leader_y + math.sin(angle) * distance
                
                self.structures.append({
                    'type': 'watchtower',
                    'x': x,
                    'y': y,
                    'health': 100,
                    'built_time': time.time()
                })
                print(f"Team built a watchtower at ({x}, {y})")
    
    def _update_strategy(self):
        """Update team strategy based on current state"""
        # Assess team state
        team_health = sum(m['health'] for m in self.members) / (len(self.members) * 100)
        has_shelter = any(s['type'] == 'shelter' for s in self.structures)
        
        # Resource assessment
        food_level = (self.inventory['food_plant'] + self.inventory['food_meat']) / (len(self.members) * 50)
        building_level = (self.inventory['wood'] + self.inventory['stone']) / (len(self.members) * 100)
        
        # Decision making
        if team_health < 0.5:
            self.strategy = 'survival'
        elif not has_shelter and building_level > 0.6:
            self.strategy = 'establish_base'
        elif has_shelter and food_level < 0.3:
            self.strategy = 'gather_food'
        elif has_shelter and team_health > 0.8 and building_level > 0.7:
            self.strategy = 'expand'
        else:
            self.strategy = 'balanced'
    
    def draw(self, screen, camera_x, camera_y):
        """Draw team on screen"""
        # Initialize font for rendering emojis if not already done
        if not hasattr(self, 'emoji_font'):
            try:
                # Try to use a font that supports emojis
                self.emoji_font = pygame.font.SysFont('Segoe UI Emoji', 24)  # Windows emoji font
            except:
                # Fallback to default font
                self.emoji_font = pygame.font.SysFont('Arial', 24)
        
        # Define building emojis
        building_emojis = {
            'shelter': '🏠',      # House
            'watchtower': '🗼',   # Tower
            'storage': '🏪',      # Store
            'wall': '🧱'          # Brick Wall
        }
        
        # Draw territory circle
        pygame.draw.circle(
            screen,
            (*self.color, 30),  # Semi-transparent
            (self.leader_x - camera_x, self.leader_y - camera_y),
            self.territory_radius,
            1  # Just the outline
        )
        
        # Draw leader
        pygame.draw.circle(
            screen,
            self.color,
            (self.leader_x - camera_x, self.leader_y - camera_y),
            10
        )
        
        # Draw members
        for member in self.members:
            pygame.draw.circle(
                screen,
                self.color,
                (member['x'] - camera_x, member['y'] - camera_y),
                6
            )
        
        # Draw structures with emojis
        for structure in self.structures:
            x = structure['x'] - camera_x
            y = structure['y'] - camera_y
            
            # Draw colored background circle for the building
            pygame.draw.circle(
                screen,
                self.color,  # Use team color
                (x, y),
                15  # Size of background
            )
            
            # Draw building emoji
            emoji = building_emojis.get(structure['type'], '?')
            try:
                emoji_surface = self.emoji_font.render(emoji, True, (0, 0, 0))
                screen.blit(
                    emoji_surface,
                    (x - emoji_surface.get_width() // 2, 
                     y - emoji_surface.get_height() // 2)
                )
            except Exception as e:
                # Fallback to text if emoji rendering fails
                fallback = structure['type'][0].upper()  # First letter
                text_surface = self.emoji_font.render(fallback, True, (0, 0, 0))
                screen.blit(
                    text_surface,
                    (x - text_surface.get_width() // 2, 
                     y - text_surface.get_height() // 2)
                )

def generate_test_world():
    """Generate a simple test world grid"""
    terrain_types = ['grassland', 'forest', 'mountain', 'desert', 'aquatic', 'wetland']
    world_grid = []
    
    for y in range(WORLD_HEIGHT):
        row = []
        for x in range(WORLD_WIDTH):
            # Create some coherent terrain patterns
            if 5 <= y <= 10 and 10 <= x <= 30:
                terrain = 'forest'
            elif 15 <= y <= 20 and 5 <= x <= 15:
                terrain = 'mountain'
            elif 22 <= y <= 28 and 20 <= x <= 40:
                terrain = 'wetland'
            elif y < 3 or y > WORLD_HEIGHT - 3 or x < 3 or x > WORLD_WIDTH - 3:
                terrain = 'desert'
            else:
                terrain = random.choice(['grassland', 'grassland', 'grassland', 'forest', 'mountain', 'desert', 'wetland'])
            row.append(terrain)
        world_grid.append(row)
    
    return world_grid

def main():
    """Main test function"""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Resource System Test")
    clock = pygame.time.Clock()
    
    # Generate test world
    world_grid = generate_test_world()
    
    # Create resource system
    resource_system = TestResourceSystem(world_grid)
    
    # Create test teams
    teams = []
    for _ in range(5):
        x = random.randint(100, WORLD_WIDTH * TILE_SIZE - 100)
        y = random.randint(100, WORLD_HEIGHT * TILE_SIZE - 100)
        teams.append(TestTeam(x, y))
    
    # Camera position
    camera_x = 0
    camera_y = 0
    camera_speed = 300
    
    # UI font
    font = pygame.font.SysFont('Arial', 16)
    
    # Main loop
    running = True
    selected_team = None
    
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.1)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if clicked on a team
                mouse_x, mouse_y = pygame.mouse.get_pos()
                world_x = mouse_x + camera_x
                world_y = mouse_y + camera_y
                
                for team in teams:
                    dx = team.leader_x - world_x
                    dy = team.leader_y - world_y
                    if math.sqrt(dx*dx + dy*dy) < 20:
                        selected_team = team
                        break
        
        # Handle camera movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            camera_x -= camera_speed * dt
        if keys[pygame.K_RIGHT]:
            camera_x += camera_speed * dt
        if keys[pygame.K_UP]:
            camera_y -= camera_speed * dt
        if keys[pygame.K_DOWN]:
            camera_y += camera_speed * dt
        
        # Update systems
        resource_system.update(dt)
        for team in teams:
            team.update(dt, resource_system)
        
        # Draw world
        screen.fill((0, 0, 0))
        
        # Draw terrain
        for y, row in enumerate(world_grid):
            for x, terrain in enumerate(row):
                screen_x = x * TILE_SIZE - camera_x
                screen_y = y * TILE_SIZE - camera_y
                
                # Skip if off screen
                if (screen_x < -TILE_SIZE or screen_x > screen.get_width() or
                    screen_y < -TILE_SIZE or screen_y > screen.get_height()):
                    continue
                
                # Draw terrain
                color = {
                    'grassland': (100, 200, 100),
                    'forest': (0, 100, 0),
                    'mountain': (100, 100, 100),
                    'desert': (200, 200, 100),
                    'aquatic': (0, 0, 150),
                    'wetland': (100, 150, 200)
                }.get(terrain, (100, 100, 100))
                
                pygame.draw.rect(screen, color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
        
        # Draw resources
        resource_system.draw(screen, camera_x, camera_y)
        
        # Draw teams
        for team in teams:
            team.draw(screen, camera_x, camera_y)
        
        # Draw UI for selected team
        if selected_team:
            # Draw inventory panel
            panel_width = 200
            panel_height = 300
            panel_x = screen.get_width() - panel_width - 10
            panel_y = 10
            
            # Draw panel background
            pygame.draw.rect(screen, (50, 50, 50, 200), (panel_x, panel_y, panel_width, panel_height))
            
            # Draw inventory
            y_offset = panel_y + 10
            pygame.draw.rect(screen, selected_team.color, (panel_x + 5, y_offset, 20, 20))
            text = font.render(f"Team Strategy: {selected_team.strategy}", True, (255, 255, 255))
            screen.blit(text, (panel_x + 30, y_offset))
            y_offset += 30
            
            # Draw resources
            for resource, amount in selected_team.inventory.items():
                text = font.render(f"{resource}: {amount:.1f}", True, (255, 255, 255))
                screen.blit(text, (panel_x + 10, y_offset))
                y_offset += 20
            
            # Draw structures
            y_offset += 10
            text = font.render(f"Structures: {len(selected_team.structures)}", True, (255, 255, 255))
            screen.blit(text, (panel_x + 10, y_offset))
            y_offset += 20
            
            for structure in selected_team.structures:
                text = font.render(f"- {structure['type']}", True, (255, 255, 255))
                screen.blit(text, (panel_x + 20, y_offset))
                y_offset += 20
        
        # Update display
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main() 