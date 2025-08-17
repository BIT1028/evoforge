# -*- coding: utf-8 -*-
"""
验证中间件

提供请求数据验证和业务规则检查功能。
"""

import logging
import json
from typing import Dict, Any, List, Optional, Callable, Union
from functools import wraps

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class ValidationResult:
    """
    验证结果类
    """
    
    def __init__(self, valid: bool = True, errors: List[Dict[str, Any]] = None, warnings: List[str] = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, field: str, message: str, code: str = None):
        """
        添加错误
        
        Args:
            field: 字段名
            message: 错误消息
            code: 错误代码
        """
        self.valid = False
        error = {'field': field, 'message': message}
        if code:
            error['code'] = code
        self.errors.append(error)
    
    def add_warning(self, message: str):
        """
        添加警告
        
        Args:
            message: 警告消息
        """
        self.warnings.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 验证结果字典
        """
        result = {
            'valid': self.valid,
            'errors': self.errors
        }
        if self.warnings:
            result['warnings'] = self.warnings
        return result

class RequestValidator:
    """
    请求验证器
    
    提供各种验证功能
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 验证规则
        self.validation_rules = self.config.get('rules', {})
        
        # 业务规则
        self.business_rules = self.config.get('business_rules', {})
        
        # 自定义验证器
        self.custom_validators = {}
        
        logger.debug("Request validator initialized")
    
    def register_validator(self, name: str, validator: Callable):
        """
        注册自定义验证器
        
        Args:
            name: 验证器名称
            validator: 验证器函数
        """
        self.custom_validators[name] = validator
        logger.debug(f"Registered custom validator: {name}")
    
    def validate_request(self, request: Request, data: Dict[str, Any] = None) -> ValidationResult:
        """
        验证请求
        
        Args:
            request: HTTP请求
            data: 请求数据
            
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult()
        
        # 获取路径对应的验证规则
        path_rules = self._get_rules_for_path(request.url.path, request.method)
        if not path_rules:
            return result
        
        # 验证请求头
        if 'headers' in path_rules:
            self._validate_headers(request, path_rules['headers'], result)
        
        # 验证查询参数
        if 'query_params' in path_rules:
            self._validate_query_params(request, path_rules['query_params'], result)
        
        # 验证请求体
        if 'body' in path_rules and data:
            self._validate_body(data, path_rules['body'], result)
        
        # 执行业务规则验证
        if 'business_rules' in path_rules:
            self._validate_business_rules(request, data, path_rules['business_rules'], result)
        
        # 执行自定义验证
        if 'custom_validators' in path_rules:
            self._validate_custom(request, data, path_rules['custom_validators'], result)
        
        return result
    
    def _get_rules_for_path(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """
        获取路径对应的验证规则
        
        Args:
            path: 请求路径
            method: HTTP方法
            
        Returns:
            Optional[Dict[str, Any]]: 验证规则
        """
        # 精确匹配
        exact_key = f"{method.upper()} {path}"
        if exact_key in self.validation_rules:
            return self.validation_rules[exact_key]
        
        # 路径匹配
        for rule_path, rules in self.validation_rules.items():
            if ' ' in rule_path:
                rule_method, rule_path_pattern = rule_path.split(' ', 1)
                if rule_method.upper() != method.upper():
                    continue
            else:
                rule_path_pattern = rule_path
            
            # 简单的通配符匹配
            if self._path_matches(path, rule_path_pattern):
                return rules
        
        return None
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """
        检查路径是否匹配模式
        
        Args:
            path: 实际路径
            pattern: 路径模式
            
        Returns:
            bool: 是否匹配
        """
        # 简单的通配符匹配
        if '*' in pattern:
            pattern_parts = pattern.split('*')
            if len(pattern_parts) == 2:
                prefix, suffix = pattern_parts
                return path.startswith(prefix) and path.endswith(suffix)
        
        # 精确匹配
        return path == pattern
    
    def _validate_headers(self, request: Request, rules: Dict[str, Any], result: ValidationResult):
        """
        验证请求头
        
        Args:
            request: HTTP请求
            rules: 验证规则
            result: 验证结果
        """
        required_headers = rules.get('required', [])
        for header_name in required_headers:
            if header_name.lower() not in [h.lower() for h in request.headers.keys()]:
                result.add_error(
                    f'headers.{header_name}',
                    f'Required header {header_name} is missing',
                    'missing_header'
                )
        
        # 验证头部值
        header_patterns = rules.get('patterns', {})
        for header_name, pattern in header_patterns.items():
            header_value = request.headers.get(header_name)
            if header_value and not self._validate_pattern(header_value, pattern):
                result.add_error(
                    f'headers.{header_name}',
                    f'Header {header_name} does not match required pattern',
                    'invalid_header_format'
                )
    
    def _validate_query_params(self, request: Request, rules: Dict[str, Any], result: ValidationResult):
        """
        验证查询参数
        
        Args:
            request: HTTP请求
            rules: 验证规则
            result: 验证结果
        """
        required_params = rules.get('required', [])
        for param_name in required_params:
            if param_name not in request.query_params:
                result.add_error(
                    f'query.{param_name}',
                    f'Required query parameter {param_name} is missing',
                    'missing_query_param'
                )
        
        # 验证参数类型
        param_types = rules.get('types', {})
        for param_name, param_type in param_types.items():
            param_value = request.query_params.get(param_name)
            if param_value and not self._validate_type(param_value, param_type):
                result.add_error(
                    f'query.{param_name}',
                    f'Query parameter {param_name} has invalid type, expected {param_type}',
                    'invalid_query_param_type'
                )
        
        # 验证参数范围
        param_ranges = rules.get('ranges', {})
        for param_name, param_range in param_ranges.items():
            param_value = request.query_params.get(param_name)
            if param_value and not self._validate_range(param_value, param_range):
                result.add_error(
                    f'query.{param_name}',
                    f'Query parameter {param_name} is out of allowed range',
                    'invalid_query_param_range'
                )
    
    def _validate_body(self, data: Dict[str, Any], rules: Dict[str, Any], result: ValidationResult):
        """
        验证请求体
        
        Args:
            data: 请求数据
            rules: 验证规则
            result: 验证结果
        """
        # 验证必需字段
        required_fields = rules.get('required', [])
        for field_name in required_fields:
            if field_name not in data:
                result.add_error(
                    f'body.{field_name}',
                    f'Required field {field_name} is missing',
                    'missing_field'
                )
        
        # 验证字段类型
        field_types = rules.get('types', {})
        for field_name, field_type in field_types.items():
            if field_name in data:
                field_value = data[field_name]
                if not self._validate_type(field_value, field_type):
                    result.add_error(
                        f'body.{field_name}',
                        f'Field {field_name} has invalid type, expected {field_type}',
                        'invalid_field_type'
                    )
        
        # 验证字段范围
        field_ranges = rules.get('ranges', {})
        for field_name, field_range in field_ranges.items():
            if field_name in data:
                field_value = data[field_name]
                if not self._validate_range(field_value, field_range):
                    result.add_error(
                        f'body.{field_name}',
                        f'Field {field_name} is out of allowed range',
                        'invalid_field_range'
                    )
        
        # 验证字段模式
        field_patterns = rules.get('patterns', {})
        for field_name, pattern in field_patterns.items():
            if field_name in data:
                field_value = data[field_name]
                if isinstance(field_value, str) and not self._validate_pattern(field_value, pattern):
                    result.add_error(
                        f'body.{field_name}',
                        f'Field {field_name} does not match required pattern',
                        'invalid_field_format'
                    )
    
    def _validate_business_rules(self, request: Request, data: Dict[str, Any], rules: List[str], result: ValidationResult):
        """
        验证业务规则
        
        Args:
            request: HTTP请求
            data: 请求数据
            rules: 业务规则列表
            result: 验证结果
        """
        for rule_name in rules:
            if rule_name in self.business_rules:
                rule_func = self.business_rules[rule_name]
                try:
                    rule_result = rule_func(request, data)
                    if not rule_result.get('valid', True):
                        result.add_error(
                            'business_rule',
                            rule_result.get('message', f'Business rule {rule_name} failed'),
                            rule_name
                        )
                except Exception as e:
                    logger.error(f"Business rule {rule_name} execution failed: {str(e)}")
                    result.add_error(
                        'business_rule',
                        f'Business rule {rule_name} execution failed',
                        'rule_execution_error'
                    )
    
    def _validate_custom(self, request: Request, data: Dict[str, Any], validators: List[str], result: ValidationResult):
        """
        执行自定义验证
        
        Args:
            request: HTTP请求
            data: 请求数据
            validators: 自定义验证器列表
            result: 验证结果
        """
        for validator_name in validators:
            if validator_name in self.custom_validators:
                validator_func = self.custom_validators[validator_name]
                try:
                    validator_result = validator_func(request, data)
                    if not validator_result.get('valid', True):
                        result.add_error(
                            'custom_validation',
                            validator_result.get('message', f'Custom validator {validator_name} failed'),
                            validator_name
                        )
                except Exception as e:
                    logger.error(f"Custom validator {validator_name} execution failed: {str(e)}")
                    result.add_error(
                        'custom_validation',
                        f'Custom validator {validator_name} execution failed',
                        'validator_execution_error'
                    )
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        验证值类型
        
        Args:
            value: 值
            expected_type: 期望类型
            
        Returns:
            bool: 是否匹配
        """
        type_map = {
            'string': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict
        }
        
        if expected_type in type_map:
            expected_python_type = type_map[expected_type]
            
            # 特殊处理字符串类型的数字
            if expected_python_type in [int, float] and isinstance(value, str):
                try:
                    if expected_python_type == int:
                        int(value)
                    else:
                        float(value)
                    return True
                except ValueError:
                    return False
            
            return isinstance(value, expected_python_type)
        
        return True
    
    def _validate_range(self, value: Any, range_config: Dict[str, Any]) -> bool:
        """
        验证值范围
        
        Args:
            value: 值
            range_config: 范围配置
            
        Returns:
            bool: 是否在范围内
        """
        try:
            # 数值范围
            if 'min' in range_config or 'max' in range_config:
                numeric_value = float(value) if isinstance(value, str) else value
                
                if 'min' in range_config and numeric_value < range_config['min']:
                    return False
                
                if 'max' in range_config and numeric_value > range_config['max']:
                    return False
            
            # 长度范围
            if 'min_length' in range_config or 'max_length' in range_config:
                length = len(value) if hasattr(value, '__len__') else 0
                
                if 'min_length' in range_config and length < range_config['min_length']:
                    return False
                
                if 'max_length' in range_config and length > range_config['max_length']:
                    return False
            
            # 枚举值
            if 'enum' in range_config:
                return value in range_config['enum']
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def _validate_pattern(self, value: str, pattern: str) -> bool:
        """
        验证字符串模式
        
        Args:
            value: 字符串值
            pattern: 正则表达式模式
            
        Returns:
            bool: 是否匹配
        """
        import re
        try:
            return bool(re.match(pattern, value))
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return True

