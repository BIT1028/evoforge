# EvoForge 项目运行流程图

## 概述

本文档详细描述了 EvoForge 项目的完整运行流程，包括启动脚本 Build.bat 的执行流程、系统初始化过程、服务启动顺序和运行时架构。

## 1. Build.bat 启动流程图

### 1.1 主启动流程

```mermaid
flowchart TD
    START([启动 Build.bat]) --> BANNER[显示喀迈拉计划横幅]
    BANNER --> MENU[显示操作菜单]
    
    MENU --> CHOICE{用户选择}
    
    %% 开发模式 (选项1)
    CHOICE --> |1| DEV_MODE[开发模式]
    DEV_MODE --> CHECK_DEPS1[检查依赖]
    CHECK_DEPS1 --> INSTALL_DEPS1[安装依赖]
    INSTALL_DEPS1 --> START_BACKEND1[启动后端服务]
    START_BACKEND1 --> START_FRONTEND1[启动前端服务]
    START_FRONTEND1 --> DEV_RUNNING[开发环境运行中]
    
    %% 生产模式 (选项2)
    CHOICE --> |2| PROD_MODE[生产模式]
    PROD_MODE --> CHECK_DEPS2[检查依赖]
    CHECK_DEPS2 --> BUILD_PROD[构建生产版本]
    BUILD_PROD --> DOCKER_BUILD[Docker构建]
    DOCKER_BUILD --> DOCKER_COMPOSE[启动Docker Compose]
    DOCKER_COMPOSE --> PROD_RUNNING[生产环境运行中]
    
    %% 仅后端 (选项3)
    CHOICE --> |3| BACKEND_ONLY[仅启动后端]
    BACKEND_ONLY --> CHECK_BACKEND[检查后端依赖]
    CHECK_BACKEND --> START_BACKEND_ONLY[启动后端服务]
    START_BACKEND_ONLY --> BACKEND_RUNNING[后端服务运行中]
    
    %% 仅前端 (选项4)
    CHOICE --> |4| FRONTEND_ONLY[仅启动前端]
    FRONTEND_ONLY --> CHECK_FRONTEND[检查前端依赖]
    CHECK_FRONTEND --> START_FRONTEND_ONLY[启动前端服务]
    START_FRONTEND_ONLY --> FRONTEND_RUNNING[前端服务运行中]
    
    %% 初始化项目 (选项5)
    CHOICE --> |5| INIT_PROJECT[初始化项目]
    INIT_PROJECT --> SETUP_ENV[设置环境变量]
    SETUP_ENV --> INSTALL_ALL_DEPS[安装所有依赖]
    INSTALL_ALL_DEPS --> SETUP_DATABASE[设置数据库]
    SETUP_DATABASE --> INIT_CONFIG[初始化配置]
    INIT_CONFIG --> INIT_COMPLETE[初始化完成]
    
    %% 清理项目 (选项6)
    CHOICE --> |6| CLEAN_PROJECT[清理项目]
    CLEAN_PROJECT --> STOP_SERVICES[停止所有服务]
    STOP_SERVICES --> CLEAN_CACHE[清理缓存]
    CLEAN_CACHE --> CLEAN_LOGS[清理日志]
    CLEAN_LOGS --> CLEAN_TEMP[清理临时文件]
    CLEAN_TEMP --> CLEAN_COMPLETE[清理完成]
    
    %% 退出 (选项7)
    CHOICE --> |7| EXIT[退出程序]
    EXIT --> END([结束])
    
    %% 运行状态循环
    DEV_RUNNING --> MONITOR1[监控服务状态]
    PROD_RUNNING --> MONITOR2[监控服务状态]
    BACKEND_RUNNING --> MONITOR3[监控后端状态]
    FRONTEND_RUNNING --> MONITOR4[监控前端状态]
    
    MONITOR1 --> |服务异常| RESTART1[重启服务]
    MONITOR2 --> |服务异常| RESTART2[重启服务]
    MONITOR3 --> |服务异常| RESTART3[重启后端]
    MONITOR4 --> |服务异常| RESTART4[重启前端]
    
    RESTART1 --> DEV_RUNNING
    RESTART2 --> PROD_RUNNING
    RESTART3 --> BACKEND_RUNNING
    RESTART4 --> FRONTEND_RUNNING
    
    MONITOR1 --> |用户中断| STOP1[停止服务]
    MONITOR2 --> |用户中断| STOP2[停止服务]
    MONITOR3 --> |用户中断| STOP3[停止服务]
    MONITOR4 --> |用户中断| STOP4[停止服务]
    
    STOP1 --> END
    STOP2 --> END
    STOP3 --> END
    STOP4 --> END
    
    INIT_COMPLETE --> MENU
    CLEAN_COMPLETE --> MENU
    
    %% 样式定义
    classDef start fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef running fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class START,END start
    class BANNER,MENU,CHECK_DEPS1,INSTALL_DEPS1,START_BACKEND1,START_FRONTEND1 process
    class CHOICE,MONITOR1,MONITOR2,MONITOR3,MONITOR4 decision
    class DEV_RUNNING,PROD_RUNNING,BACKEND_RUNNING,FRONTEND_RUNNING running
```

