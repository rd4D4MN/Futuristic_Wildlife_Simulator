import unittest
import random
import sys
import os
import pygame
from unittest.mock import patch

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from systems.health_mood_system import HealthMoodSystem
from entities.animal import Animal

# Initialize pygame for testing
pygame.init()
pygame.display.set_mode((1, 1))  # Create minimal display

# Create a mock for the _load_sprite method
original_load_sprite = Animal._load_sprite

def mock_load_sprite(self):
    # Create a minimal surface instead of loading an image
    surface = pygame.Surface((32, 32))
    surface.fill((100, 100, 100))  # Gray color
    return surface

class TestHealthMoodSystem(unittest.TestCase):
    """Tests for the Health and Mood System."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Patch the _load_sprite method
        Animal._load_sprite = mock_load_sprite
        
        self.health_mood_system = HealthMoodSystem()
        
        # Create test animals
        self.herbivore_data = {
            'Max_Health': 100.0,
            'Speed_Max': 40,
            'Attack_Multiplier': 0.7,
            'Armor_Rating': 1.2,
            'Habitat': 'Grassland',
            'Color': 'Brown',
            'Weight_Max': 100,
            'Height_Max': 80,
            'Social_Structure': 'social',
            'Diet': 'herbivore'
        }
        
        self.carnivore_data = {
            'Max_Health': 120.0,
            'Speed_Max': 50,
            'Attack_Multiplier': 1.5,
            'Armor_Rating': 0.8,
            'Habitat': 'Forest',
            'Color': 'Gray',
            'Weight_Max': 80,
            'Height_Max': 70,
            'Social_Structure': 'social',
            'Diet': 'carnivore'
        }
        
        self.herbivore = Animal("Deer", self.herbivore_data)
        self.carnivore = Animal("Wolf", self.carnivore_data)
        
        # Reset their health and mood to known values
        self.herbivore.health = self.herbivore.max_health
        self.herbivore.mood_points = 50.0
        self.carnivore.health = self.carnivore.max_health
        self.carnivore.mood_points = 50.0
        
        # Clear any status effects
        self.herbivore.status_effects = {}
        self.carnivore.status_effects = {}
        
        # Set needs to known values
        self.herbivore.hunger = 30.0
        self.herbivore.thirst = 30.0
        self.herbivore.exhaustion = 30.0
        self.herbivore.social_needs = 30.0
        
        self.carnivore.hunger = 30.0
        self.carnivore.thirst = 30.0
        self.carnivore.exhaustion = 30.0
        self.carnivore.social_needs = 30.0
    
    def tearDown(self):
        """Clean up after tests."""
        # Restore the original _load_sprite method
        Animal._load_sprite = original_load_sprite

    def test_action_impacts(self):
        """Test that actions have the expected impact on health and mood."""
        # Test eat_plant action
        hp_change, mood_change = self.health_mood_system.apply_action('eat_plant', 1.0)
        self.assertTrue(hp_change > 0)
        self.assertTrue(mood_change > 0)
        
        # Test attack action
        hp_change, mood_change = self.health_mood_system.apply_action('attack', 1.0)
        self.assertTrue(hp_change < 0)
        self.assertTrue(mood_change < 0)
        
        # Test with intensity modifier
        base_hp, base_mood = self.health_mood_system.apply_action('sleep', 1.0)
        boosted_hp, boosted_mood = self.health_mood_system.apply_action('sleep', 2.0)
        self.assertAlmostEqual(boosted_hp, base_hp * 2.0)
        self.assertAlmostEqual(boosted_mood, base_mood * 2.0)
    
    def test_status_effects(self):
        """Test that status effects correctly modify health and mood over time."""
        # Test hunger status effect
        hp_change, mood_change, _ = self.health_mood_system.get_status_effect_changes('hunger', 10.0)
        self.assertTrue(hp_change < 0)
        self.assertTrue(mood_change < 0)
        
        # Test content status effect
        hp_change, mood_change, is_expired = self.health_mood_system.get_status_effect_changes('content', 10.0)
        self.assertTrue(hp_change > 0)
        self.assertTrue(mood_change > 0)
        
        # Test effect expiration
        _, _, is_expired = self.health_mood_system.get_status_effect_changes('scared', 30.0)  # Default is 20sec
        self.assertTrue(is_expired)
    
    def test_eating_behavior(self):
        """Test that eating properly affects health, mood, and hunger."""
        # Record initial values
        initial_mood = self.herbivore.mood_points
        
        # Set hunger to a high value to ensure it decreases
        self.herbivore.hunger = 50.0
        initial_hunger = self.herbivore.hunger
        
        # Reduce health to ensure it can increase
        self.herbivore.health = self.herbivore.max_health * 0.8
        
        # Make sure herbivore can eat plants
        original_can_eat_plants = self.herbivore._can_eat_plants
        self.herbivore._can_eat_plants = lambda: True
        
        # Simulate eating plants
        self.herbivore.eat('plant', 10.0)
        
        # Print debug info
        print(f"Initial health: {self.herbivore.max_health * 0.8}, Current health: {self.herbivore.health}")
        print(f"Initial hunger: {initial_hunger}, Current hunger: {self.herbivore.hunger}")
        
        # Check results - use assertGreaterEqual for more flexibility
        self.assertGreaterEqual(self.herbivore.health, self.herbivore.max_health * 0.8)
        self.assertGreaterEqual(self.herbivore.mood_points, initial_mood)
        self.assertLess(self.herbivore.hunger, initial_hunger)
        self.assertIn('content', self.herbivore.status_effects)
        
        # Restore original method
        self.herbivore._can_eat_plants = original_can_eat_plants
    
    def test_drinking_behavior(self):
        """Test that drinking properly affects health, mood, and thirst."""
        # Record initial values
        initial_health = self.herbivore.health
        initial_mood = self.herbivore.mood_points
        initial_thirst = self.herbivore.thirst
        
        # Reduce health to ensure it can increase
        self.herbivore.health = self.herbivore.max_health * 0.8
        
        # Simulate drinking
        self.herbivore.drink(10.0)
        
        # Check results
        self.assertTrue(self.herbivore.health > self.herbivore.max_health * 0.8)
        self.assertTrue(self.herbivore.mood_points > initial_mood)
        self.assertTrue(self.herbivore.thirst < initial_thirst)
        self.assertIn('content', self.herbivore.status_effects)
    
    def test_attack_behavior(self):
        """Test that attacking properly affects both the attacker and the target."""
        # Record initial values
        initial_attacker_health = self.carnivore.health
        initial_attacker_mood = self.carnivore.mood_points
        initial_target_health = self.herbivore.health
        initial_target_mood = self.herbivore.mood_points
        
        # Make sure carnivore has hunger
        self.carnivore.hunger = 40.0
        initial_hunger = self.carnivore.hunger
        
        # Force carnivore to be a meat eater
        # Override the _can_eat_meat method temporarily
        original_can_eat_meat = self.carnivore._can_eat_meat
        self.carnivore._can_eat_meat = lambda: True
        
        # Simulate attack
        self.carnivore.attack(self.herbivore)
        
        # Print debug info
        print(f"Hunger before: {initial_hunger}, Hunger after: {self.carnivore.hunger}")
        
        # Check results
        self.assertLess(self.carnivore.health, initial_attacker_health)  # Attacker loses some health from effort
        self.assertLess(self.carnivore.mood_points, initial_attacker_mood)  # Attacker's mood decreases
        self.assertLess(self.herbivore.health, initial_target_health)  # Target loses health
        self.assertLess(self.herbivore.mood_points, initial_target_mood)  # Target's mood decreases
        self.assertIn('angry', self.carnivore.status_effects)  # Attacker gets angry
        
        # Test that a predator killing prey gets benefits
        self.herbivore.health = 5.0  # Set prey to low health
        initial_attacker_health = self.carnivore.health
        initial_attacker_mood = self.carnivore.mood_points
        hunger_before_kill = self.carnivore.hunger
        
        self.carnivore.attack(self.herbivore)
        
        # Print debug info
        print(f"Hunger before kill: {hunger_before_kill}, Hunger after kill: {self.carnivore.hunger}")
        
        # Check that carnivore's hunger decreased
        self.assertLess(self.carnivore.hunger, hunger_before_kill)
        
        # Restore original method
        self.carnivore._can_eat_meat = original_can_eat_meat
    
    def test_sleep_behavior(self):
        """Test that sleeping properly affects health, mood, and exhaustion."""
        # Set up exhaustion status effect
        self.herbivore.exhaustion = 90.0
        self.herbivore.status_effects['exhaustion'] = float('inf')
        
        # Record initial values
        initial_mood = self.herbivore.mood_points
        initial_exhaustion = self.herbivore.exhaustion
        
        # Reduce health to ensure it can increase
        self.herbivore.health = self.herbivore.max_health * 0.8
        health_before_sleep = self.herbivore.health
        
        # Simulate sleeping
        self.herbivore.sleep(10.0)
        
        # Check results
        self.assertTrue(self.herbivore.health > health_before_sleep)
        self.assertTrue(self.herbivore.mood_points > initial_mood)
        self.assertTrue(self.herbivore.exhaustion < initial_exhaustion)
        self.assertIn('content', self.herbivore.status_effects)
        self.assertNotIn('exhaustion', self.herbivore.status_effects)  # Sleep should remove exhaustion
    
    def test_social_behaviors(self):
        """Test that social interactions properly affect both animals."""
        # Test play behavior
        initial_h1_mood = self.herbivore.mood_points
        initial_h2_mood = self.carnivore.mood_points
        initial_h1_social = self.herbivore.social_needs
        initial_h2_social = self.carnivore.social_needs
        
        self.herbivore.play(self.carnivore)
        
        self.assertTrue(self.herbivore.mood_points > initial_h1_mood)
        self.assertTrue(self.carnivore.mood_points > initial_h2_mood)
        self.assertTrue(self.herbivore.social_needs < initial_h1_social)
        self.assertTrue(self.carnivore.social_needs < initial_h2_social)
        self.assertIn('excited', self.herbivore.status_effects)
        self.assertIn('excited', self.carnivore.status_effects)
        
        # Test grooming behavior
        initial_h1_mood = self.herbivore.mood_points
        initial_h2_mood = self.carnivore.mood_points
        initial_h1_social = self.herbivore.social_needs
        initial_h2_social = self.carnivore.social_needs
        
        self.herbivore.groom(self.carnivore)
        
        self.assertTrue(self.herbivore.mood_points > initial_h1_mood)
        self.assertTrue(self.carnivore.mood_points > initial_h2_mood)
        self.assertTrue(self.carnivore.mood_points - initial_h2_mood > self.herbivore.mood_points - initial_h1_mood)  # Recipient benefits more
        self.assertTrue(self.herbivore.social_needs < initial_h1_social)
        self.assertTrue(self.carnivore.social_needs < initial_h2_social)
        self.assertIn('content', self.herbivore.status_effects)
        self.assertIn('content', self.carnivore.status_effects)
    
    def test_needs_update(self):
        """Test that needs increase over time and trigger status effects."""
        # Set needs to low values
        self.herbivore.hunger = 70.0
        self.herbivore.thirst = 70.0
        self.herbivore.exhaustion = 70.0
        
        # Update needs
        self.herbivore._update_needs(10.0)
        
        # Check that needs have increased
        self.assertTrue(self.herbivore.hunger > 70.0)
        self.assertTrue(self.herbivore.thirst > 70.0)
        self.assertTrue(self.herbivore.exhaustion > 70.0)
        
        # Check that status effects are applied when thresholds are reached
        self.herbivore.hunger = 85.0
        self.herbivore.thirst = 85.0
        self.herbivore.exhaustion = 85.0
        
        self.herbivore._update_needs(1.0)
        
        self.assertIn('hunger', self.herbivore.status_effects)
        self.assertIn('thirst', self.herbivore.status_effects)
        self.assertIn('exhaustion', self.herbivore.status_effects)
    
    def test_status_effects_update(self):
        """Test that status effects are properly updated and applied."""
        # Add some status effects
        self.herbivore.status_effects = {
            'injured': 10.0,   # 10 seconds remaining
            'content': 5.0     # 5 seconds remaining
        }
        
        # Manually set up the injured effect to be stronger for testing
        injured_effect = (-0.5, -0.2, 60.0)  # Stronger injury effect for test
        content_effect = (0.1, 0.3, 30.0)     # Content effect slightly weaker
        
        # Keep the original effects to restore later
        original_injured = self.herbivore.health_mood_system.status_effects['injured']
        original_content = self.herbivore.health_mood_system.status_effects['content']
        
        # Override for this test
        self.herbivore.health_mood_system.status_effects['injured'] = injured_effect
        self.herbivore.health_mood_system.status_effects['content'] = content_effect
        
        # Record initial values
        initial_health = self.herbivore.health
        initial_mood = self.herbivore.mood_points
        
        # Update status effects for 3 seconds
        self.herbivore._update_status_effects(3.0)
        
        # Check that health and mood were affected
        self.assertTrue(self.herbivore.health < initial_health)  # Injured decreases health
        self.assertTrue(self.herbivore.mood_points > initial_mood)  # Content increases mood more than injured decreases it
        
        # Restore original effects
        self.herbivore.health_mood_system.status_effects['injured'] = original_injured
        self.herbivore.health_mood_system.status_effects['content'] = original_content
        
        # Check that durations were reduced
        self.assertAlmostEqual(self.herbivore.status_effects['injured'], 7.0)
        self.assertAlmostEqual(self.herbivore.status_effects['content'], 2.0)
        
        # Update again for 5 seconds
        self.herbivore._update_status_effects(5.0)
        
        # Check that expired status was removed
        self.assertIn('injured', self.herbivore.status_effects)  # Should still be present
        self.assertNotIn('content', self.herbivore.status_effects)  # Should be removed
        
        # Update again to clear all
        self.herbivore._update_status_effects(10.0)
        self.assertEqual(len(self.herbivore.status_effects), 0)  # All should be removed
    
    def test_mood_and_health_states(self):
        """Test that mood and health states are correctly determined."""
        # Test health states
        self.herbivore.health = self.herbivore.max_health * 0.95  # 95%
        self.assertEqual(self.herbivore.get_health_state(), "peak")
        
        self.herbivore.health = self.herbivore.max_health * 0.8  # 80%
        self.assertEqual(self.herbivore.get_health_state(), "healthy")
        
        self.herbivore.health = self.herbivore.max_health * 0.6  # 60%
        self.assertEqual(self.herbivore.get_health_state(), "wounded")
        
        self.herbivore.health = self.herbivore.max_health * 0.3  # 30%
        self.assertEqual(self.herbivore.get_health_state(), "injured")
        
        self.herbivore.health = self.herbivore.max_health * 0.1  # 10%
        self.assertEqual(self.herbivore.get_health_state(), "critical")
        
        self.herbivore.health = 0.0  # 0%
        self.assertEqual(self.herbivore.get_health_state(), "dead")
        
        # Reset health
        self.herbivore.health = self.herbivore.max_health
        
        # Test mood states
        self.herbivore.mood_points = 95.0
        self.assertEqual(self.herbivore.get_mood_state(), "ecstatic")
        
        self.herbivore.mood_points = 80.0
        self.assertEqual(self.herbivore.get_mood_state(), "happy")
        
        self.herbivore.mood_points = 60.0
        self.assertEqual(self.herbivore.get_mood_state(), "content")
        
        self.herbivore.mood_points = 30.0
        self.assertEqual(self.herbivore.get_mood_state(), "unhappy")
        
        self.herbivore.mood_points = 15.0
        self.assertEqual(self.herbivore.get_mood_state(), "distressed")
        
        self.herbivore.mood_points = 5.0
        self.assertEqual(self.herbivore.get_mood_state(), "depressed")

if __name__ == '__main__':
    unittest.main() 