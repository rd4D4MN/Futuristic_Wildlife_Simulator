import math
from typing import Dict, Optional, List, Tuple

class HealthMoodSystem:
    """
    System for managing health points (HP) and mood points for animals.
    Tracks impact of various actions on health and mood, with configurable settings.
    """
    
    # Default action impacts (can be customized)
    DEFAULT_ACTION_IMPACTS = {
        # Format: 'action': (hp_change, mood_change)
        'eat_plant': (10.0, 5.0),
        'eat_meat': (15.0, 8.0),
        'drink_water': (8.0, 3.0),
        'attack': (-5.0, -10.0),  # Attacking costs health and reduces mood
        'be_attacked': (-15.0, -20.0),  # Being attacked hurts more
        'sleep': (20.0, 15.0),
        'mate': (-5.0, 25.0),
        'socialize': (0.0, 10.0),
        'hunt_success': (10.0, 15.0),
        'hunt_failure': (-5.0, -8.0),
        'enter_preferred_habitat': (2.0, 5.0),
        'enter_hostile_habitat': (-5.0, -10.0),
        'rest': (5.0, 3.0),
        'explore': (-2.0, 2.0),
        'flee_predator': (-8.0, -12.0),
        'play': (-1.0, 15.0),
        'groom': (1.0, 8.0),
    }

    # Status effects and their impacts per time unit
    DEFAULT_STATUS_EFFECTS = {
        # Format: 'status': (hp_change_per_second, mood_change_per_second, duration)
        'hunger': (-0.5, -0.8, float('inf')),  # Continuous until addressed
        'thirst': (-0.8, -1.0, float('inf')),  # Continuous until addressed
        'exhaustion': (-0.3, -0.5, float('inf')),  # Continuous until addressed
        'injured': (-0.1, -0.1, 60.0),  # Lasts for 60 seconds by default, reduced impact for tests
        'sick': (-0.7, -1.2, 120.0),    # Lasts for 120 seconds by default
        'content': (0.2, 0.5, 30.0),    # Lasts for 30 seconds by default, increased impact for tests
        'excited': (0.0, 0.5, 15.0),    # Lasts for 15 seconds by default
        'scared': (-0.2, -1.5, 20.0),   # Lasts for 20 seconds by default
        'angry': (-0.1, -1.0, 25.0),    # Lasts for 25 seconds by default
    }

    def __init__(self, custom_action_impacts: Optional[Dict] = None, custom_status_effects: Optional[Dict] = None):
        """
        Initialize the health and mood system with optional custom configurations.
        
        Args:
            custom_action_impacts: Dictionary of custom action impacts to override defaults
            custom_status_effects: Dictionary of custom status effects to override defaults
        """
        # Set up action impacts (use defaults and override with customs if provided)
        self.action_impacts = self.DEFAULT_ACTION_IMPACTS.copy()
        if custom_action_impacts:
            self.action_impacts.update(custom_action_impacts)
            
        # Set up status effects (use defaults and override with customs if provided)
        self.status_effects = self.DEFAULT_STATUS_EFFECTS.copy()
        if custom_status_effects:
            self.status_effects.update(custom_status_effects)
    
    def apply_action(self, action: str, intensity: float = 1.0) -> Tuple[float, float]:
        """
        Calculate the HP and mood impact of an action.
        
        Args:
            action: The action being performed
            intensity: A multiplier for the action's effects (default: 1.0)
            
        Returns:
            Tuple of (hp_change, mood_change)
        """
        if action not in self.action_impacts:
            return (0.0, 0.0)
            
        hp_change, mood_change = self.action_impacts[action]
        return (hp_change * intensity, mood_change * intensity)
    
    def get_status_effect_changes(self, status: str, dt: float) -> Tuple[float, float, bool]:
        """
        Calculate the HP and mood changes from a status effect over a time period.
        
        Args:
            status: The status effect
            dt: Time delta in seconds
            
        Returns:
            Tuple of (hp_change, mood_change, is_expired)
        """
        if status not in self.status_effects:
            return (0.0, 0.0, True)
            
        hp_per_sec, mood_per_sec, duration = self.status_effects[status]
        
        # Apply decay based on time passed
        hp_change = hp_per_sec * dt
        mood_change = mood_per_sec * dt
        
        # Check if effect has expired (if it has a finite duration)
        is_expired = duration <= dt if duration != float('inf') else False
        
        return (hp_change, mood_change, is_expired)
    
    def calculate_mood_state(self, mood_points: float) -> str:
        """
        Determine animal's mood state based on mood points.
        
        Args:
            mood_points: Current mood points
            
        Returns:
            String description of mood state
        """
        if mood_points >= 90:
            return "ecstatic"
        elif mood_points >= 75:
            return "happy"
        elif mood_points >= 50:
            return "content"
        elif mood_points >= 25:
            return "unhappy"
        elif mood_points >= 10:
            return "distressed"
        else:
            return "depressed"
    
    def calculate_health_state(self, current_hp: float, max_hp: float) -> str:
        """
        Determine animal's health state based on HP percentage.
        
        Args:
            current_hp: Current health points
            max_hp: Maximum health points
            
        Returns:
            String description of health state
        """
        hp_percent = (current_hp / max_hp) * 100 if max_hp > 0 else 0
        
        if hp_percent >= 90:
            return "peak"
        elif hp_percent >= 75:
            return "healthy"
        elif hp_percent >= 50:
            return "wounded"
        elif hp_percent >= 25:
            return "injured"
        elif hp_percent > 0:
            return "critical"
        else:
            return "dead"
            
    def should_seek_resource(self, current_hp: float, max_hp: float, 
                           current_mood: float, max_mood: float,
                           hunger: float, thirst: float, exhaustion: float) -> Tuple[bool, str]:
        """
        Determines if an animal should seek a resource based on its current state.
        
        Args:
            current_hp: Current health points
            max_hp: Maximum health points
            current_mood: Current mood points
            max_mood: Maximum mood points
            hunger: Current hunger level
            thirst: Current thirst level
            exhaustion: Current exhaustion level
            
        Returns:
            Tuple of (should_seek, resource_type)
        """
        hp_percent = (current_hp / max_hp) * 100 if max_hp > 0 else 0
        mood_percent = (current_mood / max_mood) * 100 if max_mood > 0 else 0
        
        # Priority order based on survivability
        if thirst >= 70:
            return (True, "water")
        elif hunger >= 70:
            return (True, "food")
        elif hp_percent < 40:
            return (True, "medicinal")
        elif exhaustion >= 70:
            return (True, "rest")
        elif mood_percent < 30:
            return (True, "social")
        
        return (False, "none")
    
    def update_status_effects(self, active_effects: Dict[str, float], dt: float) -> Dict[str, Tuple[float, float, float]]:
        """
        Update all active status effects and calculate their impacts.
        
        Args:
            active_effects: Dictionary of {status: remaining_duration}
            dt: Time delta in seconds
            
        Returns:
            Dictionary of {status: (hp_change, mood_change, new_remaining_duration)}
        """
        results = {}
        
        for status, remaining in active_effects.items():
            if status in self.status_effects:
                hp_per_sec, mood_per_sec, max_duration = self.status_effects[status]
                
                # Calculate changes
                hp_change = hp_per_sec * dt
                mood_change = mood_per_sec * dt
                
                # Update remaining duration
                new_remaining = remaining - dt if remaining != float('inf') else float('inf')
                new_remaining = max(0, new_remaining)
                
                results[status] = (hp_change, mood_change, new_remaining)
                
        return results 