### 1.2 依赖检查与安装流程

```mermaid
flowchart TD
    START_CHECK([开始依赖检查]) --> CHECK_PYTHON[检查Python环境]
    CHECK_PYTHON --> |存在| CHECK_PIP[检查pip]
    CHECK_PYTHON --> |不存在| INSTALL_PYTHON[安装Python]
    INSTALL_PYTHON --> CHECK_PIP
    
    CHECK_PIP --> |存在| CHECK_NODE[检查Node.js]
    CHECK_PIP --> |不存在| INSTALL_PIP[安装pip]
    INSTALL_PIP --> CHECK_NODE
    
    CHECK_NODE --> |存在| CHECK_NPM[检查npm]
    CHECK_NODE --> |不存在| INSTALL_NODE[安装Node.js]
    INSTALL_NODE --> CHECK_NPM
    
    CHECK_NPM --> |存在| CHECK_REQUIREMENTS[检查requirements.txt]
    CHECK_NPM --> |不存在| INSTALL_NPM[安装npm]
    INSTALL_NPM --> CHECK_REQUIREMENTS
    
    CHECK_REQUIREMENTS --> |存在| INSTALL_PYTHON_DEPS[安装Python依赖]
    CHECK_REQUIREMENTS --> |不存在| CREATE_REQUIREMENTS[创建requirements.txt]
    CREATE_REQUIREMENTS --> INSTALL_PYTHON_DEPS
    
    INSTALL_PYTHON_DEPS --> CHECK_PACKAGE_JSON[检查package.json]
    CHECK_PACKAGE_JSON --> |存在| INSTALL_NODE_DEPS[安装Node.js依赖]
    CHECK_PACKAGE_JSON --> |不存在| CREATE_PACKAGE_JSON[创建package.json]
    CREATE_PACKAGE_JSON --> INSTALL_NODE_DEPS
    
    INSTALL_NODE_DEPS --> CHECK_ENV[检查环境变量]
    CHECK_ENV --> |配置完整| DEPS_COMPLETE[依赖检查完成]
    CHECK_ENV --> |配置缺失| SETUP_ENV[设置环境变量]
    SETUP_ENV --> DEPS_COMPLETE
    
    DEPS_COMPLETE --> END_CHECK([依赖检查结束])
    
    %% 样式定义
    classDef start fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef success fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    
    class START_CHECK,END_CHECK start
    class INSTALL_PYTHON,INSTALL_PIP,INSTALL_NODE,INSTALL_NPM,INSTALL_PYTHON_DEPS,INSTALL_NODE_DEPS process
    class CHECK_PYTHON,CHECK_PIP,CHECK_NODE,CHECK_NPM,CHECK_REQUIREMENTS,CHECK_PACKAGE_JSON,CHECK_ENV decision
    class DEPS_COMPLETE success
```

