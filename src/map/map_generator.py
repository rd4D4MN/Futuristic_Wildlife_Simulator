import os
import random
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from shapely.geometry import shape
import geopandas as gpd
import shapely.geometry as geom
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Optional, List
import pygame

# Constants
TILE_SIZE = 32
WORLD_HEIGHT = 400
WORLD_WIDTH = 600

# Simple tile colors
tile_mapping = {
    "mountain": (139, 69, 19),    # Darker brown
    "forest": (34, 139, 34),      # Darker green
    "grassland": (76, 187, 23),   # Adjusted green
    "aquatic": (0, 105, 148),     # Deeper blue (for ocean)
    "desert": (238, 214, 175),    # Softer sand color
    "polar": (220, 220, 220),     # Lighter gray
    "wetland": (107, 142, 35),    # Not used in example
    "forest_edge": (60, 160, 60),    # Lighter green
    "savanna": (180, 180, 100),      # Light yellow-green
    "hills": (120, 100, 80),         # Light brown
    "wooded_hills": (80, 120, 60),   # Dark green-brown
    "beach": (240, 230, 140)         # Light sand
}

def load_raster_data(file_path: str) -> Tuple[np.ndarray, rasterio.Affine]:
    """
    Load a single-band raster at its original resolution.
    Returns (raster_data, transform).
    """
    with rasterio.open(file_path) as src:
        raster_data = src.read(1)
        transform = src.transform
    return raster_data, transform

def resample_raster(file_path: str,
                    target_height: int,
                    target_width: int,
                    debug: bool = False) -> Tuple[np.ndarray, rasterio.Affine]:
    """
    Resample the raster to (target_height, target_width) using bilinear resampling.
    Returns (data, new_transform).
    """
    try:
        with rasterio.open(file_path) as src:
            data = src.read(
                1,
                out_shape=(target_height, target_width),
                resampling=Resampling.bilinear
            )
            # Scale transform for the smaller shape
            scale_x = src.width / float(target_width)
            scale_y = src.height / float(target_height)
            new_transform = src.transform * rasterio.Affine.scale(scale_x, scale_y)

            # Normalize data silently
            min_value = np.min(data)
            max_value = np.max(data)
            if min_value != max_value:
                data = (data - min_value) / (max_value - min_value)

            return data, new_transform
    except Exception as e:
        if debug:
            print(f"Error resampling raster: {e}")
        return None, None

def load_land_shapefile(shapefile_path: str) -> gpd.GeoDataFrame:
    """
    Load the Natural Earth 10m land polygon shapefile (EPSG:4326).
    Return empty if not found.
    """
    try:
        land_gdf = gpd.read_file(shapefile_path)
        if not land_gdf.crs:
            land_gdf.set_crs(epsg=4326, inplace=True)
        return land_gdf
    except Exception as e:
        print(f"Error loading shapefile: {e}")
        return None

def rasterize_land(land_gdf: gpd.GeoDataFrame,
                   out_shape: tuple,
                   transform: rasterio.Affine) -> np.ndarray:
    """
    Create a (WORLD_HEIGHT x WORLD_WIDTH) land mask array using rasterize.
    1 = land, 0 = water.
    """
    if land_gdf.empty:
        # No shapefile => all water
        return np.zeros(out_shape, dtype=np.uint8)

    # Convert each polygon to (geometry, value=1)
    shapes = ((geom, 1) for geom in land_gdf.geometry)
    land_mask = rasterize(
        shapes=shapes,
        out_shape=out_shape,
        fill=0,
        transform=transform,
        all_touched=True,
        dtype=np.uint8
    )
    return land_mask

def normalize_raster_data(raster_data: np.ndarray,
                          min_value: float = None,
                          max_value: float = None,
                          debug: bool = False) -> np.ndarray:
    """
    Optional: apply min-max stretching to the raster_data.
    """
    if min_value is None:
        min_value = np.nanmin(raster_data)
    if max_value is None:
        max_value = np.nanmax(raster_data)
    if debug:
        print(f"Normalizing raster: Min={min_value}, Max={max_value}")
    clipped = np.clip(raster_data, min_value, max_value)
    return (clipped - min_value) / (max_value - min_value)

def classify_color_based(r, g, b) -> str:
    """
    Very rough color classification for 3-band data.
    """
    if g > r and g > b:
        return "forest"
    elif r > g and r > b:
        return "desert"
    else:
        return "grassland"

