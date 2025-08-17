# -*- coding: utf-8 -*-
"""
基因数据结构 - EvoForge核心组件

根据comprehensive_implementation_plan.md任务5实现的基因数据结构，包括：
- Gene类（基于AST）
- 基因序列化/反序列化
- 基因完整性验证
- 基因表达调控机制

作者: EvoForge Team
创建时间: 2024
"""

import ast
import json
import hashlib
import random
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# 配置日志
logger = logging.getLogger(__name__)

class GeneType(Enum):
    """基因类型枚举"""
    STRUCTURAL = "structural"  # 结构基因（编码蛋白质）
    REGULATORY = "regulatory"  # 调控基因（转录因子等）
    FUNCTIONAL = "functional"  # 功能基因（可执行代码）
    METABOLIC = "metabolic"   # 代谢基因（酶催化）
    SIGNALING = "signaling"   # 信号基因（细胞通信）
    HOUSEKEEPING = "housekeeping"  # 管家基因（基础功能）

class ExpressionLevel(Enum):
    """表达水平枚举"""
    SILENT = 0.0      # 沉默
    LOW = 0.25        # 低表达
    MODERATE = 0.5    # 中等表达
    HIGH = 0.75       # 高表达
    MAXIMUM = 1.0     # 最大表达

@dataclass
class Promoter:
    """启动子区域"""
    sequence: str
    strength: float = 0.5  # 启动子强度 (0-1)
    binding_sites: Dict[str, float] = field(default_factory=dict)  # 转录因子结合位点
    tata_box: bool = True  # 是否包含TATA盒
    cpg_islands: int = 0   # CpG岛数量
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.binding_sites:
            # 默认添加一些常见的转录因子结合位点
            self.binding_sites = {
                "CREB": random.uniform(0.1, 0.9),
                "NF-kB": random.uniform(0.1, 0.9),
                "p53": random.uniform(0.1, 0.9)
            }
    
    def calculate_activity(self, transcription_factors: Dict[str, float]) -> float:
        """计算启动子活性"""
        base_activity = self.strength
        
        # 转录因子影响
        tf_effect = 1.0
        for tf_name, tf_concentration in transcription_factors.items():
            if tf_name in self.binding_sites:
                binding_affinity = self.binding_sites[tf_name]
                tf_effect *= (1.0 + binding_affinity * tf_concentration)
        
        # TATA盒影响
        tata_effect = 1.2 if self.tata_box else 0.8
        
        # CpG岛影响（甲基化调控）
        cpg_effect = 1.0 + (self.cpg_islands * 0.1)
        
        return min(1.0, base_activity * tf_effect * tata_effect * cpg_effect)

@dataclass
class CodingRegion:
    """编码区域"""
    sequence: str
    start_codon: str = "ATG"
    stop_codons: List[str] = field(default_factory=lambda: ["TAA", "TAG", "TGA"])
    reading_frame: int = 0  # 阅读框 (0, 1, 2)
    
    def validate_sequence(self) -> bool:
        """验证编码序列"""
        # 检查起始密码子
        if not self.sequence.startswith(self.start_codon):
            return False
        
        # 检查终止密码子
        has_stop = any(self.sequence.endswith(stop) for stop in self.stop_codons)
        if not has_stop:
            return False
        
        # 检查序列长度是否为3的倍数
        if len(self.sequence) % 3 != 0:
            return False
        
        return True
    
    def translate_to_amino_acids(self) -> str:
        """翻译为氨基酸序列"""
        codon_table = {
            'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
            'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
            'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
            'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
            'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
            'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
            'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
            'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
            'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
            'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
            'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
            'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
            'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
            'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
            'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
            'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G'
        }
        
        amino_acids = []
        for i in range(0, len(self.sequence), 3):
            codon = self.sequence[i:i+3]
            if len(codon) == 3:
                amino_acid = codon_table.get(codon, 'X')  # X表示未知氨基酸
                amino_acids.append(amino_acid)
                if amino_acid == '*':  # 终止密码子
                    break
        
        return ''.join(amino_acids)