## 2. 系统启动序列图

### 2.1 完整系统启动序列

```mermaid
sequenceDiagram
    participant User as 用户
    participant Script as Build.bat
    participant Env as 环境检查器
    participant Backend as 后端服务
    participant Frontend as 前端服务
    participant DB as 数据库
    participant Cache as 缓存服务
    
    User->>Script: 执行 Build.bat
    Script->>Script: 显示启动横幅
    Script->>User: 显示操作菜单
    User->>Script: 选择开发模式(1)
    
    Script->>Env: 检查系统依赖
    Env->>Env: 检查Python环境
    Env->>Env: 检查Node.js环境
    Env->>Env: 检查依赖包
    Env->>Script: 依赖检查完成
    
    Script->>DB: 启动数据库服务
    DB->>DB: 初始化数据库连接
    DB->>Script: 数据库就绪
    
    Script->>Cache: 启动缓存服务
    Cache->>Cache: 初始化缓存连接
    Cache->>Script: 缓存服务就绪
    
    Script->>Backend: 启动后端服务
    Backend->>Backend: 加载配置文件
    Backend->>Backend: 初始化模块
    Backend->>Backend: 启动API服务器
    Backend->>DB: 建立数据库连接
    Backend->>Cache: 建立缓存连接
    Backend->>Script: 后端服务就绪
    
    Script->>Frontend: 启动前端服务
    Frontend->>Frontend: 编译前端资源
    Frontend->>Frontend: 启动开发服务器
    Frontend->>Backend: 建立API连接
    Frontend->>Script: 前端服务就绪
    
    Script->>User: 系统启动完成
    
    loop 运行时监控
        Script->>Backend: 检查后端状态
        Backend->>Script: 返回健康状态
        Script->>Frontend: 检查前端状态
        Frontend->>Script: 返回健康状态
    end
    
    User->>Script: Ctrl+C 中断
    Script->>Frontend: 停止前端服务
    Frontend->>Script: 前端已停止
    Script->>Backend: 停止后端服务
    Backend->>DB: 关闭数据库连接
    Backend->>Cache: 关闭缓存连接
    Backend->>Script: 后端已停止
    Script->>User: 系统已关闭
```

## 3. 模块加载与初始化流程

### 3.1 核心模块加载顺序

```mermaid
flowchart TD
    START([系统启动]) --> LOAD_CONFIG[加载配置文件]
    LOAD_CONFIG --> INIT_LOGGING[初始化日志系统]
    INIT_LOGGING --> LOAD_ENGINE[加载engine.py]
    
    LOAD_ENGINE --> LOAD_CORE[加载核心模块]
    LOAD_CORE --> LOAD_EVOLUTION[加载evolution.py]
    LOAD_CORE --> LOAD_FITNESS[加载fitness.py]
    LOAD_CORE --> LOAD_SELECTION[加载selection.py]
    LOAD_CORE --> LOAD_CELL[加载cell.py]
    
    LOAD_EVOLUTION --> CHECK_IMPORTS1[检查导入依赖]
    LOAD_FITNESS --> CHECK_IMPORTS2[检查导入依赖]
    LOAD_SELECTION --> CHECK_IMPORTS3[检查导入依赖]
    LOAD_CELL --> CHECK_IMPORTS4[检查导入依赖]
    
    CHECK_IMPORTS1 --> INIT_MODULES[初始化模块]
    CHECK_IMPORTS2 --> INIT_MODULES
    CHECK_IMPORTS3 --> INIT_MODULES
    CHECK_IMPORTS4 --> INIT_MODULES
    
    INIT_MODULES --> LOAD_SUPPORT[加载支持模块]
    LOAD_SUPPORT --> LOAD_TASK_MGR[加载task_manager.py]
    LOAD_SUPPORT --> LOAD_SANDBOX[加载sandbox.py]
    
    LOAD_TASK_MGR --> INIT_SERVICES[初始化服务]
    LOAD_SANDBOX --> INIT_SERVICES
    
    INIT_SERVICES --> START_API[启动API服务]
    START_API --> START_WEB[启动Web服务]
    START_WEB --> SYSTEM_READY[系统就绪]
    
    %% 错误处理
    CHECK_IMPORTS1 --> |导入失败| IMPORT_ERROR[导入错误]
    CHECK_IMPORTS2 --> |导入失败| IMPORT_ERROR
    CHECK_IMPORTS3 --> |导入失败| IMPORT_ERROR
    CHECK_IMPORTS4 --> |导入失败| IMPORT_ERROR
    
    IMPORT_ERROR --> FIX_IMPORTS[修复导入路径]
    FIX_IMPORTS --> RETRY_LOAD[重试加载]
    RETRY_LOAD --> INIT_MODULES
    
    %% 样式定义
    classDef start fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef core fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef support fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef success fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    
    class START,SYSTEM_READY start
    class LOAD_CONFIG,INIT_LOGGING,LOAD_ENGINE process
    class LOAD_EVOLUTION,LOAD_FITNESS,LOAD_SELECTION,LOAD_CELL core
    class LOAD_TASK_MGR,LOAD_SANDBOX support
    class IMPORT_ERROR,FIX_IMPORTS error
    class INIT_MODULES,INIT_SERVICES,START_API,START_WEB success
```

