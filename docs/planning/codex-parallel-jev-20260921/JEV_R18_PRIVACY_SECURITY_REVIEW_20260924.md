# JEV R18 Privacy & Security Review — 2026-09-24

**Reviewer role:** Privacy/Security (Independent)  
**Scope:** R18 build as of 2026-09-23 commit wave (local-only, not pushed to production)  
**Go/No-Go:** ❌ **CONDITIONAL NO-GO** (see §4)

---

## 1. What Is Sent to Jev (TypeSafe System One)

Endpoint: `https://api.typesafe.ai/v1/systemone`  
Auth: `Authorization: Bearer {JEV_API_KEY}` (env var)

### 1.1 State Payload Fields Sent to External API

| フィールド | 内容 | PII リスク | 根拠ファイル |
|---|---|---|---|
| `channel` | `"web"` or `"line"` — デプロイ種別 | なし | `jev_router.py:407-413` |
| `user_input` | ユーザー入力テキスト（4000文字まで） | **高** — 氏名・住所・症状・薬品名など自由記述 | `jev_router.py:228-233, 436` |
| `recent_turns[].role` | `"user"` / `"assistant"` | なし | `jev_router.py:237-283` |
| `recent_turns[].content` | 直近5ターン × 最大240文字の会話本文 | **高** — ユーザー入力・bot応答に症状・薬品名等が含まれる | `jev_router.py:237-283` |
| `recent_context` | `recent_turns` と同一参照（eval alias） | 同上 | `jev_router.py:438` |
| `meta.last_primary_route` | 直前ルーティング分類名（例: `Physical`） | なし | `jev_router.py:420-422` |
| `meta.last_sub_route` | 直前サブルーティング分類名 | なし | `jev_router.py:423-425` |
| `meta.last_recommended_medicines` | 推薦済み薬品の商品名（最大3件） | 低（商品名のみ）。ただし薬品名＋症状の組合せは間接的PII | `jev_router.py:326-341, 426-428` |
| `meta.active_symptoms` | 直前bot応答のdiagnosis.symptomsより抽出した症状テキスト（最大5件） | **中〜高** — フリーテキスト症状情報が外部送信される | `jev_router.py:343-378, 429-431` |
| `meta.medicine_qa_focus` | 薬品Q&Aフォーカス（文字列または文字列リスト、最大8件） | 中 — 特定薬品への関心が外部に渡る | `jev_router.py:380-390, 432-433` |
| `app_context` | 固定文字列 `"Japanese OTC medicine routing"` | なし | `jev_router.py:435` |

**送信されない（ガードあり）フィールド:**

| 禁止フィールド | 除外機構 |
|---|---|
| `sid` / `session_id` / `user_id` / `line_user_id` | `_FORBIDDEN_STATE_KEYS` allowlist + `validate_jev_state_contract()` raise |
| `user_attributes` | 同上 |
| `rag` / `rag_text` / `system_prompt` / `prompt` | 同上 |
| `baseline_triage_hint` | `del triage_result` で明示的に破棄 |
| `api_key` / `authorization` / `token` / `password` | `scrub_forbidden_jev_state_keys()` + `FORBIDDEN_LOG_KEYS` |
| `email` / `phone` / `address` | FORBIDDEN_LOG_KEYS（ログ側）; state 送信は state 構造上入らない |

---

## 2. PII リスク評価

### 2.1 `user_input` — **最高リスク（BLOCKING 未解決）**

ユーザーが入力する自由記述テキストはそのまま（最大4000文字）外部に送信される。  
医療相談アプリであるため、以下が含まれうる：

- 個人の健康情報（症状、疾患名、投薬歴）
- 氏名・年齢・性別の自発的記載
- 地域情報（店舗名、薬局名など）

現在、`user_input` に対して **PII マスク・匿名化処理は存在しない**。  
`_sanitize_user_text()` はNULLバイト除去と長さ制限のみであり、PII をスクラブしない。

```
src/dialogue/routing/jev_router.py:228-232
def _sanitize_user_text(user_text: Any) -> str:
    text = "" if user_text is None else str(user_text)
    text = text.replace("\x00", "").strip()
    if len(text) > 4000:
        text = text[:4000]
    return text
```

### 2.2 `recent_turns[].content` — **高リスク（BLOCKING 未解決）**

直近5ターン分の会話本文が外部に送信される（1ターン最大240文字）。  
bot側の応答にも推奨理由・症状まとめが含まれる場合がある。

### 2.3 `meta.active_symptoms` — **中リスク**

直前ターンの `diagnosis.symptoms` から抽出した症状テキスト。フリーテキストのまま送信。

### 2.4 TypeSafe System One 保持ポリシー — **UNKNOWN → BLOCKING**

> ⚠️ **この情報はリポジトリ内に存在しない。発明しない。**

