import numpy as np
from typing import List, Dict, Optional, Any, Set, Tuple
from .macro_molecule import MacroMolecule, MoleculeType, BindingSite
from .code_primitives import SyntaxTokenMolecule, VariableMolecule, ASTNodeMolecule
from .organelles import ASTAssembler, CodeOptimizer, CompilerRunner
import uuid
import time
from dataclasses import dataclass

@dataclass
class CellularMemory:
    """细胞记忆结构
    
    存储细胞的历史信息和学习经验
    """
    successful_patterns: List[Dict[str, Any]]  # 成功的代码模式
    failed_patterns: List[Dict[str, Any]]      # 失败的代码模式
    energy_history: List[float]               # 能量历史
    generation_count: int                     # 代数
    mutation_history: List[Dict[str, Any]]    # 突变历史
    learning_rate: float = 0.1                # 学习率

class CellMembrane:
    """增强的细胞膜 - 智能控制分子进出
    
    细胞膜负责选择性地允许分子进入和离开细胞，
    维持细胞内环境的稳定性，支持动态调节和学习机制。
    """
    
    def __init__(self, permeability: float = 0.7, selectivity: float = 0.8):
        """
        初始化增强的细胞膜
        
        Args:
            permeability: 通透性 (0-1)
            selectivity: 选择性 (0-1)
        """
        self.permeability = permeability
        self.selectivity = selectivity
        
        # 基础传输通道
        self.transport_channels = {
            MoleculeType.SYNTAX_TOKEN: 0.9,
            MoleculeType.VARIABLE: 0.8,
            MoleculeType.AST_NODE: 0.7,
            MoleculeType.MRNA: 0.6,
            MoleculeType.PROTEIN: 0.5,
            MoleculeType.ENERGY_TOKEN: 1.0
        }
        
        # 智能调节机制
        self.adaptive_channels = {}  # 自适应通道
        self.molecular_memory = {}   # 分子记忆
        self.stress_response = {}    # 应激反应
        self.blocked_molecules: Set[str] = set()
        
        # 膜电位和离子梯度
        self.membrane_potential = -70.0  # mV
        self.ion_gradients = {
            'Na+': {'inside': 10, 'outside': 140},
            'K+': {'inside': 140, 'outside': 5},
            'Ca2+': {'inside': 0.1, 'outside': 2.5},
            'Cl-': {'inside': 10, 'outside': 110}
        }
        
        # 膜蛋白和受体
        self.membrane_proteins = {
            'sodium_potassium_pump': {'activity': 1.0, 'efficiency': 0.8},
            'calcium_channel': {'activity': 0.5, 'sensitivity': 0.7},
            'glucose_transporter': {'activity': 0.9, 'saturation': 0.3}
        }
        
        # 信号传导受体
        self.signal_receptors = {
            'growth_factor': {'sensitivity': 0.8, 'bound_ligands': []},
            'stress_signal': {'sensitivity': 0.6, 'bound_ligands': []},
            'nutrient_sensor': {'sensitivity': 0.9, 'bound_ligands': []}
        }
        
        # 膜流动性和完整性
        self.membrane_fluidity = 0.7
        self.membrane_integrity = 1.0
        self.lipid_composition = {
            'phospholipids': 0.6,
            'cholesterol': 0.3,
            'proteins': 0.1
        }
    
    def can_enter(self, molecule: MacroMolecule) -> bool:
        """智能判断分子是否可以进入细胞
        
        Args:
            molecule: 要检查的分子
            
        Returns:
            bool: 是否可以进入
        """
        if molecule.id in self.blocked_molecules:
            return False
        
        # 基础通透性计算
        base_probability = self._calculate_base_permeability(molecule)
        
        # 自适应调节
        adaptive_factor = self._get_adaptive_factor(molecule)
        
        # 膜电位影响
        electrical_factor = self._calculate_electrical_factor(molecule)
        
        # 膜蛋白介导的转运
        protein_factor = self._calculate_protein_mediated_transport(molecule)
        
        # 应激反应调节
        stress_factor = self._get_stress_response_factor(molecule)
        
        # 综合概率
        entry_probability = (base_probability * adaptive_factor * 
                           electrical_factor * protein_factor * stress_factor)
        
        # 记录分子进入历史
        self._record_molecular_interaction(molecule, 'entry_attempt', entry_probability)
        
        return np.random.random() < entry_probability
    
    def _calculate_base_permeability(self, molecule: MacroMolecule) -> float:
        """计算基础通透性"""
        # 基于分子类型的通透性
        type_permeability = self.transport_channels.get(molecule.type, 0.1)
        
        # 基于分子大小的限制
        size_factor = 1.0 / (1.0 + molecule.radius * 0.1)
        
        # 基于分子稳定性的选择
        stability_factor = molecule.stability / max(molecule.max_stability, 1.0)
        
        # 膜流动性影响
        fluidity_factor = 0.5 + 0.5 * self.membrane_fluidity
        
        return (type_permeability * self.permeability * 
                size_factor * stability_factor * fluidity_factor * self.selectivity)
    
    def _get_adaptive_factor(self, molecule: MacroMolecule) -> float:
        """获取自适应调节因子"""
        mol_type_key = molecule.type.value if hasattr(molecule.type, 'value') else str(molecule.type)
        
        if mol_type_key in self.adaptive_channels:
            channel_data = self.adaptive_channels[mol_type_key]
            # 基于历史成功率调节
            success_rate = channel_data.get('success_rate', 0.5)
            adaptation = 0.8 + 0.4 * success_rate  # 0.8-1.2范围
            return adaptation
        
        return 1.0
    
    def _calculate_electrical_factor(self, molecule: MacroMolecule) -> float:
        """计算膜电位对分子转运的影响"""
        # 假设分子带电性基于其类型
        charge_map = {
            MoleculeType.ENERGY_TOKEN: 1,   # 正电荷
            MoleculeType.MRNA: -1,          # 负电荷
            MoleculeType.PROTEIN: 0,        # 中性
            MoleculeType.SYNTAX_TOKEN: 0,   # 中性
            MoleculeType.VARIABLE: 0,       # 中性
            MoleculeType.AST_NODE: 0        # 中性
        }
        
        charge = charge_map.get(molecule.type, 0)
        
        if charge == 0:
            return 1.0  # 中性分子不受膜电位影响
        
        # 计算电化学梯度影响
        potential_factor = 1.0 + (charge * self.membrane_potential * 0.001)
        return max(0.1, min(2.0, potential_factor))
    
    def _calculate_protein_mediated_transport(self, molecule: MacroMolecule) -> float:
        """计算膜蛋白介导的转运"""
        transport_factor = 1.0
        
        # 能量分子通过葡萄糖转运蛋白
        if molecule.type == MoleculeType.ENERGY_TOKEN:
            transporter = self.membrane_proteins.get('glucose_transporter', {})
            activity = transporter.get('activity', 0.5)
            saturation = transporter.get('saturation', 0.5)
            transport_factor *= (1.0 + activity * (1.0 - saturation))
        
        # 钙离子通道影响蛋白质转运
        elif molecule.type == MoleculeType.PROTEIN:
            channel = self.membrane_proteins.get('calcium_channel', {})
            activity = channel.get('activity', 0.5)
            transport_factor *= (0.8 + 0.4 * activity)
        
        return transport_factor
    
    def _get_stress_response_factor(self, molecule: MacroMolecule) -> float:
        """获取应激反应调节因子"""
        mol_type_key = molecule.type.value if hasattr(molecule.type, 'value') else str(molecule.type)
        
        if mol_type_key in self.stress_response:
            stress_data = self.stress_response[mol_type_key]
            stress_level = stress_data.get('level', 0.0)
            
            # 应激状态下调节通透性
            if stress_level > 0.7:  # 高应激
                return 0.5  # 降低通透性
            elif stress_level > 0.3:  # 中等应激
                return 0.8
            else:  # 低应激
                return 1.2  # 提高通透性
        
        return 1.0
    
    def _record_molecular_interaction(self, molecule: MacroMolecule, interaction_type: str, probability: float):
        """记录分子相互作用历史"""
        mol_id = molecule.id
        
        if mol_id not in self.molecular_memory:
            self.molecular_memory[mol_id] = {
                'interactions': [],
                'success_count': 0,
                'total_count': 0
            }
        
        memory = self.molecular_memory[mol_id]
        memory['interactions'].append({
            'type': interaction_type,
            'probability': probability,
            'timestamp': time.time()
        })
        
        # 限制记忆大小
        if len(memory['interactions']) > 100:
            memory['interactions'] = memory['interactions'][-50:]
        
        memory['total_count'] += 1
    
    def can_exit(self, molecule: MacroMolecule) -> bool:
        """判断分子是否可以离开细胞
        
        Args:
            molecule: 要检查的分子
            
        Returns:
            bool: 是否可以离开
        """
        # 产物分子更容易离开
        if molecule.type in [MoleculeType.AST_NODE, MoleculeType.ENERGY_TOKEN]:
            return np.random.random() < 0.9
        
        # 其他分子根据通透性决定
        return np.random.random() < self.permeability * 0.5
    
    def block_molecule(self, molecule_id: str):
        """阻止特定分子进入
        
        Args:
            molecule_id: 分子ID
        """
        self.blocked_molecules.add(molecule_id)
    
    def unblock_molecule(self, molecule_id: str):
        """解除对特定分子的阻止
        
        Args:
            molecule_id: 分子ID
        """
        self.blocked_molecules.discard(molecule_id)
    
    def receive_signal(self, signal_type: str, signal_strength: float, ligand_data: Dict[str, Any] = None):
        """接收外部信号
        
        Args:
            signal_type: 信号类型
            signal_strength: 信号强度
            ligand_data: 配体数据
        """
        if signal_type in self.signal_receptors:
            receptor = self.signal_receptors[signal_type]
            sensitivity = receptor['sensitivity']
            
            # 检查信号是否足够强以激活受体
            if signal_strength >= sensitivity:
                # 绑定配体
                if ligand_data:
                    receptor['bound_ligands'].append({
                        'data': ligand_data,
                        'strength': signal_strength,
                        'timestamp': time.time()
                    })
                
                # 触发信号传导级联
                self._trigger_signal_cascade(signal_type, signal_strength)
    
    def _trigger_signal_cascade(self, signal_type: str, signal_strength: float):
        """触发信号传导级联反应"""
        if signal_type == 'growth_factor':
            # 生长因子信号：增加通透性和膜蛋白活性
            self.permeability = min(1.0, self.permeability * (1.0 + signal_strength * 0.1))
            for protein_name, protein_data in self.membrane_proteins.items():
                protein_data['activity'] = min(1.0, protein_data['activity'] * (1.0 + signal_strength * 0.05))
        
        elif signal_type == 'stress_signal':
            # 应激信号：激活应激反应
            for mol_type in self.transport_channels.keys():
                mol_type_key = mol_type.value if hasattr(mol_type, 'value') else str(mol_type)
                self.stress_response[mol_type_key] = {
                    'level': signal_strength,
                    'timestamp': time.time()
                }
        
        elif signal_type == 'nutrient_sensor':
            # 营养感受信号：调节转运蛋白
            if 'glucose_transporter' in self.membrane_proteins:
                transporter = self.membrane_proteins['glucose_transporter']
                transporter['activity'] = min(1.0, transporter['activity'] + signal_strength * 0.2)
                transporter['saturation'] = max(0.0, transporter['saturation'] - signal_strength * 0.1)
    
    def update_membrane_dynamics(self, dt: float, cellular_energy: float, cellular_health: float):
        """更新膜动态特性
        
        Args:
            dt: 时间步长
            cellular_energy: 细胞能量水平
            cellular_health: 细胞健康状态
        """
        # 基于能量水平调节膜蛋白活性
        energy_factor = cellular_energy / 100.0  # 假设最大能量为100
        
        for protein_name, protein_data in self.membrane_proteins.items():
            # 能量不足时降低蛋白活性
            if energy_factor < 0.3:
                protein_data['activity'] *= 0.95
            elif energy_factor > 0.8:
                protein_data['activity'] = min(1.0, protein_data['activity'] * 1.01)
        
        # 基于健康状态调节膜完整性
        if cellular_health < 0.5:
            self.membrane_integrity *= 0.99
            self.membrane_fluidity *= 0.98
        elif cellular_health > 0.8:
            self.membrane_integrity = min(1.0, self.membrane_integrity * 1.001)
            self.membrane_fluidity = min(1.0, self.membrane_fluidity * 1.002)
        
        # 更新自适应通道
        self._update_adaptive_channels()
        
        # 清理过期的信号受体配体
        self._cleanup_receptor_ligands()
    
    def _update_adaptive_channels(self):
        """更新自适应通道"""
        for mol_id, memory in self.molecular_memory.items():
            if memory['total_count'] > 10:  # 有足够的历史数据
                success_rate = memory['success_count'] / memory['total_count']
                
                # 根据成功率调整通道
                # 这里需要从分子ID推断分子类型，简化处理
                for mol_type in self.transport_channels.keys():
                    mol_type_key = mol_type.value if hasattr(mol_type, 'value') else str(mol_type)
                    
                    if mol_type_key not in self.adaptive_channels:
                        self.adaptive_channels[mol_type_key] = {
                            'success_rate': success_rate,
                            'adjustment_factor': 1.0
                        }
                    else:
                        # 平滑更新成功率
                        current_rate = self.adaptive_channels[mol_type_key]['success_rate']
                        self.adaptive_channels[mol_type_key]['success_rate'] = \
                            0.9 * current_rate + 0.1 * success_rate
    
    def _cleanup_receptor_ligands(self):
        """清理过期的受体配体"""
        current_time = time.time()
        ligand_lifetime = 60.0  # 60秒生命周期
        
        for receptor_name, receptor_data in self.signal_receptors.items():
            receptor_data['bound_ligands'] = [
                ligand for ligand in receptor_data['bound_ligands']
                if current_time - ligand['timestamp'] < ligand_lifetime
            ]
    
    def get_membrane_status(self) -> Dict[str, Any]:
        """获取膜状态信息"""
        return {
            'permeability': self.permeability,
            'selectivity': self.selectivity,
            'membrane_potential': self.membrane_potential,
            'membrane_integrity': self.membrane_integrity,
            'membrane_fluidity': self.membrane_fluidity,
            'transport_channels': self.transport_channels.copy(),
            'membrane_proteins': {k: v.copy() for k, v in self.membrane_proteins.items()},
            'signal_receptors': {k: {'sensitivity': v['sensitivity'], 
                                   'bound_ligands_count': len(v['bound_ligands'])} 
                               for k, v in self.signal_receptors.items()},
            'adaptive_channels': self.adaptive_channels.copy(),
            'stress_response': self.stress_response.copy(),
            'blocked_molecules_count': len(self.blocked_molecules),
            'molecular_memory_count': len(self.molecular_memory)
        }

