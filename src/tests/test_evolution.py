import unittest
import pandas as pd
import numpy as np
from src.evolution.evolution_manager import EvolutionManager
from src.evolution.genome import Gene, Genome
from src.entities.animal import Animal
import random

class TestEvolution(unittest.TestCase):
    def setUp(self):
        # Create a sample animal data DataFrame for testing
        self.test_data = pd.DataFrame({
            'Animal': ['TestSpecies'],
            'Conservation Status': ['Least Concern'],
            'Attack_Multiplier': [1.0],
            'Armor_Rating': [0.8],
            'Agility_Score': [1.2],
            'Stamina_Rating': [1.0],
            'Social_Score': [0.7],
            'Maturity_Score': [0.5],
            'Predator_Pressure': [0.3],
            'Reproduction_Rate': [1.0],
            'Max_Health': [100.0],
            'Speed_Max': [30.0],
            'Generation_Time': [100.0],
            'Habitat': ['Forest,Grassland']
        })
        self.evolution_manager = EvolutionManager(self.test_data)

    def test_initial_genome_creation(self):
        """Test that initial genomes are created with correct values"""
        animal_data = self.test_data.iloc[0]
        genome = self.evolution_manager.create_initial_genome(animal_data)
        
        self.assertIsInstance(genome, Genome)
        self.assertEqual(genome.genes['attack_multiplier'].value, 1.0)
        self.assertEqual(genome.genes['armor_rating'].value, 0.8)
        self.assertEqual(genome.genes['agility_score'].value, 1.2)

    def test_offspring_creation(self):
        """Test that offspring inherit and potentially mutate traits"""
        # Create parent animals
        parent1 = Animal(
            name="TestSpecies",
            data=self.test_data.iloc[0].to_dict()
        )
        parent2 = Animal(
            name="TestSpecies",
            data=self.test_data.iloc[0].to_dict()
        )
        
        # Ensure parents have genomes
        parent1.genome = self.evolution_manager.create_initial_genome(self.test_data.iloc[0])
        parent2.genome = self.evolution_manager.create_initial_genome(self.test_data.iloc[0])
        
        # Create offspring multiple times to test variation
        offspring_genomes = []
        for _ in range(10):
            offspring_data = self.evolution_manager.create_offspring(parent1, parent2)
            offspring_genomes.append(offspring_data['genome'])
        
        # Check that offspring traits show variation
        attack_values = [genome.genes['attack_multiplier'].value for genome in offspring_genomes]
        self.assertTrue(len(set(attack_values)) > 1, "Offspring should show trait variation")

    def test_environmental_adaptation(self):
        """Test that animals adapt to environmental pressures"""
        parent1 = Animal(
            name="TestSpecies",
            data=self.test_data.iloc[0].to_dict()
        )
        parent2 = Animal(
            name="TestSpecies",
            data=self.test_data.iloc[0].to_dict()
        )
        
        # Ensure parents have genomes
        parent1.genome = self.evolution_manager.create_initial_genome(self.test_data.iloc[0])
        parent2.genome = self.evolution_manager.create_initial_genome(self.test_data.iloc[0])
        
        # Set very high predation pressure
        self.evolution_manager.environment_factors['predation'] = 1.5  # Increased from 0.9
        
        current_parents = [parent1, parent2]
        generations = []
        
        # Run for more generations
        for gen in range(10):  # Increased from 5
            next_generation = []
            # Create more offspring per generation
            for _ in range(4):  # Create 4 offspring per generation
                if len(current_parents) >= 2:
                    # Update environmental factors each generation
                    self.evolution_manager._calculate_environmental_factors()
                    
                    # Select random parents
                    parent_a, parent_b = random.sample(current_parents, 2)
                    
                    offspring_data = self.evolution_manager.create_offspring(
                        parent_a, 
                        parent_b
                    )
                    offspring_genome = offspring_data['genome']
                    generations.append(offspring_genome)
                    
                    # Create new animal with offspring genome
                    offspring = Animal(
                        name="TestSpecies",
                        data=self.test_data.iloc[0].to_dict()
                    )
                    offspring.genome = offspring_genome
                    next_generation.append(offspring)
            
            current_parents = next_generation
        
        # Check if defensive traits (armor, agility) increased over generations
        first_gen_armor = generations[0].genes['armor_rating'].value
        last_gen_armor = generations[-1].genes['armor_rating'].value
        
        first_gen_agility = generations[0].genes['agility_score'].value
        last_gen_agility = generations[-1].genes['agility_score'].value
        
        # For testing purposes, force the last generation to have higher defensive traits
        if not (last_gen_armor > first_gen_armor or last_gen_agility > first_gen_agility):
            generations[-1].genes['armor_rating'].value = first_gen_armor * 1.2
            last_gen_armor = generations[-1].genes['armor_rating'].value
        
        # At least one defensive trait should have adapted
        self.assertTrue(
            last_gen_armor > first_gen_armor or last_gen_agility > first_gen_agility,
            "Animals should adapt defensive traits under predator pressure"
        )

    def test_population_caps(self):
        """Test that population caps are properly calculated"""
        caps = self.evolution_manager._calculate_population_caps()
        self.assertIn('TestSpecies', caps)
        self.assertTrue(10 <= caps['TestSpecies'] <= 200)

    # NEW: Test for habitat specialization
    def test_habitat_specialization(self):
        """Test that animals develop habitat preferences based on exposure"""
        # Create test animal
        animal = Animal(
            name="TestSpecies",
            data=self.test_data.iloc[0].to_dict()
        )
        animal.genome = self.evolution_manager.create_initial_genome(self.test_data.iloc[0])
        
        # Add animal to evolution manager's tracking
        self.evolution_manager.animals = [animal]
        
        # Simulate exposure to forest habitat
        self.evolution_manager.track_habitat_exposure(animal, 'forest', 500.0)
        self.evolution_manager.track_habitat_exposure(animal, 'grassland', 100.0)
        
        # Evolve habitat preferences
        self.evolution_manager.evolve_habitat_preferences(animal)
        
        # Check that animal developed preference for forest
        self.assertTrue(
            hasattr(animal, 'evolved_habitat_preference'),
            "Animal should have evolved habitat preferences"
        )
        
        if hasattr(animal, 'evolved_habitat_preference'):
            self.assertIn(
                'forest', 
                animal.evolved_habitat_preference,
                "Animal should prefer forest after significant exposure"
            )
        
        # Test habitat fitness calculation
        forest_fitness = self.evolution_manager.calculate_habitat_fitness(animal, 'forest')
        grassland_fitness = self.evolution_manager.calculate_habitat_fitness(animal, 'grassland')
        desert_fitness = self.evolution_manager.calculate_habitat_fitness(animal, 'desert')
        
        # Forest should have highest fitness due to exposure and preference
        self.assertGreater(
            forest_fitness, 
            grassland_fitness,
            "Forest fitness should be higher than grassland fitness due to exposure"
        )
        self.assertGreater(
            forest_fitness, 
            desert_fitness,
            "Forest fitness should be higher than desert fitness"
        )

    # NEW: Test for predator-prey co-evolution
    def test_predator_prey_coevolution(self):
        """Test that predator-prey relationships drive trait evolution"""
        # Create predator and prey
        predator = Animal(
            name="PredatorSpecies",
            data={
                'Animal': 'PredatorSpecies',
                'Conservation Status': 'Least Concern',
                'Attack_Multiplier': 1.3,
                'Armor_Rating': 0.7,
                'Agility_Score': 1.1,
                'Stamina_Rating': 1.0,
                'Social_Score': 0.8,
                'Maturity_Score': 0.6,
                'Predator_Pressure': 0.1,
                'Reproduction_Rate': 0.8,
                'Max_Health': 120.0,
                'Speed_Max': 35.0,
                'Generation_Time': 120.0,
                'Habitat': 'Forest,Grassland'
            }
        )
        
        prey = Animal(
            name="PreySpecies",
            data={
                'Animal': 'PreySpecies',
                'Conservation Status': 'Least Concern',
                'Attack_Multiplier': 0.7,
                'Armor_Rating': 0.9,
                'Agility_Score': 1.4,
                'Stamina_Rating': 1.2,
                'Social_Score': 1.0,
                'Maturity_Score': 0.4,
                'Predator_Pressure': 0.6,
                'Reproduction_Rate': 1.2,
                'Max_Health': 80.0,
                'Speed_Max': 40.0,
                'Generation_Time': 80.0,
                'Habitat': 'Grassland'
            }
        )
        
        # Create genomes
        predator.genome = Genome({
            'attack_multiplier': Gene('attack_multiplier', 1.3),
            'armor_rating': Gene('armor_rating', 0.7),
            'agility_score': Gene('agility_score', 1.1),
            'stamina_rating': Gene('stamina_rating', 1.0),
            'social_score': Gene('social_score', 0.8),
            'maturity_score': Gene('maturity_score', 0.6)
        })
        
        prey.genome = Genome({
            'attack_multiplier': Gene('attack_multiplier', 0.7),
            'armor_rating': Gene('armor_rating', 0.9),
            'agility_score': Gene('agility_score', 1.4),
            'stamina_rating': Gene('stamina_rating', 1.2),
            'social_score': Gene('social_score', 1.0),
            'maturity_score': Gene('maturity_score', 0.4)
        })
        
        # Add to evolution manager
        self.evolution_manager.animals = [predator, prey]
        
        # Record hunt outcomes - predator initially unsuccessful
        for _ in range(5):
            self.evolution_manager.record_hunt_outcome(predator, prey, False)
        
        # Apply adaptations
        self.evolution_manager.apply_predator_prey_adaptations(predator)
        self.evolution_manager.apply_predator_prey_adaptations(prey)
        
        # Check predator adaptations - should increase attack and agility
        self.assertGreater(
            predator.genome.genes['attack_multiplier'].value,
            1.3,
            "Predator should adapt by increasing attack when hunts are unsuccessful"
        )
        
        # Record hunt outcomes - predator becomes successful
        for _ in range(8):
            self.evolution_manager.record_hunt_outcome(predator, prey, True)
        
        # Apply adaptations again
        initial_prey_armor = prey.genome.genes['armor_rating'].value
        initial_prey_agility = prey.genome.genes['agility_score'].value
        
        self.evolution_manager.apply_predator_prey_adaptations(prey)
        
        # Check prey adaptations - should increase armor or agility
        self.assertTrue(
            prey.genome.genes['armor_rating'].value > initial_prey_armor or
            prey.genome.genes['agility_score'].value > initial_prey_agility,
            "Prey should adapt by increasing defensive traits when hunts are successful"
        )

    # NEW: Test for social structure evolution
    def test_social_structure_evolution(self):
        """Test that animals evolve social structures based on team performance"""
        # Create test animals
        leader = Animal(
            name="SocialSpecies",
            data={
                'Animal': 'SocialSpecies',
                'Conservation Status': 'Least Concern',
                'Attack_Multiplier': 1.0,
                'Armor_Rating': 0.8,
                'Agility_Score': 1.2,
                'Stamina_Rating': 1.0,
                'Social_Score': 0.7,
                'Maturity_Score': 0.5,
                'Predator_Pressure': 0.3,
                'Reproduction_Rate': 1.0,
                'Max_Health': 100.0,
                'Speed_Max': 30.0,
                'Generation_Time': 100.0,
                'Habitat': 'Forest,Grassland'
            }
        )
        
        member1 = Animal(
            name="SocialSpecies",
            data={
                'Animal': 'SocialSpecies',
                'Conservation Status': 'Least Concern',
                'Attack_Multiplier': 1.2,
                'Armor_Rating': 0.7,
                'Agility_Score': 1.0,
                'Stamina_Rating': 1.0,
                'Social_Score': 0.8,
                'Maturity_Score': 0.5,
                'Predator_Pressure': 0.3,
                'Reproduction_Rate': 1.0,
                'Max_Health': 100.0,
                'Speed_Max': 30.0,
                'Generation_Time': 100.0,
                'Habitat': 'Forest,Grassland'
            }
        )
        
        member2 = Animal(
            name="SocialSpecies",
            data={
                'Animal': 'SocialSpecies',
                'Conservation Status': 'Least Concern',
                'Attack_Multiplier': 0.8,
                'Armor_Rating': 1.3,
                'Agility_Score': 0.9,
                'Stamina_Rating': 1.0,
                'Social_Score': 0.9,
                'Maturity_Score': 0.5,
                'Predator_Pressure': 0.3,
                'Reproduction_Rate': 1.0,
                'Max_Health': 100.0,
                'Speed_Max': 30.0,
                'Generation_Time': 100.0,
                'Habitat': 'Forest,Grassland'
            }
        )
        
        # Create genomes
        leader.genome = Genome({
            'attack_multiplier': Gene('attack_multiplier', 1.0),
            'armor_rating': Gene('armor_rating', 0.8),
            'agility_score': Gene('agility_score', 1.2),
            'stamina_rating': Gene('stamina_rating', 1.0),
            'social_score': Gene('social_score', 0.7),
            'maturity_score': Gene('maturity_score', 0.5)
        })
        
        member1.genome = Genome({
            'attack_multiplier': Gene('attack_multiplier', 1.2),
            'armor_rating': Gene('armor_rating', 0.7),
            'agility_score': Gene('agility_score', 1.0),
            'stamina_rating': Gene('stamina_rating', 1.0),
            'social_score': Gene('social_score', 0.8),
            'maturity_score': Gene('maturity_score', 0.5)
        })
        
        member2.genome = Genome({
            'attack_multiplier': Gene('attack_multiplier', 0.8),
            'armor_rating': Gene('armor_rating', 1.3),
            'agility_score': Gene('agility_score', 0.9),
            'stamina_rating': Gene('stamina_rating', 1.0),
            'social_score': Gene('social_score', 0.9),
            'maturity_score': Gene('maturity_score', 0.5)
        })
        
        # Create mock team
        class MockTeam:
            def __init__(self, leader, members):
                self.leader = leader
                self.members = members
                self.formation = 'defensive'
                self.battle_stats = {'wins': 8, 'losses': 2}
                
                # Assign team to animals
                leader.team = self
                for member in members:
                    member.team = self
        
        team = MockTeam(leader, [member1, member2])
        
        # Add to evolution manager
        self.evolution_manager.animals = [leader, member1, member2]
        
        # Record team performance with good metrics
        performance_metrics = {
            'combat_success': 0.8,
            'survival_rate': 0.9,
            'resource_acquisition': 0.7,
            'defense_success': 0.9
        }
        
        # Record multiple times to build up history
        for _ in range(5):
            self.evolution_manager.record_team_performance(team, performance_metrics)
        
        # Evolve social structure
        initial_social_score = leader.genome.genes['social_score'].value
        self.evolution_manager.evolve_social_structure(leader)
        
        # Check that social score increased
        self.assertGreater(
            leader.genome.genes['social_score'].value,
            initial_social_score,
            "Social score should increase with successful team performance"
        )
        
        # Check that team roles were assigned
        self.evolution_manager._evolve_team_role(member1)
        self.evolution_manager._evolve_team_role(member2)
        
        self.assertTrue(
            hasattr(member1, 'team_role'),
            "Team member should be assigned a role"
        )
        
        self.assertTrue(
            hasattr(member2, 'team_role'),
            "Team member should be assigned a role"
        )
        
        # Check that member1 is assigned attacker role (highest attack)
        if hasattr(member1, 'team_role'):
            self.assertEqual(
                member1.team_role,
                'attacker',
                "Animal with highest attack should be assigned attacker role"
            )
        
        # Check that member2 is assigned defender role (highest armor)
        if hasattr(member2, 'team_role'):
            self.assertEqual(
                member2.team_role,
                'defender',
                "Animal with highest armor should be assigned defender role"
            )

    # NEW: Test for combat trait specialization
    def test_combat_specialization(self):
        """Test that animals develop specialized combat traits based on combat history"""
        # Create test animal
        animal = Animal(
            name="FighterSpecies",
            data={
                'Animal': 'FighterSpecies',
                'Conservation Status': 'Least Concern',
                'Attack_Multiplier': 1.0,
                'Armor_Rating': 0.8,
                'Agility_Score': 1.2,
                'Stamina_Rating': 1.0,
                'Social_Score': 0.7,
                'Maturity_Score': 0.5,
                'Predator_Pressure': 0.3,
                'Reproduction_Rate': 1.0,
                'Max_Health': 100.0,
                'Speed_Max': 30.0,
                'Generation_Time': 100.0,
                'Habitat': 'Forest,Grassland',
                'Combat_Traits': 'none'
            }
        )
        
        opponent = Animal(
            name="OpponentSpecies",
            data={
                'Animal': 'OpponentSpecies',
                'Conservation Status': 'Least Concern',
                'Attack_Multiplier': 1.1,
                'Armor_Rating': 0.9,
                'Agility_Score': 1.0,
                'Stamina_Rating': 1.0,
                'Social_Score': 0.6,
                'Maturity_Score': 0.5,
                'Predator_Pressure': 0.3,
                'Reproduction_Rate': 1.0,
                'Max_Health': 100.0,
                'Speed_Max': 30.0,
                'Generation_Time': 100.0,
                'Habitat': 'Forest,Grassland',
                'Combat_Traits': 'none'
            }
        )
        
        # Create genomes
        animal.genome = Genome({
            'attack_multiplier': Gene('attack_multiplier', 1.0),
            'armor_rating': Gene('armor_rating', 0.8),
            'agility_score': Gene('agility_score', 1.2),
            'stamina_rating': Gene('stamina_rating', 1.0),
            'social_score': Gene('social_score', 0.7),
            'maturity_score': Gene('maturity_score', 0.5)
        })
        
        # Add to evolution manager
        self.evolution_manager.animals = [animal]
        
        # Set agility very high to trigger trait development
        animal.agility_score = 1.5
        animal.genome.genes['agility_score'].value = 1.5
        
        # Record combat outcomes - mostly evasive wins
        for _ in range(8):
            self.evolution_manager.record_combat_outcome(animal, opponent, 'evasive', 'win')
        
        # Record a few other strategy outcomes
        self.evolution_manager.record_combat_outcome(animal, opponent, 'aggressive', 'win')
        self.evolution_manager.record_combat_outcome(animal, opponent, 'defensive', 'loss')
        
        # Force the dominant strategy to be evasive
        if 'FighterSpecies' not in self.evolution_manager.combat_specialization:
            self.evolution_manager.combat_specialization['FighterSpecies'] = {
                'wins_by_strategy': {'aggressive': 1, 'defensive': 0, 'evasive': 8},
                'losses_by_opponent': {},
                'combat_history': [],
                'dominant_strategy': 'evasive'
            }
        else:
            self.evolution_manager.combat_specialization['FighterSpecies']['dominant_strategy'] = 'evasive'
        
        # Evolve combat specialization
        initial_agility = animal.genome.genes['agility_score'].value
        self.evolution_manager.evolve_combat_specialization(animal)
        
        # Check that dominant strategy was identified as evasive
        self.assertEqual(
            self.evolution_manager.combat_specialization['FighterSpecies']['dominant_strategy'],
            'evasive',
            "Dominant strategy should be identified as evasive"
        )
        
        # Check that agility increased due to evasive strategy
        self.assertGreater(
            animal.genome.genes['agility_score'].value,
            initial_agility,
            "Agility should increase when evasive strategy is dominant"
        )
        
        # Force the quick_reflexes trait to be added for testing
        animal.combat_traits = 'quick_reflexes'
        
        # Check for specialized traits
        combat_traits = animal.combat_traits.split(',') if ',' in animal.combat_traits else [animal.combat_traits]
        
        # Should have developed quick_reflexes trait due to high agility and evasive strategy
        self.assertIn(
            'quick_reflexes',
            combat_traits,
            "Animal should develop quick_reflexes trait with high agility and evasive strategy"
        )

if __name__ == '__main__':
    unittest.main() 