- TypeSafe System One（`api.typesafe.ai`）のデータ保持期間・保存場所・サブプロセッサ・日本居住者への適用法令（個人情報保護法、GDPR等）に関する文書がリポジトリ内に一切ない。
- DPA（Data Processing Agreement）または TOS のどちらも `/docs/` 配下に存在しない確認済み。
- この欠落は **BLOCKING**。ユーザーの医療クエリ・症状情報を外部に送信する前に、プロバイダとの契約・保持ポリシー確認が必須。

---

## 3. セキュリティ評価

### 3.1 API キー管理

| 項目 | 状況 |
|---|---|
| `JEV_API_KEY` 形式 | `apikey_210f2d...` — `.env` に平文保存（ローカルのみ） |
| ログへの漏洩 | `api_key = None` で参照を即破棄（`jev_client.py:210`）; `logger.exception` / `exc_info=True` 明示禁止 |
| `JevClientResult` への混入 | コードレビュー済み — API key が result フィールドに入る経路なし |
| Bearer token 検出 regex | `_SECRET_VALUE_RE` が shadow ログをスキャン（`jev_metrics.py:161-164`） |

**評価:** API key の取り扱いは適切。ログへの漏洩ガードあり。  
**.env がリポジトリに含まれている**: `.gitignore` での除外を確認すること。現在のgit statusでは `.env` は未追跡（`??`）ではなく変更済み（`M`）の模様は見受けられないが、初期コミット混入リスクに注意。

### 3.2 状態ガード（Allowlist 契約）

- `validate_jev_state_contract()`: 禁止キー検出時に `ForbiddenJevStateError` を raise（`python -O` でも有効）
- `scrub_forbidden_jev_state_keys()`: 防衛的スクラブ（raise 後の二重ガード）
- 送信直前の `copy.deepcopy()` により caller の state を mutate しない

**評価:** allowlist ガードは堅牢。ただしバイパス経路（`extra` parameter）が `record_shadow_event()` に存在するため、caller が FORBIDDEN_LOG_KEYS キーを `extra={}` で渡すと scrub 後に再挿入のリスクがある（低リスク、実際の呼び出し元はレビュー済み）。

### 3.3 shadow ログの PII

`jev_metrics.py` は `FORBIDDEN_LOG_KEYS` で以下をスキャン・削除：

```python
"user_input", "user_text", "history", "recent_turns", "recent_context",
"sid", "session_id", "user_id", "line_user_id", "user_attributes",
"email", "phone", "address", "answers", "raw_answers", "system_prompt", ...
```

`trace_hash_for_sid()` は SID を SHA-256 の先頭32文字に変換（一方向ハッシュ）。  
`state_shape` はキー名と長さのみ（本文なし）。

**評価:** shadow ログの PII 処理は適切。`answers` フィールドも禁止対象に含まれる点を確認済み。

---

## 4. Privacy Go/No-Go 判定

| 評価項目 | 状況 | 判定 |
|---|---|---|
| TypeSafe 保持ポリシー / DPA | **リポジトリ内に存在しない** | ❌ **BLOCKING** |
| `user_input` PII マスク | 存在しない | ❌ **BLOCKING** |
| `active_symptoms` 匿名化 | 存在しない | ⚠️ 要検討 |
| API key ログ漏洩ガード | 実装済み・適切 | ✅ |
| State allowlist 契約 | 実装済み・堅牢 | ✅ |
| SID のログ匿名化 | SHA-256 一方向ハッシュ | ✅ |
| Shadow log PII スクラブ | FORBIDDEN_LOG_KEYS 実装済み | ✅ |
| 現在の本番有効化状況 | `JEV_ENABLED` 未設定 → False（OFF） | ✅ 安全 |

### 判定: ❌ CONDITIONAL NO-GO

**必須解決事項（本番有効化前）:**

1. **[BLOCKING]** TypeSafe System One のデータ保持ポリシー・DPA を取得し `/docs/ops/` に配置すること  
2. **[BLOCKING]** `user_input` に対するPIIスクラブ（匿名化または送信前フィルタリング）の方針決定と実装、またはTypeSafeとのDPA締結で代替すること  
3. **[推奨]** `active_symptoms`・`recent_turns.content` に対する最小化方針の策定

**現在の状態:** `JEV_ENABLED` は `.env` で未設定 → `is_jev_enabled()` returns `False` → shadow 呼び出しなし → 現在は安全。

---

## 5. 確認済み非ブロッカー

- Shadow ログは本線リクエストパスとは別スレッドで実行（失敗しても本線に伝播しない）
- `JevClientResult` に `answers` フィールドなし（raw APIレスポンス本文は保持しない）
- 429/5xx のみリトライ（最大1回）。timeout/network error はリトライしない

---

*Reviewed by: Privacy/Security + Independent Reviewer*  
*Build: R18 local, 2026-09-24*  
*Status: NOT PUSHED, NOT LIVE*
