# JEV R18 SRE / Rollback Runbook — 2026-09-24

**Reviewer role:** SRE / Rollback (Independent)  
**Scope:** R18 build, local + staging-equivalent environment  
**Kill switch proven?:** ✅ YES (default OFF)  
**Rollback proven?:** ⚠️ PARTIAL (env var rollback proven; Cloud Run redeploy path undocumented)  
**Async isolation present?:** ❌ NO — circuit breaker absent; queue is software-only soft cap

---

## 1. Kill Switch 一覧

### 1.1 Jev 全体キルスイッチ

```powershell
# ローカル PowerShell — JEV を完全 OFF にする
$env:JEV_ENABLED = "false"
```

```python
# config/llm_flags.py:479-481
def is_jev_enabled() -> bool:
    """Jev 全体キルスイッチ。未設定 / false は OFF（v2 unset=ON とは逆）。"""
    return _flag("JEV_ENABLED", False)
```

**重要:** `JEV_ENABLED` は **デフォルト False**（v2フラグの「未設定=ON」とは逆設計）。  
明示的 `true` のみ有効。未設定 = OFF。

### 1.2 Shadow 専用キルスイッチ

```powershell
# Jev 有効だが shadow を停止する（将来用）
$env:JEV_ENABLED = "true"
$env:JEV_INTENT_ROUTER_SHADOW = "false"
```

```python
# config/llm_flags.py:483-490
def is_jev_intent_router_shadow_enabled() -> bool:
    return is_jev_enabled() and _flag("JEV_INTENT_ROUTER_SHADOW", False)
```

### 1.3 Primary 用キルスイッチ（現在は使用禁止）

```python
# config/llm_flags.py:491-499
def is_jev_intent_router_primary_enabled() -> bool:
    """Phase 1 では実行 route 変更に使ってはならない（shadow adapter のみ）。"""
    return is_jev_enabled() and _flag("JEV_INTENT_ROUTER_PRIMARY", False)
```

`JEV_INTENT_ROUTER_PRIMARY` は Phase 1 では **routing を変えない**。Supervisor 制約あり。

---

## 2. Kill Switch 伝播経路（コード確認済み）

```
JEV_ENABLED=false (env)
  └─ is_jev_enabled() → False
       └─ schedule_jev_shadow() (jev_router.py:658-661)
            if not force and (not _is_jev_enabled() or ...):
                return False  ← API 呼び出しなし
```

伝播経路はコードで確認済み。`force=True` フラグが付いたテスト用同期実行（`run_jev_shadow_sync()`）はフラグを迂回するが、本線コードから呼ばれない。

---

## 3. Kill Switch 確認手順（ローカル / staging-equivalent）

### 手順A: env 変数で OFF 確認

```powershell
# 1. 現在の設定確認
Write-Host "JEV_ENABLED = $($env:JEV_ENABLED)"
Write-Host "JEV_INTENT_ROUTER_SHADOW = $($env:JEV_INTENT_ROUTER_SHADOW)"

# 2. キルスイッチを確実に OFF
$env:JEV_ENABLED = "false"

# 3. Python でフラグ状態を確認（秘密情報なし）
cd d:\Programing\medicine-recommend
.venv\Scripts\python.exe -c @"
import sys
sys.path.insert(0, '.')
from config.llm_flags import is_jev_enabled, is_jev_intent_router_shadow_enabled
print('is_jev_enabled:', is_jev_enabled())
print('is_jev_shadow_enabled:', is_jev_intent_router_shadow_enabled())
assert not is_jev_enabled(), 'FAIL: JEV must be OFF'
print('PASS: Jev is OFF')
"@
```

期待出力:
```
is_jev_enabled: False
is_jev_shadow_enabled: False
PASS: Jev is OFF
```

### 手順B: OFF 時に API 呼び出しなしを確認

```powershell
# JEV_ENABLED=false のまま shadow をスケジュールし、呼び出しなしを確認
$env:JEV_ENABLED = "false"

.venv\Scripts\python.exe -c @"
import sys
sys.path.insert(0, '.')

# Mock httpx を使わず、実際にフラグがガードを通過するか確認
from src.dialogue.routing.jev_router import schedule_jev_shadow

result = schedule_jev_shadow(
    state={"user_input": "テスト", "channel": "web", "recent_turns": [], "recent_context": [], "meta": {}, "app_context": "test"},
    legacy_decision={"primary_route": "Physical", "sub_route": None},
    correlation_id="test-kill-switch-verify",
    sync=False,
)
print(f'schedule_jev_shadow returned: {result}')
assert result == False, f'FAIL: expected False, got {result}'
print('PASS: Shadow skipped (kill switch effective)')
"@
```

期待出力:
```
schedule_jev_shadow returned: False
PASS: Shadow skipped (kill switch effective)
```

---

## 4. Rollback 手順

### 4.1 ローカル環境 rollback（即時）

```powershell
# 最速ロールバック: 環境変数を削除または false にする
Remove-Item Env:JEV_ENABLED -ErrorAction SilentlyContinue
# または
$env:JEV_ENABLED = "false"
```

プロセス再起動不要（`_flag()` は `os.getenv()` を毎回呼び出すため）。  
ただし `_shared_client` (httpx) は `atexit` で解放 — 実行中リクエストは完了を待つ。

### 4.2 Cloud Run / GCP staging-equivalent rollback

> **注意:** 以下は原則のみ記載。実際の Cloud Run サービス名・リージョンは secrets なしでは確認できないため、具体的なコマンドは placeholder とする。

```powershell
# GCP Cloud Run への env var 設定 (gcloud CLI)
gcloud run services update <SERVICE_NAME> `
    --region <REGION> `
    --update-env-vars JEV_ENABLED=false

# 反映確認（新リビジョンが SERVING になるまで待つ）
gcloud run services describe <SERVICE_NAME> --region <REGION> `
    --format="value(status.latestReadyRevisionName)"
