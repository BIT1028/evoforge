"""意识模拟模块 - EvoForge 思想和意识产生系统

本模块实现了程序意识和思想产生的核心功能:
- 生物学模拟: 基因表达、转录翻译、蛋白质合成
- 意识模拟: 自我认知、目标设定、情感状态
- 元进化: 进化策略的自我改进和优化
- 智能行为: 学习、适应、决策和行为涌现
- 虚拟世界: 复杂环境交互和任务系统

这些模块协同工作，使程序能够:
1. 从简单的代码进化出复杂的思维模式
2. 具备自我意识和目标导向行为
3. 在复杂环境中学习和适应
4. 产生创新性的解决方案
5. 展现类似生物的智能行为
"""

from .biology import (
    Gene, mRNA, Protein,
    Transcriber, Translator, AminoAcidRegistry
)

from .consciousness import (
    HormoneType, ProteinType, CellState,
    Gene, mRNA, Protein, DigitalCell, VirtualWorld
)

from .meta_evolution import (
    EvolutionStrategy, OptimizationObjective,
    EvolutionParameters, StrategyConfiguration,
    PerformanceAnalyzer, StrategyEvolution, MetaEvolutionEngine
)

from .intelligent_behavior import (
    BehaviorType, DecisionContext, LearningMode,
    Action, BehaviorPattern, DecisionMaking,
    LearningSystem, AdaptationEngine, IntelligentAgent
)

from .virtual_world import (
    EnvironmentType, TaskType, ResourceType, InteractionType,
    Position, Resource, Entity, Task,
    ResourceManager, EnvironmentDynamics, InteractionEngine, VirtualWorld
)

__all__ = [
    # 生物学模拟
    'Gene', 'mRNA', 'Protein',
    'Transcriber', 'Translator', 'AminoAcidRegistry',
    
    # 意识模拟
    'HormoneType', 'ProteinType', 'CellState',
    'Gene', 'mRNA', 'Protein', 'DigitalCell', 'VirtualWorld',
    
    # 元进化
    'EvolutionStrategy', 'OptimizationObjective',
    'EvolutionParameters', 'StrategyConfiguration',
    'PerformanceAnalyzer', 'StrategyEvolution', 'MetaEvolutionEngine',
    
    # 智能行为
    'BehaviorType', 'DecisionContext', 'LearningMode',
    'Action', 'BehaviorPattern', 'DecisionMaking',
    'LearningSystem', 'AdaptationEngine', 'IntelligentAgent',
    
    # 虚拟世界
    'EnvironmentType', 'TaskType', 'ResourceType', 'InteractionType',
    'Position', 'Resource', 'Entity', 'Task',
    'ResourceManager', 'EnvironmentDynamics', 'InteractionEngine', 'VirtualWorld'
]