class CellNucleus:
    """增强的细胞核 - 智能基因转录和调控中心
    
    细胞核包含细胞的"基因组"（代码生成模板），
    负责转录mRNA和管理细胞的遗传表达，支持动态调控和表观遗传修饰。
    """
    
    def __init__(self, genome_template: Dict[str, Any]):
        """
        初始化增强的细胞核
        
        Args:
            genome_template: 基因组模板
        """
        self.genome_template = genome_template
        self.active_genes = set()
        self.transcription_rate = 0.1
        self.mrna_pool: List[MacroMolecule] = []
        self.transcription_count = 0
        
        # 转录调控机制
        self.transcription_factors = {}  # 转录因子
        self.chromatin_state = {}        # 染色质状态
        self.epigenetic_marks = {}       # 表观遗传标记
        self.gene_expression_levels = {} # 基因表达水平
        
        # 转录机器
        self.rna_polymerase = {
            'activity': 1.0,
            'processivity': 0.8,
            'fidelity': 0.95
        }
        
        # 核质转运
        self.nuclear_pores = {
            'count': 100,
            'transport_rate': 0.9,
            'selectivity': 0.8
        }
        
        # 基因调控网络
        self.regulatory_network = {}
        self.feedback_loops = []
        
        # 初始化基因调控状态
        self._initialize_gene_regulation()
    
    def _initialize_gene_regulation(self):
        """初始化基因调控状态"""
        for gene_name in self.genome_template.keys():
            # 初始化染色质状态
            self.chromatin_state[gene_name] = {
                'accessibility': 0.7,  # 染色质可及性
                'compaction': 0.3,     # 压缩程度
                'histone_modifications': []  # 组蛋白修饰
            }
            
            # 初始化表观遗传标记
            self.epigenetic_marks[gene_name] = {
                'methylation': 0.1,    # DNA甲基化
                'acetylation': 0.6,    # 组蛋白乙酰化
                'ubiquitination': 0.2  # 泛素化
            }
            
            # 初始化基因表达水平
            self.gene_expression_levels[gene_name] = 0.5
            
            # 初始化调控网络
            self.regulatory_network[gene_name] = {
                'activators': [],
                'repressors': [],
                'enhancers': [],
                'silencers': []
            }
    
    def transcribe_gene(self, gene_name: str, position: np.ndarray) -> Optional[MacroMolecule]:
        """智能转录基因为mRNA
        
        Args:
            gene_name: 基因名称
            position: mRNA生成位置
            
        Returns:
            Optional[MacroMolecule]: 生成的mRNA分子
        """
        if gene_name not in self.genome_template:
            return None
        
        # 检查转录可行性
        if not self._can_transcribe(gene_name):
            return None
        
        # 计算转录效率
        transcription_efficiency = self._calculate_transcription_efficiency(gene_name)
        
        # 基于效率决定是否转录
        if np.random.random() > transcription_efficiency:
            return None
        
        gene_data = self.genome_template[gene_name]
        
        # 创建增强的mRNA分子
        mrna = self._create_enhanced_mrna(gene_name, gene_data, position)
        
        # 更新转录统计
        self._update_transcription_stats(gene_name)
        
        # 应用转录后调控
        self._apply_post_transcriptional_regulation(mrna, gene_name)
        
        self.mrna_pool.append(mrna)
        self.transcription_count += 1
        
        return mrna
    
    def _can_transcribe(self, gene_name: str) -> bool:
        """检查基因是否可以转录"""
        # 检查染色质可及性
        chromatin = self.chromatin_state.get(gene_name, {})
        accessibility = chromatin.get('accessibility', 0.5)
        
        # 检查表观遗传抑制
        epigenetic = self.epigenetic_marks.get(gene_name, {})
        methylation = epigenetic.get('methylation', 0.0)
        
        # 高甲基化抑制转录
        if methylation > 0.7:
            return False
        
        # 低可及性抑制转录
        if accessibility < 0.3:
            return False
        
        return True
    
    def _calculate_transcription_efficiency(self, gene_name: str) -> float:
        """计算转录效率"""
        base_efficiency = self.transcription_rate
        
        # 染色质状态影响
        chromatin = self.chromatin_state.get(gene_name, {})
        accessibility_factor = chromatin.get('accessibility', 0.5)
        
        # 表观遗传修饰影响
        epigenetic = self.epigenetic_marks.get(gene_name, {})
        acetylation_factor = 1.0 + epigenetic.get('acetylation', 0.0) * 0.5
        methylation_factor = 1.0 - epigenetic.get('methylation', 0.0) * 0.8
        
        # 转录因子影响
        tf_factor = self._calculate_transcription_factor_effect(gene_name)
        
        # RNA聚合酶活性
        polymerase_factor = self.rna_polymerase['activity']
        
        # 基因表达水平反馈
        expression_level = self.gene_expression_levels.get(gene_name, 0.5)
        feedback_factor = 1.0 - expression_level * 0.3  # 负反馈
        
        efficiency = (base_efficiency * accessibility_factor * 
                     acetylation_factor * methylation_factor * 
                     tf_factor * polymerase_factor * feedback_factor)
        
        return min(1.0, max(0.0, efficiency))
    
    def _calculate_transcription_factor_effect(self, gene_name: str) -> float:
        """计算转录因子效应"""
        if gene_name not in self.regulatory_network:
            return 1.0
        
        network = self.regulatory_network[gene_name]
        
        # 激活因子效应
        activator_effect = 1.0
        for activator in network['activators']:
            if activator in self.transcription_factors:
                tf_data = self.transcription_factors[activator]
                activator_effect *= (1.0 + tf_data.get('strength', 0.5) * 0.5)
        
        # 抑制因子效应
        repressor_effect = 1.0
        for repressor in network['repressors']:
            if repressor in self.transcription_factors:
                tf_data = self.transcription_factors[repressor]
                repressor_effect *= (1.0 - tf_data.get('strength', 0.5) * 0.5)
        
        return activator_effect * repressor_effect
    
    def _create_enhanced_mrna(self, gene_name: str, gene_data: Dict[str, Any], position: np.ndarray) -> MacroMolecule:
        """创建增强的mRNA分子"""
        # 基础mRNA创建
        mrna = MacroMolecule(
            mol_type=MoleculeType.MRNA,
            position=position,
            binding_sites={
                'ribosome_binding': BindingSite(shape_id='mrna_ribosome', binding_strength=1.0),
                'degradation_protection': BindingSite(shape_id='mrna_protection', binding_strength=0.8)
            },
            data={
                'gene_name': gene_name,
                'instructions': gene_data.get('instructions', []),
                'stability_modifier': gene_data.get('stability', 1.0),
                'expression_level': self.gene_expression_levels.get(gene_name, 0.5),
                'transcription_timestamp': time.time()
            }
        )
        
        # 基于转录质量设置稳定性
        fidelity = self.rna_polymerase['fidelity']
        base_stability = 100.0 * gene_data.get('stability', 1.0)
        mrna.stability = base_stability * fidelity
        mrna.max_stability = mrna.stability
        
        return mrna
    
    def _update_transcription_stats(self, gene_name: str):
        """更新转录统计信息"""
        # 更新基因表达水平
        current_level = self.gene_expression_levels.get(gene_name, 0.5)
        self.gene_expression_levels[gene_name] = min(1.0, current_level + 0.1)
        
        # 更新染色质状态（转录激活导致染色质开放）
        if gene_name in self.chromatin_state:
            chromatin = self.chromatin_state[gene_name]
            chromatin['accessibility'] = min(1.0, chromatin['accessibility'] + 0.05)
            chromatin['compaction'] = max(0.0, chromatin['compaction'] - 0.02)
    
    def _apply_post_transcriptional_regulation(self, mrna: MacroMolecule, gene_name: str):
        """应用转录后调控"""
        # 添加5'帽子和3'多聚A尾
        mrna.data['has_5_cap'] = True
        mrna.data['poly_a_tail_length'] = np.random.randint(50, 200)
        
        # 基于基因类型添加调控元件
        if 'regulatory' in gene_name.lower():
            mrna.data['regulatory_elements'] = ['enhancer', 'silencer']
        elif 'structural' in gene_name.lower():
            mrna.data['regulatory_elements'] = ['stability_element']
        
        # 添加microRNA结合位点（简化模拟）
        if np.random.random() < 0.3:
            mrna.data['mirna_binding_sites'] = [f'mir_{np.random.randint(1, 100)}']
    
    def activate_gene(self, gene_name: str, activation_strength: float = 0.5):
        """激活基因表达
        
        Args:
            gene_name: 要激活的基因名称
            activation_strength: 激活强度 (0.0-1.0)
        """
        self.active_genes.add(gene_name)
        
        if gene_name in self.genome_template:
            # 更新基因表达水平
            current_level = self.gene_expression_levels.get(gene_name, 0.5)
            new_level = min(1.0, current_level + activation_strength * 0.3)
            self.gene_expression_levels[gene_name] = new_level
            
            # 更新染色质状态
            if gene_name not in self.chromatin_state:
                self.chromatin_state[gene_name] = {
                    'accessibility': 0.5,
                    'compaction': 0.5,
                    'histone_modifications': {}
                }
            
            chromatin = self.chromatin_state[gene_name]
            chromatin['accessibility'] = min(1.0, chromatin['accessibility'] + activation_strength * 0.2)
            chromatin['compaction'] = max(0.0, chromatin['compaction'] - activation_strength * 0.1)
            
            # 更新表观遗传标记
            if gene_name not in self.epigenetic_marks:
                self.epigenetic_marks[gene_name] = {
                    'methylation': 0.0,
                    'acetylation': 0.0,
                    'ubiquitination': 0.0
                }
            
            epigenetic = self.epigenetic_marks[gene_name]
            epigenetic['acetylation'] = min(1.0, epigenetic['acetylation'] + activation_strength * 0.3)
            epigenetic['methylation'] = max(0.0, epigenetic['methylation'] - activation_strength * 0.2)
            
            # 触发调控网络级联
            self._trigger_regulatory_cascade(gene_name, 'activation', activation_strength)
    
    def deactivate_gene(self, gene_name: str, suppression_strength: float = 0.5):
        """抑制基因表达
        
        Args:
            gene_name: 要抑制的基因名称
            suppression_strength: 抑制强度 (0.0-1.0)
        """
        self.active_genes.discard(gene_name)
        
        if gene_name in self.genome_template:
            # 更新基因表达水平
            current_level = self.gene_expression_levels.get(gene_name, 0.5)
            new_level = max(0.0, current_level - suppression_strength * 0.3)
            self.gene_expression_levels[gene_name] = new_level
            
            # 更新染色质状态
            if gene_name not in self.chromatin_state:
                self.chromatin_state[gene_name] = {
                    'accessibility': 0.5,
                    'compaction': 0.5,
                    'histone_modifications': {}
                }
            
            chromatin = self.chromatin_state[gene_name]
            chromatin['accessibility'] = max(0.0, chromatin['accessibility'] - suppression_strength * 0.2)
            chromatin['compaction'] = min(1.0, chromatin['compaction'] + suppression_strength * 0.1)
            
            # 更新表观遗传标记
            if gene_name not in self.epigenetic_marks:
                self.epigenetic_marks[gene_name] = {
                    'methylation': 0.0,
                    'acetylation': 0.0,
                    'ubiquitination': 0.0
                }
            
            epigenetic = self.epigenetic_marks[gene_name]
            epigenetic['methylation'] = min(1.0, epigenetic['methylation'] + suppression_strength * 0.3)
            epigenetic['acetylation'] = max(0.0, epigenetic['acetylation'] - suppression_strength * 0.2)
            
            # 触发调控网络级联
            self._trigger_regulatory_cascade(gene_name, 'suppression', suppression_strength)
    
    def get_active_transcription(self, position: np.ndarray) -> List[MacroMolecule]:
        """获取当前活跃的转录产物
        
        Args:
            position: 转录位置
            
        Returns:
            List[MacroMolecule]: mRNA分子列表
        """
        new_mrnas = []
        
        for gene_name in self.active_genes:
            if np.random.random() < self.transcription_rate:
                mrna = self.transcribe_gene(gene_name, position)
                if mrna:
                    new_mrnas.append(mrna)
        
        return new_mrnas
    
    def mutate_genome(self, mutation_rate: float = 0.01):
        """基因组突变
        
        Args:
            mutation_rate: 突变率
        """
        try:
            # 尝试使用新的基因组系统
            from .genome import Genome, create_random_genome
            import json
            
            # 检查是否为新格式的基因组
            if isinstance(self.genome_template, dict) and 'root' in self.genome_template:
                # 新格式：使用基因组对象进行突变
                genome_obj = Genome.from_dict(self.genome_template)
                self._mutate_genome_nodes(genome_obj.root, mutation_rate)
                self.genome_template = genome_obj.to_dict()
            else:
                # 旧格式：使用原有的突变逻辑
                self._legacy_mutate_genome(mutation_rate)
                
        except ImportError:
            # 如果新的基因组系统不可用，使用旧的方法
            self._legacy_mutate_genome(mutation_rate)
    
    def _mutate_genome_nodes(self, node, mutation_rate: float):
        """递归变异基因组节点"""
        if np.random.random() < mutation_rate:
            # 变异当前节点的值
            if hasattr(node, 'node_type') and hasattr(node.node_type, 'value'):
                if node.node_type.value == 'constant' and isinstance(node.value, (int, float)):
                    node.value = int(node.value + np.random.normal(0, 10))
                elif node.node_type.value == 'name' and isinstance(node.value, str):
                    variables = ['x', 'y', 'z', 'data', 'result', 'temp', 'numbers']
                    node.value = np.random.choice(variables)
        
        # 递归处理子节点
        if hasattr(node, 'children'):
            for child in node.children:
                self._mutate_genome_nodes(child, mutation_rate)
    
    def _legacy_mutate_genome(self, mutation_rate: float):
        """旧格式的基因组突变"""
        for gene_name, gene_data in self.genome_template.items():
            if np.random.random() < mutation_rate:
                # 随机修改指令
                instructions = gene_data.get('instructions', [])
                if instructions:
                    idx = np.random.randint(len(instructions))
                    instruction = instructions[idx]
                    
                    # 随机修改指令参数
                    if 'value' in instruction:
                        instruction['value'] += np.random.normal(0, 0.1)
                    elif 'name' in instruction:
                        instruction['name'] = f"mutated_{instruction['name']}"
    
    def _trigger_regulatory_cascade(self, gene_name: str, regulation_type: str, strength: float):
        """触发基因调控级联反应"""
        if gene_name not in self.regulatory_network:
            return
        
        network = self.regulatory_network[gene_name]
        
        # 处理下游目标基因
        for target_gene in network.get('targets', []):
            if target_gene in self.genome_template:
                cascade_strength = strength * 0.5  # 级联强度衰减
                
                if regulation_type == 'activation':
                    # 激活下游基因
                    current_level = self.gene_expression_levels.get(target_gene, 0.5)
                    self.gene_expression_levels[target_gene] = min(1.0, current_level + cascade_strength * 0.2)
                else:
                    # 抑制下游基因
                    current_level = self.gene_expression_levels.get(target_gene, 0.5)
                    self.gene_expression_levels[target_gene] = max(0.0, current_level - cascade_strength * 0.2)
        
        # 检测并处理反馈回路
        self._process_feedback_loops(gene_name, regulation_type, strength)
    
    def _process_feedback_loops(self, gene_name: str, regulation_type: str, strength: float):
        """处理反馈回路"""
        for loop in self.feedback_loops:
            if gene_name in loop['genes']:
                loop_type = loop['type']
                loop_strength = loop['strength']
                
                if loop_type == 'positive':
                    # 正反馈：增强原始调控
                    feedback_factor = 1.0 + loop_strength * 0.3
                    if regulation_type == 'activation':
                        current_level = self.gene_expression_levels.get(gene_name, 0.5)
                        self.gene_expression_levels[gene_name] = min(1.0, current_level * feedback_factor)
                    else:
                        current_level = self.gene_expression_levels.get(gene_name, 0.5)
                        self.gene_expression_levels[gene_name] = max(0.0, current_level / feedback_factor)
                
                elif loop_type == 'negative':
                    # 负反馈：抑制原始调控
                    feedback_factor = 1.0 - loop_strength * 0.2
                    if regulation_type == 'activation':
                        current_level = self.gene_expression_levels.get(gene_name, 0.5)
                        self.gene_expression_levels[gene_name] = max(0.0, current_level * feedback_factor)
                    else:
                        current_level = self.gene_expression_levels.get(gene_name, 0.5)
                        self.gene_expression_levels[gene_name] = min(1.0, current_level / feedback_factor)
    
    def update_regulatory_network(self, cell_state: Dict[str, Any]):
        """基于细胞状态更新调控网络"""
        energy_level = cell_state.get('energy', 50.0) / 100.0
        health_level = cell_state.get('health', 100.0) / 100.0
        stress_level = cell_state.get('stress', 0.0)
        
        # 基于细胞状态调整转录因子活性
        for tf_name, tf_data in self.transcription_factors.items():
            base_activity = tf_data.get('base_activity', 0.5)
            
            # 能量影响转录因子活性
            energy_factor = 0.5 + energy_level * 0.5
            
            # 健康状态影响
            health_factor = 0.3 + health_level * 0.7
            
            # 应激反应
            stress_factor = 1.0 - stress_level * 0.3
            
            new_activity = base_activity * energy_factor * health_factor * stress_factor
            tf_data['activity'] = min(1.0, max(0.0, new_activity))
        
        # 更新RNA聚合酶活性
        self.rna_polymerase['activity'] = min(1.0, energy_level * health_level)
        self.rna_polymerase['fidelity'] = min(1.0, 0.7 + health_level * 0.3)
    
    def get_gene_regulation_status(self) -> Dict[str, Any]:
        """获取基因调控状态信息"""
        return {
            'gene_expression_levels': dict(self.gene_expression_levels),
            'chromatin_state': dict(self.chromatin_state),
            'epigenetic_marks': dict(self.epigenetic_marks),
            'transcription_factors': dict(self.transcription_factors),
            'rna_polymerase': dict(self.rna_polymerase),
            'regulatory_network': dict(self.regulatory_network),
            'feedback_loops': list(self.feedback_loops),
            'transcription_rate': self.transcription_rate,
            'transcription_count': self.transcription_count,
            'mrna_pool_size': len(self.mrna_pool)
        }