### 3.2 模块依赖关系图

```mermaid
flowchart LR
    %% 配置层
    subgraph "配置层"
        CONFIG[config.py]
        ENV[.env文件]
        SETTINGS[settings.json]
    end
    
    %% 核心层
    subgraph "核心算法层"
        ENGINE[engine.py]
        EVOLUTION[evolution.py]
        FITNESS[fitness.py]
        SELECTION[selection.py]
        CELL[cell.py]
    end
    
    %% 服务层
    subgraph "服务层"
        TASK_MGR[task_manager.py]
        SANDBOX[sandbox.py]
        API[api_server.py]
        WEB[web_server.py]
    end
    
    %% 数据层
    subgraph "数据层"
        DATABASE[(数据库)]
        CACHE[(Redis缓存)]
        FILES[(文件系统)]
    end
    
    %% 外部依赖
    subgraph "外部依赖"
        PYTHON[Python运行时]
        NODEJS[Node.js运行时]
        DOCKER[Docker容器]
    end
    
    %% 依赖关系
    CONFIG --> ENGINE
    ENV --> CONFIG
    SETTINGS --> CONFIG
    
    ENGINE --> EVOLUTION
    ENGINE --> TASK_MGR
    EVOLUTION --> FITNESS
    EVOLUTION --> SELECTION
    EVOLUTION --> CELL
    
    TASK_MGR --> DATABASE
    SANDBOX --> FILES
    FITNESS --> SANDBOX
    
    API --> ENGINE
    WEB --> API
    
    ENGINE --> CACHE
    TASK_MGR --> CACHE
    
    PYTHON --> ENGINE
    NODEJS --> WEB
    DOCKER --> DATABASE
    DOCKER --> CACHE
    
    %% 样式定义
    classDef config fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef core fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef service fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef data fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef external fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class CONFIG,ENV,SETTINGS config
    class ENGINE,EVOLUTION,FITNESS,SELECTION,CELL core
    class TASK_MGR,SANDBOX,API,WEB service
    class DATABASE,CACHE,FILES data
    class PYTHON,NODEJS,DOCKER external
```

## 4. 运行时架构图

### 4.1 系统运行时架构

