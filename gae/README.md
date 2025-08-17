# EvoForge 数字生命进化系统

基于 comprehensive_implementation_plan.md 文档完全重新实现的数字生命进化系统。

## 系统概述

EvoForge 是一个先进的数字生命进化系统，通过模拟细胞生物学过程来探索智能涌现规律。系统采用模块化架构，集成了分子系统、细胞模拟、基因表达、进化算法、多模态评估和安全执行等核心组件。

## 核心特性

### 🧬 MacroMolecule 分子系统
- **六种分子类型**: Protein、mRNA、tRNA、Lipid、ResourceToken、EnergyToken
- **物理模拟**: 布朗运动、碰撞检测、分子交互
- **结合位点系统**: 结合亲和力、特异性识别、动态结合/解离
- **催化逻辑**: 蛋白质催化功能、反应速率、底物特异性

### 🔬 DigitalCell 细胞系统
- **3D空间物理模拟器**: 完整的细胞环境模拟
- **细胞器系统**: Nucleus、Mitochondrion、Ribosome、ProteinProcessor
- **分子容器和索引**: 高效的分子管理和查找
- **生命周期循环**: 分子运动、交互、表达、催化、降解
- **糖蛋白系统**: 细胞间识别和交互机制

### 🧪 基因表达系统
- **完整转录翻译流程**: DNA → mRNA → 蛋白质
- **转录调控机制**: 基因表达的精确控制
- **激素影响因子**: 环境对基因表达的调节
- **安全代码执行**: 沙箱环境中的安全基因表达
- **错误处理和验证**: 翻译错误处理和基因完整性验证

### 🚀 增强型进化引擎
- **多算法集成**: NEAT、NSGA-II、QD算法
- **多目标优化**: 帕累托前沿计算
- **LLM辅助变异**: 智能变异策略
- **种群管理**: 完整的进化循环控制
- **并行评估**: 高效的适应度评估

### 🎯 多模态评估系统
- **多模态集成**: 文本、视觉、音频模型
- **六维度评估**: 复杂性、效率、稳定性、创新性、适应性、鲁棒性
- **智能缓存**: 评估结果缓存和成本优化
- **任务特定函数**: 针对不同任务的适应度函数

### 🔒 安全沙箱系统
- **多层沙箱**: Docker + WebAssembly + 权限控制
- **资源限制**: CPU、内存、网络隔离
- **动态权限控制**: 基于安全级别的权限管理
- **威胁检测**: 代码验证和安全检查

## 系统架构

```
gae/
├── digital_cell/           # 数字细胞核心模块
│   ├── macro_molecule.py   # 分子系统
│   ├── digital_cell.py     # 细胞模拟
│   └── gene_expression.py  # 基因表达
├── engine/                 # 进化引擎
│   └── engine.py          # 增强型进化引擎
├── llm_oracle/            # 多模态评估
│   └── fitness.py         # 适应度评估系统
├── sandbox/               # 安全沙箱
│   └── secure_executor.py # 安全执行器
├── config/                # 配置管理
│   └── config_manager.py  # 配置管理器
├── core/                  # 核心基础设施
│   ├── module_coordinator.py  # 模块协调器
│   ├── logging_system.py     # 日志系统
│   └── error_handler.py      # 错误处理
├── main.py                # 主系统启动器
├── start_system.py        # 简化启动脚本
└── README.md              # 本文档
```

## 快速开始

### 1. 环境要求

- Python 3.8+
- 推荐使用虚拟环境

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install numpy scipy matplotlib pandas
pip install dataclasses typing-extensions
pip install psutil docker
```

### 3. 快速启动

#### 方式一：使用简化启动脚本

```bash
cd gae
python start_system.py
```

选择选项：
- `1` - 快速测试：自动测试所有系统功能
- `2` - 交互式启动：进入交互模式
- `3` - 退出

#### 方式二：使用主启动器

```bash
cd gae

# 启动交互模式
python main.py --interactive

# 显示系统状态
python main.py --status

# 运行实验
python main.py --experiment experiments/test_experiment.json

# 查看帮助
python main.py --help
```

### 4. 交互模式命令

进入交互模式后，可以使用以下命令：

- `status` - 显示系统状态
- `health` - 显示健康状态
- `errors` - 显示错误统计
- `molecules <count>` - 创建测试分子
- `experiment <name>` - 运行进化实验
- `help` - 显示帮助
- `quit` - 退出

## 配置说明

### 系统配置文件

系统配置文件位于 `config/system_config.json`，包含以下主要配置：

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "evoforge"
  },
  "logging": {
    "level": "INFO",
    "format": "detailed",
    "file_path": "logs/evoforge.log"
  },
  "security": {
    "enable_sandbox": true,
    "max_execution_time": 30,
    "max_memory_mb": 512
  },
  "modules": {
    "digital_cell": {
      "enabled": true,
      "max_molecules": 10000,
      "simulation_step": 0.01
    }
  }
}
```