class Cytoplasm:
    """细胞质 - 细胞内的反应环境
    
    细胞质是细胞内分子反应的主要场所，
    包含各种细胞器和分子。
    """
    
    def __init__(self, volume: float = 1000.0):
        """
        初始化细胞质
        
        Args:
            volume: 细胞质体积
        """
        self.volume = volume
        self.molecules: List[MacroMolecule] = []
        self.organelles: Dict[str, MacroMolecule] = {}
        self.ph = 7.0
        self.temperature = 310.0  # 37°C in Kelvin
        self.ionic_strength = 0.15
    
    def add_molecule(self, molecule: MacroMolecule):
        """添加分子到细胞质
        
        Args:
            molecule: 要添加的分子
        """
        self.molecules.append(molecule)
    
    def remove_molecule(self, molecule: MacroMolecule):
        """从细胞质移除分子
        
        Args:
            molecule: 要移除的分子
        """
        if molecule in self.molecules:
            self.molecules.remove(molecule)
    
    def add_organelle(self, name: str, organelle: MacroMolecule):
        """添加细胞器
        
        Args:
            name: 细胞器名称
            organelle: 细胞器分子
        """
        self.organelles[name] = organelle
        self.add_molecule(organelle)
    
    def get_molecules_by_type(self, mol_type: MoleculeType) -> List[MacroMolecule]:
        """根据类型获取分子
        
        Args:
            mol_type: 分子类型
            
        Returns:
            List[MacroMolecule]: 指定类型的分子列表
        """
        return [mol for mol in self.molecules if mol.type == mol_type]
    
    def get_molecular_density(self) -> float:
        """获取分子密度
        
        Returns:
            float: 分子密度
        """
        return len(self.molecules) / self.volume
    
    def cleanup_degraded_molecules(self):
        """清理降解的分子"""
        self.molecules = [mol for mol in self.molecules if mol.stability > 0]