def get_terrain_type(raster_value: float, land_mask_value: int) -> str:
    """Determine terrain type based on raster and land mask values."""
    if land_mask_value == 0:
        return "aquatic"
        
    # Add random offset for variety
    offset = random.uniform(-0.05, 0.05)
    val = raster_value + offset
    
    # Terrain thresholds
    thresholds = [0.2, 0.4, 0.6, 0.8]
    
    if val <= thresholds[0]:
        return "aquatic"
    elif val <= thresholds[1]:
        return "grassland"
    elif val <= thresholds[2]:
        return "forest"
    elif val <= thresholds[3]:
        return "mountain"
    else:
        return "desert"

def generate_world_grid(
    raster_data: np.ndarray,
    transform: rasterio.Affine,
    land_mask: np.ndarray,
    color_classification: bool = False,
    debug: bool = False
) -> Tuple[List[List[str]], np.ndarray]:
    """
    Create a 2D list of terrain from the raster.
    land_mask: 1=land, 0=water.
    """
    data = np.array(raster_data).copy()  # shape => (40,60) or (3,40,60)

    # Determine array shape
    if data.ndim == 3 and color_classification:
        height, width = data.shape[1], data.shape[2]
    else:
        height, width = data.shape

    if (height, width) != (WORLD_HEIGHT, WORLD_WIDTH):
        raise ValueError(f"raster_data shape {data.shape} != ({WORLD_HEIGHT},{WORLD_WIDTH}). Did you resample?")

    world_grid = [[None for _ in range(WORLD_WIDTH)] for _ in range(WORLD_HEIGHT)]
    terrain_counts = {'aquatic': 0, 'mountain': 0, 'desert': 0, 'forest': 0, 'grassland': 0}
    
    # First pass: determine base terrain types
    for y in range(WORLD_HEIGHT):
        for x in range(WORLD_WIDTH):
            # Get terrain type based on raster data and land mask
            terrain = get_terrain_type(data[y, x], land_mask[y, x])
            world_grid[y][x] = terrain
            terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
    
    # Second pass: add terrain transitions
    smoothed_grid = apply_terrain_transitions(world_grid)
    
    # Only print terrain distribution in debug mode
    if debug:
        print("Terrain distribution:", terrain_counts)
    
    return smoothed_grid, data

def apply_terrain_transitions(world_grid: List[List[str]]) -> List[List[str]]:
    """Apply terrain transitions to make the world look more natural."""
    height = len(world_grid)
    width = len(world_grid[0])
    
    # Create a copy of the grid to store the result
    result_grid = [row[:] for row in world_grid]
    
    # Define transition terrain types
    transition_terrains = {
        ('grassland', 'forest'): 'forest_edge',
        ('forest', 'grassland'): 'forest_edge',
        ('grassland', 'desert'): 'savanna',
        ('desert', 'grassland'): 'savanna',
        ('mountain', 'grassland'): 'hills',
        ('grassland', 'mountain'): 'hills',
        ('mountain', 'forest'): 'wooded_hills',
        ('forest', 'mountain'): 'wooded_hills',
        ('aquatic', 'grassland'): 'wetland',
        ('grassland', 'aquatic'): 'wetland',
        ('aquatic', 'desert'): 'beach',
        ('desert', 'aquatic'): 'beach',
    }
    
    # Define terrain compatibility for transitions
    # Higher value means more likely to transition
    terrain_compatibility = {
        'grassland': {'forest': 0.7, 'desert': 0.5, 'mountain': 0.3, 'aquatic': 0.4},
        'forest': {'grassland': 0.7, 'mountain': 0.4, 'aquatic': 0.5, 'desert': 0.1},
        'desert': {'grassland': 0.5, 'mountain': 0.3, 'aquatic': 0.2, 'forest': 0.1},
        'mountain': {'grassland': 0.3, 'forest': 0.4, 'desert': 0.3, 'aquatic': 0.1},
        'aquatic': {'grassland': 0.4, 'forest': 0.5, 'desert': 0.2, 'mountain': 0.1}
    }
    
    # Apply transitions
    for y in range(height):
        for x in range(width):
            current_terrain = world_grid[y][x]
            
            # Check neighbors
            neighbors = []
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width:
                    neighbors.append(world_grid[ny][nx])
            
            # Count neighbor terrain types
            neighbor_counts = {}
            for neighbor in neighbors:
                neighbor_counts[neighbor] = neighbor_counts.get(neighbor, 0) + 1
            
            # Find most common different neighbor
            different_neighbors = [t for t in neighbor_counts if t != current_terrain]
            if different_neighbors:
                most_common = max(different_neighbors, key=lambda t: neighbor_counts[t])
                
                # Check if we should apply a transition
                if (most_common in terrain_compatibility.get(current_terrain, {}) and 
                    random.random() < terrain_compatibility[current_terrain][most_common] * 
                    (neighbor_counts[most_common] / len(neighbors))):
                    
                    # Apply transition terrain if defined
                    transition_key = (current_terrain, most_common)
                    if transition_key in transition_terrains:
                        result_grid[y][x] = transition_terrains[transition_key]
    
    return result_grid

