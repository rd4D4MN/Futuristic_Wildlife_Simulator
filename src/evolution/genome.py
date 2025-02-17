import random
from dataclasses import dataclass
from typing import Dict

@dataclass
class Gene:
    """Represents a single gene with value and mutation probability."""
    name: str
    value: float
    mutation_rate: float = 0.1
    mutation_range: float = 0.2

    def mutate(self) -> float:
        """Attempt mutation of the gene."""
        if random.random() < self.mutation_rate:
            # Apply random mutation within range
            change = random.uniform(-self.mutation_range, self.mutation_range)
            return max(0, self.value * (1 + change))
        return self.value

@dataclass
class Genome:
    """Collection of genes that define an animal's traits."""
    genes: Dict[str, Gene]
    
    def __init__(self, genes: Dict[str, 'Gene']):
        self.genes = genes

    def mutate(self) -> 'Genome':
        """Apply mutations to genes."""
        for gene in self.genes.values():
            gene.mutate()
        return self
    
    def crossover(self, other: 'Genome') -> 'Genome':
        """Perform crossover between two genomes with safety checks."""
        if not isinstance(other, Genome):
            raise ValueError("Cannot crossover with non-Genome object")
            
        if not self.genes or not other.genes:
            raise ValueError("Cannot crossover with empty genes")
            
        child_genes = {}
        for gene_name in self.genes:
            if gene_name not in other.genes:
                # Use this genome's gene if other doesn't have it
                child_genes[gene_name] = self.genes[gene_name].copy()
                continue
                
            # Perform crossover between matching genes
            if random.random() < 0.5:
                child_genes[gene_name] = self.genes[gene_name].copy()
            else:
                child_genes[gene_name] = other.genes[gene_name].copy()
                
        return Genome(child_genes) 