class DigitalCell:
    """数字细胞 - 完整的细胞模拟
    
    数字细胞是一个完整的生物细胞模拟，包含细胞膜、细胞核、
    细胞质等组件，能够进行代码生成、优化和执行。
    """
    
    def __init__(self, 
                 position: np.ndarray,
                 genome_template: Dict[str, Any],
                 cell_id: Optional[str] = None):
        """
        初始化数字细胞
        
        Args:
            position: 细胞在3D空间中的位置
            genome_template: 基因组模板
            cell_id: 细胞ID
        """
        self.id = cell_id or str(uuid.uuid4())
        self.position = position.copy()
        self.radius = 10.0
        self.age = 0
        self.energy = 100.0
        self.max_energy = 200.0
        self.health = 1.0
        self.division_threshold = 150.0
        
        # 细胞组件
        self.membrane = CellMembrane()
        self.nucleus = CellNucleus(genome_template)
        self.cytoplasm = Cytoplasm()
        
        # 细胞记忆
        self.memory = CellularMemory(
            successful_patterns=[],
            failed_patterns=[],
            energy_history=[],
            generation_count=0,
            mutation_history=[]
        )
        
        # 细胞间通信
        self.signal_receptors: Dict[str, Dict[str, Any]] = {
            'growth_factor': {'sensitivity': 0.8, 'threshold': 0.3},
            'stress_signal': {'sensitivity': 0.9, 'threshold': 0.2},
            'nutrient_signal': {'sensitivity': 0.7, 'threshold': 0.4},
            'death_signal': {'sensitivity': 0.6, 'threshold': 0.5}
        }
        
        self.signal_transmitters: Dict[str, float] = {
            'growth_factor': 0.0,
            'stress_signal': 0.0,
            'nutrient_signal': 0.0,
            'death_signal': 0.0
        }
        
        self.neighboring_cells: List['DigitalCell'] = []
        self.communication_range = 50.0
        
        # 协作状态
        self.cooperation_level = 0.5
        self.altruism_factor = 0.3
        self.competition_factor = 0.4

        # 生命周期状态
        self.lifecycle_stage = 'G1'  # G1, S, G2, M, death
        self.division_timer = 0
        self.death_timer = 0
        
        # 初始化细胞器
        self._initialize_organelles()
        
        # 激活基础基因
        self._activate_basic_genes()
    
    def _initialize_organelles(self):
        """初始化细胞器"""
        # 创建AST组装器（核糖体）
        ribosome_pos = self.position + np.random.randn(3) * 2
        ribosome = ASTAssembler(ribosome_pos)
        self.cytoplasm.add_organelle('ribosome', ribosome)
        
        # 创建代码优化器（高尔基体）
        golgi_pos = self.position + np.random.randn(3) * 2
        golgi = CodeOptimizer(golgi_pos)
        self.cytoplasm.add_organelle('golgi', golgi)
        
        # 创建编译器运行器（线粒体）
        mitochondria_pos = self.position + np.random.randn(3) * 2
        mitochondria = CompilerRunner(mitochondria_pos)
        self.cytoplasm.add_organelle('mitochondria', mitochondria)
    
    def _activate_basic_genes(self):
        """激活基础基因"""
        basic_genes = ['basic_function', 'variable_assignment', 'simple_expression']
        for gene in basic_genes:
            if gene in self.nucleus.genome_template:
                self.nucleus.activate_gene(gene)
    
    def update(self, dt: float, external_molecules: List[MacroMolecule] = None):
        """更新细胞状态
        
        Args:
            dt: 时间步长
            external_molecules: 外部分子列表
        """
        self.age += dt
        
        # 处理外部分子的进入
        if external_molecules:
            self._process_molecular_transport(external_molecules)
        
        # 转录过程
        self._transcription_process()
        
        # 翻译过程
        self._translation_process()
        
        # 细胞器功能
        self._organelle_functions()
        
        # 能量代谢
        self._energy_metabolism()
        
        # 分子降解
        self._molecular_degradation(dt)
        
        # 生命周期管理
        self._lifecycle_management(dt)
        
        # 健康状态更新
        self._update_health()
        
        # 细胞间信号传导
        self._process_intercellular_communication()
        
        # 更新基因调控网络
        cell_state = {
            'energy': self.energy,
            'health': self.health * 100.0,
            'stress': max(0.0, (100.0 - self.energy) / 100.0)
        }
        self.nucleus.update_regulatory_network(cell_state)
        
        # 更新膜动态
        self.membrane.update_membrane_dynamics(self.energy, self.health)
        
        # 记录历史
        self.memory.energy_history.append(self.energy)
        if len(self.memory.energy_history) > 100:
            self.memory.energy_history.pop(0)
    
    def _process_molecular_transport(self, external_molecules: List[MacroMolecule]):
        """处理分子运输
        
        Args:
            external_molecules: 外部分子列表
        """
        # 分子进入
        for molecule in external_molecules:
            if self._is_molecule_nearby(molecule) and self.membrane.can_enter(molecule):
                # 将分子移动到细胞内
                molecule.position = self.position + np.random.randn(3) * self.radius * 0.8
                self.cytoplasm.add_molecule(molecule)
        
        # 分子离开
        molecules_to_remove = []
        for molecule in self.cytoplasm.molecules:
            if self.membrane.can_exit(molecule):
                # 将分子移动到细胞外
                molecule.position = self.position + np.random.randn(3) * self.radius * 1.2
                molecules_to_remove.append(molecule)
        
        for molecule in molecules_to_remove:
            self.cytoplasm.remove_molecule(molecule)
    
    def _is_molecule_nearby(self, molecule: MacroMolecule) -> bool:
        """检查分子是否在细胞附近
        
        Args:
            molecule: 要检查的分子
            
        Returns:
            bool: 是否在附近
        """
        distance = np.linalg.norm(molecule.position - self.position)
        return distance <= (self.radius + molecule.radius + 2.0)
    
    def _transcription_process(self):
        """转录过程"""
        # 获取新的mRNA
        new_mrnas = self.nucleus.get_active_transcription(self.position)
        for mrna in new_mrnas:
            self.cytoplasm.add_molecule(mrna)
    
    def _translation_process(self):
        """翻译过程"""
        ribosome = self.cytoplasm.organelles.get('ribosome')
        if not ribosome:
            return
        
        # 寻找mRNA分子
        mrnas = self.cytoplasm.get_molecules_by_type(MoleculeType.MRNA)
        for mrna in mrnas:
            if not ribosome.is_bound_to(mrna):
                # 尝试结合mRNA
                if isinstance(ribosome, ASTAssembler):
                    ribosome.load_mrna(mrna)
    
    def _organelle_functions(self):
        """细胞器功能执行"""
        # 获取所有分子作为底物
        all_molecules = self.cytoplasm.molecules.copy()
        
        # 执行各个细胞器的催化功能
        for organelle_name, organelle in self.cytoplasm.organelles.items():
            if organelle.catalytic_logic:
                try:
                    products = organelle.catalytic_logic(all_molecules, organelle)
                    # 添加新产生的分子
                    for product in products:
                        if product not in all_molecules:
                            self.cytoplasm.add_molecule(product)
                except Exception as e:
                    print(f"细胞器 {organelle_name} 功能执行错误: {e}")
    
    def _energy_metabolism(self):
        """能量代谢"""
        # 基础代谢消耗
        base_consumption = 0.5
        self.energy -= base_consumption
        
        # 从能量令牌获取能量
        energy_tokens = self.cytoplasm.get_molecules_by_type(MoleculeType.ENERGY_TOKEN)
        for token in energy_tokens:
            energy_value = token.data.get('energy_value', 0)
            self.energy += energy_value
            self.cytoplasm.remove_molecule(token)
        
        # 限制能量范围
        self.energy = max(0, min(self.max_energy, self.energy))
    
    def _molecular_degradation(self, dt: float):
        """分子降解
        
        Args:
            dt: 时间步长
        """
        for molecule in self.cytoplasm.molecules:
            molecule.update_physics(dt)
            molecule.check_degradation()
        
        # 清理降解的分子
        self.cytoplasm.cleanup_degraded_molecules()
    
    def _lifecycle_management(self, dt: float):
        """生命周期管理
        
        Args:
            dt: 时间步长
        """
        if self.lifecycle_stage == 'G1':
            # 生长期
            if self.energy > self.division_threshold:
                self.lifecycle_stage = 'S'
        elif self.lifecycle_stage == 'S':
            # DNA复制期
            self.division_timer += dt
            if self.division_timer > 10.0:  # 10秒后进入G2期
                self.lifecycle_stage = 'G2'
        elif self.lifecycle_stage == 'G2':
            # 准备分裂期
            self.division_timer += dt
            if self.division_timer > 15.0:  # 15秒后进入M期
                self.lifecycle_stage = 'M'
        elif self.lifecycle_stage == 'M':
            # 分裂期 - 准备分裂
            pass
        
        # 死亡检查
        if self.energy <= 0 or self.health <= 0:
            self.lifecycle_stage = 'death'
            self.death_timer += dt
    
    def _update_health(self):
        """更新健康状态"""
        # 基于能量水平的健康
        energy_factor = self.energy / self.max_energy
        
        # 基于分子密度的健康
        density = self.cytoplasm.get_molecular_density()
        density_factor = 1.0 / (1.0 + density * 0.01)
        
        # 基于年龄的健康衰减
        age_factor = max(0.1, 1.0 - self.age * 0.001)
        
        self.health = energy_factor * density_factor * age_factor
    
    def can_divide(self) -> bool:
        """检查是否可以分裂
        
        Returns:
            bool: 是否可以分裂
        """
        return (self.lifecycle_stage == 'M' and 
                self.energy > self.division_threshold and 
                self.health > 0.5)
    
    def divide(self) -> 'DigitalCell':
        """细胞分裂
        
        Returns:
            DigitalCell: 新的子细胞
        """
        if not self.can_divide():
            return None
        
        # 创建子细胞
        child_position = self.position + np.random.randn(3) * self.radius
        
        try:
            # 尝试使用新的基因组系统
            from .genome import Genome, create_random_genome
            import json
            import copy
            
            # 检查是否为新格式的基因组
            if isinstance(self.nucleus.genome_template, dict) and 'root' in self.nucleus.genome_template:
                # 新格式：使用基因组对象进行复制和突变
                parent_genome = Genome.from_dict(self.nucleus.genome_template)
                child_genome_obj = parent_genome.copy()
                
                # 基因突变
                if np.random.random() < 0.1:  # 10%突变概率
                    self._mutate_genome_nodes(child_genome_obj.root, 0.05)
                
                child_genome = child_genome_obj.to_dict()
            else:
                # 旧格式：使用原有的复制和突变逻辑
                child_genome = copy.deepcopy(self.nucleus.genome_template)
                
                # 基因突变
                if np.random.random() < 0.1:  # 10%突变概率
                    self._legacy_mutate_child_genome(child_genome)
                    
        except ImportError:
            # 如果新的基因组系统不可用，使用旧的方法
            import copy
            child_genome = copy.deepcopy(self.nucleus.genome_template)
            
            # 基因突变
            if np.random.random() < 0.1:  # 10%突变概率
                self._legacy_mutate_child_genome(child_genome)
        
        child_cell = DigitalCell(child_position, child_genome)
        child_cell.memory.generation_count = self.memory.generation_count + 1
        
        # 分配能量
        self.energy *= 0.6
        child_cell.energy = self.energy * 0.8
        
        # 重置生命周期
        self.lifecycle_stage = 'G1'
        self.division_timer = 0
        
        return child_cell
    
    def _legacy_mutate_child_genome(self, genome: Dict[str, Any]):
        """旧格式的子细胞基因组突变"""
        mutation_record = {
            'timestamp': time.time(),
            'mutations': []
        }
        
        for gene_name, gene_data in genome.items():
            if np.random.random() < 0.05:  # 5%基因突变率
                instructions = gene_data.get('instructions', [])
                if instructions:
                    # 随机修改一个指令
                    idx = np.random.randint(len(instructions))
                    old_instruction = instructions[idx].copy()
                    
                    # 突变类型
                    mutation_type = np.random.choice(['value_change', 'type_change', 'parameter_add'])
                    
                    if mutation_type == 'value_change' and 'value' in instructions[idx]:
                        instructions[idx]['value'] += np.random.normal(0, 0.2)
                    elif mutation_type == 'type_change':
                        instructions[idx]['type'] = np.random.choice(['CREATE_FUNCTION', 'CREATE_ASSIGNMENT', 'CREATE_EXPRESSION'])
                    elif mutation_type == 'parameter_add':
                        instructions[idx]['mutated_param'] = np.random.random()
                    
                    mutation_record['mutations'].append({
                        'gene': gene_name,
                        'instruction_index': idx,
                        'old': old_instruction,
                        'new': instructions[idx].copy(),
                        'type': mutation_type
                    })
        
        self.memory.mutation_history.append(mutation_record)
    
    def _mutate_genome(self, genome: Dict[str, Any]):
        """基因组突变
        
        Args:
            genome: 要突变的基因组
        """
        mutation_record = {
            'timestamp': time.time(),
            'mutations': []
        }
        
        for gene_name, gene_data in genome.items():
            if np.random.random() < 0.05:  # 5%基因突变率
                instructions = gene_data.get('instructions', [])
                if instructions:
                    # 随机修改一个指令
                    idx = np.random.randint(len(instructions))
                    old_instruction = instructions[idx].copy()
                    
                    # 突变类型
                    mutation_type = np.random.choice(['value_change', 'type_change', 'parameter_add'])
                    
                    if mutation_type == 'value_change' and 'value' in instructions[idx]:
                        instructions[idx]['value'] += np.random.normal(0, 0.2)
                    elif mutation_type == 'type_change':
                        instructions[idx]['type'] = np.random.choice(['CREATE_FUNCTION', 'CREATE_ASSIGNMENT', 'CREATE_EXPRESSION'])
                    elif mutation_type == 'parameter_add':
                        instructions[idx]['mutated_param'] = np.random.random()
                    
                    mutation_record['mutations'].append({
                        'gene': gene_name,
                        'instruction_index': idx,
                        'old': old_instruction,
                        'new': instructions[idx].copy(),
                        'type': mutation_type
                    })
        
        self.memory.mutation_history.append(mutation_record)
    
    def is_dead(self) -> bool:
        """检查细胞是否死亡
        
        Returns:
            bool: 是否死亡
        """
        return self.lifecycle_stage == 'death' and self.death_timer > 5.0
    
    def get_fitness(self) -> float:
        """获取细胞适应度
        
        Returns:
            float: 适应度值
        """
        # 基于能量的适应度
        energy_fitness = self.energy / self.max_energy
        
        # 基于健康的适应度
        health_fitness = self.health
        
        # 基于成功编译的适应度
        mitochondria = self.cytoplasm.organelles.get('mitochondria')
        compilation_fitness = 0.5
        if mitochondria and isinstance(mitochondria, CompilerRunner):
            stats = mitochondria.get_compilation_stats()
            compilation_fitness = stats.get('success_rate', 0.5)
        
        # 基于代数的适应度（奖励长寿）
        generation_fitness = min(1.0, self.memory.generation_count * 0.1)
        
        return (energy_fitness * 0.3 + 
                health_fitness * 0.3 + 
                compilation_fitness * 0.3 + 
                generation_fitness * 0.1)
    
    def get_status(self) -> Dict[str, Any]:
        """获取细胞状态
        
        Returns:
            Dict[str, Any]: 细胞状态信息
        """
        mitochondria = self.cytoplasm.organelles.get('mitochondria')
        compilation_stats = {}
        if mitochondria and isinstance(mitochondria, CompilerRunner):
            compilation_stats = mitochondria.get_compilation_stats()
        
        return {
            'id': self.id,
            'position': self.position.tolist(),
            'age': self.age,
            'energy': self.energy,
            'health': self.health,
            'lifecycle_stage': self.lifecycle_stage,
            'fitness': self.get_fitness(),
            'generation': self.memory.generation_count,
            'molecule_count': len(self.cytoplasm.molecules),
            'active_genes': list(self.nucleus.active_genes),
            'compilation_stats': compilation_stats,
            'can_divide': self.can_divide(),
            'is_dead': self.is_dead(),
            'cooperation_level': self.cooperation_level,
            'signal_status': dict(self.signal_transmitters),
            'neighboring_cells': len(self.neighboring_cells)
        }
    
    def _process_intercellular_communication(self):
        """处理细胞间通信"""
        # 更新邻居细胞列表
        self._update_neighboring_cells()
        
        # 发送信号
        self._emit_signals()
        
        # 接收和处理信号
        self._receive_signals()
        
        # 更新协作状态
        self._update_cooperation_state()
    
    def _update_neighboring_cells(self):
        """更新邻居细胞列表（需要外部环境提供）"""
        # 这个方法需要由环境系统调用来更新邻居列表
        # 这里只是占位符，实际实现需要访问环境中的其他细胞
        pass
    
    def add_neighbor(self, neighbor_cell: 'DigitalCell'):
        """添加邻居细胞"""
        distance = np.linalg.norm(self.position - neighbor_cell.position)
        if distance <= self.communication_range and neighbor_cell not in self.neighboring_cells:
            self.neighboring_cells.append(neighbor_cell)
    
    def remove_neighbor(self, neighbor_cell: 'DigitalCell'):
        """移除邻居细胞"""
        if neighbor_cell in self.neighboring_cells:
            self.neighboring_cells.remove(neighbor_cell)
    
    def _emit_signals(self):
        """发送信号分子"""
        # 基于细胞状态决定发送什么信号
        if self.energy < 30.0:
            # 低能量时发送应激信号
            self.signal_transmitters['stress_signal'] = min(1.0, 
                self.signal_transmitters['stress_signal'] + 0.3)
        
        if self.health < 0.5:
            # 健康状况差时发送死亡信号
            self.signal_transmitters['death_signal'] = min(1.0,
                self.signal_transmitters['death_signal'] + 0.4)
        
        if self.energy > 80.0 and self.health > 0.8:
            # 状态良好时发送生长因子
            self.signal_transmitters['growth_factor'] = min(1.0,
                self.signal_transmitters['growth_factor'] + 0.2)
        
        # 营养信号基于分子密度
        molecular_density = self.cytoplasm.get_molecular_density()
        if molecular_density > 0.1:
            self.signal_transmitters['nutrient_signal'] = min(1.0,
                self.signal_transmitters['nutrient_signal'] + 0.1)
    
    def _receive_signals(self):
        """接收邻居细胞的信号"""
        for neighbor in self.neighboring_cells:
            distance = np.linalg.norm(self.position - neighbor.position)
            signal_strength = max(0.0, 1.0 - distance / self.communication_range)
            
            # 处理各种信号
            for signal_type, signal_value in neighbor.signal_transmitters.items():
                if signal_value > 0 and signal_type in self.signal_receptors:
                    receptor = self.signal_receptors[signal_type]
                    received_strength = signal_value * signal_strength * receptor['sensitivity']
                    
                    if received_strength > receptor['threshold']:
                        self._process_received_signal(signal_type, received_strength)
    
    def _process_received_signal(self, signal_type: str, strength: float):
        """处理接收到的信号"""
        if signal_type == 'growth_factor':
            # 生长因子促进细胞生长和分裂
            self.energy += strength * 5.0
            self.nucleus.activate_gene('growth_genes', strength)
            
        elif signal_type == 'stress_signal':
            # 应激信号触发应激反应
            self.membrane.receive_signal('stress', strength)
            self.nucleus.activate_gene('stress_response_genes', strength)
            
        elif signal_type == 'nutrient_signal':
            # 营养信号调节代谢
            self.membrane.receive_signal('nutrient', strength)
            self.nucleus.activate_gene('metabolic_genes', strength)
            
        elif signal_type == 'death_signal':
            # 死亡信号可能触发凋亡或防御反应
            if strength > 0.7:
                self.health -= strength * 0.1
            else:
                # 轻微死亡信号触发防御
                self.nucleus.activate_gene('defense_genes', strength)
    
    def _update_cooperation_state(self):
        """更新协作状态"""
        if not self.neighboring_cells:
            return
        
        # 计算邻居的平均健康状态
        neighbor_health_avg = sum(neighbor.health for neighbor in self.neighboring_cells) / len(self.neighboring_cells)
        
        # 计算邻居的平均能量
        neighbor_energy_avg = sum(neighbor.energy for neighbor in self.neighboring_cells) / len(self.neighboring_cells)
        
        # 基于邻居状态调整协作水平
        if neighbor_health_avg > 0.7 and neighbor_energy_avg > 50.0:
            # 邻居状态良好，增加协作
            self.cooperation_level = min(1.0, self.cooperation_level + 0.05)
        elif neighbor_health_avg < 0.3 or neighbor_energy_avg < 20.0:
            # 邻居状态不佳，可能减少协作或增加竞争
            self.cooperation_level = max(0.0, self.cooperation_level - 0.03)
            self.competition_factor = min(1.0, self.competition_factor + 0.02)
    
    def perform_altruistic_action(self, target_cell: 'DigitalCell'):
        """执行利他行为"""
        if self.energy > 50.0 and self.altruism_factor > 0.5:
            # 分享能量
            energy_to_share = self.energy * 0.1 * self.altruism_factor
            self.energy -= energy_to_share
            target_cell.energy += energy_to_share
            
            # 分享有益分子
            beneficial_molecules = [mol for mol in self.cytoplasm.molecules 
                                  if mol.type == MoleculeType.ENERGY_TOKEN]
            if beneficial_molecules:
                molecule_to_share = beneficial_molecules[0]
                self.cytoplasm.remove_molecule(molecule_to_share)
                target_cell.cytoplasm.add_molecule(molecule_to_share)
    
    def compete_with_cell(self, target_cell: 'DigitalCell'):
        """与其他细胞竞争资源"""
        if self.competition_factor > 0.6:
            # 竞争能量资源
            if target_cell.energy > self.energy:
                energy_stolen = min(target_cell.energy * 0.05, 10.0)
                target_cell.energy -= energy_stolen
                self.energy += energy_stolen * 0.8  # 效率损失
    
    def get_communication_status(self) -> Dict[str, Any]:
        """获取通信状态信息"""
        return {
            'signal_receptors': dict(self.signal_receptors),
            'signal_transmitters': dict(self.signal_transmitters),
            'neighboring_cells_count': len(self.neighboring_cells),
            'communication_range': self.communication_range,
            'cooperation_level': self.cooperation_level,
            'altruism_factor': self.altruism_factor,
            'competition_factor': self.competition_factor,
            'neighbor_positions': [neighbor.position.tolist() for neighbor in self.neighboring_cells]
        }