class ValidationMiddleware(BaseHTTPMiddleware):
    """
    验证中间件
    
    对API请求进行数据验证
    """
    
    def __init__(self, app, config: Dict[str, Any] = None):
        super().__init__(app)
        self.config = config or {}
        
        # 配置选项
        self.enabled = self.config.get('enabled', True)
        self.exclude_paths = set(self.config.get('exclude_paths', []))
        
        # 创建验证器
        self.validator = RequestValidator(self.config)
        
        # 统计信息
        self.validation_errors = 0
        self.total_requests = 0
        
        logger.info("Validation middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并进行验证
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或路由处理器
            
        Returns:
            Response: HTTP响应
        """
        # 检查是否启用验证
        if not self.enabled:
            return await call_next(request)
        
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        self.total_requests += 1
        
        # 获取请求数据
        request_data = await self._extract_request_data(request)
        
        # 执行验证
        validation_result = self.validator.validate_request(request, request_data)
        
        if not validation_result.valid:
            self.validation_errors += 1
            return self._create_validation_error_response(validation_result)
        
        # 如果有警告，添加到响应头
        response = await call_next(request)
        if validation_result.warnings:
            response.headers['X-Validation-Warnings'] = json.dumps(validation_result.warnings)
        
        return response
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        检查是否应该排除此路径
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否排除
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    async def _extract_request_data(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        提取请求数据
        
        Args:
            request: HTTP请求
            
        Returns:
            Optional[Dict[str, Any]]: 请求数据
        """
        try:
            # 只处理有请求体的方法
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    body = await request.body()
                    if body:
                        return json.loads(body)
                elif 'application/x-www-form-urlencoded' in content_type:
                    form_data = await request.form()
                    return dict(form_data)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract request data: {str(e)}")
            return None
    
    def _create_validation_error_response(self, validation_result: ValidationResult) -> JSONResponse:
        """
        创建验证错误响应
        
        Args:
            validation_result: 验证结果
            
        Returns:
            JSONResponse: 错误响应
        """
        # 记录验证错误
        logger.warning(
            f"Request validation failed: {len(validation_result.errors)} errors",
            extra={'validation_errors': validation_result.errors}
        )
        
        response_data = {
            'error': 'Validation failed',
            'message': 'Request data validation failed',
            'details': validation_result.to_dict()
        }
        
        return JSONResponse(
            status_code=422,
            content=response_data
        )
    
    def register_business_rule(self, name: str, rule_func: Callable):
        """
        注册业务规则
        
        Args:
            name: 规则名称
            rule_func: 规则函数
        """
        self.validator.business_rules[name] = rule_func
        logger.info(f"Registered business rule: {name}")
    
    def register_custom_validator(self, name: str, validator_func: Callable):
        """
        注册自定义验证器
        
        Args:
            name: 验证器名称
            validator_func: 验证器函数
        """
        self.validator.register_validator(name, validator_func)
        logger.info(f"Registered custom validator: {name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取验证统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        error_rate = (
            self.validation_errors / self.total_requests 
            if self.total_requests > 0 else 0
        )
        
        return {
            'enabled': self.enabled,
            'total_requests': self.total_requests,
            'validation_errors': self.validation_errors,
            'error_rate': f"{error_rate:.2%}",
            'business_rules_count': len(self.validator.business_rules),
            'custom_validators_count': len(self.validator.custom_validators)
        }

def setup_validation_middleware(app, config_manager=None):
    """
    设置验证中间件
    
    Args:
        app: FastAPI应用实例
        config_manager: 配置管理器
    """
    # 默认验证配置
    default_config = {
        'enabled': True,
        'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json'],
        'rules': {
            # 示例验证规则
            'POST /api/experiments': {
                'body': {
                    'required': ['name', 'config'],
                    'types': {
                        'name': 'string',
                        'description': 'string',
                        'config': 'dict'
                    },
                    'ranges': {
                        'name': {'min_length': 1, 'max_length': 100}
                    }
                }
            },
            'PUT /api/experiments/*': {
                'body': {
                    'types': {
                        'name': 'string',
                        'description': 'string',
                        'config': 'dict'
                    },
                    'ranges': {
                        'name': {'min_length': 1, 'max_length': 100}
                    }
                }
            },
            'GET /api/experiments': {
                'query_params': {
                    'types': {
                        'page': 'int',
                        'size': 'int',
                        'status': 'string'
                    },
                    'ranges': {
                        'page': {'min': 1},
                        'size': {'min': 1, 'max': 100},
                        'status': {'enum': ['active', 'completed', 'failed', 'paused']}
                    }
                }
            }
        }
    }
    
    # 从配置管理器获取配置（如果可用）
    if config_manager:
        try:
            # 这里可以从配置管理器获取验证配置
            # validation_config = config_manager.get_validation_config()
            # 暂时使用默认配置
            validation_config = default_config
        except Exception as e:
            logger.warning(f"Failed to get validation config: {str(e)}, using default")
            validation_config = default_config
    else:
        validation_config = default_config
    
    # 创建验证中间件实例
    validation_middleware = ValidationMiddleware(app, config=validation_config)
    
    # 添加验证中间件
    app.add_middleware(ValidationMiddleware, config=validation_config)
    
    logger.info("Validation middleware configured")
    
    return validation_middleware

# 验证装饰器
def validate_request(model: BaseModel = None, **validation_kwargs):
    """
    请求验证装饰器
    
    Args:
        model: Pydantic模型类
        **validation_kwargs: 其他验证参数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里可以添加装饰器级别的验证逻辑
            return await func(*args, **kwargs)