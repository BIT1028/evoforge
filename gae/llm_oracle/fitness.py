#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态评估系统 - 核心实现文件

根据 comprehensive_implementation_plan.md 文档重新实现

功能包括：
- MultiModalOracle 类：多模态智能评估核心
- 集成文本/视觉/音频模型
- 六维度适应度评估体系
- 评估结果缓存和成本优化
- 任务特定适应度函数
"""

import logging
import hashlib
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
import os
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ModalityType(Enum):
    """模态类型枚举"""
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"

class FitnessMetric(Enum):
    """适应度指标枚举"""
    FUNCTIONALITY = "functionality"  # 功能性
    EFFICIENCY = "efficiency"        # 效率
    ROBUSTNESS = "robustness"        # 鲁棒性
    ADAPTABILITY = "adaptability"    # 适应性
    NOVELTY = "novelty"              # 新颖性
    COMPLEXITY = "complexity"        # 复杂性

@dataclass
class EvaluationRequest:
    """评估请求数据结构"""
    task_id: str
    content: Any
    modality: ModalityType
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1-5, 5为最高优先级
    timeout: float = 30.0
    cache_enabled: bool = True
    
    def get_cache_key(self) -> str:
        """生成缓存键"""
        content_str = str(self.content)
        context_str = json.dumps(self.context, sort_keys=True)
        combined = f"{self.task_id}:{content_str}:{context_str}:{self.modality.value}"
        return hashlib.md5(combined.encode()).hexdigest()

@dataclass
class EvaluationResult:
    """评估结果数据结构"""
    request_id: str
    fitness_scores: Dict[FitnessMetric, float]
    detailed_analysis: Dict[str, Any]
    confidence: float
    processing_time: float
    model_used: str
    timestamp: float = field(default_factory=time.time)
    
    def get_overall_fitness(self) -> float:
        """计算综合适应度分数"""
        if not self.fitness_scores:
            return 0.0
        return sum(self.fitness_scores.values()) / len(self.fitness_scores)

class ModelInterface(ABC):
    """模型接口抽象基类"""
    
    @abstractmethod
    async def evaluate(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """评估内容"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        pass

