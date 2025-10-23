"""
セキュリティイベントログモジュール
セキュリティ関連のイベントを記録・監視
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class SecurityLogger:
    """セキュリティログ管理クラス"""
    
    def __init__(self, log_file: str = "log/security_events.jsonl"):
        self.log_file = log_file
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """ログディレクトリの作成"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def log_security_event(self, event_type: str, user_id: str = None, 
                          input_text: str = None, risk_score: int = None,
                          is_safe: bool = None, action: str = None,
                          warnings: List[str] = None, details: Dict[str, Any] = None):
        """
        セキュリティイベントのログ記録
        
        Args:
            event_type: イベントタイプ
            user_id: ユーザーID
            input_text: 入力テキスト
            risk_score: リスクスコア
            is_safe: 安全かどうか
            action: 実行されたアクション
            warnings: 警告リスト
            details: 詳細情報
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "input_length": len(input_text) if input_text else 0,
            "risk_score": risk_score,
            "is_safe": is_safe,
            "action": action,
            "warnings": warnings or [],
            "details": details or {}
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Error writing security log: {e}")
    
    def log_input_validation(self, user_id: str, input_text: str, risk_score: int, 
                           is_safe: bool, warnings: List[str], sanitized_text: str):
        """入力検証イベントのログ記録"""
        self.log_security_event(
            event_type="input_validation",
            user_id=user_id,
            input_text=input_text,
            risk_score=risk_score,
            is_safe=is_safe,
            action="allowed" if is_safe else "blocked",
            warnings=warnings,
            details={"sanitized_text": sanitized_text}
        )
    
    def log_blocked_input(self, user_id: str, input_text: str, risk_score: int, 
                         reason: str, patterns_detected: List[str]):
        """ブロックされた入力のログ記録"""
        self.log_security_event(
            event_type="blocked_input",
            user_id=user_id,
            input_text=input_text,
            risk_score=risk_score,
            is_safe=False,
            action="blocked",
            warnings=[reason],
            details={"patterns_detected": patterns_detected}
        )
    
    def log_whitelist_addition(self, pattern: str, reason: str, added_by: str):
        """ホワイトリスト追加のログ記録"""
        self.log_security_event(
            event_type="whitelist_addition",
            user_id=added_by,
            input_text=pattern,
            is_safe=True,
            action="whitelisted",
            details={"reason": reason}
        )
    
    def log_phase_advancement(self, old_phase: int, new_phase: int, advanced_by: str):
        """フェーズ進行のログ記録"""
        self.log_security_event(
            event_type="phase_advancement",
            user_id=advanced_by,
            is_safe=True,
            action="phase_advanced",
            details={"old_phase": old_phase, "new_phase": new_phase}
        )
    
    def log_safety_check(self, medicine_name: str, user_info: Dict[str, Any], 
                        safety_result: Dict[str, Any]):
        """安全性チェックのログ記録"""
        self.log_security_event(
            event_type="safety_check",
            user_id=user_info.get('user_id'),
            input_text=medicine_name,
            is_safe=safety_result.get('is_safe', True),
            action="safety_checked",
            details={
                "medicine_name": medicine_name,
                "user_age": user_info.get('age'),
                "pregnant": user_info.get('pregnant', False),
                "breastfeeding": user_info.get('breastfeeding', False),
                "safety_score": safety_result.get('safety_score', 100),
                "requires_escalation": safety_result.get('requires_escalation', False),
                "doctor_referral_required": safety_result.get('doctor_referral_required', False)
            }
        )
    
    def get_security_stats(self, hours: int = 24) -> Dict[str, Any]:
        """セキュリティ統計の取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        total_events = 0
        blocked_count = 0
        risk_scores = []
        event_types = Counter()
        patterns_detected = Counter()
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                            
                            if entry_time >= cutoff_time:
                                total_events += 1
                                event_types[entry.get("event_type", "unknown")] += 1
                                
                                if not entry.get("is_safe", True):
                                    blocked_count += 1
                                
                                risk_score = entry.get("risk_score")
                                if risk_score is not None:
                                    risk_scores.append(risk_score)
                                
                                # 検出されたパターンの集計
                                details = entry.get("details", {})
                                patterns = details.get("patterns_detected", [])
                                for pattern in patterns:
                                    patterns_detected[pattern] += 1
                        
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Error parsing log entry: {e}")
                            continue
        
        except FileNotFoundError:
            logger.info("Security log file not found")
        
        return {
            "total_events": total_events,
            "blocked_count": blocked_count,
            "block_rate": blocked_count / total_events if total_events > 0 else 0,
            "avg_risk_score": sum(risk_scores) / len(risk_scores) if risk_scores else 0,
            "max_risk_score": max(risk_scores) if risk_scores else 0,
            "min_risk_score": min(risk_scores) if risk_scores else 0,
            "event_types": dict(event_types),
            "top_patterns": dict(patterns_detected.most_common(10)),
            "time_range_hours": hours
        }
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """最近のイベント取得"""
        events = []
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 最新のイベントから取得
                for line in reversed(lines[-limit:]):
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            events.append(entry)
                        except (json.JSONDecodeError, ValueError):
                            continue
        
        except FileNotFoundError:
            logger.info("Security log file not found")
        
        return events
    
    def get_high_risk_events(self, risk_threshold: int = 80) -> List[Dict[str, Any]]:
        """高リスクイベントの取得"""
        high_risk_events = []
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if entry.get("risk_score", 0) >= risk_threshold:
                                high_risk_events.append(entry)
                        except (json.JSONDecodeError, ValueError):
                            continue
        
        except FileNotFoundError:
            logger.info("Security log file not found")
        
        return high_risk_events
    
    def cleanup_old_logs(self, days: int = 30):
        """古いログのクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(days=days)
        temp_file = self.log_file + ".tmp"
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as infile, \
                 open(temp_file, "w", encoding="utf-8") as outfile:
                
                for line in infile:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                            
                            if entry_time >= cutoff_time:
                                outfile.write(line)
                        except (json.JSONDecodeError, ValueError):
                            continue
            
            # 一時ファイルを元のファイルに置き換え
            os.replace(temp_file, self.log_file)
            logger.info(f"Cleaned up logs older than {days} days")
        
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

# グローバルインスタンス
security_logger = SecurityLogger()

def log_security_event(event_type: str, user_id: str = None, input_text: str = None, 
                      risk_score: int = None, is_safe: bool = None, action: str = None,
                      warnings: List[str] = None, details: Dict[str, Any] = None):
    """セキュリティイベントのログ記録（外部インターフェース）"""
    security_logger.log_security_event(event_type, user_id, input_text, risk_score, 
                                     is_safe, action, warnings, details)

def log_input_validation(user_id: str, input_text: str, risk_score: int, 
                        is_safe: bool, warnings: List[str], sanitized_text: str):
    """入力検証イベントのログ記録（外部インターフェース）"""
    security_logger.log_input_validation(user_id, input_text, risk_score, 
                                       is_safe, warnings, sanitized_text)

def log_blocked_input(user_id: str, input_text: str, risk_score: int, 
                     reason: str, patterns_detected: List[str]):
    """ブロックされた入力のログ記録（外部インターフェース）"""
    security_logger.log_blocked_input(user_id, input_text, risk_score, 
                                     reason, patterns_detected)

def get_security_stats(hours: int = 24) -> Dict[str, Any]:
    """セキュリティ統計の取得（外部インターフェース）"""
    return security_logger.get_security_stats(hours)

def get_recent_events(limit: int = 100) -> List[Dict[str, Any]]:
    """最近のイベント取得（外部インターフェース）"""
    return security_logger.get_recent_events(limit)

def get_high_risk_events(risk_threshold: int = 80) -> List[Dict[str, Any]]:
    """高リスクイベントの取得（外部インターフェース）"""
    return security_logger.get_high_risk_events(risk_threshold)
