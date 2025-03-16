import pygame
import random
import math
import time
from typing import Dict, List, Tuple, Any, Optional

class ResourceSystem:
    def __init__(self, world_grid):
        """Initialize the resource system with the world grid."""
        self.world_grid = world_grid
        self.resources = {}  # Map of position to resource
        self.resource_types = {
            'food_plant': {'terrain': ['grassland', 'forest'], 'regrowth_rate': 0.02, 'color': (0, 255, 0)},
            'food_meat': {'terrain': ['grassland'], 'regrowth_rate': 0.01, 'color': (255, 0, 0)},
            'wood': {'terrain': ['forest'], 'regrowth_rate': 0.015, 'color': (139, 69, 19)},
            'stone': {'terrain': ['mountain'], 'regrowth_rate': 0.008, 'color': (128, 128, 128)},
            'water': {'terrain': ['aquatic', 'wetland'], 'regrowth_rate': 0.03, 'color': (0, 0, 255)},
            'medicinal': {'terrain': ['forest', 'wetland'], 'regrowth_rate': 0.01, 'color': (255, 0, 255)},
            'minerals': {'terrain': ['mountain'], 'regrowth_rate': 0.005, 'color': (255, 215, 0)}
        }
        
        # Initialize emoji font for rendering
        self.emoji_font = None
        self.emoji_symbols = {
            'food_plant': '🍎',  # Apple
            'food_meat': '🍖',   # Meat
            'wood': '🌲',        # Tree
            'stone': '🗿',       # Moai statue
            'water': '💧',       # Water Drop
            'medicinal': '💊',   # Pill
            'minerals': '💎'     # Gem
        }
        
        # Fallback symbols in case emojis don't render properly
        self.fallback_symbols = {
            'food_plant': 'F',
            'food_meat': 'M',
            'wood': 'W',
            'stone': 'S',
            'water': 'H',
            'medicinal': '+',
            'minerals': '$'
        }
        
        # Initialize resources
        self._initialize_resources()
        
    def _initialize_resources(self):
        """Generate initial resources based on terrain with even distribution across the map."""
        # Set a maximum limit for resources
        MAX_RESOURCES = 1200  # Increased from 800 to provide more resources
        
        # Divide the map into regions for more even distribution
        world_height = len(self.world_grid)
        world_width = len(self.world_grid[0])
        
        # Create regions (divide map into a 4x4 grid)
        num_regions_x = 4
        num_regions_y = 4
        region_width = world_width // num_regions_x
        region_height = world_height // num_regions_y
        
        # Calculate resources per region
        resources_per_region = MAX_RESOURCES // (num_regions_x * num_regions_y)
        
        # Initialize resources by region
        for region_y in range(num_regions_y):
            for region_x in range(num_regions_x):
                # Calculate region boundaries
                start_x = region_x * region_width
                end_x = start_x + region_width
                start_y = region_y * region_height
                end_y = start_y + region_height
                
                # Count resources in this region
                region_resource_count = 0
                
                # Create a list of all valid positions in this region
                valid_positions = []
                for y in range(start_y, end_y):
                    if y >= world_height:
                        continue
                    for x in range(start_x, end_x):
                        if x >= world_width:
                            continue
                        terrain = self.world_grid[y][x].lower()
                        # Check which resource types can spawn here
                        possible_resources = [r for r, data in self.resource_types.items() 
                                            if terrain in data['terrain']]
                        if possible_resources:
                            valid_positions.append((x, y, possible_resources))
                
                # Shuffle positions for randomness
                random.shuffle(valid_positions)
                
                # Add resources to valid positions until we reach the target for this region
                for x, y, possible_resources in valid_positions:
                    if region_resource_count >= resources_per_region:
                        break
                        
                    # Increased probability to 40% to ensure more resources
                    if random.random() < 0.4:
                        resource_type = random.choice(possible_resources)
                        pos = (x, y)
                        if pos not in self.resources:
                            self.resources[pos] = []
                        self.resources[pos].append({
                            'type': resource_type,
                            'amount': random.randint(30, 100),  # Increased minimum amount
                            'max_amount': 100,
                            'last_update': time.time()
                        })
                        region_resource_count += 1
    
    def update(self, dt: float):
        """Update resources (regrowth) with optimized performance."""
        current_time = time.time()
        
        # Only update resources every 0.5 seconds instead of every frame
        if not hasattr(self, 'last_update_time'):
            self.last_update_time = current_time
        
        # Skip updates if not enough time has passed (reduces CPU usage)
        if current_time - self.last_update_time < 0.5:
            return
        
        # Calculate time difference since last update
        time_diff = current_time - self.last_update_time
        self.last_update_time = current_time
        
        # Process regrowth for existing resources
        for pos, resources in list(self.resources.items()):
            for resource in resources:
                if resource['amount'] < resource['max_amount']:
                    regrowth_rate = self.resource_types[resource['type']]['regrowth_rate']
                    resource['amount'] += regrowth_rate * time_diff * 15  # Increased scaling factor
                    resource['amount'] = min(resource['amount'], resource['max_amount'])
                resource['last_update'] = current_time
        
        # Count current resources
        current_resource_count = sum(len(resources) for resources in self.resources.values())
        MAX_RESOURCES = 1200  # Same as in _initialize_resources
        
        # Increased chance of new resources spawning
        if current_resource_count < MAX_RESOURCES and random.random() < 0.003 * dt:
            # Find a random region to add resources to
            world_height = len(self.world_grid)
            world_width = len(self.world_grid[0])
            
            # Pick a random area of the map
            region_x = random.randint(0, 3)  # 4 regions horizontally
            region_y = random.randint(0, 3)  # 4 regions vertically
            
            region_width = world_width // 4
            region_height = world_height // 4
            
            # Calculate region boundaries
            start_x = region_x * region_width
            end_x = min(start_x + region_width, world_width)
            start_y = region_y * region_height
            end_y = min(start_y + region_height, world_height)
            
            # Try to add a resource in this region
            for _ in range(10):  # Increased attempts from 5 to 10
                x = random.randint(start_x, end_x - 1)
                y = random.randint(start_y, end_y - 1)
                terrain = self.world_grid[y][x].lower()
                
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
                            'amount': random.randint(30, 80),  # Increased minimum amount
                            'max_amount': 100,
                            'last_update': current_time
                        })
                        break  # Successfully added a resource, exit loop
    
    def draw(self, screen, camera_x, camera_y, tile_size):
        """Draw resources on screen with highly optimized rendering."""
        # Initialize font for rendering emojis if not already done
        if not self.emoji_font:
            try:
                # Try to use a font that supports emojis
                self.emoji_font = pygame.font.SysFont('Segoe UI Emoji', 24)  # Windows emoji font
            except:
                # Fallback to default font
                self.emoji_font = pygame.font.SysFont('Arial', 24)
        
        # Pre-render emojis if not already done
        if not hasattr(self, 'emoji_surfaces'):
            self.emoji_surfaces = {}
            for resource_type, emoji in self.emoji_symbols.items():
                try:
                    self.emoji_surfaces[resource_type] = self.emoji_font.render(emoji, True, (0, 0, 0))
                except:
                    # Fallback to text if emoji rendering fails
                    fallback = self.fallback_symbols.get(resource_type, '?')
                    self.emoji_surfaces[resource_type] = self.emoji_font.render(fallback, True, (0, 0, 0))
        
        # Calculate visible area in grid coordinates
        visible_min_x = max(0, int(camera_x // tile_size) - 1)
        visible_max_x = min(len(self.world_grid[0]), int((camera_x + screen.get_width()) // tile_size) + 1)
        visible_min_y = max(0, int(camera_y // tile_size) - 1)
        visible_max_y = min(len(self.world_grid), int((camera_y + screen.get_height()) // tile_size) + 1)
        
        # Create batches for each resource type to reduce draw calls
        resource_batches = {}
        
        # Only process resources in the visible area
        visible_count = 0
        max_visible = 100  # Limit the number of resources drawn to improve performance
        
        # First pass: collect all visible resources
        visible_resources = []
        
        for pos, resources in self.resources.items():
            x, y = pos
            
            # Skip if outside visible area
            if not (visible_min_x <= x <= visible_max_x and visible_min_y <= y <= visible_max_y):
                continue
            
            screen_x = x * tile_size - camera_x
            screen_y = y * tile_size - camera_y
            
            # Center of the tile
            center_x = screen_x + tile_size // 2
            center_y = screen_y + tile_size // 2
            
            for resource in resources:
                if resource['amount'] > 10:  # Only draw if significant amount (increased threshold)
                    visible_resources.append((resource, center_x, center_y))
        
        # Sort resources by amount (largest first) and limit the number drawn
        visible_resources.sort(key=lambda r: r[0]['amount'], reverse=True)
        visible_resources = visible_resources[:max_visible]
        
        # Second pass: draw the limited set of resources
        for resource, center_x, center_y in visible_resources:
            # Simplified size calculation
            size_factor = min(1.0, resource['amount'] / resource['max_amount'])
            base_size = 4 + int(6 * size_factor)  # Further reduced size
            color = self.resource_types[resource['type']]['color']
            
            # Simplified drawing - just a circle for all resources
            pygame.draw.circle(
                screen,
                color,
                (center_x, center_y),
                base_size
            )
            
            # Draw the emoji or symbol
            resource_type = resource['type']
            if resource_type in self.emoji_surfaces:
                emoji_surf = self.emoji_surfaces[resource_type]
                # No scaling, just center the emoji
                screen.blit(
                    emoji_surf,
                    (center_x - emoji_surf.get_width() // 2, 
                     center_y - emoji_surf.get_height() // 2)
                )
    
    def get_resources_at(self, grid_x: int, grid_y: int) -> List[Dict]:
        """Get resources at a specific grid position."""
        pos = (grid_x, grid_y)
        if pos in self.resources:
            return self.resources[pos]
        return []
    
    def gather_resource(self, grid_x: int, grid_y: int, resource_type: str, amount: float) -> float:
        """Gather a specific amount of a resource at a position.
        Returns the actual amount gathered."""
        pos = (grid_x, grid_y)
        if pos not in self.resources:
            return 0.0
            
        for resource in self.resources[pos]:
            if resource['type'] == resource_type and resource['amount'] > 0:
                gathered = min(amount, resource['amount'])
                resource['amount'] -= gathered
                
                # Remove resource if depleted
                if resource['amount'] <= 0:
                    self.resources[pos].remove(resource)
                    
                # Remove position if no resources left
                if not self.resources[pos]:
                    del self.resources[pos]
                    
                return gathered
                
        return 0.0
    
    def find_nearest_resource(self, x: float, y: float, resource_type: Optional[str] = None, 
                             max_distance: float = 500.0) -> Tuple[Optional[Tuple[int, int]], float]:
        """Find the nearest resource of a specific type (or any type if None).
        Returns (position, distance) or (None, float('inf')) if not found."""
        grid_x, grid_y = int(x // 32), int(y // 32)  # Assuming TILE_SIZE = 32
        min_distance = float('inf')
        nearest_pos = None
        
        for pos, resources in self.resources.items():
            if resource_type is None or any(r['type'] == resource_type and r['amount'] > 0 for r in resources):
                pos_x, pos_y = pos
                dx = (pos_x - grid_x) * 32
                dy = (pos_y - grid_y) * 32
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < min_distance and distance <= max_distance:
                    min_distance = distance
                    nearest_pos = pos
                    
        return nearest_pos, min_distance 