### 实验配置文件

实验配置文件位于 `experiments/` 目录，定义进化实验的参数：

```json
{
  "name": "test_experiment",
  "type": "evolution",
  "parameters": {
    "population_size": 20,
    "generations": 10,
    "mutation_rate": 0.15
  },
  "fitness_function": {
    "type": "multi_objective",
    "objectives": ["complexity", "efficiency", "stability"]
  }
}
```

## 开发指南

### 添加新的分子类型

1. 在 `digital_cell/macro_molecule.py` 中继承 `MacroMolecule` 基类
2. 实现必要的方法：`interact_with`、`catalyze`、`degrade`
3. 在 `MoleculeType` 枚举中添加新类型
4. 更新 `create_molecule` 工厂函数

### 添加新的细胞器

1. 在 `digital_cell/digital_cell.py` 中继承 `Organelle` 基类
2. 实现 `process_molecules` 方法
3. 在 `DigitalCell` 类中注册新细胞器

### 添加新的进化算法

1. 在 `engine/engine.py` 中实现新的算法类
2. 继承适当的基类或接口
3. 在 `EnhancedEvolutionEngine` 中集成新算法

### 添加新的评估维度

1. 在 `llm_oracle/fitness.py` 中扩展评估函数
2. 更新 `MultiModalOracle` 类的评估逻辑
3. 添加相应的缓存和优化策略

## 调试和监控

### 日志系统

系统提供了完整的日志记录功能：

- **控制台输出**: 实时查看系统状态
- **文件日志**: 详细的历史记录
- **性能监控**: 资源使用情况追踪
- **错误追踪**: 异常和错误的详细记录

### 性能监控

```python
# 获取系统状态
status = system.get_status()
print(f"运行时间: {status['system']['uptime_seconds']}秒")
print(f"错误计数: {status['system']['error_count']}")
```

### 错误处理

系统提供了多层错误处理机制：

- **自动恢复**: 常见错误的自动恢复
- **断路器模式**: 防止级联故障
- **健康检查**: 定期系统健康状态检查
- **故障诊断**: 详细的故障信息收集

## 实验示例

### 基础进化实验

```python
# 创建系统实例
system = EvoForgeSystem()
system.start()

# 定义实验配置
experiment_config = {
    "name": "basic_evolution",
    "parameters": {
        "population_size": 50,
        "generations": 20,
        "mutation_rate": 0.1
    }
}

# 运行实验
result = system.run_evolution_experiment(experiment_config)
print(f"实验结果: {result}")

# 关闭系统
system.shutdown()
```

### 分子交互实验

```python
# 创建测试分子
molecules = system.create_test_molecules(10)

# 添加到细胞中
for molecule in molecules:
    system.digital_cell.add_molecule(molecule)

# 运行模拟步骤
for step in range(100):
    system.digital_cell.simulate_step()
    
    # 记录状态
    if step % 10 == 0:
        status = system.digital_cell.get_status()
        print(f"步骤 {step}: 分子数量 = {status['molecule_count']}")
```

## 故障排除

### 常见问题

1. **系统启动失败**
   - 检查Python版本（需要3.8+）
   - 确认所有依赖已安装
   - 查看日志文件中的错误信息

2. **模块加载失败**
   - 检查模块依赖关系
   - 确认配置文件格式正确
   - 查看模块协调器的状态

3. **实验运行错误**
   - 验证实验配置文件格式
   - 检查参数范围是否合理
   - 查看进化引擎的错误日志

4. **性能问题**
   - 调整系统配置中的资源限制
   - 启用性能监控查看瓶颈
   - 考虑减少分子数量或简化模拟

### 调试技巧

1. **启用详细日志**
   ```bash
   python main.py --debug --verbose
   ```

2. **查看系统状态**
   ```bash
   python main.py --status
   ```

3. **运行快速测试**
   ```bash
   python start_system.py
   # 选择选项 1
   ```

## 贡献指南

1. **代码规范**
   - 遵循PEP 8编码规范
   - 添加详细的函数和类文档
   - 包含类型注解
   - 添加适当的错误处理

2. **测试要求**
   - 为新功能添加单元测试
   - 确保所有测试通过
   - 添加集成测试验证模块交互

3. **文档更新**
   - 更新相关的API文档
   - 添加使用示例
   - 更新配置说明

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目仓库: [EvoForge GitHub](https://github.com/your-org/evoforge)
- 问题报告: [GitHub Issues](https://github.com/your-org/evoforge/issues)
- 邮箱: evoforge@example.com

---

**EvoForge** - 探索数字生命的无限可能