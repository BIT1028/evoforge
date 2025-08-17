# EvoForge架构可视化图

## 🏗️ 系统架构总览

```mermaid
graph TB
    subgraph "🌐 前端层 (Frontend)"
        UI["🖥️ React UI"]
        VIS["📊 3D可视化"]
        MON["📈 监控面板"]
    end
    
    subgraph "🔌 API层 (API Gateway)"
        REST["🌍 REST API"]
        WS["⚡ WebSocket"]
        AUTH["🔐 认证中间件"]
    end
    
    subgraph "🧠 GAE核心引擎 (GAE Engine)"
        ENGINE["⚙️ 进化引擎"]
        ORACLE["🔮 LLM-Oracle"]
        CURR["📚 课程系统"]
    end
    
    subgraph "🧬 进化算法层 (Evolution Core)"
        GENOME["🧬 基因组管理"]
        OPS["🔄 遗传算子"]
        SEL["🎯 选择策略"]
        FIT["📊 适应度评估"]
    end
    
    subgraph "🔬 生物学模拟 (Bio Simulation)"
        CELL["🦠 数字细胞"]
        WORLD["🌍 虚拟世界"]
        HORMONE["💊 激素系统"]
    end
    
    subgraph "🛡️ 执行环境 (Execution)"
        SANDBOX["📦 代码沙箱"]
        EVAL["🧪 评估系统"]
        SAFE["🔒 安全检查"]
    end
    
    subgraph "💾 数据层 (Data Layer)"
        DB["🗄️ 数据库"]
        CACHE["⚡ 缓存"]
        LOG["📝 日志系统"]
    end

    %% 连接关系
    UI --> REST
    VIS --> WS
    MON --> REST
    
    REST --> ENGINE
    WS --> ENGINE
    AUTH --> REST
    
    ENGINE --> GENOME
    ENGINE --> CELL
    ENGINE --> SANDBOX
    
    ORACLE --> FIT
    CURR --> ENGINE
    
    GENOME --> OPS
    OPS --> SEL
    SEL --> FIT
    
    CELL --> WORLD
    CELL --> HORMONE
    
    SANDBOX --> EVAL
    EVAL --> SAFE
    
    ENGINE --> DB
    ENGINE --> CACHE
    ENGINE --> LOG

    %% 样式定义
    classDef completed fill:#90EE90,stroke:#006400,stroke-width:2px
    classDef partial fill:#FFD700,stroke:#FF8C00,stroke-width:2px
    classDef problematic fill:#FFB6C1,stroke:#DC143C,stroke-width:2px
    classDef missing fill:#D3D3D3,stroke:#696969,stroke-width:2px
    
    %% 应用样式
    class GENOME,OPS,SEL,SANDBOX completed
    class ENGINE,CELL,REST,UI partial
    class VIS,WS,ORACLE problematic
    class CURR,SAFE missing
```

## 📊 模块状态详细分析

### ✅ 已完成模块 (绿色)
- **基因组管理** (`genome.py`) - 完整实现
- **遗传算子** (`operators.py`) - 交叉变异完备
- **选择策略** (`selection.py`) - 多种算法支持
- **代码沙箱** (`sandbox.py`) - 安全执行环境

### 🟡 部分完成模块 (黄色)
- **进化引擎** (`engine.py`) - 核心功能完成，需重构
- **数字细胞** (`consciousness.py`) - 基础模拟完成
- **REST API** - 基本接口可用
- **React UI** - 主要页面完成

### 🔴 问题模块 (红色)
- **3D可视化** - Three.js集成问题
- **WebSocket** - 连接不稳定
- **LLM-Oracle** - 实现不完整

### ⚪ 缺失模块 (灰色)
- **课程系统** - 未开始实现
- **安全检查** - 代码安全扫描缺失

---

## 🔄 数据流图

```mermaid
flowchart LR
    subgraph "输入层"
        TASK["📋 任务定义"]
        CONFIG["⚙️ 配置参数"]
        TESTS["🧪 测试用例"]
    end
    
    subgraph "处理层"
        INIT["🌱 种群初始化"]
        EVAL["📊 适应度评估"]
        SELECT["🎯 选择操作"]
        CROSS["🔄 交叉操作"]
        MUTATE["🎲 变异操作"]
        REPLACE["🔄 环境选择"]
    end
    
    subgraph "输出层"
        BEST["🏆 最优个体"]
        STATS["📈 统计数据"]
        HISTORY["📚 进化历史"]
    end
    
    TASK --> INIT
    CONFIG --> INIT
    TESTS --> EVAL
    
    INIT --> EVAL
    EVAL --> SELECT
    SELECT --> CROSS
    CROSS --> MUTATE
    MUTATE --> EVAL
    EVAL --> REPLACE
    REPLACE --> SELECT
    
    SELECT --> BEST
    EVAL --> STATS
    REPLACE --> HISTORY
    
    %% 循环箭头
    REPLACE -.-> SELECT
```

---

## 🧬 生物学模拟架构

