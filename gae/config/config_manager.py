#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理系统 - 核心实现文件

根据 comprehensive_implementation_plan.md 文档重新实现

功能包括：
- 统一配置管理
- 环境变量处理
- 配置文件加载
- 动态配置更新
- 配置验证
"""

import os
import json
import yaml
import logging
import threading
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import configparser
from datetime import datetime
import copy

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ConfigFormat(Enum):
    """配置文件格式枚举"""
    JSON = "json"
    YAML = "yaml"
    INI = "ini"
    ENV = "env"

class ConfigScope(Enum):
    """配置作用域枚举"""
    GLOBAL = "global"        # 全局配置
    MODULE = "module"        # 模块配置
    INSTANCE = "instance"    # 实例配置
    RUNTIME = "runtime"      # 运行时配置

@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 5432
    database: str = "evoforge"
    username: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    
    def get_connection_string(self) -> str:
        """获取连接字符串"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    
    def get_level(self) -> int:
        """获取日志级别"""
        return getattr(logging, self.level.upper(), logging.INFO)

@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = ""
    jwt_secret: str = ""
    jwt_expiration: int = 3600  # 1小时
    password_min_length: int = 8
    max_login_attempts: int = 5
    session_timeout: int = 1800  # 30分钟
    encryption_algorithm: str = "AES-256-GCM"
    
    def is_valid(self) -> bool:
        """验证安全配置"""
        return bool(self.secret_key and self.jwt_secret)

@dataclass
class PerformanceConfig:
    """性能配置"""
    max_workers: int = 4
    thread_pool_size: int = 10
    process_pool_size: int = 2
    cache_size: int = 1000
    cache_ttl: int = 3600  # 1小时
    batch_size: int = 100
    timeout: float = 30.0
    
    def get_optimal_workers(self) -> int:
        """获取最优工作线程数"""
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        return min(self.max_workers, cpu_count * 2)

@dataclass
class ModuleConfig:
    """模块配置"""
    enabled: bool = True
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def has_dependency(self, module_name: str) -> bool:
        """检查是否依赖指定模块"""
        return module_name in self.dependencies

@dataclass
class SystemConfig:
    """系统主配置"""
    # 基础配置
    app_name: str = "EvoForge"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"  # development, testing, production
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # 模块配置
    modules: Dict[str, ModuleConfig] = field(default_factory=dict)
    
    # 自定义配置
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"
    
    def is_debug_enabled(self) -> bool:
        """是否启用调试模式"""
        return self.debug or self.environment == "development"

