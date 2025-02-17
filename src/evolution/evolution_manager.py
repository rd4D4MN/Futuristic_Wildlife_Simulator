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
        self.breeding_cooldowns = {}
        self.generation_counters = {}
        self.species_stats = {}
        
        # Enhanced evolution parameters
        self.min_breeding_age = 100
        self.base_reproduction_chance = 0.1
        self.environmental_pressure = 0.8
        self.social_breeding_threshold = 0.6
        self.maturity_impact = 0.2
        
        # Enhanced genetic system
        self.trait_weights = {
            'attack_multiplier': {'combat': 1.0, 'survival': 0.5},
            'armor_rating': {'combat': 0.8, 'survival': 0.7},
            'agility_score': {'combat': 0.7, 'survival': 0.8},
            'stamina_rating': {'survival': 1.0, 'combat': 0.6},
            'social_score': {'survival': 0.9, 'combat': 0.3},
            'maturity_score': {'survival': 0.8}
        }
        
        # Environmental adaptation system
        self.environment_factors = {
            'temperature': {'hot': 0.8, 'cold': -0.8},
            'humidity': {'high': 0.6, 'low': -0.6},
            'predation': {'high': 0.9, 'low': -0.3},
            'competition': {'high': 0.7, 'low': -0.4},
            'food_availability': {'high': -0.5, 'low': 0.8}
        }
        
        # Trait specialization tracking
        self.specialization_thresholds = {
            'combat': {'threshold': 0.8, 'traits': ['attack_multiplier', 'armor_rating']},
            'survival': {'threshold': 0.8, 'traits': ['stamina_rating', 'agility_score']},
            'social': {'threshold': 0.8, 'traits': ['social_score', 'maturity_score']}
        }
        
        # Population dynamics
        self.population_factors = {
            'Critically Endangered': {
                'mutation_rate': 1.5,
                'breeding_boost': 1.3,
                'survival_pressure': 0.7
            },
            'Endangered': {
                'mutation_rate': 1.3,
                'breeding_boost': 1.2,
                'survival_pressure': 0.8
            },
            'Vulnerable': {
                'mutation_rate': 1.1,
                'breeding_boost': 1.1,
                'survival_pressure': 0.9
            },
            'Near Threatened': {
                'mutation_rate': 1.0,
                'breeding_boost': 1.0,
                'survival_pressure': 1.0
            },
            'Least Concern': {
                'mutation_rate': 0.9,
                'breeding_boost': 0.9,
                'survival_pressure': 1.1
            }
        }
        
        # Adaptive mutation system
        self.base_mutation_rates = {
            'attack_multiplier': 0.1,
            'armor_rating': 0.08,
            'agility_score': 0.12,
            'stamina_rating': 0.1,
            'social_score': 0.05,
            'maturity_score': 0.03
        }
        
        # Dynamic adaptation tracking
        self.adaptation_history = {}
        self.specialization_history = {}
        self.environmental_history = {}
        
        # Generation tracking with enhanced metrics
        self.generation_stats = {}
        
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
        """Enhanced offspring creation with sophisticated genetic algorithms."""
        if not parent1.genome or not parent2.genome:
            self._ensure_genomes(parent1, parent2)
        
        species = parent1.name
        current_stats = self.get_species_stats(species)
        
        # Calculate environmental pressures
        env_factors = self._calculate_environmental_factors(parent1)
        
        # Get population factors based on conservation status
        pop_factors = self.population_factors.get(
            parent1.original_data.get('Conservation Status', 'Least Concern'),
            self.population_factors['Least Concern']
        )
        
        # Calculate adaptive mutation rates
        mutation_rates = self._calculate_adaptive_mutation_rates(
            species, current_stats, env_factors, pop_factors
        )
        
        # Perform enhanced crossover
        child_genome = self._perform_enhanced_crossover(
            parent1.genome, parent2.genome, mutation_rates, env_factors
        )
        
        # Track adaptations and specializations
        self._update_adaptation_tracking(species, child_genome, env_factors)
        
        # Update generation stats
        self._update_generation_stats(species, child_genome)
        
        return {
            'genome': child_genome,
            'generation': self.generation_counters.get(species, 1)
        }

    def _calculate_environmental_factors(self, animal: 'Animal') -> Dict:
        """Calculate current environmental pressures and their impact."""
        factors = {}
        
        # Get terrain-based factors
        terrain = self._get_terrain_at_position(animal)
        if terrain == 'desert':
            factors['temperature'] = 'hot'
            factors['humidity'] = 'low'
        elif terrain == 'mountain':
            factors['temperature'] = 'cold'
            factors['humidity'] = 'low'
        elif terrain == 'forest':
            factors['humidity'] = 'high'
            factors['food_availability'] = 'high'
        
        # Calculate predation pressure
        factors['predation'] = 'high' if animal.predator_pressure > 0.6 else 'low'
        
        # Calculate competition based on population
        species_pop = len([a for a in self.animals if a.name == animal.name])
        factors['competition'] = 'high' if species_pop > self.population_caps[animal.name] * 0.8 else 'low'
        
        return factors

    def _calculate_adaptive_mutation_rates(self, species: str, stats: Dict, env_factors: Dict, pop_factors: Dict) -> Dict:
        """Calculate mutation rates adapted to current conditions."""
        rates = self.base_mutation_rates.copy()
        
        # Apply population factor
        base_modifier = pop_factors['mutation_rate']
        
        # Apply environmental pressure modifications
        for factor, value in env_factors.items():
            modifier = self.environment_factors[factor].get(value, 0)
            base_modifier *= (1 + abs(modifier) * 0.1)
        
        # Apply specific trait modifications based on environmental needs
        for trait, rate in rates.items():
            # Get trait weights for current conditions
            weights = self.trait_weights[trait]
            
            # Calculate environmental need for this trait
            env_need = sum(
                weights.get(category, 0) * self.environment_factors[factor].get(value, 0)
                for factor, value in env_factors.items()
                for category in ['combat', 'survival']
            )
            
            # Modify rate based on need
            rates[trait] = rate * base_modifier * (1 + env_need)
        
        return rates

    def _perform_enhanced_crossover(self, genome1: Genome, genome2: Genome, mutation_rates: Dict, env_factors: Dict) -> Genome:
        """Perform enhanced crossover with environmental adaptation."""
        child_genes = {}
        
        for gene_name in genome1.genes:
            if gene_name not in genome2.genes:
                child_genes[gene_name] = genome1.genes[gene_name].copy()
                continue
            
            # Calculate environmental preference for each parent's gene
            parent1_fitness = self._calculate_gene_fitness(genome1.genes[gene_name], env_factors)
            parent2_fitness = self._calculate_gene_fitness(genome2.genes[gene_name], env_factors)
            
            # Select gene based on fitness
            if parent1_fitness > parent2_fitness:
                selected_gene = genome1.genes[gene_name]
                fitness_ratio = parent1_fitness / (parent1_fitness + parent2_fitness)
            else:
                selected_gene = genome2.genes[gene_name]
                fitness_ratio = parent2_fitness / (parent1_fitness + parent2_fitness)
            
            # Create child gene with potential mutation
            child_gene = selected_gene.copy()
            
            # Apply mutation with adaptive rate
            if random.random() < mutation_rates[gene_name]:
                mutation_range = 0.2 * (1 - fitness_ratio)  # Lower fitness allows bigger mutations
                mutation = random.uniform(-mutation_range, mutation_range)
                child_gene.value = max(0.1, min(2.0, child_gene.value * (1 + mutation)))
            
            child_genes[gene_name] = child_gene
        
        return Genome(child_genes)

    def _calculate_gene_fitness(self, gene: Gene, env_factors: Dict) -> float:
        """Calculate how well a gene's value fits current environmental conditions."""
        fitness = 1.0
        weights = self.trait_weights.get(gene.name, {})
        
        for factor, value in env_factors.items():
            factor_impact = self.environment_factors[factor].get(value, 0)
            
            # Apply impact based on trait weights
            if factor_impact > 0:  # Positive pressure
                if 'combat' in weights and factor in ['predation', 'competition']:
                    fitness *= 1 + (factor_impact * weights['combat'] * gene.value)
                if 'survival' in weights and factor in ['temperature', 'humidity', 'food_availability']:
                    fitness *= 1 + (factor_impact * weights['survival'] * gene.value)
            else:  # Negative pressure
                if 'combat' in weights and factor in ['predation', 'competition']:
                    fitness *= 1 + (abs(factor_impact) * weights['combat'] * (2 - gene.value))
                if 'survival' in weights and factor in ['temperature', 'humidity', 'food_availability']:
                    fitness *= 1 + (abs(factor_impact) * weights['survival'] * (2 - gene.value))
        
        return fitness

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