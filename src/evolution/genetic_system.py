import random
from typing import List, Dict, Any
from entities.animal import Animal

class GeneticSystem:
    def __init__(self):
        self.generation = 0
        self.mutation_rate = 0.1
        self.population_history: List[Dict] = []

    def breed(self, parent1: Animal, parent2: Animal) -> Animal:
        """Create offspring by combining parent traits."""
        child_attributes = {}
        
        # Inherit attributes with possible mutations
        for key in ["Height_Max", "Weight_Max", "Speed_Max", "Armor_Rating"]:
            base_value = (getattr(parent1, key) + getattr(parent2, key)) / 2
            mutation = random.uniform(-0.1, 0.1) if random.random() < self.mutation_rate else 0
            child_attributes[key] = base_value * (1 + mutation)

        # Inherit combat traits
        child_attributes["Attack_Multiplier"] = max(parent1.attack_multiplier, parent2.attack_multiplier)
        child_attributes["Natural_Weapons"] = parent1.natural_weapons

        # Create new animal
        child = Animal(
            name=f"Gen{self.generation}_{parent1.name}_{parent2.name}",
            attributes=child_attributes
        )
        
        return child

    def should_breed(self, animal: Animal) -> bool:
        """Determine if an animal should breed based on health and stats."""
        return (animal.health > animal.max_health * 0.7 and 
                random.random() < 0.1)  # 10% chance if healthy