```mermaid
flowchart TB
    %% 用户接口层
    subgraph "用户接口层"
        BROWSER[浏览器]
        CLI[命令行]
        API_CLIENT[API客户端]
    end
    
    %% 网关层
    subgraph "网关层"
        NGINX[Nginx反向代理]
        LOAD_BALANCER[负载均衡器]
    end
    
    %% 应用层
    subgraph "应用层"
        WEB_SERVER[Web服务器:3000]
        API_SERVER[API服务器:8000]
        WEBSOCKET[WebSocket服务:8001]
    end
    
    %% 业务逻辑层
    subgraph "业务逻辑层"
        EVOLUTION_SERVICE[进化服务]
        TASK_SERVICE[任务服务]
        EVALUATION_SERVICE[评估服务]
        RESULT_SERVICE[结果服务]
    end
    
    %% 核心引擎层
    subgraph "核心引擎层"
        EVOLUTION_ENGINE[进化引擎]
        FITNESS_ENGINE[适应度引擎]
        SELECTION_ENGINE[选择引擎]
        SANDBOX_ENGINE[沙箱引擎]
    end
    
    %% 数据存储层
    subgraph "数据存储层"
        POSTGRESQL[(PostgreSQL:5432)]
        REDIS[(Redis:6379)]
        MONGODB[(MongoDB:27017)]
        FILE_STORAGE[(文件存储)]
    end
    
    %% 监控层
    subgraph "监控层"
        PROMETHEUS[Prometheus]
        GRAFANA[Grafana]
        ELASTICSEARCH[Elasticsearch]
        KIBANA[Kibana]
    end
    
    %% 连接关系
    BROWSER --> NGINX
    CLI --> API_SERVER
    API_CLIENT --> NGINX
    
    NGINX --> LOAD_BALANCER
    LOAD_BALANCER --> WEB_SERVER
    LOAD_BALANCER --> API_SERVER
    LOAD_BALANCER --> WEBSOCKET
    
    WEB_SERVER --> TASK_SERVICE
    API_SERVER --> EVOLUTION_SERVICE
    API_SERVER --> TASK_SERVICE
    API_SERVER --> EVALUATION_SERVICE
    API_SERVER --> RESULT_SERVICE
    WEBSOCKET --> EVOLUTION_SERVICE
    
    EVOLUTION_SERVICE --> EVOLUTION_ENGINE
    TASK_SERVICE --> EVOLUTION_ENGINE
    EVALUATION_SERVICE --> FITNESS_ENGINE
    EVALUATION_SERVICE --> SANDBOX_ENGINE
    EVOLUTION_SERVICE --> SELECTION_ENGINE
    
    EVOLUTION_ENGINE --> REDIS
    FITNESS_ENGINE --> POSTGRESQL
    SANDBOX_ENGINE --> FILE_STORAGE
    TASK_SERVICE --> MONGODB
    RESULT_SERVICE --> POSTGRESQL
    
    %% 监控连接
    API_SERVER --> PROMETHEUS
    EVOLUTION_ENGINE --> PROMETHEUS
    PROMETHEUS --> GRAFANA
    
    API_SERVER --> ELASTICSEARCH
    EVOLUTION_ENGINE --> ELASTICSEARCH
    ELASTICSEARCH --> KIBANA
    
    %% 样式定义
    classDef interface fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px
    classDef gateway fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef application fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef business fill:#fce4ec,stroke:#ad1457,stroke-width:2px
    classDef engine fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef storage fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef monitoring fill:#fff8e1,stroke:#f57c00,stroke-width:2px
    
    class BROWSER,CLI,API_CLIENT interface
    class NGINX,LOAD_BALANCER gateway
    class WEB_SERVER,API_SERVER,WEBSOCKET application
    class EVOLUTION_SERVICE,TASK_SERVICE,EVALUATION_SERVICE,RESULT_SERVICE business
    class EVOLUTION_ENGINE,FITNESS_ENGINE,SELECTION_ENGINE,SANDBOX_ENGINE engine
    class POSTGRESQL,REDIS,MONGODB,FILE_STORAGE storage
    class PROMETHEUS,GRAFANA,ELASTICSEARCH,KIBANA monitoring
```

## 5. 错误处理与恢复流程

### 5.1 系统错误处理流程