class TextModel(ModelInterface):
    """文本模型实现"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        logger.debug(f"初始化文本模型: {model_name}")
    
    async def evaluate(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """评估文本内容"""
        logger.debug(f"文本模型评估: {str(content)[:100]}...")
        
        # 模拟文本评估逻辑
        text_content = str(content)
        
        # 基础指标计算
        functionality = self._evaluate_functionality(text_content, context)
        efficiency = self._evaluate_efficiency(text_content, context)
        robustness = self._evaluate_robustness(text_content, context)
        adaptability = self._evaluate_adaptability(text_content, context)
        novelty = self._evaluate_novelty(text_content, context)
        complexity = self._evaluate_complexity(text_content, context)
        
        return {
            "functionality": functionality,
            "efficiency": efficiency,
            "robustness": robustness,
            "adaptability": adaptability,
            "novelty": novelty,
            "complexity": complexity,
            "confidence": 0.85,
            "analysis": {
                "length": len(text_content),
                "word_count": len(text_content.split()),
                "complexity_score": complexity,
                "readability": efficiency
            }
        }
    
    def _evaluate_functionality(self, text: str, context: Dict[str, Any]) -> float:
        """评估功能性"""
        # 基于文本长度和结构评估功能性
        base_score = min(len(text) / 1000, 1.0)
        
        # 检查是否包含关键功能词汇
        functional_keywords = ['function', 'method', 'class', 'def', 'return', 'if', 'for', 'while']
        keyword_score = sum(1 for keyword in functional_keywords if keyword in text.lower()) / len(functional_keywords)
        
        return (base_score + keyword_score) / 2
    
    def _evaluate_efficiency(self, text: str, context: Dict[str, Any]) -> float:
        """评估效率"""
        # 基于文本简洁性评估效率
        if len(text) == 0:
            return 0.0
        
        word_count = len(text.split())
        char_count = len(text)
        
        # 简洁性指标
        conciseness = 1.0 - min(char_count / 10000, 1.0)
        
        # 信息密度
        info_density = word_count / max(char_count, 1) * 10
        
        return (conciseness + min(info_density, 1.0)) / 2
    
    def _evaluate_robustness(self, text: str, context: Dict[str, Any]) -> float:
        """评估鲁棒性"""
        # 基于文本结构和错误处理评估鲁棒性
        robustness_keywords = ['try', 'except', 'error', 'handle', 'validate', 'check']
        keyword_score = sum(1 for keyword in robustness_keywords if keyword in text.lower()) / len(robustness_keywords)
        
        # 结构完整性
        structure_score = 0.5  # 基础分数
        if '{' in text and '}' in text:
            structure_score += 0.2
        if '(' in text and ')' in text:
            structure_score += 0.2
        if '[' in text and ']' in text:
            structure_score += 0.1
        
        return (keyword_score + min(structure_score, 1.0)) / 2
    
    def _evaluate_adaptability(self, text: str, context: Dict[str, Any]) -> float:
        """评估适应性"""
        # 基于参数化和配置能力评估适应性
        adaptability_keywords = ['config', 'parameter', 'option', 'setting', 'variable', 'customize']
        keyword_score = sum(1 for keyword in adaptability_keywords if keyword in text.lower()) / len(adaptability_keywords)
        
        # 变量使用
        variable_indicators = ['=', 'var', 'let', 'const']
        variable_score = sum(1 for indicator in variable_indicators if indicator in text) / len(variable_indicators)
        
        return (keyword_score + min(variable_score, 1.0)) / 2
    
    def _evaluate_novelty(self, text: str, context: Dict[str, Any]) -> float:
        """评估新颖性"""
        # 基于独特性和创新性评估新颖性
        import random
        
        # 模拟新颖性评估
        base_novelty = random.uniform(0.3, 0.9)
        
        # 基于文本复杂性调整
        complexity_bonus = min(len(set(text.lower().split())) / 100, 0.3)
        
        return min(base_novelty + complexity_bonus, 1.0)
    
    def _evaluate_complexity(self, text: str, context: Dict[str, Any]) -> float:
        """评估复杂性"""
        # 基于文本结构和内容复杂性评估
        if len(text) == 0:
            return 0.0
        
        # 词汇复杂性
        unique_words = len(set(text.lower().split()))
        total_words = len(text.split())
        vocab_complexity = unique_words / max(total_words, 1)
        
        # 结构复杂性
        nesting_indicators = ['{', '}', '(', ')', '[', ']']
        nesting_score = sum(text.count(indicator) for indicator in nesting_indicators) / len(text)
        
        return min((vocab_complexity + nesting_score * 10) / 2, 1.0)
    
    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            "name": self.model_name,
            "type": "text",
            "version": "1.0",
            "capabilities": "文本分析、代码评估、自然语言理解"
        }

class VisionModel(ModelInterface):
    """视觉模型实现"""
    
    def __init__(self, model_name: str = "gpt-4-vision"):
        self.model_name = model_name
        logger.debug(f"初始化视觉模型: {model_name}")
    
    async def evaluate(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """评估视觉内容"""
        logger.debug(f"视觉模型评估: {type(content)}")
        
        # 模拟视觉评估逻辑
        import random
        
        return {
            "functionality": random.uniform(0.6, 0.9),
            "efficiency": random.uniform(0.5, 0.8),
            "robustness": random.uniform(0.4, 0.7),
            "adaptability": random.uniform(0.3, 0.6),
            "novelty": random.uniform(0.7, 1.0),
            "complexity": random.uniform(0.5, 0.9),
            "confidence": 0.75,
            "analysis": {
                "visual_complexity": random.uniform(0.3, 0.8),
                "color_diversity": random.uniform(0.2, 0.9),
                "structure_clarity": random.uniform(0.4, 0.8)
            }
        }
    
    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            "name": self.model_name,
            "type": "vision",
            "version": "1.0",
            "capabilities": "图像分析、视觉理解、场景识别"
        }

class AudioModel(ModelInterface):
    """音频模型实现"""
    
    def __init__(self, model_name: str = "whisper-large"):
        self.model_name = model_name
        logger.debug(f"初始化音频模型: {model_name}")
    
    async def evaluate(self, content: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """评估音频内容"""
        logger.debug(f"音频模型评估: {type(content)}")
        
        # 模拟音频评估逻辑
        import random
        
        return {
            "functionality": random.uniform(0.5, 0.8),
            "efficiency": random.uniform(0.6, 0.9),
            "robustness": random.uniform(0.4, 0.7),
            "adaptability": random.uniform(0.3, 0.6),
            "novelty": random.uniform(0.6, 0.9),
            "complexity": random.uniform(0.4, 0.8),
            "confidence": 0.70,
            "analysis": {
                "audio_quality": random.uniform(0.5, 0.9),
                "speech_clarity": random.uniform(0.4, 0.8),
                "content_richness": random.uniform(0.3, 0.7)
            }
        }
    
    def get_model_info(self) -> Dict[str, str]:
        """获取模型信息"""
        return {
            "name": self.model_name,
            "type": "audio",
            "version": "1.0",
            "capabilities": "音频分析、语音识别、声音理解"
        }

class EvaluationCache:
    """评估结果缓存系统"""
    
    def __init__(self, cache_dir: str = "./cache", max_size: int = 10000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size = max_size
        self.memory_cache: Dict[str, EvaluationResult] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()
        
        logger.debug(f"初始化评估缓存: {cache_dir}, 最大大小: {max_size}")
    
    def get(self, cache_key: str) -> Optional[EvaluationResult]:
        """获取缓存结果"""
        with self.lock:
            # 先检查内存缓存
            if cache_key in self.memory_cache:
                self.access_times[cache_key] = time.time()
                logger.debug(f"命中内存缓存: {cache_key}")
                return self.memory_cache[cache_key]
            
            # 检查磁盘缓存
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        result = pickle.load(f)
                    
                    # 加载到内存缓存
                    self.memory_cache[cache_key] = result
                    self.access_times[cache_key] = time.time()
                    
                    logger.debug(f"命中磁盘缓存: {cache_key}")
                    return result
                except Exception as e:
                    logger.warning(f"读取缓存文件失败: {e}")
            
            return None
    
    def put(self, cache_key: str, result: EvaluationResult):
        """存储缓存结果"""
        with self.lock:
            # 检查缓存大小限制
            if len(self.memory_cache) >= self.max_size:
                self._evict_oldest()
            
            # 存储到内存缓存
            self.memory_cache[cache_key] = result
            self.access_times[cache_key] = time.time()
            
            # 异步存储到磁盘
            self._save_to_disk(cache_key, result)
            
            logger.debug(f"缓存结果已存储: {cache_key}")
    
    def _evict_oldest(self):
        """淘汰最旧的缓存项"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.memory_cache[oldest_key]
        del self.access_times[oldest_key]
        
        logger.debug(f"淘汰缓存项: {oldest_key}")
    
    def _save_to_disk(self, cache_key: str, result: EvaluationResult):
        """保存到磁盘"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            logger.warning(f"保存缓存到磁盘失败: {e}")
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.memory_cache.clear()
            self.access_times.clear()
            
            # 清空磁盘缓存
            for cache_file in self.cache_dir.glob("*.pkl"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"删除缓存文件失败: {e}")
            
            logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            return {
                "memory_cache_size": len(self.memory_cache),
                "disk_cache_size": len(list(self.cache_dir.glob("*.pkl"))),
                "max_size": self.max_size,
                "cache_dir": str(self.cache_dir)
            }

class CostOptimizer:
    """成本优化器"""
    
    def __init__(self):
        self.model_costs = {
            "text": 0.001,    # 每次调用成本
            "vision": 0.01,
            "audio": 0.005
        }
        self.usage_stats = {
            "text": 0,
            "vision": 0,
            "audio": 0
        }
        self.total_cost = 0.0
        self.lock = threading.RLock()
        
        logger.debug("初始化成本优化器")
    
    def record_usage(self, modality: ModalityType, processing_time: float):
        """记录使用情况"""
        with self.lock:
            modality_str = modality.value
            if modality_str in self.usage_stats:
                self.usage_stats[modality_str] += 1
                cost = self.model_costs.get(modality_str, 0.001) * (1 + processing_time / 10)
                self.total_cost += cost
                
                logger.debug(f"记录使用: {modality_str}, 成本: {cost:.4f}, 总成本: {self.total_cost:.4f}")
    
    def get_cost_stats(self) -> Dict[str, Any]:
        """获取成本统计"""
        with self.lock:
            return {
                "usage_stats": self.usage_stats.copy(),
                "total_cost": self.total_cost,
                "model_costs": self.model_costs.copy()
            }
    
    def optimize_model_selection(self, request: EvaluationRequest) -> str:
        """优化模型选择"""
        # 基于优先级和成本选择最优模型
        if request.priority >= 4:
            return "premium"  # 高优先级使用高质量模型
        elif request.priority >= 2:
            return "standard"  # 中等优先级使用标准模型
        else:
            return "basic"  # 低优先级使用基础模型

class MultiModalOracle:
    """多模态智能评估系统核心类"""
    
    def __init__(self, cache_dir: str = "./cache", max_workers: int = 4):
        self.models: Dict[ModalityType, ModelInterface] = {
            ModalityType.TEXT: TextModel(),
            ModalityType.VISION: VisionModel(),
            ModalityType.AUDIO: AudioModel()
        }
        
        self.cache = EvaluationCache(cache_dir)
        self.cost_optimizer = CostOptimizer()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 统计信息
        self.evaluation_count = 0
        self.cache_hit_count = 0
        self.total_processing_time = 0.0
        
        self.lock = threading.RLock()
        
        logger.info(f"多模态评估系统初始化完成，工作线程数: {max_workers}")
    
    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """执行评估"""
        start_time = time.time()
        
        logger.debug(f"开始评估请求: {request.task_id}, 模态: {request.modality.value}")
        
        # 检查缓存
        if request.cache_enabled:
            cache_key = request.get_cache_key()
            cached_result = self.cache.get(cache_key)
            if cached_result:
                with self.lock:
                    self.cache_hit_count += 1
                logger.debug(f"使用缓存结果: {request.task_id}")
                return cached_result
        
        try:
            # 选择合适的模型
            model = self.models.get(request.modality)
            if not model:
                raise ValueError(f"不支持的模态类型: {request.modality}")
            
            # 执行评估
            model_result = await asyncio.wait_for(
                model.evaluate(request.content, request.context),
                timeout=request.timeout
            )
            
            # 构建评估结果
            fitness_scores = {
                FitnessMetric.FUNCTIONALITY: model_result.get("functionality", 0.0),
                FitnessMetric.EFFICIENCY: model_result.get("efficiency", 0.0),
                FitnessMetric.ROBUSTNESS: model_result.get("robustness", 0.0),
                FitnessMetric.ADAPTABILITY: model_result.get("adaptability", 0.0),
                FitnessMetric.NOVELTY: model_result.get("novelty", 0.0),
                FitnessMetric.COMPLEXITY: model_result.get("complexity", 0.0)
            }
            
            processing_time = time.time() - start_time
            
            result = EvaluationResult(
                request_id=request.task_id,
                fitness_scores=fitness_scores,
                detailed_analysis=model_result.get("analysis", {}),
                confidence=model_result.get("confidence", 0.5),
                processing_time=processing_time,
                model_used=model.get_model_info()["name"]
            )
            
            # 缓存结果
            if request.cache_enabled:
                self.cache.put(cache_key, result)
            
            # 记录统计信息
            with self.lock:
                self.evaluation_count += 1
                self.total_processing_time += processing_time
            
            # 记录成本
            self.cost_optimizer.record_usage(request.modality, processing_time)
            
            logger.debug(f"评估完成: {request.task_id}, 处理时间: {processing_time:.3f}s")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"评估超时: {request.task_id}")
            raise
        except Exception as e:
            logger.error(f"评估失败: {request.task_id}, 错误: {e}")
            raise
    
    async def batch_evaluate(self, requests: List[EvaluationRequest]) -> List[EvaluationResult]:
        """批量评估"""
        logger.info(f"开始批量评估，请求数量: {len(requests)}")
        
        # 按优先级排序
        sorted_requests = sorted(requests, key=lambda r: r.priority, reverse=True)
        
        # 并发执行评估
        tasks = [self.evaluate(request) for request in sorted_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量评估中的请求失败: {sorted_requests[i].task_id}, 错误: {result}")
            else:
                valid_results.append(result)
        
        logger.info(f"批量评估完成，成功: {len(valid_results)}, 失败: {len(results) - len(valid_results)}")
        
        return valid_results
    
    def create_task_specific_evaluator(self, task_type: str) -> Callable[[Any], Dict[FitnessMetric, float]]:
        """创建任务特定的评估器"""
        logger.debug(f"创建任务特定评估器: {task_type}")
        
        def evaluator(content: Any) -> Dict[FitnessMetric, float]:
            """任务特定评估函数"""
            if task_type == "code_generation":
                return self._evaluate_code_generation(content)
            elif task_type == "problem_solving":
                return self._evaluate_problem_solving(content)
            elif task_type == "creative_writing":
                return self._evaluate_creative_writing(content)
            else:
                # 默认评估
                return self._evaluate_default(content)
        
        return evaluator
    
    def _evaluate_code_generation(self, content: Any) -> Dict[FitnessMetric, float]:
        """代码生成任务评估"""
        code_str = str(content)
        
        return {
            FitnessMetric.FUNCTIONALITY: self._check_code_functionality(code_str),
            FitnessMetric.EFFICIENCY: self._check_code_efficiency(code_str),
            FitnessMetric.ROBUSTNESS: self._check_code_robustness(code_str),
            FitnessMetric.ADAPTABILITY: self._check_code_adaptability(code_str),
            FitnessMetric.NOVELTY: self._check_code_novelty(code_str),
            FitnessMetric.COMPLEXITY: self._check_code_complexity(code_str)
        }
    
    def _evaluate_problem_solving(self, content: Any) -> Dict[FitnessMetric, float]:
        """问题解决任务评估"""
        import random
        
        return {
            FitnessMetric.FUNCTIONALITY: random.uniform(0.6, 0.9),
            FitnessMetric.EFFICIENCY: random.uniform(0.5, 0.8),
            FitnessMetric.ROBUSTNESS: random.uniform(0.4, 0.7),
            FitnessMetric.ADAPTABILITY: random.uniform(0.7, 0.9),
            FitnessMetric.NOVELTY: random.uniform(0.8, 1.0),
            FitnessMetric.COMPLEXITY: random.uniform(0.3, 0.6)
        }
    
    def _evaluate_creative_writing(self, content: Any) -> Dict[FitnessMetric, float]:
        """创意写作任务评估"""
        import random
        
        return {
            FitnessMetric.FUNCTIONALITY: random.uniform(0.7, 0.9),
            FitnessMetric.EFFICIENCY: random.uniform(0.6, 0.8),
            FitnessMetric.ROBUSTNESS: random.uniform(0.5, 0.7),
            FitnessMetric.ADAPTABILITY: random.uniform(0.6, 0.8),
            FitnessMetric.NOVELTY: random.uniform(0.9, 1.0),
            FitnessMetric.COMPLEXITY: random.uniform(0.7, 0.9)
        }
    
    def _evaluate_default(self, content: Any) -> Dict[FitnessMetric, float]:
        """默认评估"""
        import random
        
        return {
            FitnessMetric.FUNCTIONALITY: random.uniform(0.5, 0.8),
            FitnessMetric.EFFICIENCY: random.uniform(0.4, 0.7),
            FitnessMetric.ROBUSTNESS: random.uniform(0.3, 0.6),
            FitnessMetric.ADAPTABILITY: random.uniform(0.4, 0.7),
            FitnessMetric.NOVELTY: random.uniform(0.6, 0.9),
            FitnessMetric.COMPLEXITY: random.uniform(0.4, 0.7)
        }
    
    def _check_code_functionality(self, code: str) -> float:
        """检查代码功能性"""
        # 基础功能检查
        functionality_indicators = ['def ', 'class ', 'return ', 'if ', 'for ', 'while ']
        score = sum(1 for indicator in functionality_indicators if indicator in code) / len(functionality_indicators)
        return min(score, 1.0)
    
    def _check_code_efficiency(self, code: str) -> float:
        """检查代码效率"""
        # 效率指标
        efficient_patterns = ['list comprehension', 'generator', 'enumerate', 'zip']
        inefficient_patterns = ['nested loop', 'repeated calculation']
        
        # 简化检查
        if 'for' in code and 'for' in code[code.find('for')+3:]:
            return 0.3  # 嵌套循环降低效率分数
        
        return 0.7  # 默认效率分数
    
    def _check_code_robustness(self, code: str) -> float:
        """检查代码鲁棒性"""
        robustness_indicators = ['try:', 'except:', 'assert', 'raise', 'isinstance']
        score = sum(1 for indicator in robustness_indicators if indicator in code) / len(robustness_indicators)
        return min(score + 0.3, 1.0)  # 基础分数 + 错误处理分数
    
    def _check_code_adaptability(self, code: str) -> float:
        """检查代码适应性"""
        adaptability_indicators = ['**kwargs', '*args', 'config', 'parameter', 'option']
        score = sum(1 for indicator in adaptability_indicators if indicator in code) / len(adaptability_indicators)
        return min(score + 0.4, 1.0)
    
    def _check_code_novelty(self, code: str) -> float:
        """检查代码新颖性"""
        import random
        # 模拟新颖性检查
        base_novelty = random.uniform(0.4, 0.8)
        
        # 基于代码复杂性调整
        if len(code) > 500:
            base_novelty += 0.1
        if 'class' in code:
            base_novelty += 0.1
        
        return min(base_novelty, 1.0)
    
    def _check_code_complexity(self, code: str) -> float:
        """检查代码复杂性"""
        # 基于代码结构计算复杂性
        complexity_indicators = ['{', '}', '(', ')', '[', ']', 'if', 'for', 'while', 'def', 'class']
        complexity_score = sum(code.count(indicator) for indicator in complexity_indicators) / len(code) if code else 0
        
        return min(complexity_score * 10, 1.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            avg_processing_time = self.total_processing_time / max(self.evaluation_count, 1)
            cache_hit_rate = self.cache_hit_count / max(self.evaluation_count, 1)
            
            return {
                "evaluation_count": self.evaluation_count,
                "cache_hit_count": self.cache_hit_count,
                "cache_hit_rate": cache_hit_rate,
                "average_processing_time": avg_processing_time,
                "total_processing_time": self.total_processing_time,
                "cache_stats": self.cache.get_stats(),
                "cost_stats": self.cost_optimizer.get_cost_stats()
            }
    
    def shutdown(self):
        """关闭系统"""
        logger.info("关闭多模态评估系统")
        self.executor.shutdown(wait=True)
        
        # 打印最终统计信息
        stats = self.get_statistics()
        logger.info(f"最终统计信息: {stats}")

# 测试代码
if __name__ == "__main__":
    async def test_multimodal_oracle():
        """测试多模态评估系统"""
        logger.info("多模态评估系统测试开始")
        
        # 创建评估系统
        oracle = MultiModalOracle()
        
        # 创建测试请求
        test_requests = [
            EvaluationRequest(
                task_id="test_text_1",
                content="def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
                modality=ModalityType.TEXT,
                context={"task_type": "code_generation"},
                priority=3
            ),
            EvaluationRequest(
                task_id="test_text_2",
                content="这是一个测试文本，用于评估文本处理能力。",
                modality=ModalityType.TEXT,
                context={"task_type": "text_analysis"},
                priority=2
            ),
            EvaluationRequest(
                task_id="test_vision_1",
                content="image_data_placeholder",
                modality=ModalityType.VISION,
                context={"task_type": "image_analysis"},
                priority=4
            )
        ]
        
        # 单个评估测试
        logger.info("测试单个评估")
        result = await oracle.evaluate(test_requests[0])
        logger.info(f"评估结果: 综合适应度={result.get_overall_fitness():.3f}, "
                   f"置信度={result.confidence:.3f}, 处理时间={result.processing_time:.3f}s")
        
        # 批量评估测试
        logger.info("测试批量评估")
        batch_results = await oracle.batch_evaluate(test_requests)
        logger.info(f"批量评估完成，结果数量: {len(batch_results)}")
        
        # 任务特定评估器测试
        logger.info("测试任务特定评估器")
        code_evaluator = oracle.create_task_specific_evaluator("code_generation")
        code_scores = code_evaluator("def hello(): print('Hello, World!')")
        logger.info(f"代码评估分数: {code_scores}")
        
        # 缓存测试
        logger.info("测试缓存功能")
        cached_result = await oracle.evaluate(test_requests[0])  # 应该命中缓存
        
        # 获取统计信息
        stats = oracle.get_statistics()
        logger.info(f"系统统计信息: {stats}")
        
        # 关闭系统
        oracle.shutdown()
        
        logger.info("多模态评估系统测试完成")
    
    # 运行测试
    asyncio.run(test_multimodal_oracle())