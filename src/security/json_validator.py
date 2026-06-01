"""
JSON解析の安全性強化モジュール
悪意あるペイロードの検出とスキーマ検証を提供
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# JSONスキーマ定義
SCHEMAS = {
    'medicine_recommendation': {
        'type': 'object',
        'required': ['recommended_medicines', 'doctor_consultation'],
        'properties': {
            'recommended_medicines': {
                'type': 'array',
                'maxItems': 3,
                'items': {
                    'type': 'object',
                    'required': ['product_name', 'manufacturer', 'reason', 'usage_notes'],
                    'properties': {
                        'product_name': {'type': 'string', 'maxLength': 100},
                        'manufacturer': {'type': 'string', 'maxLength': 50},
                        'reason': {'type': 'string', 'maxLength': 500},
                        'efficacy': {'type': 'string', 'maxLength': 1000},
                        'ingredients': {'type': 'string', 'maxLength': 500},
                        'usage_notes': {'type': 'string', 'maxLength': 2000}
                    }
                }
            },
            'usage_notes': {'type': 'string', 'maxLength': 3000},
            'doctor_consultation': {'type': 'string', 'maxLength': 500}
        }
    },
    
    'symptom_analysis': {
        'type': 'object',
        'required': ['symptoms', 'red_flags', 'needs_escalation'],
        'properties': {
            'symptoms': {
                'type': 'array',
                'maxItems': 10,
                'items': {
                    'type': 'object',
                    'required': ['name', 'severity'],
                    'properties': {
                        'name': {'type': 'string', 'maxLength': 50},
                        'severity': {'type': 'string', 'enum': ['軽度', '中等度', '重度']},
                        'duration_days': {'type': ['integer', 'null'], 'minimum': 0, 'maximum': 365}
                    }
                }
            },
            'red_flags': {'type': 'array', 'maxItems': 5, 'items': {'type': 'string', 'maxLength': 100}},
            'needs_escalation': {'type': 'boolean'},
            'escalation_reason': {'type': 'string', 'maxLength': 200}
        }
    },
    'preference_analysis': {
        'type': 'object',
        'properties': {
            'user_preferences': {
                'type': 'object',
                'additionalProperties': True,
            }
        },
    },
}

# 危険なパターン
DANGEROUS_PATTERNS = [
    r'<script.*?</script>',
    r'javascript:',
    r'on\w+\s*=',
    r'<iframe',
    r'<object',
    r'<embed',
    r'<link',
    r'<meta',
    r'<style',
    r'<form',
    r'<input',
    r'<button',
    r'<select',
    r'<textarea',
    r'<img.*onerror',
    r'<svg.*onload',
    r'<math.*onload',
    r'<details.*onload',
    r'<marquee.*onstart',
    r'<video.*onload',
    r'<audio.*onload',
    r'<iframe.*src',
    r'<object.*data',
    r'<embed.*src',
    r'<link.*href',
    r'<meta.*content',
    r'<style.*type',
    r'<form.*action',
    r'<input.*type',
    r'<button.*onclick',
    r'<select.*onchange',
    r'<textarea.*oninput'
]

class JSONValidator:
    """JSON検証クラス"""
    
    def __init__(self):
        self.dangerous_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]
        self.max_json_size = 10000  # 10KB制限
        self.max_string_length = 2000  # 文字列長制限
        
    def safe_json_parse(self, json_str: str, schema: str = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        安全なJSON解析
        
        Args:
            json_str: JSON文字列
            schema: スキーマ名
            max_retries: 最大再試行回数
            
        Returns:
            解析されたJSONオブジェクト
            
        Raises:
            ValueError: 解析に失敗した場合
        """
        if not json_str or not json_str.strip():
            raise ValueError("Empty JSON string")
        
        # サイズチェック
        if len(json_str) > self.max_json_size:
            raise ValueError(f"JSON too large: {len(json_str)} bytes")
        
        # 危険なパターンの検出
        for pattern in self.dangerous_patterns:
            if pattern.search(json_str):
                raise ValueError(f"Dangerous pattern detected: {pattern.pattern}")
        
        # JSON構造の基本検証
        if not json_str.strip().startswith('{'):
            raise ValueError("Invalid JSON format: must start with '{'")
        
        # JSON解析
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            if max_retries > 0:
                # 危険な文字を除去して再試行
                cleaned_json = self._clean_dangerous_chars(json_str)
                return self.safe_json_parse(cleaned_json, schema, max_retries - 1)
            else:
                raise ValueError(f"JSON parsing failed: {e}")
        
        # スキーマ検証
        if schema and schema in SCHEMAS:
            self._validate_schema(parsed, SCHEMAS[schema])
        
        # 文字列長チェック
        self._validate_string_lengths(parsed)
        
        return parsed
    
    def _clean_dangerous_chars(self, json_str: str) -> str:
        """危険な文字の除去"""
        dangerous_chars = ['<', '>', '&', '"', "'", '\\', '\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', '\x1c', '\x1d', '\x1e', '\x1f']
        for char in dangerous_chars:
            json_str = json_str.replace(char, '')
        return json_str
    
    def _validate_schema(self, data: Any, schema: Dict[str, Any]) -> None:
        """スキーマ検証"""
        if not isinstance(data, dict):
            raise ValueError("Root must be an object")
        
        # 必須フィールドのチェック
        for required_field in schema.get('required', []):
            if required_field not in data:
                raise ValueError(f"Missing required field: {required_field}")
        
        # プロパティの検証
        properties = schema.get('properties', {})
        for field, value in data.items():
            if field in properties:
                self._validate_property(field, value, properties[field])
    
    def _validate_property(self, field_name: str, value: Any, schema: Dict[str, Any]) -> None:
        """プロパティの検証"""
        expected_type = schema.get('type')
        
        if expected_type == 'string':
            if not isinstance(value, str):
                raise ValueError(f"Field '{field_name}' must be a string")
            max_length = schema.get('maxLength')
            if max_length and len(value) > max_length:
                raise ValueError(f"Field '{field_name}' too long: {len(value)} > {max_length}")
        
        elif expected_type == 'array':
            if not isinstance(value, list):
                raise ValueError(f"Field '{field_name}' must be an array")
            max_items = schema.get('maxItems')
            if max_items and len(value) > max_items:
                raise ValueError(f"Field '{field_name}' has too many items: {len(value)} > {max_items}")
            
            # 配列アイテムの検証
            items_schema = schema.get('items')
            if items_schema:
                for i, item in enumerate(value):
                    self._validate_property(f"{field_name}[{i}]", item, items_schema)
        
        elif expected_type == 'object':
            if not isinstance(value, dict):
                raise ValueError(f"Field '{field_name}' must be an object")
            # オブジェクトのプロパティ検証は再帰的に行う
        
        elif expected_type == 'boolean':
            if not isinstance(value, bool):
                raise ValueError(f"Field '{field_name}' must be a boolean")
        
        elif expected_type == 'integer':
            if not isinstance(value, int):
                raise ValueError(f"Field '{field_name}' must be an integer")
            minimum = schema.get('minimum')
            if minimum is not None and value < minimum:
                raise ValueError(f"Field '{field_name}' below minimum: {value} < {minimum}")
            maximum = schema.get('maximum')
            if maximum is not None and value > maximum:
                raise ValueError(f"Field '{field_name}' above maximum: {value} > {maximum}")
        
        # 列挙値のチェック
        enum_values = schema.get('enum')
        if enum_values and value not in enum_values:
            raise ValueError(f"Field '{field_name}' must be one of {enum_values}")
    
    def _validate_string_lengths(self, data: Any, path: str = "") -> None:
        """文字列長の検証"""
        if isinstance(data, dict):
            for key, value in data.items():
                self._validate_string_lengths(value, f"{path}.{key}" if path else key)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_string_lengths(item, f"{path}[{i}]")
        elif isinstance(data, str):
            if len(data) > self.max_string_length:
                raise ValueError(f"String too long at {path}: {len(data)} > {self.max_string_length}")

# グローバルインスタンス
json_validator = JSONValidator()

def safe_json_parse(json_str: str, schema: str = None, max_retries: int = 3) -> Dict[str, Any]:
    """
    安全なJSON解析（外部インターフェース）
    
    Args:
        json_str: JSON文字列
        schema: スキーマ名
        max_retries: 最大再試行回数
        
    Returns:
        解析されたJSONオブジェクト
    """
    return json_validator.safe_json_parse(json_str, schema, max_retries)

def validate_json_schema(data: Any, schema_name: str) -> bool:
    """
    JSONスキーマの検証
    
    Args:
        data: 検証するデータ
        schema_name: スキーマ名
        
    Returns:
        検証結果
    """
    if schema_name not in SCHEMAS:
        return False
    
    try:
        json_validator._validate_schema(data, SCHEMAS[schema_name])
        return True
    except ValueError:
        return False

def get_json_validation_stats() -> Dict[str, Any]:
    """JSON検証統計の取得"""
    # 実装は必要に応じて追加
    return {
        "total_validations": 0,
        "failed_validations": 0,
        "schema_violations": 0,
        "dangerous_patterns_detected": 0
    }
