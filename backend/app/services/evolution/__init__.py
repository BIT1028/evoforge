"""EvoForge进化算法核心模块

本模块包含了遗传算法的核心组件:
- genome: 基因表示和代码生成
- operators: 遗传算子(变异和交叉)
- selection: 选择算法(NSGA-II等)
- distance: 距离度量算法
"""

# 基因表示
from .genome import (
    NodeType,
    OperatorType,
    GeneNode,
    Genome,
    GenomeGenerator,
    create_random_genome,
    create_genome_from_code
)

# 遗传算子
from .operators import (
    MutationType,
    CrossoverType,
    MutationConfig,
    CrossoverConfig,
    GeneticOperators
)

# 选择算法
from .selection import (
    Individual,
    SelectionConfig,
    NSGA2Selector,
    TournamentSelector,
    FitnessSharingSelector,
    SelectionManager
)

# 距离度量
from .distance import (
    DistanceType,
    DistanceConfig,
    ASTDistanceCalculator,
    CodeDistanceCalculator,
    BehavioralDistanceCalculator,
    StructuralDistanceCalculator,
    DistanceManager,
    calculate_genome_distance,
    calculate_population_diversity
)

__all__ = [
    # 基因表示
    "NodeType",
    "OperatorType", 
    "GeneNode",
    "Genome",
    "GenomeGenerator",
    "create_random_genome",
    "create_genome_from_code",
    
    # 遗传算子
    "MutationType",
    "CrossoverType",
    "MutationConfig",
    "CrossoverConfig",
    "GeneticOperators",
    
    # 选择算法
    "Individual",
    "SelectionConfig",
    "NSGA2Selector",
    "TournamentSelector",
    "FitnessSharingSelector",
    "SelectionManager",
    
    # 距离度量
    "DistanceType",
    "DistanceConfig",
    "ASTDistanceCalculator",
    "CodeDistanceCalculator",
    "BehavioralDistanceCalculator",
    "StructuralDistanceCalculator",
    "DistanceManager",
    "calculate_genome_distance",
    "calculate_population_diversity",
]

# 版本信息
__version__ = "0.1.0"
__author__ = "EvoForge Team"
__description__ = "Advanced genetic algorithm components for code evolution"