@dataclass
class RegulatoryElement:
    """调控元件"""
    element_type: str  # "enhancer", "silencer", "insulator"
    position: int      # 相对于基因起始位置
    sequence: str
    activity: float = 1.0  # 调控活性
    
    def apply_regulation(self, base_expression: float, 
                        environmental_factors: Dict[str, float]) -> float:
        """应用调控效果"""
        if self.element_type == "enhancer":
            enhancement = self.activity * environmental_factors.get("growth_factors", 1.0)
            return base_expression * (1.0 + enhancement)
        elif self.element_type == "silencer":
            silencing = self.activity * environmental_factors.get("stress_factors", 1.0)
            return base_expression * (1.0 - silencing)
        elif self.element_type == "insulator":
            # 绝缘子阻止远程调控
            return base_expression * 0.9
        else:
            return base_expression

class Gene:
    """基因类（基于AST）"""
    
    def __init__(self, 
                 gene_id: str,
                 gene_type: GeneType,
                 promoter: Promoter,
                 coding_region: CodingRegion,
                 regulatory_elements: List[RegulatoryElement] = None):
        self.gene_id = gene_id
        self.gene_type = gene_type
        self.promoter = promoter
        self.coding_region = coding_region
        self.regulatory_elements = regulatory_elements or []
        
        # 表达相关属性
        self.expression_level = ExpressionLevel.MODERATE
        self.last_expression_time = 0.0
        self.expression_count = 0
        
        # AST相关属性
        self._ast_cache: Optional[ast.AST] = None
        self._code_cache: Optional[str] = None
        
        # 完整性验证
        self.integrity_hash = self._calculate_integrity_hash()
        self.is_valid = self.validate_integrity()
        
        logger.debug(f"创建基因 {gene_id}，类型: {gene_type.value}")
    
    def _calculate_integrity_hash(self) -> str:
        """计算完整性哈希"""
        content = f"{self.gene_id}{self.promoter.sequence}{self.coding_region.sequence}"
        for element in self.regulatory_elements:
            content += f"{element.element_type}{element.sequence}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def validate_integrity(self) -> bool:
        """验证基因完整性"""
        try:
            # 1. 验证基因ID
            if not self.gene_id or len(self.gene_id) < 3:
                logger.error(f"基因ID无效: {self.gene_id}")
                return False
            
            # 2. 验证启动子序列
            if not self.promoter.sequence or len(self.promoter.sequence) < 10:
                logger.error(f"启动子序列过短: {len(self.promoter.sequence)}")
                return False
            
            # 3. 验证编码区域
            if not self.coding_region.validate_sequence():
                logger.error(f"编码区域验证失败: {self.gene_id}")
                return False
            
            # 4. 验证调控元件
            for element in self.regulatory_elements:
                if not element.sequence or len(element.sequence) < 5:
                    logger.error(f"调控元件序列过短: {element.element_type}")
                    return False
            
            # 5. 验证完整性哈希
            current_hash = self._calculate_integrity_hash()
            if current_hash != self.integrity_hash:
                logger.warning(f"基因 {self.gene_id} 完整性哈希不匹配")
                self.integrity_hash = current_hash
            
            return True
            
        except Exception as e:
            logger.error(f"基因完整性验证错误: {e}")
            return False
    
    def to_ast(self) -> ast.AST:
        """转换为AST（抽象语法树）"""
        if self._ast_cache is not None:
            return self._ast_cache
        
        try:
            # 根据基因类型生成不同的AST结构
            if self.gene_type == GeneType.FUNCTIONAL:
                # 功能基因：直接从编码区域生成可执行代码
                code = self._generate_functional_code()
                self._ast_cache = ast.parse(code)
            
            elif self.gene_type == GeneType.STRUCTURAL:
                # 结构基因：生成数据结构定义
                code = self._generate_structural_code()
                self._ast_cache = ast.parse(code)
            
            elif self.gene_type == GeneType.REGULATORY:
                # 调控基因：生成调控逻辑
                code = self._generate_regulatory_code()
                self._ast_cache = ast.parse(code)
            
            else:
                # 其他类型：生成基础代码框架
                code = self._generate_basic_code()
                self._ast_cache = ast.parse(code)
            
            return self._ast_cache
            
        except Exception as e:
            logger.error(f"基因 {self.gene_id} AST生成错误: {e}")
            # 返回空的模块AST
            return ast.Module(body=[], type_ignores=[])
    
    def _generate_functional_code(self) -> str:
        """生成功能基因代码"""
        amino_sequence = self.coding_region.translate_to_amino_acids()
        
        # 简化的氨基酸到代码映射
        code_parts = []
        code_parts.append("def gene_function(input_data):")  
        code_parts.append("    \"\"\"基因功能实现\"\"\"")
        code_parts.append("    result = input_data")
        
        # 根据氨基酸序列生成简单的处理逻辑
        for i, amino in enumerate(amino_sequence[:10]):  # 限制长度
            if amino == 'M':  # 甲硫氨酸 - 初始化
                code_parts.append("    result = result * 1.0")
            elif amino == 'L':  # 亮氨酸 - 循环
                code_parts.append("    result = [x for x in result] if hasattr(result, '__iter__') else result")
            elif amino == 'S':  # 丝氨酸 - 求和
                code_parts.append("    result = sum(result) if hasattr(result, '__iter__') else result")
            elif amino == 'F':  # 苯丙氨酸 - 过滤
                code_parts.append("    result = result if result > 0 else 0")
            elif amino == '*':  # 终止
                break
        
        code_parts.append("    return result")
        return "\n".join(code_parts)
    
    def _generate_structural_code(self) -> str:
        """生成结构基因代码"""
        return f"""
class GeneProduct_{self.gene_id}:
    \"\"\"基因产物结构\"\"\"
    def __init__(self):
        self.gene_id = "{self.gene_id}"
        self.structure_type = "protein"
        self.amino_sequence = "{self.coding_region.translate_to_amino_acids()}"
        self.stability = 1.0
    
    def fold(self):
        \"\"\"蛋白质折叠\"\"\"
        return self.amino_sequence
"""
    
    def _generate_regulatory_code(self) -> str:
        """生成调控基因代码"""
        return f"""
def regulatory_function_{self.gene_id}(target_genes, environment):
    \"\"\"调控基因功能\"\"\"
    regulation_strength = {self.promoter.strength}
    
    for gene_id in target_genes:
        if environment.get('stress_level', 0) > 0.5:
            # 压力条件下抑制表达
            target_genes[gene_id] *= (1.0 - regulation_strength)
        else:
            # 正常条件下促进表达
            target_genes[gene_id] *= (1.0 + regulation_strength)
    
    return target_genes
"""
    
    def _generate_basic_code(self) -> str:
        """生成基础代码框架"""
        return f"""
# 基因 {self.gene_id} - {self.gene_type.value}
def basic_function():
    \"\"\"基础基因功能\"\"\"
    return "{self.gene_id}_product"
"""
    
    def to_code(self) -> str:
        """转换为可执行代码"""
        if self._code_cache is not None:
            return self._code_cache
        
        try:
            ast_tree = self.to_ast()
            self._code_cache = ast.unparse(ast_tree)
            return self._code_cache
        except Exception as e:
            logger.error(f"基因 {self.gene_id} 代码生成错误: {e}")
            return f"# 基因 {self.gene_id} 代码生成失败\npass"
    
    def calculate_expression_level(self, 
                                 transcription_factors: Dict[str, float],
                                 environmental_factors: Dict[str, float],
                                 hormones: Dict[str, float]) -> float:
        """计算表达水平"""
        try:
            # 1. 启动子活性
            promoter_activity = self.promoter.calculate_activity(transcription_factors)
            
            # 2. 调控元件影响
            regulatory_effect = 1.0
            for element in self.regulatory_elements:
                regulatory_effect *= element.apply_regulation(1.0, environmental_factors)
            
            # 3. 激素影响
            hormone_effect = 1.0
            for hormone_name, concentration in hormones.items():
                if hormone_name in ["growth_hormone", "insulin"]:
                    hormone_effect *= (1.0 + concentration * 0.2)
                elif hormone_name in ["cortisol", "adrenaline"]:
                    hormone_effect *= (1.0 - concentration * 0.1)
            
            # 4. 基因类型特异性调节
            type_modifier = {
                GeneType.HOUSEKEEPING: 1.2,  # 管家基因稳定高表达
                GeneType.REGULATORY: 0.8,    # 调控基因适度表达
                GeneType.FUNCTIONAL: 1.0,    # 功能基因正常表达
                GeneType.METABOLIC: 1.1,     # 代谢基因稍高表达
                GeneType.SIGNALING: 0.9,     # 信号基因适度表达
                GeneType.STRUCTURAL: 1.0     # 结构基因正常表达
            }.get(self.gene_type, 1.0)
            
            final_expression = promoter_activity * regulatory_effect * hormone_effect * type_modifier
            return max(0.0, min(1.0, final_expression))
            
        except Exception as e:
            logger.error(f"基因 {self.gene_id} 表达水平计算错误: {e}")
            return 0.1  # 返回最低表达水平
    
    def mutate(self, mutation_rate: float = 0.01) -> 'Gene':
        """基因突变"""
        try:
            # 创建基因副本
            new_promoter = Promoter(
                sequence=self._mutate_sequence(self.promoter.sequence, mutation_rate),
                strength=max(0.0, min(1.0, self.promoter.strength + random.gauss(0, 0.1))),
                binding_sites=self.promoter.binding_sites.copy(),
                tata_box=self.promoter.tata_box,
                cpg_islands=self.promoter.cpg_islands
            )
            
            new_coding_region = CodingRegion(
                sequence=self._mutate_sequence(self.coding_region.sequence, mutation_rate),
                start_codon=self.coding_region.start_codon,
                stop_codons=self.coding_region.stop_codons.copy(),
                reading_frame=self.coding_region.reading_frame
            )
            
            new_regulatory_elements = []
            for element in self.regulatory_elements:
                new_element = RegulatoryElement(
                    element_type=element.element_type,
                    position=element.position,
                    sequence=self._mutate_sequence(element.sequence, mutation_rate),
                    activity=max(0.0, min(2.0, element.activity + random.gauss(0, 0.1)))
                )
                new_regulatory_elements.append(new_element)
            
            mutated_gene = Gene(
                gene_id=f"{self.gene_id}_mut_{random.randint(1000, 9999)}",
                gene_type=self.gene_type,
                promoter=new_promoter,
                coding_region=new_coding_region,
                regulatory_elements=new_regulatory_elements
            )
            
            logger.debug(f"基因突变: {self.gene_id} -> {mutated_gene.gene_id}")
            return mutated_gene
            
        except Exception as e:
            logger.error(f"基因突变错误: {e}")
            return self  # 返回原基因
    
    def _mutate_sequence(self, sequence: str, mutation_rate: float) -> str:
        """序列突变"""
        nucleotides = ['A', 'T', 'G', 'C']
        mutated = list(sequence)
        
        for i in range(len(mutated)):
            if random.random() < mutation_rate:
                mutated[i] = random.choice(nucleotides)
        
        return ''.join(mutated)
    
    def serialize(self) -> Dict[str, Any]:
        """序列化基因数据"""
        return {
            'gene_id': self.gene_id,
            'gene_type': self.gene_type.value,
            'promoter': {
                'sequence': self.promoter.sequence,
                'strength': self.promoter.strength,
                'binding_sites': self.promoter.binding_sites,
                'tata_box': self.promoter.tata_box,
                'cpg_islands': self.promoter.cpg_islands
            },
            'coding_region': {
                'sequence': self.coding_region.sequence,
                'start_codon': self.coding_region.start_codon,
                'stop_codons': self.coding_region.stop_codons,
                'reading_frame': self.coding_region.reading_frame
            },
            'regulatory_elements': [
                {
                    'element_type': elem.element_type,
                    'position': elem.position,
                    'sequence': elem.sequence,
                    'activity': elem.activity
                } for elem in self.regulatory_elements
            ],
            'expression_level': self.expression_level.value,
            'expression_count': self.expression_count,
            'integrity_hash': self.integrity_hash,
            'is_valid': self.is_valid
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Gene':
        """反序列化基因数据"""
        try:
            # 重建启动子
            promoter_data = data['promoter']
            promoter = Promoter(
                sequence=promoter_data['sequence'],
                strength=promoter_data['strength'],
                binding_sites=promoter_data['binding_sites'],
                tata_box=promoter_data['tata_box'],
                cpg_islands=promoter_data['cpg_islands']
            )
            
            # 重建编码区域
            coding_data = data['coding_region']
            coding_region = CodingRegion(
                sequence=coding_data['sequence'],
                start_codon=coding_data['start_codon'],
                stop_codons=coding_data['stop_codons'],
                reading_frame=coding_data['reading_frame']
            )
            
            # 重建调控元件
            regulatory_elements = []
            for elem_data in data['regulatory_elements']:
                element = RegulatoryElement(
                    element_type=elem_data['element_type'],
                    position=elem_data['position'],
                    sequence=elem_data['sequence'],
                    activity=elem_data['activity']
                )
                regulatory_elements.append(element)
            
            # 创建基因对象
            gene = cls(
                gene_id=data['gene_id'],
                gene_type=GeneType(data['gene_type']),
                promoter=promoter,
                coding_region=coding_region,
                regulatory_elements=regulatory_elements
            )
            
            # 恢复状态
            gene.expression_level = ExpressionLevel(data['expression_level'])
            gene.expression_count = data['expression_count']
            gene.integrity_hash = data['integrity_hash']
            gene.is_valid = data['is_valid']
            
            return gene
            
        except Exception as e:
            logger.error(f"基因反序列化错误: {e}")
            raise ValueError(f"无法反序列化基因数据: {e}")
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.serialize(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Gene':
        """从JSON字符串创建基因"""
        data = json.loads(json_str)
        return cls.deserialize(data)
    
    def __str__(self) -> str:
        return f"Gene({self.gene_id}, {self.gene_type.value}, valid={self.is_valid})"
    
    def __repr__(self) -> str:
        return self.__str__()

# 基因工厂函数
def create_random_gene(gene_id: str, gene_type: GeneType) -> Gene:
    """创建随机基因"""
    # 生成随机启动子
    promoter_sequence = ''.join(random.choices(['A', 'T', 'G', 'C'], k=50))
    promoter = Promoter(
        sequence=promoter_sequence,
        strength=random.uniform(0.1, 0.9),
        tata_box=random.choice([True, False]),
        cpg_islands=random.randint(0, 5)
    )
    
    # 生成随机编码区域
    coding_length = random.randint(30, 300)  # 确保是3的倍数
    coding_length = (coding_length // 3) * 3
    coding_sequence = "ATG"  # 起始密码子
    coding_sequence += ''.join(random.choices(['A', 'T', 'G', 'C'], k=coding_length-6))
    coding_sequence += "TAA"  # 终止密码子
    
    coding_region = CodingRegion(sequence=coding_sequence)
    
    # 生成随机调控元件
    regulatory_elements = []
    for i in range(random.randint(0, 3)):
        element = RegulatoryElement(
            element_type=random.choice(["enhancer", "silencer", "insulator"]),
            position=random.randint(-1000, 1000),
            sequence=''.join(random.choices(['A', 'T', 'G', 'C'], k=20)),
            activity=random.uniform(0.1, 2.0)
        )
        regulatory_elements.append(element)
    
    return Gene(
        gene_id=gene_id,
        gene_type=gene_type,
        promoter=promoter,
        coding_region=coding_region,
        regulatory_elements=regulatory_elements
    )

# 测试代码
if __name__ == "__main__":
    logger.info("基因数据结构测试开始")
    
    # 创建测试基因
    test_gene = create_random_gene("test_gene_001", GeneType.FUNCTIONAL)
    
    print(f"创建基因: {test_gene}")
    print(f"基因有效性: {test_gene.is_valid}")
    print(f"完整性哈希: {test_gene.integrity_hash[:16]}...")
    
    # 测试AST转换
    ast_tree = test_gene.to_ast()
    print(f"AST节点数: {len(ast_tree.body)}")
    
    # 测试代码生成
    code = test_gene.to_code()
    print(f"生成代码长度: {len(code)} 字符")
    
    # 测试表达水平计算
    tf_dict = {"CREB": 0.5, "NF-kB": 0.3}
    env_dict = {"growth_factors": 0.8, "stress_factors": 0.2}
    hormone_dict = {"growth_hormone": 0.6, "cortisol": 0.3}
    
    expression = test_gene.calculate_expression_level(tf_dict, env_dict, hormone_dict)
    print(f"表达水平: {expression:.3f}")
    
    # 测试序列化/反序列化
    json_data = test_gene.to_json()
    print(f"JSON数据长度: {len(json_data)} 字符")
    
    restored_gene = Gene.from_json(json_data)
    print(f"恢复基因: {restored_gene}")
    print(f"序列化测试: {'通过' if restored_gene.gene_id == test_gene.gene_id else '失败'}")
    
    # 测试基因突变
    mutated_gene = test_gene.mutate(mutation_rate=0.05)
    print(f"突变基因: {mutated_gene}")
    print(f"突变测试: {'通过' if mutated_gene.gene_id != test_gene.gene_id else '失败'}")
    
    logger.info("基因数据结构测试完成")