```mermaid
graph TD
    subgraph "🦠 数字细胞内部结构"
        MEMBRANE["🧱 细胞膜<br/>离子通道/膜电位"]
        NUCLEUS["🧬 细胞核<br/>基因组/转录"]
        CYTOPLASM["🌊 细胞质<br/>蛋白质/代谢"]
        ORGANELLE["🏭 细胞器<br/>线粒体/内质网"]
    end
    
    subgraph "🌍 虚拟世界环境"
        RESOURCES["💎 资源分布"]
        PHYSICS["⚛️ 物理规律"]
        ECOLOGY["🌱 生态系统"]
    end
    
    subgraph "💊 激素系统"
        SIGNALS["📡 信号分子"]
        RECEPTORS["🔗 受体蛋白"]
        CASCADE["⛓️ 信号级联"]
    end
    
    MEMBRANE <--> CYTOPLASM
    NUCLEUS --> CYTOPLASM
    CYTOPLASM <--> ORGANELLE
    
    MEMBRANE <--> SIGNALS
    SIGNALS <--> RECEPTORS
    RECEPTORS --> CASCADE
    
    CYTOPLASM <--> RESOURCES
    MEMBRANE <--> PHYSICS
    ORGANELLE <--> ECOLOGY
```

---

## 🔧 技术栈架构

```mermaid
graph TB
    subgraph "前端技术栈"
        REACT["⚛️ React 18"]
        THREE["🎮 Three.js"]
        CHART["📊 Chart.js"]
        TAILWIND["🎨 Tailwind CSS"]
    end
    
    subgraph "后端技术栈"
        FASTAPI["🚀 FastAPI"]
        ASYNCIO["⚡ AsyncIO"]
        NUMPY["🔢 NumPy"]
        SCIPY["🧮 SciPy"]
    end
    
    subgraph "AI/ML技术栈"
        OPENAI["🤖 OpenAI API"]
        ANTHROPIC["🧠 Anthropic"]
        TORCH["🔥 PyTorch"]
        SKLEARN["📚 Scikit-learn"]
    end
    
    subgraph "基础设施"
        DOCKER["🐳 Docker"]
        REDIS["⚡ Redis"]
        POSTGRES["🐘 PostgreSQL"]
        NGINX["🌐 Nginx"]
    end
    
    REACT --> FASTAPI
    THREE --> FASTAPI
    FASTAPI --> OPENAI
    FASTAPI --> TORCH
    FASTAPI --> REDIS
    FASTAPI --> POSTGRES
```

---

## 🚀 部署架构

```mermaid
graph TB
    subgraph "开发环境"
        DEV_FE["前端开发服务器<br/>:3000"]
        DEV_BE["后端开发服务器<br/>:8000"]
        DEV_DB["本地数据库<br/>:5432"]
    end
    
    subgraph "生产环境"
        LB["🔄 负载均衡器"]
        FE_PROD["前端生产服务器"]
        BE_PROD["后端生产服务器"]
        DB_PROD["生产数据库集群"]
        CACHE_PROD["Redis缓存集群"]
    end
    
    subgraph "监控系统"
        METRICS["📊 性能监控"]
        LOGS["📝 日志聚合"]
        ALERTS["🚨 告警系统"]
    end
    
    DEV_FE -.-> FE_PROD
    DEV_BE -.-> BE_PROD
    DEV_DB -.-> DB_PROD
    
    LB --> FE_PROD
    LB --> BE_PROD
    BE_PROD --> DB_PROD
    BE_PROD --> CACHE_PROD
    
    FE_PROD --> METRICS
    BE_PROD --> LOGS
    DB_PROD --> ALERTS
```

---

## 📈 性能监控架构

```mermaid
graph LR
    subgraph "数据收集"
        APP_METRICS["应用指标"]
        SYS_METRICS["系统指标"]
        USER_METRICS["用户行为"]
    end
    
    subgraph "数据处理"
        COLLECTOR["数据收集器"]
        PROCESSOR["数据处理器"]
        AGGREGATOR["数据聚合器"]
    end
    
    subgraph "数据存储"
        TSDB["时序数据库"]
        SEARCH["搜索引擎"]
        WAREHOUSE["数据仓库"]
    end
    
    subgraph "数据展示"
        DASHBOARD["实时仪表板"]
        REPORTS["定期报告"]
        ALERTS["告警通知"]
    end
    
    APP_METRICS --> COLLECTOR
    SYS_METRICS --> COLLECTOR
    USER_METRICS --> COLLECTOR
    
    COLLECTOR --> PROCESSOR
    PROCESSOR --> AGGREGATOR
    
    AGGREGATOR --> TSDB
    AGGREGATOR --> SEARCH
    AGGREGATOR --> WAREHOUSE
    
    TSDB --> DASHBOARD
    SEARCH --> REPORTS
    WAREHOUSE --> ALERTS
```

---

## 🔄 CI/CD流水线

```mermaid
graph LR
    subgraph "开发阶段"
        CODE["💻 代码提交"]
        REVIEW["👀 代码审查"]
        MERGE["🔀 合并请求"]
    end
    
    subgraph "构建阶段"
        BUILD["🔨 构建"]
        TEST["🧪 测试"]
        SCAN["🔍 安全扫描"]
    end
    
    subgraph "部署阶段"
        STAGING["🎭 预发布"]
        PROD["🚀 生产部署"]
        MONITOR["📊 监控"]
    end
    
    CODE --> REVIEW
    REVIEW --> MERGE
    MERGE --> BUILD
    BUILD --> TEST
    TEST --> SCAN
    SCAN --> STAGING
    STAGING --> PROD
    PROD --> MONITOR
    
    MONITOR -.-> CODE
```

---

**图表说明**:
- 🟢 绿色: 功能完整，运行稳定
- 🟡 黄色: 基本功能完成，需要优化
- 🔴 红色: 存在问题，需要修复
- ⚪ 灰色: 功能缺失，需要实现

**更新时间**: 2024年12月19日  
**版本**: v1.0