def create_digital_cell(position: np.ndarray, 
                       genome_template: Optional[Dict[str, Any]] = None) -> DigitalCell:
    """创建数字细胞的工厂函数
    
    Args:
        position: 细胞位置
        genome_template: 基因组模板
        
    Returns:
        DigitalCell: 新创建的数字细胞
    """
    if genome_template is None:
        genome_template = _create_default_genome()
    
    return DigitalCell(position, genome_template)

def _create_default_genome() -> Dict[str, Any]:
    """创建默认基因组模板
    
    Returns:
        Dict[str, Any]: 默认基因组
    """
    try:
        # 尝试使用新的基因组系统
        from .genome import create_random_genome
        
        # 创建新格式的基因组
        genome_obj = create_random_genome()
        return genome_obj.to_dict()
        
    except ImportError:
        # 如果新的基因组系统不可用，返回旧格式
        return {
            'basic_function': {
                'instructions': [
                    {'type': 'CREATE_FUNCTION', 'name': 'hello_world', 'args': []},
                    {'type': 'CREATE_EXPRESSION', 'expr_type': 'Constant', 'value': 'Hello, World!'}
                ],
                'stability': 1.0
            },
            'variable_assignment': {
                'instructions': [
                    {'type': 'CREATE_ASSIGNMENT', 'target': 'x'},
                    {'type': 'CREATE_EXPRESSION', 'expr_type': 'Constant', 'value': 42}
                ],
                'stability': 0.9
            },
            'simple_expression': {
                'instructions': [
                    {'type': 'CREATE_EXPRESSION', 'expr_type': 'Name', 'id': 'x'},
                    {'type': 'CREATE_EXPRESSION', 'expr_type': 'Constant', 'value': 1}
                ],
                'stability': 0.8
            }
        }