def get_spawn_points_by_terrain(world_grid: List[List[str]]) -> Dict[str, List[Tuple[int, int]]]:
    """Generate dictionary of spawn points for each terrain type with improved clustering."""
    spawn_points = {
        "mountain": [],
        "forest": [],
        "grassland": [],
        "aquatic": [],
        "desert": [],
        "wetland": []
    }
    
    # Helper to check surrounding tiles
    def count_similar_neighbors(x: int, y: int, terrain: str) -> int:
        count = 0
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < len(world_grid[0]) and 
                0 <= ny < len(world_grid) and 
                world_grid[ny][nx] == terrain):
                count += 1
        return count
    
    # First pass: collect all potential spawn points
    potential_points = {terrain: [] for terrain in spawn_points}
    
    for y in range(len(world_grid)):
        for x in range(len(world_grid[0])):
            terrain = world_grid[y][x]
            if terrain in spawn_points:
                # Calculate cluster score based on similar neighbors
                cluster_score = count_similar_neighbors(x, y, terrain)
                potential_points[terrain].append((x, y, cluster_score))
    
    # Second pass: select best spawn points
    for terrain, points in potential_points.items():
        # Sort by cluster score (higher is better)
        points.sort(key=lambda p: p[2], reverse=True)
        
        # Take points with good clustering, remove the cluster score
        spawn_points[terrain] = [(x, y) for x, y, _ in points if _ >= 2]
        
        # If we don't have enough clustered points, add some random ones
        if len(spawn_points[terrain]) < 10:
            random_points = [(x, y) for x, y, _ in points if _ < 2]
            random.shuffle(random_points)
            spawn_points[terrain].extend(random_points[:10-len(spawn_points[terrain])])
    
    return spawn_points

def visualize_raster(data: np.ndarray, title="Raster Data"):
    """
    Quick visualization. If single-band => colormap, else => approximate RGB.
    """
    plt.figure(figsize=(6,4))
    if data.ndim == 2:
        plt.imshow(data, cmap="viridis")
        plt.colorbar()
    else:
        # shape: (3,40,60)
        rgb = np.transpose(data, (1, 2, 0))
        rgb = (rgb - np.min(rgb)) / np.ptp(rgb)
        plt.imshow(rgb)
    plt.title(title)
    plt.show()

# Add to existing file
class EnvironmentSystem:
    def __init__(self, world_grid):
        self.world_grid = world_grid
        self.time_of_day = 0  # 0-24 hours
        self.weather_conditions = "clear"
        self.season = "summer"

    def update(self, dt: float):
        # Update time of day
        self.time_of_day = (self.time_of_day + dt/60) % 24  # 1 real second = 1 game minute
        
        # Random weather changes
        if random.random() < 0.001:  # 0.1% chance per update
            self.weather_conditions = random.choice(["clear", "rain", "cloudy", "storm"])

    def get_environment_effects(self, x: int, y: int) -> Dict[str, float]:
        """Get environmental effects for a position."""
        terrain = self.world_grid[y][x]
        time_multiplier = 1.0 - (0.3 if 20 < self.time_of_day < 6 else 0)  # Night penalty
        weather_multiplier = {
            "clear": 1.0,
            "rain": 0.8,
            "cloudy": 0.9,
            "storm": 0.6
        }[self.weather_conditions]
        
        return {
            "visibility": time_multiplier * weather_multiplier,
            "movement_speed": weather_multiplier,
            "stamina_drain": 1.0 + (0.2 if self.weather_conditions == "storm" else 0)
        }
