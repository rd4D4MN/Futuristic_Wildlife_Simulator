import pygame
from typing import Dict, Optional
import weakref

class ResourceManager:
    _instance = None
    
    def __init__(self):
        self.sprite_cache: Dict[str, weakref.ref] = {}
        self.sound_cache: Dict[str, weakref.ref] = {}
    
    @classmethod
    def get_instance(cls) -> 'ResourceManager':
        if cls._instance is None:
            cls._instance = ResourceManager()
        return cls._instance
    
    def get_sprite(self, filepath: str, size: tuple) -> Optional[pygame.Surface]:
        cache_key = f"{filepath}_{size}"
        
        if cache_key in self.sprite_cache:
            cached = self.sprite_cache[cache_key]()
            if cached is not None:
                return cached
                
        try:
            sprite = pygame.image.load(filepath).convert_alpha()
            sprite = pygame.transform.scale(sprite, size)
            self.sprite_cache[cache_key] = weakref.ref(sprite)
            return sprite
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading sprite {filepath}: {e}")
            return None
            
    def cleanup(self):
        """Remove dead references"""
        self.sprite_cache = {k: v for k, v in self.sprite_cache.items() if v() is not None}
        self.sound_cache = {k: v for k, v in self.sound_cache.items() if v() is not None}