```

**注意事項:**
- Cloud Run は env var 変更時に新リビジョンをデプロイする（数十秒〜数分）
- 既存リクエストは旧リビジョンで完了する（並走期間あり）
- Jev shadow は非同期スレッドのため、rollback 後も実行中 worker は完了する

### 4.3 セッション単位ロールバック（denylist）

Jev には現時点でセッション単位 denylist なし（v2の `CHAT_PIPELINE_V2_DENYLIST` とは別）。  
セッション単位のロールバックが必要な場合は `JEV_ENABLED=false` 一択。

---

## 5. FLAG OFF 確認チェックリスト

```powershell
# Rollback rehearsal: JEV flags OFF verification
.venv\Scripts\python.exe -c @"
import sys, os
sys.path.insert(0, '.')

# Ensure both flags are off
os.environ['JEV_ENABLED'] = 'false'
os.environ['JEV_INTENT_ROUTER_SHADOW'] = 'false'

import importlib
import config.llm_flags as lf
importlib.reload(lf)

checks = {
    'is_jev_enabled': lf.is_jev_enabled(),
    'is_jev_shadow_enabled': lf.is_jev_intent_router_shadow_enabled(),
    'is_jev_primary_enabled': lf.is_jev_intent_router_primary_enabled(),
}

print('=== JEV Kill Switch Verification ===')
all_ok = True
for name, val in checks.items():
    status = 'PASS' if not val else 'FAIL'
    if val:
        all_ok = False
    print(f'  {status}: {name} = {val}')

if all_ok:
    print('=== ALL CLEAR: Jev is completely disabled ===')
else:
    print('=== ALERT: Some flags are still ON ===')
    sys.exit(1)
"@
```

---

## 6. 非同期分離（Async Isolation）の現状評価

### 6.1 実装されているもの

| コンポーネント | 実装 | ファイル |
|---|---|---|
| Jev shadow executor | `ThreadPoolExecutor(max_workers=2)` | `jev_router.py:127-138` |
| Pending task soft cap | `_MAX_PENDING_SHADOW = 8`（カウンタ） | `jev_router.py:27` |
| Queue full スキップ | `error_class="queue_full"` でメトリクスに記録しスキップ | `jev_router.py:726-733` |
| Submit 失敗スキップ | `error_class="submit_failed"` でスキップ | `jev_router.py:750-760` |
| 本線ブロック防止 | shadow 失敗は `return False` のみ、本線例外なし | `jev_router.py:763` |
| IntentRouter shadow | `threading.Thread(daemon=True)` | `shadow.py:108-116` |

### 6.2 **欠如しているもの — Shadow Not Ready 要因**

| 欠如コンポーネント | リスク | 影響 |
|---|---|---|
| **Circuit Breaker** | Jev API が連続失敗しても自動 open しない。手動 kill switch が必要 | 外部 API 障害時にスレッドが溜まる可能性 |
| **外部 Queue（Redis/SQS等）** | `_pending_count` はプロセスローカルのメモリカウンタ。再起動で消える | マルチプロセス環境で pending cap が機能しない |
| **Retry budget isolation** | worker 内の retry は `jev_client.py` の 1 回のみだが、複数 worker が同時 retry しうる | 429 バースト時にリトライが重なる可能性 |
| **Timeout budget per worker** | executor worker の実行時間に上限なし（httpx timeout=3.5秒は API タイムアウトのみ） | executor 枯渇リスク（低） |
| **daemon thread 依存** | IntentRouter shadow は bare daemon thread（atexit なし、join なし） | 結果ログ消失リスク（プロセス終了時） |

**判定: Shadow Not Ready（production shadow は本番投入前に circuit breaker 実装が必要）**

---

## 7. Cost メトリクス評価

| 項目 | 状況 |
|---|---|
| コスト単価 | `JEV_INPUT_COST_USD_PER_MTOK = 0.042`（入力のみ推定） |
| 測定種別 | `jev_cost_usd_estimate` = **推定**（token×単価）。実測でない |
| 実測コスト | `openai_cost_usd_actual` フィールドがあるが TypeSafe の実測取得は未実装 |
| 命名規則 | `jev_cost_usd` は **DEPRECATED** エイリアス。新規集計は `jev_cost_usd_estimate` を使う |
| ダッシュボード | ローカル JSONL（`log/jev_intent_router_shadow.jsonl`）のみ。本番 Datadog/CloudWatch 接続なし |

**評価:** コスト推定は適切に「推定」と明記されている。実測コスト取得は未実装（UNKNOWN リスク）。

---

## 8. SRE 判定サマリー

| 評価項目 | 状況 | 判定 |
|---|---|---|
| Kill switch 存在 | `JEV_ENABLED=false`（デフォルト OFF） | ✅ |
| Kill switch proven | ローカルコードレビュー＋手順確認済み | ✅ |
| Rollback（ローカル） | env var 削除で即時 | ✅ |
| Rollback（Cloud Run） | gcloud update env vars（redeploy 数分） | ⚠️ 未リハーサル |
| Async shadow isolation | ThreadPoolExecutor soft cap あり | ⚠️ 不十分 |
| Circuit breaker | **なし** | ❌ |
| 外部 Queue | **なし**（インメモリカウンタのみ） | ❌ |
| 本番 shadow 準備 | **Not Ready** | ❌ |
| 現在の本番稼働状況 | `JEV_ENABLED` 未設定 → OFF → 安全 | ✅ |

---

*Reviewed by: SRE/Rollback (Independent)*  
*Build: R18 local, 2026-09-24*  
*Status: NOT PUSHED, NOT LIVE*
