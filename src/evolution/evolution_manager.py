import random
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
import pandas as pd

from src.entities.animal import Animal
from .genome import Gene, Genome

class EvolutionManager:
    def __init__(self, processed_animals_df: pd.DataFrame):
        """Initialize evolution manager with animal data."""
        self.animal_data = processed_animals_df
        self.population_caps = self._calculate_population_caps()
        self.breeding_cooldowns = {}  # Track breeding cooldowns by species
        self.generation_counters = {}  # Track generations by species
        self.species_stats = {}  # Track evolutionary stats by species
        
        # Enhanced evolution parameters
        self.min_breeding_age = 100  # frames
        self.base_reproduction_chance = 0.1
        self.environmental_pressure = 0.8  # Higher means more pressure
        self.social_breeding_threshold = 0.6  # Minimum social score for group breeding
        self.maturity_impact = 0.2  # Impact of maturity on breeding success
        
        # Enhanced mutation rates with dynamic scaling
        self.base_mutation_rates = {
            'attack_multiplier': 0.1,
            'armor_rating': 0.08,
            'agility_score': 0.12,
            'stamina_rating': 0.1,
            'social_score': 0.05,
            'maturity_score': 0.03
        }
        
        # Adaptive mutation scaling
        self.mutation_pressure = 1.0  # Dynamic mutation pressure
        self.min_mutation_pressure = 0.5
        self.max_mutation_pressure = 2.0
        
        # Generation tracking
        self.generation_stats = {}  # Track stats per generation
        
    def _calculate_population_caps(self) -> Dict[str, int]:
        """Calculate population caps based on conservation status and predator pressure."""
        caps = {}
        for _, animal in self.animal_data.iterrows():
            if pd.isna(animal['Animal']):
                continue
                
            # Base cap affected by conservation status
            base_cap = {
                'Least Concern': 100,
                'Near Threatened': 80,
                'Vulnerable': 60,
                'Endangered': 40,
                'Critically Endangered': 20
            }.get(animal['Conservation Status'], 50)
            
            # Adjust for predator pressure
            predator_modifier = 1 - (animal['Predator_Pressure'] * 0.3)
            
            # Adjust for reproduction rate
            reproduction_modifier = 1 + (animal['Reproduction_Rate'] * 0.2)
            
            final_cap = int(base_cap * predator_modifier * reproduction_modifier)
            caps[animal['Animal']] = max(10, min(200, final_cap))
            
        return caps
        
    def create_initial_genome(self, animal_data: pd.Series) -> Genome:
        """Create initial genome from animal data."""
        genes = {
            'attack_multiplier': Gene('attack_multiplier', float(animal_data['Attack_Multiplier'])),
            'armor_rating': Gene('armor_rating', float(animal_data['Armor_Rating'])),
            'agility_score': Gene('agility_score', float(animal_data['Agility_Score'])),
            'stamina_rating': Gene('stamina_rating', float(animal_data['Stamina_Rating'])),
            'social_score': Gene('social_score', float(animal_data['Social_Score'])),
            'maturity_score': Gene('maturity_score', float(animal_data['Maturity_Score']))
        }
        return Genome(genes)
        
    def should_reproduce(self, animal1: 'Animal', animal2: 'Animal', current_population: int) -> bool:
        """Enhanced reproduction check using maturity and social scores."""
        if animal1.name != animal2.name:  # Must be same species
            return False
            
        # Check population cap
        if current_population >= self.population_caps.get(animal1.name, 100):
            return False
            
        # Check breeding cooldown
        species_key = f"{animal1.name}_{id(animal1)}_{id(animal2)}"
        if species_key in self.breeding_cooldowns:
            if self.breeding_cooldowns[species_key] > 0:
                return False
                
        # Enhanced maturity check using maturity score
        maturity_threshold = self.min_breeding_age * (1 - animal1.maturity_score * self.maturity_impact)
        if (animal1.age < maturity_threshold or 
            animal2.age < maturity_threshold):
            return False
            
        # Calculate breeding chance with enhanced factors
        base_chance = self.base_reproduction_chance
        
        # Social compatibility bonus
        social_compatibility = 1.0
        if (animal1.social_score > self.social_breeding_threshold and 
            animal2.social_score > self.social_breeding_threshold):
            social_compatibility = 1.3
        elif abs(animal1.social_score - animal2.social_score) > 0.3:
            social_compatibility = 0.7
        
        # Modify by reproduction rate and generation time
        repro_rate = float(animal1.reproduction_rate)
        generation_factor = 1.0 / max(0.5, float(animal1.generation_time) / 100.0)
        chance = base_chance * repro_rate * generation_factor * social_compatibility
        
        # Environmental pressure modification
        env_modifier = 1 - (self.environmental_pressure * float(animal1.predator_pressure))
        chance *= env_modifier
        
        return random.random() < chance
        
    def create_offspring(self, parent1: 'Animal', parent2: 'Animal') -> Dict:
        """Enhanced offspring creation with adaptive mutation rates."""
        # Ensure both parents have genomes
        if not parent1.genome:
            parent1.genome = self.create_initial_genome(parent1.original_data)
        if not parent2.genome:
            parent2.genome = self.create_initial_genome(parent2.original_data)
            
        # Calculate mutation pressure based on environmental factors
        species = parent1.name
        current_stats = self.get_species_stats(species)
        
        if current_stats:
            # Adjust mutation pressure based on population trend and battle performance
            population_trend = current_stats['population_trend']
            self.mutation_pressure = max(self.min_mutation_pressure,
                min(self.max_mutation_pressure,
                    self.mutation_pressure * (1 - population_trend * 0.1)))
            
            # Increase mutation pressure if species is struggling
            if current_stats['avg_attack'] < 1.0 or current_stats['avg_armor'] < 1.0:
                self.mutation_pressure *= 1.2
        
        # Apply mutation pressure to base rates
        current_mutation_rates = {
            trait: rate * self.mutation_pressure
            for trait, rate in self.base_mutation_rates.items()
        }
        
        # Perform crossover with enhanced trait inheritance
        child_genome = parent1.genome.crossover(parent2.genome)
        
        # Apply mutations with adaptive rates
        for gene_name, mutation_rate in current_mutation_rates.items():
            if gene_name in child_genome.genes:
                if random.random() < mutation_rate:
                    # Enhanced mutation based on parent traits
                    parent_avg = (parent1.genome.genes[gene_name].value + 
                                parent2.genome.genes[gene_name].value) / 2
                    mutation_range = 0.2 * self.mutation_pressure
                    mutation = random.uniform(-mutation_range, mutation_range)
                    
                    # Ensure social scores don't mutate too drastically
                    if gene_name == 'social_score':
                        mutation *= 0.5
                    
                    new_value = parent_avg * (1 + mutation)
                    child_genome.genes[gene_name].value = max(0.1, min(2.0, new_value))
        
        # Update generation counter and cooldown
        self.generation_counters[species] = self.generation_counters.get(species, 0) + 1
        
        # Set breeding cooldown based on generation time
        species_key = f"{parent1.name}_{id(parent1)}_{id(parent2)}"
        generation_time = float(parent1.generation_time)
        base_cooldown = max(100, generation_time * 60)  # Convert to frames
        
        # Modify cooldown based on maturity score
        maturity_modifier = 1 - (parent1.maturity_score + parent2.maturity_score) * 0.2
        self.breeding_cooldowns[species_key] = base_cooldown * maturity_modifier
        
        # Track evolutionary stats
        if species not in self.species_stats:
            self.species_stats[species] = {
                'generations': 1,
                'avg_attack': [],
                'avg_armor': [],
                'avg_agility': [],
                'avg_social': [],
                'avg_maturity': [],
                'population_history': []
            }
        
        stats = self.species_stats[species]
        stats['generations'] += 1
        stats['avg_attack'].append(child_genome.genes['attack_multiplier'].value)
        stats['avg_armor'].append(child_genome.genes['armor_rating'].value)
        stats['avg_agility'].append(child_genome.genes['agility_score'].value)
        stats['avg_social'].append(child_genome.genes['social_score'].value)
        stats['avg_maturity'].append(child_genome.genes['maturity_score'].value)
        
        # Return offspring traits
        return {
            'genome': child_genome,
            'generation': self.generation_counters.get(species, 1)
        }
        
    def update(self, dt: float):
        """Update breeding cooldowns and environmental factors."""
        # Update breeding cooldowns
        for species_key in list(self.breeding_cooldowns.keys()):
            self.breeding_cooldowns[species_key] = max(
                0, 
                self.breeding_cooldowns[species_key] - dt * 60
            )
            
        # Periodically adjust environmental pressure
        if random.random() < 0.001:  # Small chance each update
            self.environmental_pressure = min(1.0, max(0.2,
                self.environmental_pressure + random.uniform(-0.1, 0.1)
            ))
            
    def get_species_stats(self, species: str) -> Dict:
        """Get evolutionary statistics for a species."""
        if species not in self.species_stats:
            return None
            
        stats = self.species_stats[species]
        return {
            'generations': stats['generations'],
            'avg_attack': np.mean(stats['avg_attack'][-10:]) if stats['avg_attack'] else 0,
            'avg_armor': np.mean(stats['avg_armor'][-10:]) if stats['avg_armor'] else 0,
            'avg_agility': np.mean(stats['avg_agility'][-10:]) if stats['avg_agility'] else 0,
            'avg_social': np.mean(stats['avg_social'][-10:]) if stats['avg_social'] else 0,
            'avg_maturity': np.mean(stats['avg_maturity'][-10:]) if stats['avg_maturity'] else 0,
            'population_trend': np.mean(np.diff(stats['population_history'][-10:])) 
                if len(stats['population_history']) > 1 else 0
        } 