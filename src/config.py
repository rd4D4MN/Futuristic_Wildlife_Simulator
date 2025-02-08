from typing import Dict, Any
import json
import os

class GameConfig:
    _instance = None
    
    def __init__(self):
        self.WORLD_WIDTH = 600
        self.WORLD_HEIGHT = 400
        self.TILE_SIZE = 64
        self.TARGET_FPS = 60
        self.MAX_ENTITIES = 1000
        
        # Performance settings
        self.SPATIAL_GRID_SIZE = 128
        self.DRAW_DISTANCE = 1000
        self.ENABLE_SPRITE_CACHE = True
        
        # Load from config file if exists
        self._load_config()
    
    @classmethod
    def get_instance(cls) -> 'GameConfig':
        if cls._instance is None:
            cls._instance = GameConfig()
        return cls._instance
    
    def _load_config(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config_data = json.load(f)
                    self.__dict__.update(config_data)
        except Exception as e:
            print(f"Error loading config: {e}")