```mermaid
flowchart TD
    ERROR_DETECTED[检测到错误] --> ERROR_TYPE{错误类型}
    
    %% 模块导入错误
    ERROR_TYPE --> |模块导入错误| MODULE_ERROR[模块导入错误]
    MODULE_ERROR --> CHECK_PATH[检查模块路径]
    CHECK_PATH --> FIX_PATH[修复导入路径]
    FIX_PATH --> RETRY_IMPORT[重试导入]
    RETRY_IMPORT --> |成功| CONTINUE[继续执行]
    RETRY_IMPORT --> |失败| LOG_ERROR1[记录错误日志]
    
    %% 服务启动错误
    ERROR_TYPE --> |服务启动错误| SERVICE_ERROR[服务启动错误]
    SERVICE_ERROR --> CHECK_PORT[检查端口占用]
    CHECK_PORT --> KILL_PROCESS[终止占用进程]
    KILL_PROCESS --> RETRY_START[重试启动]
    RETRY_START --> |成功| CONTINUE
    RETRY_START --> |失败| LOG_ERROR2[记录错误日志]
    
    %% 数据库连接错误
    ERROR_TYPE --> |数据库错误| DB_ERROR[数据库连接错误]
    DB_ERROR --> CHECK_DB[检查数据库状态]
    CHECK_DB --> RESTART_DB[重启数据库]
    RESTART_DB --> RETRY_CONNECT[重试连接]
    RETRY_CONNECT --> |成功| CONTINUE
    RETRY_CONNECT --> |失败| LOG_ERROR3[记录错误日志]
    
    %% 内存不足错误
    ERROR_TYPE --> |内存不足| MEMORY_ERROR[内存不足错误]
    MEMORY_ERROR --> CLEAN_CACHE[清理缓存]
    CLEAN_CACHE --> GC_COLLECT[垃圾回收]
    GC_COLLECT --> CHECK_MEMORY[检查内存状态]
    CHECK_MEMORY --> |充足| CONTINUE
    CHECK_MEMORY --> |不足| LOG_ERROR4[记录错误日志]
    
    %% 网络连接错误
    ERROR_TYPE --> |网络错误| NETWORK_ERROR[网络连接错误]
    NETWORK_ERROR --> CHECK_NETWORK[检查网络状态]
    CHECK_NETWORK --> RETRY_NETWORK[重试网络连接]
    RETRY_NETWORK --> |成功| CONTINUE
    RETRY_NETWORK --> |失败| LOG_ERROR5[记录错误日志]
    
    %% 错误日志处理
    LOG_ERROR1 --> NOTIFY_ADMIN[通知管理员]
    LOG_ERROR2 --> NOTIFY_ADMIN
    LOG_ERROR3 --> NOTIFY_ADMIN
    LOG_ERROR4 --> NOTIFY_ADMIN
    LOG_ERROR5 --> NOTIFY_ADMIN
    
    NOTIFY_ADMIN --> GRACEFUL_SHUTDOWN[优雅关闭]
    GRACEFUL_SHUTDOWN --> END([结束])
    
    CONTINUE --> MONITOR[继续监控]
    MONITOR --> ERROR_DETECTED
    
    %% 样式定义
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef success fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef warning fill:#fff8e1,stroke:#f57c00,stroke-width:2px
    
    class ERROR_DETECTED,MODULE_ERROR,SERVICE_ERROR,DB_ERROR,MEMORY_ERROR,NETWORK_ERROR error
    class CHECK_PATH,FIX_PATH,CHECK_PORT,KILL_PROCESS,CHECK_DB,RESTART_DB process
    class ERROR_TYPE,RETRY_IMPORT,RETRY_START,RETRY_CONNECT,CHECK_MEMORY,RETRY_NETWORK decision
    class CONTINUE,MONITOR success
    class LOG_ERROR1,LOG_ERROR2,LOG_ERROR3,LOG_ERROR4,LOG_ERROR5,NOTIFY_ADMIN warning
```

