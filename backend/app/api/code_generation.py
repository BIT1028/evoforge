from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import time
import random
import uuid
from datetime import datetime

router = APIRouter()

# 数据模型
class GeneratedCode(BaseModel):
    id: str
    timestamp: int
    language: str
    code: str
    fitness: float
    generation: int
    parent_ids: List[str]
    mutations: List[str]
    performance: Dict[str, float]
    metadata: Dict[str, int]

class CodeGenerationStats(BaseModel):
    total_generated: int
    successful_compilations: int
    average_fitness: float
    best_fitness: float
    language_distribution: Dict[str, int]
    generation_trends: List[Dict[str, Any]]

class CodeGenerationRequest(BaseModel):
    language: Optional[str] = "python"
    target_function: Optional[str] = "optimization"
    complexity_level: Optional[int] = 5
    population_size: Optional[int] = 10

# 模拟数据存储
generated_codes: List[GeneratedCode] = []
code_stats = CodeGenerationStats(
    total_generated=0,
    successful_compilations=0,
    average_fitness=0.0,
    best_fitness=0.0,
    language_distribution={},
    generation_trends=[]
)

# 代码模板
CODE_TEMPLATES = {
    "python": {
        "sorting": '''def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quick_sort(left) + middle + quick_sort(right)

# 测试函数
if __name__ == "__main__":
    test_array = [3, 6, 8, 10, 1, 2, 1]
    sorted_array = quick_sort(test_array)
    print(f"Sorted array: {sorted_array}")''',
        "optimization": '''import numpy as np
from typing import List, Tuple

def genetic_algorithm(fitness_func, bounds: List[Tuple[float, float]], 
                     population_size: int = 50, generations: int = 100):
    """
    遗传算法优化函数
    """
    # 初始化种群
    population = []
    for _ in range(population_size):
        individual = []
        for low, high in bounds:
            individual.append(random.uniform(low, high))
        population.append(individual)
    
    best_fitness = float('-inf')
    best_individual = None
    
    for generation in range(generations):
        # 评估适应度
        fitness_scores = [fitness_func(ind) for ind in population]
        
        # 记录最佳个体
        max_fitness_idx = np.argmax(fitness_scores)
        if fitness_scores[max_fitness_idx] > best_fitness:
            best_fitness = fitness_scores[max_fitness_idx]
            best_individual = population[max_fitness_idx].copy()
        
        # 选择、交叉、变异
        new_population = []
        for _ in range(population_size):
            # 锦标赛选择
            parent1 = tournament_selection(population, fitness_scores)
            parent2 = tournament_selection(population, fitness_scores)
            
            # 交叉
            child = crossover(parent1, parent2)
            
            # 变异
            child = mutate(child, bounds)
            
            new_population.append(child)
        
        population = new_population
    
    return best_individual, best_fitness

def tournament_selection(population, fitness_scores, tournament_size=3):
    tournament_indices = random.sample(range(len(population)), tournament_size)
    tournament_fitness = [fitness_scores[i] for i in tournament_indices]
    winner_idx = tournament_indices[np.argmax(tournament_fitness)]
    return population[winner_idx]

def crossover(parent1, parent2, crossover_rate=0.8):
    if random.random() > crossover_rate:
        return parent1.copy()
    
    child = []
    for i in range(len(parent1)):
        if random.random() < 0.5:
            child.append(parent1[i])
        else:
            child.append(parent2[i])
    return child

def mutate(individual, bounds, mutation_rate=0.1):
    mutated = individual.copy()
    for i in range(len(mutated)):
        if random.random() < mutation_rate:
            low, high = bounds[i]
            mutated[i] = random.uniform(low, high)
    return mutated''',
        "neural_network": '''import numpy as np

class NeuralNetwork:
    def __init__(self, layers):
        self.layers = layers
        self.weights = []
        self.biases = []
        
        # 初始化权重和偏置
        for i in range(len(layers) - 1):
            w = np.random.randn(layers[i], layers[i + 1]) * 0.1
            b = np.zeros((1, layers[i + 1]))
            self.weights.append(w)
            self.biases.append(b)
    
    def sigmoid(self, x):
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def sigmoid_derivative(self, x):
        return x * (1 - x)
    
    def forward(self, X):
        self.activations = [X]
        
        for i in range(len(self.weights)):
            z = np.dot(self.activations[-1], self.weights[i]) + self.biases[i]
            a = self.sigmoid(z)
            self.activations.append(a)
        
        return self.activations[-1]
    
    def backward(self, X, y, learning_rate=0.01):
        m = X.shape[0]
        
        # 计算输出层误差
        delta = self.activations[-1] - y
        
        # 反向传播
        for i in range(len(self.weights) - 1, -1, -1):
            # 计算梯度
            dW = np.dot(self.activations[i].T, delta) / m
            db = np.sum(delta, axis=0, keepdims=True) / m
            
            # 更新权重和偏置
            self.weights[i] -= learning_rate * dW
            self.biases[i] -= learning_rate * db
            
            # 计算前一层的误差
            if i > 0:
                delta = np.dot(delta, self.weights[i].T) * self.sigmoid_derivative(self.activations[i])
    
    def train(self, X, y, epochs=1000, learning_rate=0.01):
        for epoch in range(epochs):
            output = self.forward(X)
            self.backward(X, y, learning_rate)
            
            if epoch % 100 == 0:
                loss = np.mean((output - y) ** 2)
                print(f"Epoch {epoch}, Loss: {loss:.4f}")'''
    },
    "javascript": {
        "sorting": '''function mergeSort(arr) {
    if (arr.length <= 1) {
        return arr;
    }
    
    const mid = Math.floor(arr.length / 2);
    const left = mergeSort(arr.slice(0, mid));
    const right = mergeSort(arr.slice(mid));
    
    return merge(left, right);
}

function merge(left, right) {
    let result = [];
    let leftIndex = 0;
    let rightIndex = 0;
    
    while (leftIndex < left.length && rightIndex < right.length) {
        if (left[leftIndex] < right[rightIndex]) {
            result.push(left[leftIndex]);
            leftIndex++;
        } else {
            result.push(right[rightIndex]);
            rightIndex++;
        }
    }
    
    return result.concat(left.slice(leftIndex)).concat(right.slice(rightIndex));
}

// 测试
const testArray = [64, 34, 25, 12, 22, 11, 90];
console.log("Original array:", testArray);
console.log("Sorted array:", mergeSort(testArray));''',
        "optimization": '''class GeneticAlgorithm {
    constructor(populationSize = 50, mutationRate = 0.01, crossoverRate = 0.8) {
        this.populationSize = populationSize;
        this.mutationRate = mutationRate;
        this.crossoverRate = crossoverRate;
    }
    
    // 初始化种群
    initializePopulation(geneLength, bounds) {
        const population = [];
        for (let i = 0; i < this.populationSize; i++) {
            const individual = [];
            for (let j = 0; j < geneLength; j++) {
                const [min, max] = bounds[j] || [0, 1];
                individual.push(Math.random() * (max - min) + min);
            }
            population.push(individual);
        }
        return population;
    }
    
    // 锦标赛选择
    tournamentSelection(population, fitnessScores, tournamentSize = 3) {
        const tournament = [];
        for (let i = 0; i < tournamentSize; i++) {
            const randomIndex = Math.floor(Math.random() * population.length);
            tournament.push({ individual: population[randomIndex], fitness: fitnessScores[randomIndex] });
        }
        
        tournament.sort((a, b) => b.fitness - a.fitness);
        return tournament[0].individual;
    }
    
    // 交叉操作
    crossover(parent1, parent2) {
        if (Math.random() > this.crossoverRate) {
            return [...parent1];
        }
        
        const crossoverPoint = Math.floor(Math.random() * parent1.length);
        const child = [...parent1.slice(0, crossoverPoint), ...parent2.slice(crossoverPoint)];
        return child;
    }
    
    // 变异操作
    mutate(individual, bounds) {
        const mutated = [...individual];
        for (let i = 0; i < mutated.length; i++) {
            if (Math.random() < this.mutationRate) {
                const [min, max] = bounds[i] || [0, 1];
                mutated[i] = Math.random() * (max - min) + min;
            }
        }
        return mutated;
    }
    
    // 主要的遗传算法函数
    evolve(fitnessFunction, geneLength, bounds, generations = 100) {
        let population = this.initializePopulation(geneLength, bounds);
        let bestIndividual = null;
        let bestFitness = -Infinity;
        
        for (let generation = 0; generation < generations; generation++) {
            // 计算适应度
            const fitnessScores = population.map(individual => fitnessFunction(individual));
            
            // 更新最佳个体
            const maxFitnessIndex = fitnessScores.indexOf(Math.max(...fitnessScores));
            if (fitnessScores[maxFitnessIndex] > bestFitness) {
                bestFitness = fitnessScores[maxFitnessIndex];
                bestIndividual = [...population[maxFitnessIndex]];
            }
            
            // 生成新种群
            const newPopulation = [];
            for (let i = 0; i < this.populationSize; i++) {
                const parent1 = this.tournamentSelection(population, fitnessScores);
                const parent2 = this.tournamentSelection(population, fitnessScores);
                let child = this.crossover(parent1, parent2);
                child = this.mutate(child, bounds);
                newPopulation.push(child);
            }
            
            population = newPopulation;
        }
        
        return { bestIndividual, bestFitness };
    }
}'''
    }
}

