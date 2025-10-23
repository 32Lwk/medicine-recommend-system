"""
セキュリティ設定管理モジュール
段階的ロールアウトの設定と管理を提供
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ロールアウトフェーズ設定
ROLLOUT_PHASE = int(os.getenv('SECURITY_ROLLOUT_PHASE', '1'))  # デフォルト: Phase 1

PHASE_SETTINGS = {
    1: {
        'name': 'Logging Only',
        'block_threshold': 100,  # ブロックしない
        'log_only': True,
        'description': 'ログのみ、ブロックなし'
    },
    2: {
        'name': 'High Risk Blocking',
        'block_threshold': 90,   # スコア90以上でブロック
        'log_only': False,
        'description': '高リスクのみブロック'
    },
    3: {
        'name': 'Full Protection',
        'block_threshold': 80,   # スコア80以上でブロック
        'log_only': False,
        'description': '完全保護モード'
    }
}

# ホワイトリスト設定
WHITELISTED_PATTERNS = []

# 医療用語辞書の自動更新設定
AUTO_UPDATE_MEDICAL_TERMS = os.getenv('AUTO_UPDATE_MEDICAL_TERMS', 'true').lower() == 'true'

# セキュリティログ設定
SECURITY_LOG_CONFIG = {
    'enabled': True,
    'log_file': 'log/security_events.jsonl',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
    'log_level': 'INFO'
}

# アラート設定
ALERT_CONFIG = {
    'enabled': True,
    'high_risk_threshold': 90,
    'block_rate_threshold': 0.1,  # 10%以上ブロックされた場合
    'email_alerts': False,
    'webhook_url': None
}

class SecurityConfig:
    """セキュリティ設定管理クラス"""
    
    def __init__(self):
        self.current_phase = ROLLOUT_PHASE
        self.whitelist = WHITELISTED_PATTERNS.copy()
        self.load_config()
    
    def load_config(self):
        """設定ファイルの読み込み"""
        config_file = 'security_config.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.current_phase = config.get('rollout_phase', ROLLOUT_PHASE)
                    self.whitelist = config.get('whitelisted_patterns', [])
            except Exception as e:
                logger.error(f"Error loading security config: {e}")
    
    def save_config(self):
        """設定ファイルの保存"""
        config = {
            'rollout_phase': self.current_phase,
            'whitelisted_patterns': self.whitelist,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open('security_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving security config: {e}")
    
    def get_phase_settings(self) -> Dict[str, Any]:
        """現在のフェーズ設定を取得"""
        return PHASE_SETTINGS.get(self.current_phase, PHASE_SETTINGS[1])
    
    def get_block_threshold(self) -> int:
        """ブロック閾値を取得"""
        return self.get_phase_settings()['block_threshold']
    
    def is_log_only(self) -> bool:
        """ログのみモードかどうか"""
        return self.get_phase_settings()['log_only']
    
    def should_block(self, risk_score: int) -> bool:
        """ブロックすべきかどうか判定"""
        if self.is_log_only():
            return False
        return risk_score >= self.get_block_threshold()
    
    def add_to_whitelist(self, pattern: str) -> bool:
        """ホワイトリストにパターンを追加"""
        if pattern not in self.whitelist:
            self.whitelist.append(pattern)
            self.save_config()
            logger.info(f"Added to whitelist: {pattern}")
            return True
        return False
    
    def remove_from_whitelist(self, pattern: str) -> bool:
        """ホワイトリストからパターンを削除"""
        if pattern in self.whitelist:
            self.whitelist.remove(pattern)
            self.save_config()
            logger.info(f"Removed from whitelist: {pattern}")
            return True
        return False
    
    def is_whitelisted(self, text: str) -> bool:
        """テキストがホワイトリストに含まれるかチェック"""
        for pattern in self.whitelist:
            if pattern.lower() in text.lower():
                return True
        return False
    
    def advance_phase(self) -> bool:
        """次のフェーズに進む"""
        if self.current_phase < 3:
            self.current_phase += 1
            self.save_config()
            logger.info(f"Advanced to phase {self.current_phase}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """設定統計の取得"""
        return {
            'current_phase': self.current_phase,
            'phase_name': self.get_phase_settings()['name'],
            'block_threshold': self.get_block_threshold(),
            'log_only': self.is_log_only(),
            'whitelist_count': len(self.whitelist),
            'auto_update_medical_terms': AUTO_UPDATE_MEDICAL_TERMS
        }

# グローバルインスタンス
security_config = SecurityConfig()

def get_current_phase() -> int:
    """現在のフェーズを取得"""
    return security_config.current_phase

def get_block_threshold() -> int:
    """ブロック閾値を取得"""
    return security_config.get_block_threshold()

def should_block_input(risk_score: int) -> bool:
    """入力をブロックすべきかどうか判定"""
    return security_config.should_block(risk_score)

def is_whitelisted(text: str) -> bool:
    """テキストがホワイトリストに含まれるかチェック"""
    return security_config.is_whitelisted(text)

def add_to_whitelist(pattern: str) -> bool:
    """ホワイトリストにパターンを追加"""
    return security_config.add_to_whitelist(pattern)

def remove_from_whitelist(pattern: str) -> bool:
    """ホワイトリストからパターンを削除"""
    return security_config.remove_from_whitelist(pattern)

def advance_to_next_phase() -> bool:
    """次のフェーズに進む"""
    return security_config.advance_phase()

def get_security_stats() -> Dict[str, Any]:
    """セキュリティ統計の取得"""
    return security_config.get_stats()
