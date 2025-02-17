import pygame
import random
import math
from typing import Tuple, List, Dict

class CombatEffect:
    def __init__(self, x: float, y: float, effect_type: str, color: Tuple[int, int, int], duration: float = 1.0):
        self.x = x
        self.y = y
        self.effect_type = effect_type
        self.color = color
        self.duration = duration
        self.current_time = 0
        self.particles: List[Dict] = []
        self.finished = False
        
        # Initialize particles based on effect type
        if effect_type == 'slash':
            self._init_slash_effect()
        elif effect_type == 'bite':
            self._init_bite_effect()
        elif effect_type == 'charge':
            self._init_charge_effect()
        elif effect_type == 'special':
            self._init_special_effect()
    
    def _init_slash_effect(self):
        """Initialize slash attack particles."""
        num_particles = 15
        for _ in range(num_particles):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(100, 200)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'size': random.uniform(2, 4),
                'alpha': 255
            })

    def _init_bite_effect(self):
        """Initialize bite attack particles."""
        num_particles = 10
        for _ in range(num_particles):
            angle = random.uniform(-math.pi/4, math.pi/4)
            speed = random.uniform(50, 150)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'size': random.uniform(3, 6),
                'alpha': 255
            })

    def _init_charge_effect(self):
        """Initialize charge attack particles."""
        num_particles = 20
        for _ in range(num_particles):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(150, 300)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'size': random.uniform(2, 5),
                'alpha': 255
            })

    def _init_special_effect(self):
        """Initialize special ability particles."""
        num_particles = 30
        for _ in range(num_particles):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(100, 400)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'size': random.uniform(3, 7),
                'alpha': 255
            })

    def update(self, dt: float):
        """Update effect particles."""
        self.current_time += dt
        if self.current_time >= self.duration:
            self.finished = True
            return

        # Update each particle
        for particle in self.particles:
            # Update position
            particle['x'] += particle['dx'] * dt
            particle['y'] += particle['dy'] * dt
            
            # Apply gravity and friction
            particle['dy'] += 400 * dt  # Gravity
            particle['dx'] *= 0.95  # Air resistance
            particle['dy'] *= 0.95
            
            # Fade out
            fade_rate = 255 / self.duration
            particle['alpha'] = max(0, particle['alpha'] - fade_rate * dt)

    def draw(self, screen: pygame.Surface, camera_x: int, camera_y: int):
        """Draw effect particles."""
        for particle in self.particles:
            alpha = int(particle['alpha'])
            if alpha <= 0:
                continue
                
            # Create color with alpha
            color_with_alpha = (*self.color, alpha)
            
            # Create surface for particle
            particle_surface = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                particle_surface,
                color_with_alpha,
                (particle['size'], particle['size']),
                particle['size']
            )
            
            # Draw to screen
            screen.blit(
                particle_surface,
                (
                    particle['x'] - camera_x - particle['size'],
                    particle['y'] - camera_y - particle['size']
                )
            )

class CombatEffectManager:
    def __init__(self):
        self.effects: List[CombatEffect] = []
        
    def add_effect(self, x: float, y: float, effect_type: str, color: Tuple[int, int, int]):
        """Add a new combat effect."""
        self.effects.append(CombatEffect(x, y, effect_type, color))
        
    def update(self, dt: float):
        """Update all active effects."""
        # Update effects and remove finished ones
        self.effects = [effect for effect in self.effects if not effect.finished]
        for effect in self.effects:
            effect.update(dt)
            
    def draw(self, screen: pygame.Surface, camera_x: int, camera_y: int):
        """Draw all active effects."""
        for effect in self.effects:
            effect.draw(screen, camera_x, camera_y) 