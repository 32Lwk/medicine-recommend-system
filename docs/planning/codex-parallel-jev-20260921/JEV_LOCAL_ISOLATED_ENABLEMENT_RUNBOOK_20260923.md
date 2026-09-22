# JEV Local Isolated Enablement Runbook

**Date**: 2026-09-23  
**Status**: procedure only — **R10 did not enable flags**  
**Related**: `JEV_R10_LOCAL_ENABLEMENT_READINESS_20260923.md`

---

## 1. Environment conditions

必須:

- ローカル隔離マシン / ローカルプロセスのみ
- **本番DB不使用**（接続先を起動前に確認）
- **本番session不使用**
- shadow JSONL はローカル `log/` 等へ（クラウド本番バケットへ相談全文を送らない）
- secrets を文書・チャット・ログへ貼らない
- 既存 `.env` を勝手に表示・コミットしない（必要ならローカル一時 override のみ）

## 2. Flag names（コード確認済み）

| Env | Getter | Default |
| --- | --- | --- |
| `JEV_ENABLED` | `is_jev_enabled()` | **False** |
| `JEV_INTENT_ROUTER_SHADOW` | `is_jev_intent_router_shadow_enabled()` = JEV_ENABLED **and** flag | **False** |
| `JEV_INTENT_ROUTER_PRIMARY` | `is_jev_intent_router_primary_enabled()` | **False**（実行route変更に使わない） |
| `POLICY_ENFORCEMENT_D2` | `is_policy_enforcement_d2_enabled()` | **False** |

### Local isolated ON candidate（承認後のみ）

```text
JEV_ENABLED=1
JEV_INTENT_ROUTER_SHADOW=1
JEV_INTENT_ROUTER_PRIMARY=0
POLICY_ENFORCEMENT_D2=1
```

PowerShell 例（セッション限定・未実行）:

```powershell
$env:JEV_ENABLED='1'
$env:JEV_INTENT_ROUTER_SHADOW='1'
$env:JEV_INTENT_ROUTER_PRIMARY='0'
$env:POLICY_ENFORCEMENT_D2='1'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
```

終了時はプロセス終了または env 削除で OFF に戻す。**リポジトリ default は変更しない。**

## 3. Prohibitions

- primary routing 切替（`JEV_INTENT_ROUTER_PRIMARY=1` で実行routeを変えない）
- production endpoint / 本番データ
- commit / push
- live repeat=10
- default 値のコード変更
- クラウドログへの相談全文送信
- raw medical text を counseling_detail 以外の経路へ増やす

## 4. Pre-smoke checklist（ON承認後）

手動または既存pytest（`POLICY_ENFORCEMENT_D2=1` monkeypatch相当）:

| Case | Expect |
| --- | --- |
| pure SessionOps | SessionOps early; policy 0 |
| crisis mixed | Emergency; SessionOps 0 |
| Security mixed | Security terminal; SessionOps 0 |
| prescription / controlled | typed policy terminal |
| medical examination | boundary; not Security |
| normal Physical / Concierge | continue |
| adapter / DB unavailable | SF-E1; NM off |
| shadow JSONL | schema; attempted flags sane |

推奨コマンド（フラグONは環境側）:

```powershell
$env:PYTHONUTF8='1'
python -m pytest tests/dialogue/routing/test_r8_c1_pipeline_matrix.py tests/dialogue/routing/test_r10_hsec_security_matrix.py tests/dialogue/routing/test_r8_flag_off_on_compat.py tests/dialogue/routing/test_r7_c2_rollback_integration.py -q
```

## 5. Immediate stop conditions

次のいずれかで **即 OFF・作業停止**:

- SessionOps が Safety/Policy/Security を迂回
- raw medical text の予期しないログ増
- duplicate response / recommendation 継続
- Jev primary への切替兆候
- DB書込み先不明
- Critical/High 新規
- accuracy 母集団の契約崩れ

## 6. Rollback

```powershell
Remove-Item Env:POLICY_ENFORCEMENT_D2 -ErrorAction SilentlyContinue
Remove-Item Env:JEV_INTENT_ROUTER_SHADOW -ErrorAction SilentlyContinue
Remove-Item Env:JEV_ENABLED -ErrorAction SilentlyContinue
# PRIMARY は常に 0 のまま
```

コード default は既に OFF — プロセス再起動で安全側に戻る。