def generate_code_sample(language: str, template_type: str) -> str:
    """生成代码样本"""
    templates = CODE_TEMPLATES.get(language, {})
    if template_type in templates:
        return templates[template_type]
    
    # 默认返回优化算法模板
    return templates.get("optimization", "# 代码生成中...")

def calculate_code_fitness(code: str, language: str) -> float:
    """计算代码适应度分数"""
    # 基础分数
    fitness = 50.0
    
    # 代码长度评分
    lines = code.split('\n')
    line_count = len([line for line in lines if line.strip()])
    
    if 10 <= line_count <= 100:
        fitness += 20
    elif line_count > 100:
        fitness += 10
    
    # 函数数量评分
    if language == "python":
        function_count = code.count('def ')
        class_count = code.count('class ')
    elif language == "javascript":
        function_count = code.count('function ') + code.count('=>')
        class_count = code.count('class ')
    else:
        function_count = 1
        class_count = 0
    
    fitness += min(function_count * 5, 20)
    fitness += min(class_count * 10, 20)
    
    # 注释评分
    comment_count = code.count('#') + code.count('//')
    fitness += min(comment_count * 2, 10)
    
    # 添加随机变化
    fitness += random.uniform(-5, 5)
    
    return min(max(fitness, 0), 100)

def update_code_stats():
    """更新代码生成统计"""
    global code_stats
    
    if not generated_codes:
        return
    
    total = len(generated_codes)
    successful = int(total * random.uniform(0.7, 0.9))  # 模拟编译成功率
    
    fitness_scores = [code.fitness for code in generated_codes]
    avg_fitness = sum(fitness_scores) / len(fitness_scores)
    best_fitness = max(fitness_scores)
    
    # 语言分布
    lang_dist = {}
    for code in generated_codes:
        lang_dist[code.language] = lang_dist.get(code.language, 0) + 1
    
    code_stats = CodeGenerationStats(
        total_generated=total,
        successful_compilations=successful,
        average_fitness=avg_fitness,
        best_fitness=best_fitness,
        language_distribution=lang_dist,
        generation_trends=[]
    )

