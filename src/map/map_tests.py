import os
import sys
import pygame
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.map.map_generator import (
    generate_world_grid,
    load_raster_data,
    resample_raster,
    normalize_raster_data,
    visualize_raster,
    TILE_SIZE,
    tile_mapping,
    WORLD_HEIGHT,
    WORLD_WIDTH
)

class Camera:
    """A simple camera to move around the map."""
    def __init__(self, width, height):
        self.offset_x = 0
        self.offset_y = 0
        self.width = width
        self.height = height

    def move(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        self.offset_x = max(0, min(self.offset_x, WORLD_WIDTH * TILE_SIZE - self.width))
        self.offset_y = max(0, min(self.offset_y, WORLD_HEIGHT * TILE_SIZE - self.height))


def test_map_visualization(debug: bool = False):
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Map Test")

    datasets = [
        "data/Natural_Earth/NE1_HR_LC/NE1_HR_LC.tif",
        "data/Natural_Earth/GRAY_HR_SR/GRAY_HR_SR.tif",
    ]

    rasters = []
    for dataset in datasets:
        raster, transform = load_raster_data(dataset)
        if debug:
            visualize_raster(raster, title=f"Dataset: {os.path.basename(dataset)}")
        rasters.append((raster, transform))

    # Resample and normalize combined raster data
    combined_data = np.zeros((WORLD_HEIGHT, WORLD_WIDTH), dtype=float)
    for raster, _ in rasters:
        resampled, _ = resample_raster(dataset, WORLD_HEIGHT, WORLD_WIDTH, debug=debug)
        normalized = normalize_raster_data(resampled, debug=debug)
        combined_data += normalized
    combined_data /= len(rasters)  # Average

    # Generate the world grid
    world_grid, normalized_data = generate_world_grid(
        raster_data=combined_data,
        transform=None,
        land_mask=np.ones_like(combined_data),
        color_classification=False,
        debug=debug
    )

    # Print terrain distribution only in debug mode
    if debug:
        terrain_count = Counter([tile for row in world_grid for tile in row])
        print("Terrain Distribution:", terrain_count)

    # Initialize camera
    camera = Camera(screen.get_width(), screen.get_height())

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            camera.move(0, -TILE_SIZE)
        if keys[pygame.K_DOWN]:
            camera.move(0, TILE_SIZE)
        if keys[pygame.K_LEFT]:
            camera.move(-TILE_SIZE, 0)
        if keys[pygame.K_RIGHT]:
            camera.move(TILE_SIZE, 0)

        screen.fill((0, 0, 0))

        for y, row in enumerate(world_grid):
            for x, tile in enumerate(row):
                screen_x = x * TILE_SIZE - camera.offset_x
                screen_y = y * TILE_SIZE - camera.offset_y
                if 0 <= screen_x < screen.get_width() and 0 <= screen_y < screen.get_height():
                    color = tile_mapping[tile]
                    pygame.draw.rect(screen, color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    test_map_visualization()