## 6. 性能监控与优化

### 6.1 性能监控指标

```mermaid
flowchart LR
    %% 系统指标
    subgraph "系统性能指标"
        CPU[CPU使用率]
        MEMORY[内存使用率]
        DISK[磁盘I/O]
        NETWORK[网络I/O]
    end
    
    %% 应用指标
    subgraph "应用性能指标"
        RESPONSE_TIME[响应时间]
        THROUGHPUT[吞吐量]
        ERROR_RATE[错误率]
        CONCURRENT_USERS[并发用户数]
    end
    
    %% 业务指标
    subgraph "业务性能指标"
        EVOLUTION_SPEED[进化速度]
        FITNESS_EVAL_TIME[适应度评估时间]
        CONVERGENCE_RATE[收敛速度]
        SUCCESS_RATE[成功率]
    end
    
    %% 监控工具
    subgraph "监控工具"
        PROMETHEUS_MONITOR[Prometheus]
        GRAFANA_DASHBOARD[Grafana仪表板]
        ALERT_MANAGER[告警管理器]
        LOG_AGGREGATOR[日志聚合器]
    end
    
    %% 连接关系
    CPU --> PROMETHEUS_MONITOR
    MEMORY --> PROMETHEUS_MONITOR
    DISK --> PROMETHEUS_MONITOR
    NETWORK --> PROMETHEUS_MONITOR
    
    RESPONSE_TIME --> PROMETHEUS_MONITOR
    THROUGHPUT --> PROMETHEUS_MONITOR
    ERROR_RATE --> PROMETHEUS_MONITOR
    CONCURRENT_USERS --> PROMETHEUS_MONITOR
    
    EVOLUTION_SPEED --> PROMETHEUS_MONITOR
    FITNESS_EVAL_TIME --> PROMETHEUS_MONITOR
    CONVERGENCE_RATE --> PROMETHEUS_MONITOR
    SUCCESS_RATE --> PROMETHEUS_MONITOR
    
    PROMETHEUS_MONITOR --> GRAFANA_DASHBOARD
    PROMETHEUS_MONITOR --> ALERT_MANAGER
    PROMETHEUS_MONITOR --> LOG_AGGREGATOR
    
    %% 样式定义
    classDef system fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef application fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef business fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef monitoring fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    
    class CPU,MEMORY,DISK,NETWORK system
    class RESPONSE_TIME,THROUGHPUT,ERROR_RATE,CONCURRENT_USERS application
    class EVOLUTION_SPEED,FITNESS_EVAL_TIME,CONVERGENCE_RATE,SUCCESS_RATE business
    class PROMETHEUS_MONITOR,GRAFANA_DASHBOARD,ALERT_MANAGER,LOG_AGGREGATOR monitoring
```

## 7. 部署架构图

### 7.1 Docker容器化部署