@router.get("/codes", response_model=List[GeneratedCode])
async def get_generated_codes(language: Optional[str] = None, limit: int = 50):
    """获取生成的代码列表"""
    codes = generated_codes[:limit]
    
    if language:
        codes = [code for code in codes if code.language == language]
    
    return codes

@router.get("/stats", response_model=CodeGenerationStats)
async def get_code_generation_stats():
    """获取代码生成统计信息"""
    update_code_stats()
    return code_stats

@router.post("/generate", response_model=GeneratedCode)
async def generate_code(request: CodeGenerationRequest, background_tasks: BackgroundTasks):
    """生成新代码"""
    # 选择模板类型
    template_types = ["sorting", "optimization", "neural_network"]
    template_type = random.choice(template_types)
    
    # 生成代码
    code = generate_code_sample(request.language, template_type)
    
    # 计算适应度
    fitness = calculate_code_fitness(code, request.language)
    
    # 生成变异操作
    mutations = []
    mutation_types = ["变量重命名", "函数优化", "算法改进", "性能优化", "代码重构"]
    num_mutations = random.randint(1, 3)
    mutations = random.sample(mutation_types, num_mutations)
    
    # 创建代码对象
    lines = code.split('\n')
    line_count = len([line for line in lines if line.strip()])
    
    if request.language == "python":
        function_count = code.count('def ')
        class_count = code.count('class ')
        comment_count = code.count('#')
    elif request.language == "javascript":
        function_count = code.count('function ') + code.count('=>')
        class_count = code.count('class ')
        comment_count = code.count('//')
    else:
        function_count = 1
        class_count = 0
        comment_count = 0
    
    new_code = GeneratedCode(
        id=f"code-{uuid.uuid4().hex[:8]}",
        timestamp=int(time.time() * 1000),
        language=request.language,
        code=code,
        fitness=fitness,
        generation=random.randint(1, 100),
        parent_ids=[],
        mutations=mutations,
        performance={
            "execution_time": random.uniform(1, 100),
            "memory_usage": random.uniform(1, 50),
            "complexity": random.uniform(1, 10)
        },
        metadata={
            "line_count": line_count,
            "function_count": function_count,
            "class_count": class_count,
            "comments": comment_count
        }
    )
    
    # 添加到列表
    generated_codes.insert(0, new_code)
    
    # 保持最多100个代码
    if len(generated_codes) > 100:
        generated_codes.pop()
    
    # 后台更新统计
    background_tasks.add_task(update_code_stats)
    
    return new_code

@router.delete("/codes/{code_id}")
async def delete_code(code_id: str):
    """删除指定代码"""
    global generated_codes
    
    original_length = len(generated_codes)
    generated_codes = [code for code in generated_codes if code.id != code_id]
    
    if len(generated_codes) == original_length:
        raise HTTPException(status_code=404, detail="代码未找到")
    
    update_code_stats()
    return {"message": "代码已删除"}

@router.get("/languages")
async def get_supported_languages():
    """获取支持的编程语言列表"""
    return {
        "languages": list(CODE_TEMPLATES.keys()),
        "templates": {lang: list(templates.keys()) for lang, templates in CODE_TEMPLATES.items()}
    }

# 初始化一些示例代码
async def initialize_sample_codes():
    """初始化示例代码"""
    sample_requests = [
        CodeGenerationRequest(language="python", target_function="optimization"),
        CodeGenerationRequest(language="javascript", target_function="sorting"),
        CodeGenerationRequest(language="python", target_function="neural_network"),
    ]
    
    for request in sample_requests:
        await generate_code(request, BackgroundTasks())

# 启动时初始化示例数据
@router.on_event("startup")
async def startup_event():
    await initialize_sample_codes()