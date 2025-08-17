# 两数之和问题进化实验使用指南

本指南详细说明如何使用 EvoForge 项目进行两数之和问题的进化算法实验。

## 目录

- [快速开始](#快速开始)
- [详细使用说明](#详细使用说明)
- [参数配置](#参数配置)
- [实验策略](#实验策略)
- [结果分析](#结果分析)
- [故障排除](#故障排除)
- [高级用法](#高级用法)

## 快速开始

### 1. 环境准备

确保您的系统已安装 Python 3.8+ 和必要的依赖：

```bash
# 进入项目目录
cd evoforge

# 安装依赖（如果尚未安装）
pip install -r requirements.txt
```

### 2. 运行基础实验

```bash
# 使用默认配置运行两数之和进化实验
python run_two_sum_evolution.py

# 或者使用快速测试模式
python run_two_sum_evolution.py --quick
```

### 3. 查看结果

实验完成后，您将看到：
- 控制台输出的实验进度和结果
- 生成的日志文件（`two_sum_evolution_*.log`）
- 结果数据文件（`two_sum_results_*.json`）

## 详细使用说明

### 启动脚本参数

`run_two_sum_evolution.py` 脚本支持以下参数：

```bash
python run_two_sum_evolution.py [选项]
```

#### 基础选项

- `--strategy {hash,brute,auto}`：选择进化策略
  - `hash`：针对哈希表解法优化
  - `brute`：针对暴力解法优化
  - `auto`：自动选择最佳策略（默认）

- `--quick`：启用快速测试模式
  - 减少种群大小和代数
  - 适合快速验证和调试

- `--advanced`：启用高级算法模式
  - 使用 NSGA-II 多目标优化
  - 使用 Quality-Diversity (QD) 算法
  - 提高解的多样性和质量

- `--debug`：启用调试模式
  - 输出详细的调试信息
  - 记录进化过程的详细日志

- `--test-evaluator`：测试适应度评估器
  - 验证评估系统是否正常工作
  - 不运行完整的进化实验

### 使用示例

#### 示例 1：基础哈希表解法进化

```bash
python run_two_sum_evolution.py --strategy hash
```

这将：
- 使用针对哈希表解法优化的参数
- 运行 50 个个体，100 代进化
- 目标适应度为 0.95

#### 示例 2：快速暴力解法测试

```bash
python run_two_sum_evolution.py --strategy brute --quick
```

这将：
- 使用针对暴力解法的参数
- 运行 30 个个体，20 代进化
- 快速验证算法是否能改进暴力解法

#### 示例 3：高级多目标优化

```bash
python run_two_sum_evolution.py --strategy auto --advanced --debug
```

这将：
- 使用自动策略选择
- 启用 NSGA-II 和 QD 算法
- 输出详细的调试信息

#### 示例 4：测试系统

```bash
python run_two_sum_evolution.py --test-evaluator
```

这将：
- 测试适应度评估器是否正常工作
- 验证测试用例是否正确
- 不运行完整的进化过程

## 参数配置

### 进化参数说明

不同策略使用不同的进化参数：

#### 哈希表策略 (`--strategy hash`)

- **种群大小**：50（快速模式：30）
- **最大代数**：100（快速模式：20）
- **变异率**：0.1（较低，保持哈希表结构）
- **交叉率**：0.8
- **目标适应度**：0.95

#### 暴力解法策略 (`--strategy brute`)

- **种群大小**：50（快速模式：30）
- **最大代数**：100（快速模式：20）
- **变异率**：0.2（较高，探索优化空间）
- **交叉率**：0.8
- **目标适应度**：0.8

#### 自动策略 (`--strategy auto`)

- **种群大小**：50（快速模式：30）
- **最大代数**：100（快速模式：20）
- **变异率**：0.15（平衡探索和利用）
- **交叉率**：0.8
- **目标适应度**：0.9

### 适应度评估标准

适应度评估基于以下六个维度：

1. **正确性**（权重：40%）
   - 测试用例通过率
   - 边界情况处理
   - 算法正确性验证

2. **性能**（权重：25%）
   - 执行时间
   - 时间复杂度分析
   - 大数据集性能

3. **内存效率**（权重：15%）
   - 内存使用量
   - 空间复杂度
   - 内存泄漏检测

4. **代码复杂度**（权重：10%）
   - 圈复杂度
   - 代码行数
   - 嵌套深度

5. **可读性**（权重：10%）
   - 变量命名
   - 代码结构
   - 注释质量

6. **算法类型偏好**
   - 哈希表解法：加分
   - 暴力解法：减分
   - 双指针解法：加分

## 实验策略

### 选择合适的策略

#### 何时使用哈希表策略

- 目标是获得最优的 O(n) 时间复杂度解法
- 希望进化出高效的哈希表实现
- 对内存使用有一定容忍度

#### 何时使用暴力解法策略

- 研究如何优化 O(n²) 算法
- 探索暴力解法的改进空间
- 对比不同算法的性能差异

#### 何时使用自动策略

- 不确定最佳算法类型
- 希望算法自动选择最优解法
- 进行综合性能评估

### 实验设计建议

#### 对比实验

```bash
# 运行三种策略的对比实验
python run_two_sum_evolution.py --strategy hash --debug
python run_two_sum_evolution.py --strategy brute --debug  
python run_two_sum_evolution.py --strategy auto --debug
```

#### 参数敏感性分析

通过修改 `run_two_sum_evolution.py` 中的配置参数，可以研究：
- 种群大小对收敛速度的影响
- 变异率对解多样性的影响
- 交叉率对算法性能的影响

#### 长期进化实验

```bash
# 运行长期进化实验（需要修改脚本中的代数设置）
python run_two_sum_evolution.py --strategy auto --advanced
```

## 结果分析

### 日志文件分析

日志文件包含详细的进化过程信息：

```
two_sum_evolution_auto_1640995200.log
```

关键信息包括：
- 每代的最佳适应度
- 种群多样性统计
- 算法收敛情况
- 性能指标变化

### 结果数据文件

结果文件以 JSON 格式保存：

```json
{
  "success": true,
  "total_time": 120.5,
  "strategy": "auto",
  "config": {
    "population": 50,
    "generations": 100,
    "mutation_rate": 0.15
  },
  "best_individual": {
    "fitness": 0.92,
    "code": "def twoSum(nums, target): ...",
    "performance_metrics": {...}
  }
}
```

### 性能指标解读

#### 适应度分数

- **0.9+**：优秀，算法高效且正确
- **0.7-0.9**：良好，有改进空间
- **0.5-0.7**：一般，需要进一步优化
- **<0.5**：较差，可能存在正确性问题

#### 算法类型识别

系统会自动识别进化出的算法类型：
- `hash_table`：哈希表解法
- `brute_force`：暴力解法
- `two_pointers`：双指针解法
- `unknown`：未识别的算法类型

## 故障排除

### 常见问题

#### 1. 导入错误

```
错误: 无法导入两数之和适应度评估器
```

**解决方案**：
- 确保 `problems/two_sum_fitness.py` 文件存在
- 检查 Python 路径设置
- 验证依赖包是否正确安装

#### 2. 沙盒执行失败

```
沙盒执行失败: exit_code=1
```

**解决方案**：
- 检查系统资源是否充足
- 确保 Docker 或容器环境正常运行
- 查看详细错误日志

#### 3. 适应度评估器测试失败

```
适应度评估器测试失败！
```

**解决方案**：
```bash
# 运行测试诊断
python run_two_sum_evolution.py --test-evaluator --debug
```

#### 4. 进化过程收敛过慢

**解决方案**：
- 增加种群大小
- 调整变异率和交叉率
- 使用高级算法模式

### 调试技巧

#### 启用详细日志

```bash
python run_two_sum_evolution.py --debug
```

#### 检查中间结果

在实验过程中，可以查看：
- 实时日志输出
- 临时文件内容
- 沙盒执行状态

#### 单步调试

修改 `run_two_sum_evolution.py` 脚本，添加断点：

```python
import pdb; pdb.set_trace()
```

## 高级用法

### 自定义测试用例

修改 `problems/two_sum_config.py` 文件，添加自定义测试用例：

```python
def create_custom_test_cases() -> List[TwoSumTestCase]:
    return [
        TwoSumTestCase(
            nums=[1, 2, 3, 4, 5],
            target=8,
            expected=[2, 4],
            description="自定义测试用例",
            category="custom"
        )
    ]
```

### 修改适应度权重

在 `problems/two_sum_config.py` 中调整评估标准：

```python
evaluation_criteria = {
    "correctness_weight": 0.5,  # 增加正确性权重
    "performance_weight": 0.3,  # 增加性能权重
    "memory_weight": 0.1,
    "complexity_weight": 0.05,
    "readability_weight": 0.05
}
```

### 集成到现有工作流

#### 批量实验脚本

```bash
#!/bin/bash
# batch_experiments.sh

for strategy in hash brute auto; do
    echo "运行策略: $strategy"
    python run_two_sum_evolution.py --strategy $strategy --debug
    echo "策略 $strategy 完成"
done
```

#### 结果对比分析

```python
# analyze_results.py
import json
import glob

def compare_results():
    result_files = glob.glob("two_sum_results_*.json")
    for file in result_files:
        with open(file, 'r') as f:
            data = json.load(f)
            print(f"策略: {data['strategy']}, 适应度: {data.get('best_fitness', 'N/A')}")

if __name__ == "__main__":
    compare_results()
```

### 扩展到其他问题

基于两数之和的实现，可以扩展到其他 LeetCode 问题：

1. 复制 `problems/two_sum_fitness.py` 为新问题文件
2. 修改测试用例和评估逻辑
3. 创建对应的启动脚本
4. 更新配置文件

## 总结

通过本指南，您应该能够：

1. ✅ 成功运行两数之和进化实验
2. ✅ 理解不同策略的适用场景
3. ✅ 分析实验结果和性能指标
4. ✅ 解决常见问题和故障
5. ✅ 进行高级定制和扩展

如果您在使用过程中遇到问题，请：

1. 首先查看本指南的故障排除部分
2. 启用调试模式获取详细信息
3. 检查日志文件中的错误信息
4. 运行测试评估器验证系统状态

祝您实验顺利！🚀