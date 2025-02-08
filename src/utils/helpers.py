import pygame
import random
import math
from typing import List, Tuple, Dict, Any

def load_sprite(filepath: str, size: Tuple[int, int]) -> pygame.Surface:
    """Load and scale a sprite from file with fallback colored rectangle."""
    try:
        img = pygame.image.load(filepath).convert_alpha()
        return pygame.transform.scale(img, size)
    except (pygame.error, FileNotFoundError):
        surf = pygame.Surface(size)
        surf.fill((random.randint(0,255), random.randint(0,255), random.randint(0,255)))
        return surf

def calculate_distance(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    return math.sqrt(dx*dx + dy*dy)

def random_position(bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Generate random position within bounds (x_min, y_min, x_max, y_max)."""
    x_min, y_min, x_max, y_max = bounds
    return (random.randint(x_min, x_max), random.randint(y_min, y_max))

def generate_battle_story(winner: Any, loser: Any, 
                         initial_health: Dict[str, float]) -> str:
    """Generate battle outcome story."""
    story_parts = []
    story_parts.append(f"{winner.get_leader_name()} emerged victorious over {loser.get_leader_name()}.")
    
    casualties = [m for m in loser.members if m.health <= 0]
    if casualties:
        story_parts.append(f"Casualties: {', '.join(m.name for m in casualties)}")
    
    survivors = [m for m in loser.members if m.health > 0]
    if survivors:
        story_parts.append("Survivors retained their will to fight, though weakened.")
    
    return "\n".join(story_parts)

def generate_simulation_story(events: List[Tuple[int, str]]) -> str:
    """Generate overall simulation narrative."""
    if not events:
        return "The world remained peaceful. No battles took place."

    story = []
    story.append("In the grand simulation, numerous creatures wandered the landscape.")
    story.append("They formed teams around powerful robot leaders, vying for control.")
    
    for frame, info in events:
        story.append(f"At frame {frame}: {info}")
    
    story.append("Thus concluded another chapter in the eternal struggle for dominance.")
    return "\n".join(story)