```mermaid
flowchart TB
    %% 宿主机层
    subgraph "宿主机环境"
        HOST_OS[宿主机操作系统]
        DOCKER_ENGINE[Docker引擎]
    end
    
    %% 容器层
    subgraph "容器层"
        subgraph "前端容器"
            NGINX_CONTAINER[Nginx容器]
            FRONTEND_CONTAINER[前端应用容器]
        end
        
        subgraph "后端容器"
            API_CONTAINER[API服务容器]
            EVOLUTION_CONTAINER[进化引擎容器]
            WORKER_CONTAINER[工作进程容器]
        end
        
        subgraph "数据容器"
            POSTGRES_CONTAINER[PostgreSQL容器]
            REDIS_CONTAINER[Redis容器]
            MONGO_CONTAINER[MongoDB容器]
        end
        
        subgraph "监控容器"
            PROMETHEUS_CONTAINER[Prometheus容器]
            GRAFANA_CONTAINER[Grafana容器]
        end
    end
    
    %% 存储层
    subgraph "存储层"
        DATA_VOLUME[数据卷]
        LOG_VOLUME[日志卷]
        CONFIG_VOLUME[配置卷]
    end
    
    %% 网络层
    subgraph "网络层"
        FRONTEND_NETWORK[前端网络]
        BACKEND_NETWORK[后端网络]
        DATABASE_NETWORK[数据库网络]
        MONITORING_NETWORK[监控网络]
    end
    
    %% 连接关系
    HOST_OS --> DOCKER_ENGINE
    DOCKER_ENGINE --> NGINX_CONTAINER
    DOCKER_ENGINE --> FRONTEND_CONTAINER
    DOCKER_ENGINE --> API_CONTAINER
    DOCKER_ENGINE --> EVOLUTION_CONTAINER
    DOCKER_ENGINE --> WORKER_CONTAINER
    DOCKER_ENGINE --> POSTGRES_CONTAINER
    DOCKER_ENGINE --> REDIS_CONTAINER
    DOCKER_ENGINE --> MONGO_CONTAINER
    DOCKER_ENGINE --> PROMETHEUS_CONTAINER
    DOCKER_ENGINE --> GRAFANA_CONTAINER
    
    POSTGRES_CONTAINER --> DATA_VOLUME
    REDIS_CONTAINER --> DATA_VOLUME
    MONGO_CONTAINER --> DATA_VOLUME
    
    API_CONTAINER --> LOG_VOLUME
    EVOLUTION_CONTAINER --> LOG_VOLUME
    
    NGINX_CONTAINER --> CONFIG_VOLUME
    API_CONTAINER --> CONFIG_VOLUME
    
    NGINX_CONTAINER --> FRONTEND_NETWORK
    FRONTEND_CONTAINER --> FRONTEND_NETWORK
    
    API_CONTAINER --> BACKEND_NETWORK
    EVOLUTION_CONTAINER --> BACKEND_NETWORK
    WORKER_CONTAINER --> BACKEND_NETWORK
    
    POSTGRES_CONTAINER --> DATABASE_NETWORK
    REDIS_CONTAINER --> DATABASE_NETWORK
    MONGO_CONTAINER --> DATABASE_NETWORK
    
    PROMETHEUS_CONTAINER --> MONITORING_NETWORK
    GRAFANA_CONTAINER --> MONITORING_NETWORK
    
    %% 样式定义
    classDef host fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef frontend fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef backend fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef data fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef monitoring fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef storage fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef network fill:#fff8e1,stroke:#f57c00,stroke-width:2px
    
    class HOST_OS,DOCKER_ENGINE host
    class NGINX_CONTAINER,FRONTEND_CONTAINER frontend
    class API_CONTAINER,EVOLUTION_CONTAINER,WORKER_CONTAINER backend
    class POSTGRES_CONTAINER,REDIS_CONTAINER,MONGO_CONTAINER data
    class PROMETHEUS_CONTAINER,GRAFANA_CONTAINER monitoring
    class DATA_VOLUME,LOG_VOLUME,CONFIG_VOLUME storage
    class FRONTEND_NETWORK,BACKEND_NETWORK,DATABASE_NETWORK,MONITORING_NETWORK network
```

## 8. 总结

本文档详细描述了 EvoForge 项目的完整运行流程，包括：

1. **Build.bat 启动脚本流程** - 提供多种启动模式和完整的错误处理
2. **系统初始化序列** - 确保所有组件按正确顺序启动
3. **模块加载流程** - 解决模块依赖和导入问题
4. **运行时架构** - 展示系统的完整架构和组件交互
5. **错误处理机制** - 提供完善的错误恢复策略
6. **性能监控体系** - 实时监控系统性能和业务指标
7. **容器化部署** - 支持Docker容器化部署和扩展

通过这些流程图和架构设计，确保 EvoForge 项目能够稳定、高效地运行，并具备良好的可维护性和扩展性。

---

**文档版本**: 1.0  
**创建日期**: 2024年12月  
**最后更新**: 2024年12月  
**维护者**: EvoForge Team