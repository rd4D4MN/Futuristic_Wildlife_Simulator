import pygame
import json
import os
from typing import Dict, Any, Optional, List, Tuple

from src.ui.player_setup import PlayerSetup
from src.entities.robot import Robot

class GameSetup:
    """Handles the initial game setup and player customization."""
    
    def __init__(self, screen: pygame.Surface):
        """Initialize the game setup manager."""
        self.screen = screen
        self.player_setup = PlayerSetup(screen)
        
    def run_player_setup(self) -> Optional[Robot]:
        """Run the player setup process and return a customized robot or None if canceled."""
        # Run the player setup UI
        player_name, ideology_data, archetype_data = self.player_setup.run()
        
        # If player canceled, return None
        if player_name is None or not ideology_data or not archetype_data:
            return None
            
        # Create a player-controlled robot with the chosen attributes
        player_robot = self._create_player_robot(player_name, ideology_data, archetype_data)
        
        return player_robot
        
    def _create_player_robot(self, name: str, ideology: Dict[str, Any], archetype: Dict[str, Any]) -> Robot:
        """Create a player-controlled robot with the specified attributes."""
        # Get the center of the world as the starting position
        # These values will be overridden by the game when actually spawning the robot
        x, y = 1000, 500
        
        # Create a new robot instance
        robot = Robot(x, y)
        
        # Set the robot's name
        robot.name = name
        
        # Add ideology and archetype data to the robot
        robot.ideology = ideology["Ideology"]
        robot.ideology_data = ideology
        
        robot.archetype = archetype["Archetype"]
        robot.archetype_data = archetype
        
        # Apply attribute bonuses from the chosen archetype
        self._apply_archetype_bonuses(robot, archetype)
        
        # Mark this robot as player-controlled
        robot.is_player_controlled = True
        
        return robot
    
    def _apply_archetype_bonuses(self, robot: Robot, archetype: Dict[str, Any]) -> None:
        """Apply the stat bonuses and abilities from the chosen archetype."""
        # Apply stat bonuses
        if "Strength" in archetype:
            strength = int(archetype["Strength"])
            # Convert strength to attack bonus
            robot.attack_bonus = (strength - 10) / 2
            
        if "Intelligence" in archetype:
            intelligence = int(archetype["Intelligence"])
            # Intelligence affects ability to recruit animals more easily
            robot.recruitment_bonus = (intelligence - 10) / 20
            
        if "Agility" in archetype:
            agility = int(archetype["Agility"])
            # Agility affects movement speed
            robot.speed = robot.speed * (1 + (agility - 10) / 40)
            
        if "Endurance" in archetype:
            endurance = int(archetype["Endurance"])
            # Endurance affects health
            health_bonus = (endurance - 10) / 2
            robot.max_health = 100 + health_bonus * 5
            robot.health = robot.max_health
            
        if "Luck" in archetype:
            luck = int(archetype["Luck"])
            # Luck affects various random events
            robot.luck = luck / 10
        
        # Apply special abilities
        if "Special Abilities" in archetype:
            # Store special abilities for later use
            robot.special_abilities = archetype["Special Abilities"]

def setup_player_robot(screen: pygame.Surface) -> Optional[Robot]:
    """Run the player setup process and return a customized robot."""
    game_setup = GameSetup(screen)
    return game_setup.run_player_setup()

def is_player_robot(robot: Robot) -> bool:
    """Check if a robot is the player's robot."""
    return hasattr(robot, 'is_player_controlled') and robot.is_player_controlled 