class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.validators: Dict[str, List[Callable]] = {}
        self._register_default_validators()
        logger.debug("配置验证器初始化完成")
    
    def _register_default_validators(self):
        """注册默认验证器"""
        # 数据库配置验证
        self.register_validator("database.port", self._validate_port)
        self.register_validator("database.pool_size", self._validate_positive_int)
        
        # 安全配置验证
        self.register_validator("security.password_min_length", self._validate_positive_int)
        self.register_validator("security.jwt_expiration", self._validate_positive_int)
        
        # 性能配置验证
        self.register_validator("performance.max_workers", self._validate_positive_int)
        self.register_validator("performance.timeout", self._validate_positive_float)
    
    def register_validator(self, config_path: str, validator: Callable):
        """注册验证器"""
        if config_path not in self.validators:
            self.validators[config_path] = []
        self.validators[config_path].append(validator)
        logger.debug(f"注册验证器: {config_path}")
    
    def validate(self, config: SystemConfig) -> List[str]:
        """验证配置"""
        logger.debug("开始配置验证")
        errors = []
        
        # 转换为字典进行验证
        config_dict = asdict(config)
        
        for config_path, validators in self.validators.items():
            value = self._get_nested_value(config_dict, config_path)
            if value is not None:
                for validator in validators:
                    try:
                        if not validator(value):
                            errors.append(f"配置验证失败: {config_path} = {value}")
                    except Exception as e:
                        errors.append(f"配置验证异常: {config_path}, 错误: {e}")
        
        # 自定义验证逻辑
        errors.extend(self._validate_security_config(config.security))
        errors.extend(self._validate_module_dependencies(config.modules))
        
        logger.debug(f"配置验证完成，错误数量: {len(errors)}")
        return errors
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """获取嵌套字典值"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _validate_port(self, value: int) -> bool:
        """验证端口号"""
        return isinstance(value, int) and 1 <= value <= 65535
    
    def _validate_positive_int(self, value: int) -> bool:
        """验证正整数"""
        return isinstance(value, int) and value > 0
    
    def _validate_positive_float(self, value: float) -> bool:
        """验证正浮点数"""
        return isinstance(value, (int, float)) and value > 0
    
    def _validate_security_config(self, security: SecurityConfig) -> List[str]:
        """验证安全配置"""
        errors = []
        
        if not security.secret_key:
            errors.append("安全配置: secret_key 不能为空")
        elif len(security.secret_key) < 32:
            errors.append("安全配置: secret_key 长度至少32字符")
        
        if not security.jwt_secret:
            errors.append("安全配置: jwt_secret 不能为空")
        elif len(security.jwt_secret) < 32:
            errors.append("安全配置: jwt_secret 长度至少32字符")
        
        return errors
    
    def _validate_module_dependencies(self, modules: Dict[str, ModuleConfig]) -> List[str]:
        """验证模块依赖"""
        errors = []
        
        for module_name, module_config in modules.items():
            for dependency in module_config.dependencies:
                if dependency not in modules:
                    errors.append(f"模块依赖错误: {module_name} 依赖的模块 {dependency} 不存在")
                elif not modules[dependency].enabled:
                    errors.append(f"模块依赖错误: {module_name} 依赖的模块 {dependency} 未启用")
        
        return errors

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or "config")
        self.config = SystemConfig()
        self.validator = ConfigValidator()
        self.watchers: List[Callable] = []
        self.lock = threading.RLock()
        
        # 配置文件路径
        self.config_files = {
            ConfigFormat.JSON: self.config_dir / "config.json",
            ConfigFormat.YAML: self.config_dir / "config.yaml",
            ConfigFormat.INI: self.config_dir / "config.ini",
            ConfigFormat.ENV: self.config_dir / ".env"
        }
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"配置管理器初始化完成，配置目录: {self.config_dir}")
    
    def load_config(self, format_type: ConfigFormat = ConfigFormat.JSON) -> SystemConfig:
        """加载配置"""
        logger.info(f"加载配置，格式: {format_type.value}")
        
        with self.lock:
            try:
                # 1. 加载环境变量
                self._load_from_environment()
                
                # 2. 加载配置文件
                config_file = self.config_files[format_type]
                if config_file.exists():
                    self._load_from_file(config_file, format_type)
                else:
                    logger.warning(f"配置文件不存在: {config_file}")
                
                # 3. 验证配置
                errors = self.validator.validate(self.config)
                if errors:
                    logger.error(f"配置验证失败: {errors}")
                    raise ValueError(f"配置验证失败: {errors}")
                
                # 4. 通知观察者
                self._notify_watchers()
                
                logger.info("配置加载完成")
                return copy.deepcopy(self.config)
                
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                raise
    
    def save_config(self, format_type: ConfigFormat = ConfigFormat.JSON):
        """保存配置"""
        logger.info(f"保存配置，格式: {format_type.value}")
        
        with self.lock:
            try:
                config_file = self.config_files[format_type]
                self._save_to_file(config_file, format_type)
                logger.info(f"配置已保存到: {config_file}")
                
            except Exception as e:
                logger.error(f"保存配置失败: {e}")
                raise
    
    def _load_from_environment(self):
        """从环境变量加载配置"""
        logger.debug("从环境变量加载配置")
        
        # 数据库配置
        if os.getenv("DB_HOST"):
            self.config.database.host = os.getenv("DB_HOST")
        if os.getenv("DB_PORT"):
            self.config.database.port = int(os.getenv("DB_PORT"))
        if os.getenv("DB_NAME"):
            self.config.database.database = os.getenv("DB_NAME")
        if os.getenv("DB_USER"):
            self.config.database.username = os.getenv("DB_USER")
        if os.getenv("DB_PASSWORD"):
            self.config.database.password = os.getenv("DB_PASSWORD")
        
        # 安全配置
        if os.getenv("SECRET_KEY"):
            self.config.security.secret_key = os.getenv("SECRET_KEY")
        if os.getenv("JWT_SECRET"):
            self.config.security.jwt_secret = os.getenv("JWT_SECRET")
        
        # 应用配置
        if os.getenv("APP_ENV"):
            self.config.environment = os.getenv("APP_ENV")
        if os.getenv("DEBUG"):
            self.config.debug = os.getenv("DEBUG").lower() in ("true", "1", "yes")
        
        logger.debug("环境变量配置加载完成")
    
    def _load_from_file(self, config_file: Path, format_type: ConfigFormat):
        """从文件加载配置"""
        logger.debug(f"从文件加载配置: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if format_type == ConfigFormat.JSON:
                    data = json.load(f)
                elif format_type == ConfigFormat.YAML:
                    data = yaml.safe_load(f)
                elif format_type == ConfigFormat.INI:
                    parser = configparser.ConfigParser()
                    parser.read(config_file)
                    data = {section: dict(parser[section]) for section in parser.sections()}
                else:
                    raise ValueError(f"不支持的配置格式: {format_type}")
            
            # 更新配置
            self._update_config_from_dict(data)
            
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            raise
    
    def _save_to_file(self, config_file: Path, format_type: ConfigFormat):
        """保存配置到文件"""
        logger.debug(f"保存配置到文件: {config_file}")
        
        try:
            data = asdict(self.config)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                if format_type == ConfigFormat.JSON:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                elif format_type == ConfigFormat.YAML:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                elif format_type == ConfigFormat.INI:
                    parser = configparser.ConfigParser()
                    self._dict_to_ini(data, parser)
                    parser.write(f)
                else:
                    raise ValueError(f"不支持的配置格式: {format_type}")
            
        except Exception as e:
            logger.error(f"写入配置文件失败: {e}")
            raise
    
    def _update_config_from_dict(self, data: Dict[str, Any]):
        """从字典更新配置"""
        logger.debug("从字典更新配置")
        
        # 基础配置
        if "app_name" in data:
            self.config.app_name = data["app_name"]
        if "version" in data:
            self.config.version = data["version"]
        if "debug" in data:
            self.config.debug = data["debug"]
        if "environment" in data:
            self.config.environment = data["environment"]
        
        # 数据库配置
        if "database" in data:
            db_data = data["database"]
            for key, value in db_data.items():
                if hasattr(self.config.database, key):
                    setattr(self.config.database, key, value)
        
        # 日志配置
        if "logging" in data:
            log_data = data["logging"]
            for key, value in log_data.items():
                if hasattr(self.config.logging, key):
                    setattr(self.config.logging, key, value)
        
        # 安全配置
        if "security" in data:
            sec_data = data["security"]
            for key, value in sec_data.items():
                if hasattr(self.config.security, key):
                    setattr(self.config.security, key, value)
        
        # 性能配置
        if "performance" in data:
            perf_data = data["performance"]
            for key, value in perf_data.items():
                if hasattr(self.config.performance, key):
                    setattr(self.config.performance, key, value)
        
        # 模块配置
        if "modules" in data:
            for module_name, module_data in data["modules"].items():
                module_config = ModuleConfig(
                    enabled=module_data.get("enabled", True),
                    priority=module_data.get("priority", 0),
                    dependencies=module_data.get("dependencies", []),
                    settings=module_data.get("settings", {})
                )
                self.config.modules[module_name] = module_config
        
        # 自定义配置
        if "custom" in data:
            self.config.custom.update(data["custom"])
    
    def _dict_to_ini(self, data: Dict[str, Any], parser: configparser.ConfigParser):
        """将字典转换为INI格式"""
        for section_name, section_data in data.items():
            if isinstance(section_data, dict):
                parser.add_section(section_name)
                for key, value in section_data.items():
                    if not isinstance(value, (dict, list)):
                        parser.set(section_name, key, str(value))
    
    def get_config(self) -> SystemConfig:
        """获取当前配置"""
        with self.lock:
            return copy.deepcopy(self.config)
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        logger.info(f"更新配置: {list(updates.keys())}")
        
        with self.lock:
            self._update_config_from_dict(updates)
            
            # 验证更新后的配置
            errors = self.validator.validate(self.config)
            if errors:
                logger.error(f"配置更新验证失败: {errors}")
                raise ValueError(f"配置更新验证失败: {errors}")
            
            # 通知观察者
            self._notify_watchers()
    
    def get_module_config(self, module_name: str) -> Optional[ModuleConfig]:
        """获取模块配置"""
        with self.lock:
            return copy.deepcopy(self.config.modules.get(module_name))
    
    def set_module_config(self, module_name: str, module_config: ModuleConfig):
        """设置模块配置"""
        logger.info(f"设置模块配置: {module_name}")
        
        with self.lock:
            self.config.modules[module_name] = copy.deepcopy(module_config)
            
            # 验证模块依赖
            errors = self.validator._validate_module_dependencies(self.config.modules)
            if errors:
                logger.error(f"模块配置验证失败: {errors}")
                raise ValueError(f"模块配置验证失败: {errors}")
            
            # 通知观察者
            self._notify_watchers()
    
    def add_watcher(self, callback: Callable[[SystemConfig], None]):
        """添加配置变更观察者"""
        self.watchers.append(callback)
        logger.debug(f"添加配置观察者，当前观察者数量: {len(self.watchers)}")
    
    def remove_watcher(self, callback: Callable[[SystemConfig], None]):
        """移除配置变更观察者"""
        if callback in self.watchers:
            self.watchers.remove(callback)
            logger.debug(f"移除配置观察者，当前观察者数量: {len(self.watchers)}")
    
    def _notify_watchers(self):
        """通知所有观察者"""
        logger.debug(f"通知配置观察者，数量: {len(self.watchers)}")
        
        for watcher in self.watchers:
            try:
                watcher(copy.deepcopy(self.config))
            except Exception as e:
                logger.error(f"通知配置观察者失败: {e}")
    
    def create_default_config(self) -> SystemConfig:
        """创建默认配置"""
        logger.info("创建默认配置")
        
        config = SystemConfig(
            app_name="EvoForge",
            version="1.0.0",
            debug=True,
            environment="development"
        )
        
        # 设置默认模块配置
        default_modules = {
            "digital_cell": ModuleConfig(
                enabled=True,
                priority=1,
                dependencies=[],
                settings={
                    "max_molecules": 10000,
                    "simulation_step": 0.01,
                    "enable_3d_physics": True
                }
            ),
            "gene_expression": ModuleConfig(
                enabled=True,
                priority=2,
                dependencies=["digital_cell"],
                settings={
                    "transcription_rate": 0.1,
                    "translation_rate": 0.05,
                    "enable_regulation": True
                }
            ),
            "evolution_engine": ModuleConfig(
                enabled=True,
                priority=3,
                dependencies=["digital_cell", "gene_expression"],
                settings={
                    "population_size": 100,
                    "mutation_rate": 0.01,
                    "crossover_rate": 0.8,
                    "enable_llm_mutation": True
                }
            ),
            "multimodal_oracle": ModuleConfig(
                enabled=True,
                priority=4,
                dependencies=["evolution_engine"],
                settings={
                    "enable_text_model": True,
                    "enable_vision_model": False,
                    "enable_audio_model": False,
                    "cache_size": 1000
                }
            ),
            "security_sandbox": ModuleConfig(
                enabled=True,
                priority=0,  # 最高优先级
                dependencies=[],
                settings={
                    "default_security_level": "medium",
                    "enable_docker": False,
                    "enable_wasm": True,
                    "resource_limits": {
                        "max_memory_mb": 512,
                        "max_cpu_percent": 50.0,
                        "max_execution_time": 30.0
                    }
                }
            )
        }
        
        config.modules = default_modules
        
        return config
    
    def export_config(self, output_path: str, format_type: ConfigFormat = ConfigFormat.JSON):
        """导出配置"""
        logger.info(f"导出配置到: {output_path}")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with self.lock:
            self._save_to_file(output_file, format_type)
    
    def import_config(self, input_path: str, format_type: ConfigFormat = ConfigFormat.JSON):
        """导入配置"""
        logger.info(f"从文件导入配置: {input_path}")
        
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {input_path}")
        
        with self.lock:
            self._load_from_file(input_file, format_type)
            
            # 验证导入的配置
            errors = self.validator.validate(self.config)
            if errors:
                logger.error(f"导入配置验证失败: {errors}")
                raise ValueError(f"导入配置验证失败: {errors}")
            
            # 通知观察者
            self._notify_watchers()

# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None
_config_lock = threading.Lock()

def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    
    with _config_lock:
        if _config_manager is None:
            _config_manager = ConfigManager(config_dir)
        return _config_manager

def get_config() -> SystemConfig:
    """获取当前系统配置"""
    return get_config_manager().get_config()

def update_config(updates: Dict[str, Any]):
    """更新系统配置"""
    get_config_manager().update_config(updates)

# 测试代码
if __name__ == "__main__":
    def test_config_manager():
        """测试配置管理器"""
        logger.info("配置管理器测试开始")
        
        # 创建配置管理器
        config_manager = ConfigManager("test_config")
        
        # 创建默认配置
        default_config = config_manager.create_default_config()
        config_manager.config = default_config
        
        # 保存配置
        config_manager.save_config(ConfigFormat.JSON)
        config_manager.save_config(ConfigFormat.YAML)
        
        # 加载配置
        loaded_config = config_manager.load_config(ConfigFormat.JSON)
        logger.info(f"加载的配置: {loaded_config.app_name} v{loaded_config.version}")
        
        # 更新配置
        config_manager.update_config({
            "debug": False,
            "environment": "production",
            "database": {
                "host": "prod-db.example.com",
                "port": 5432
            }
        })
        
        # 获取模块配置
        cell_config = config_manager.get_module_config("digital_cell")
        logger.info(f"数字细胞模块配置: {cell_config}")
        
        # 添加配置观察者
        def config_changed(config: SystemConfig):
            logger.info(f"配置已更改: {config.environment}")
        
        config_manager.add_watcher(config_changed)
        
        # 测试配置更新通知
        config_manager.update_config({"debug": True})
        
        # 导出配置
        config_manager.export_config("exported_config.json", ConfigFormat.JSON)
        
        logger.info("配置管理器测试完成")
    
    # 运行测试
    test_config_manager()