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

# Constants
TILE_SIZE = 8
WORLD_HEIGHT = 800
WORLD_WIDTH = 1200

# Simple tile colors
tile_mapping = {
    "mountain": (139, 69, 19),    # Darker brown
    "forest": (34, 139, 34),      # Darker green
    "grassland": (76, 187, 23),   # Adjusted green
    "aquatic": (0, 105, 148),     # Deeper blue (for ocean)
    "desert": (238, 214, 175),    # Softer sand color
    "polar": (220, 220, 220),     # Lighter gray
    "wetland": (107, 142, 35)     # Not used in example
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
                    target_width: int) -> Tuple[np.ndarray, rasterio.Affine]:
    """
    Resample the raster to (target_height, target_width) using bilinear resampling.
    Returns (data, new_transform).
    """
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

    return data, new_transform

def load_land_shapefile(shapefile_path: str) -> gpd.GeoDataFrame:
    """
    Load the Natural Earth 10m land polygon shapefile (EPSG:4326).
    Return empty if not found.
    """
    if not os.path.exists(shapefile_path):
        print(f"Warning: Shapefile not found at {shapefile_path}")
        return gpd.GeoDataFrame()
    gdf = gpd.read_file(shapefile_path)
    if gdf.crs is None:
        print("Warning: shapefile has no CRS. Assuming EPSG:4326.")
        gdf = gdf.set_crs(epsg=4326)
    return gdf

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
                          max_value: float = None) -> np.ndarray:
    """
    Optional: apply min-max stretching to the raster_data.
    """
    if min_value is None:
        min_value = np.nanmin(raster_data)
    if max_value is None:
        max_value = np.nanmax(raster_data)
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

def generate_world_grid(
    raster_data: np.ndarray,
    transform: rasterio.Affine,
    land_mask: np.ndarray,
    color_classification: bool = False
) -> Tuple[List[List[str]], np.ndarray]:
    """
    Create a 2D list of terrain from the 40x60 raster.
    land_mask: 1=land, 0=water (also 40x60).
    """
    data = np.array(raster_data).copy()  # shape => (40,60) or (3,40,60)

    # Determine array shape
    if data.ndim == 3 and color_classification:
        height, width = data.shape[1], data.shape[2]
    else:
        height, width = data.shape

    if (height, width) != (WORLD_HEIGHT, WORLD_WIDTH):
        raise ValueError(f"raster_data shape {data.shape} != (40,60). Did you resample?")

    world_grid = []

    # Single-band
    # SINGLE-BAND CASE
    if data.ndim == 2 and not color_classification:
        # <-- FIX: cast data to float
        data = data.astype(np.float32, copy=False)

        # Add random noise in float
        noise = np.random.uniform(0, 0.2, data.shape).astype(np.float32)
        data += noise

        # Normalize to 0-1
        data = (data - np.min(data)) / (np.ptp(data))

        thresholds = [0.2, 0.4, 0.6, 0.8]
        for y in range(WORLD_HEIGHT):
            row = []
            for x in range(WORLD_WIDTH):
                # If land_mask[y,x] = 0 => “aquatic”
                if land_mask[y, x] == 0:
                    row.append("aquatic")
                    continue

                val = data[y, x]
                offset = random.uniform(-0.05, 0.05)
                if val <= thresholds[0] + offset:
                    row.append("aquatic")
                elif val <= thresholds[1] + offset:
                    row.append("grassland")
                elif val <= thresholds[2] + offset:
                    row.append("forest")
                elif val <= thresholds[3] + offset:
                    row.append("mountain")
                else:
                    row.append("desert")
            world_grid.append(row)


    # 3-band color classification
    elif data.ndim == 3 and color_classification:
        R, G, B = data[0], data[1], data[2]
        for y in range(WORLD_HEIGHT):
            row = []
            for x in range(WORLD_WIDTH):
                if land_mask[y, x] == 0:
                    row.append("aquatic")
                    continue
                r_val, g_val, b_val = R[y, x], G[y, x], B[y, x]
                ctype = classify_color_based(r_val, g_val, b_val)
                row.append(ctype)
            world_grid.append(row)

    else:
        raise ValueError("Mismatch: single-band => color_classification=False, or 3-band => True")

    # Debug
    print(f"Generated world grid with dimensions: {WORLD_HEIGHT}x{WORLD_WIDTH}")
    terrain_counts = {}
    for row in world_grid:
        for tile in row:
            terrain_counts[tile] = terrain_counts.get(tile, 0) + 1
    print("Terrain distribution:", terrain_counts)

    return world_grid, data

def get_spawn_points_by_terrain(world_grid: List[List[str]]) -> Dict[str, List[Tuple[int, int]]]:
    """Generate dictionary of spawn points for each terrain type."""
    spawn_points = {
        "mountain": [],
        "forest": [],
        "grassland": [],
        "aquatic": [],
        "desert": [],
        "wetland": []
    }
    
    for y in range(len(world_grid)):
        for x in range(len(world_grid[0])):
            terrain = world_grid[y][x]
            if terrain in spawn_points:
                spawn_points[terrain].append((x, y))
    
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
