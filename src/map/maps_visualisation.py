import pygame
import numpy as np

TILE_SIZE = 32

def render_map(screen, terrain_grid, animal_positions, tile_mapping, animal_images):
    """Render the terrain grid and overlay animals."""
    for y, row in enumerate(terrain_grid):
        for x, tile in enumerate(row):
            color = tile_mapping[tile]
            pygame.draw.rect(screen, color, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            if (x, y) in animal_positions:
                animal_image = animal_images[animal_positions[(x, y)]]
                screen.blit(animal_image, (x * TILE_SIZE, y * TILE_SIZE))
