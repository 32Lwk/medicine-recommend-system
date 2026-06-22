#!/usr/bin/env bash
# CHANGELOG 思想・意図を反映して GitHub issue を更新する。
# 前提: gh auth login 済み（32Lwk アカウントが suspend 解除されていること）
set -euo pipefail
cd "$(dirname "$0")/.."

gh issue edit 57 --body "$(cat <<'EOF'
## 目的

本番 Cloud Run（`medicine.yutok.dev` / `medicine-recommend`）で LINE Messaging API Webhook を有効化し、エンドユーザーが LINE から相談できる状態にする。

親 Epic: #55 | オンボーディング #7: #88

---

## プロジェクトコンテキスト — なぜまだ本番 ON していないか

CHANGELOG が繰り返し示す方針は **「機能は揃ったが、本番は段階的・慎重に」** である。

| 教訓・方針 | CHANGELOG | 本 issue への意味 |
|-----------|-----------|------------------|
| **6/16 ロールバック** | Sage UI 全置換は本番で崩れ、即 revert | LINE も **dev E2E → 法務 → 本番 env** の順が自然 |
| **6/17 段階公開** | デュアルパス・フラグ・Cookie で QA | `LINE_WEBHOOK_ENABLED=false` は **意図的保留**（壊れていない） |
| **6/22 法務先行** | プライバシーポリシー改定（長期記憶・削除請求） | 技術 ON の前に **規約が本番に載っていること** を確認 |
| **6/22 長期記憶** | プロファイル + 要約 + 削除 + 引き継ぎ | 本番 ON の価値は「**続きから相談できる LINE**」— 実装は完了、運用待ち |
| **待たせない** | 6/13–15 Reply 優先・loading・二重返信防止 | 本番 smoke は `LINE_SPEED_BENCH.md`（挨拶 <1s、症状 4–6s）を基準に |

> オンボーディング（#88）: 「β版（試験運用）— より**安全で分かりやすい**情報提供に向けて改善を続けています」  
> LINE 連携に ✅ が付いているが、**本番 Webhook OFF = まだ一般公開していない** という正直な状態。

---

## 設計意図 — LINE を「日常の相談導線」にする

CHANGELOG 2026-06 集約:

1. **待たせない** — Reply 優先配信、loading animation、Physical 段階 Push（carousel → advice）
2. **信頼** — 二重返信防止、Quick Reply フィードバック永続化、危機・緊急は Flex ではなく安全テキスト
3. **続きから** — 長期記憶 + Web 引き継ぎ Sage 統合（6/22）。LINE 単体でも Web でも同じ diagnosis 体験
4. **削除できる** — MemoryDeleteAgent + プライバシーポリシー第5条。β でも「消して」と言えることが前提

本 issue は **コード完成後の「約束を履行する」スイッチ** である。

---

## 詳細レポート（2026-06-22）

### エグゼクティブサマリー

- **結論**: ❌ **未着手** — コード ~92% 完成、本番 `LINE_WEBHOOK_ENABLED=false` のまま
- **根拠**: `config/line_config.py` 既定 false、`docs/ops/LINE_WEBHOOK_SETUP.md` §6.4
- **ブロッカー（思想順）**: **#74** 信頼の前提 → **#56** dev で約束速度の検証 → 本 issue

### 現状調査

| 項目 | 2026-06-11 | 2026-06-22 | 根拠 |
|------|------------|------------|------|
| 実装進捗 | ~85% | **~92%** | #55 Epic |
| 本番 Webhook | ❌ 無効 | ❌ **変更なし（意図的）** | `LINE_WEBHOOK_ENABLED=false` |
| テスト | 12 ファイル | **26 ファイル** | `tests/line/` |
| Rich Menu | 未 | ✅ コード完了 | #82 クローズ |
| 長期記憶 + doc | 未 | ✅ | #87, #60 クローズ |
| Web 引き継ぎ Sage | 未 | ✅ | CHANGELOG 2026-06-22 |
| dev Cloud Run E2E | 未 | 🟡 手順あり | #56 |

### 本番 URL・エンドポイント

| 環境 | URL | Webhook |
|------|-----|---------|
| 本番（カスタム） | `https://medicine.yutok.dev` | `/line/webhook` |
| 本番（Cloud Run） | `https://medicine-recommend-340042923793.asia-northeast1.run.app` | 同上 |
| dev | `medicine-recommend-dev-340042923793.asia-northeast1.run.app` | 検証用 |
| 状態確認 | — | `GET /line/webhook/status` |

### 本番ロールアウト手順（チェックリスト）

#### Phase 0 — 前提（CHANGELOG 思想順）

- [ ] **#74** — β への約束（セキュリティ ✅）をコードで裏付け
- [ ] **#56** — dev Cloud Run E2E（速度・引き継ぎ・記憶削除）
- [ ] プライバシーポリシー 2026-06-22 改定が本番デプロイ済み

#### Phase 1 — Cloud Run 環境変数

```bash
LINE_WEBHOOK_ENABLED=true
LINE_CHANNEL_SECRET=<本番>
LINE_CHANNEL_ACCESS_TOKEN=<本番>
PUBLIC_SITE_URL=https://medicine.yutok.dev
DATABASE_URL=<Neon pooler>
APP_ENV=production
SECRET_KEY=<強い値>   # #74
ADMIN_PASSWORD=<強い値>
```

- [ ] min-instances=1 検討（コールドスタート、`LINE_WEBHOOK_SETUP.md` §9.5）

#### Phase 2 — LINE Developers Console

- [ ] Webhook URL → `https://medicine.yutok.dev/line/webhook`、検証成功
- [ ] 応答メッセージ・あいさつ **オフ**
- [ ] Rich Menu: `python scripts/register_line_rich_menu.py --pattern a-sage-minimal`

#### Phase 3 — 本番 smoke

- [ ] 友だち追加 → 症状相談 → Flex + 速度ベンチ
- [ ] Web 引き継ぎ → `/resume` → Sage 描画
- [ ] 「記憶を消して」→ MemoryDeleteAgent
- [ ] フィードバック postback → 管理画面

#### Phase 4 — ロールバック（6/16 教訓）

- [ ] `LINE_WEBHOOK_ENABLED=false` + Console Webhook 無効化手順を文書化済み

### 開発者メモ

- **92% なのに未 ON** は遅延ではなく **品質ゲート**。6/16 の「動かない本番」より、dev で検証中の方が利用者に誠実。
- Rich Menu・長期記憶 doc は **#57 の中身ではなく前提** として完了済み — 残りは env + Console + smoke の **運用 4–8h**。
- 推奨着手: **#74 → #56 → #57**

### 受け入れ条件

- [ ] 本番 E2E 成功（速度ベンチ内）
- [ ] ロールバック手順確認済み
- [ ] #55 Epic 本番項目クリア

### 関連

[`CHANGELOG.md`](https://github.com/32Lwk/medicine-recommend-system/blob/main/CHANGELOG.md)（2026-06-22）| #74, #56, #71, #88 | `docs/planning/ISSUE_REPORT_FORMAT.md`

---
_2026-06-22 CHANGELOG 思想 + コード再調査_
EOF
)"

gh issue edit 52 --body "$(cat <<'EOF'
## 元のメモ

これまぁまぁ酷いね

## 目的

SSE ストリーム中にユーザーが過去メッセージを読めるようにする。下端付近にいるときだけ自動追従を維持する。

親: #46 | テスト: #63 | **P0**

---

## プロジェクトコンテキスト — なぜ P0 か

CHANGELOG は **「待たせない・見える」** ストリーム UX を 2026-05〜06 に全力で作った。

| マイルストーン | 意図 | スクロールとの関係 |
|--------------|------|------------------|
| **2026-05-16 SSE** | 本番同等の `recommendation-result` を逐次描画 | 見える化の代价 = **毎 chunk で scrollToBottom** |
| **2026-06-21 Big Bang** | Diagnosis v1 + Sage マーカーで描画統一 | **描画は改善、スクロール挙動は未変更**（CHANGELOG 言及なし） |
| **2026-06-20 typing** | bot 描画完了 **＋スクロール後** に typing 除去 | スクロールタイミングが UX の一部 — 無条件 scroll は設計と矛盾 |
| **2026-06-16 ロールバック** | 本番 UI は段階 QA | ストリームも **小さく直して検証**（~30 行）が教訓に合う |

> 元メモ「これまぁまぁ酷いね」= 長い推奨ほど **過去ログが読めない** のが最大の信頼毀損。Sage の見た目を整えても、読めなければ β として不十分。

---

## 設計意図 — 「追従」と「読む」の両立

CHANGELOG が目指す体験:

- **追従**: 新しい cards / advice が来たら進捗が見える（待たせない）
- **読む**: 推奨理由・注意事項をストリーム中に確認したい（安全で分かりやすい）

現状の `scrollToBottom()` は **追従のみ** を実装し、**読む** を犠牲にしている。

推奨 **案 B**（`isNearBottom` + `userPinned`）は CHANGELOG の両方針をコードで両立する最小変更。

---

## 詳細レポート（2026-06-22）

### エグゼクティブサマリー

- **結論**: ❌ **未修正**
- **根拠**: `isNearBottom` / `userPinned` 未実装、`scrollToBottom()` 無条件（21 箇所）
- **ROI**: 極高（~30 行 + #63）

### コード根拠

```javascript
// static/js/main.js L10510-10519
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    setTimeout(() => {
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }, 200);
}
```

| ストリーム呼び出し元 | 行 | トリガー |
|-------------------|-----|---------|
| `appendAdviceDelta` | L9253 | `advice_delta` |
| `appendChatDelta` | L9264 | `chat_delta` |
| `renderStreamingMedicineCards` | L9345+ | `cards` |
| `updateStreamingExplanations` | L9416 | `explanations` |

### 修正方針（案 B 推奨）

1. `isNearBottom(el, 80px)` — 下端付近判定
2. `userPinned` — 上方向スクロールで pin、下端 or 送信で解除
3. ストリーム経路のみ `scrollToBottomIfAllowed()` に差替え
4. #63 jsdom 回帰

### 開発者メモ

- Sage / bulk mode（#62）と独立。**cards 到着時の scroll** が主战场。
- 6/21 Big Bang で `main.js` は大きく触ったが scroll は **意図的に温存** — 今回初めて直すタイミング。
- #74 より先に着手してよい **唯一の P0**（利用者全員・毎セッション）。

### 受け入れ条件

- [ ] ストリーム中に上スクロール可能
- [ ] 下端 80px 以内は自動追従
- [ ] pin 中は chunk 到着でも位置維持
- [ ] #63 テスト green

### 関連

#46, #54, #71, #88 | `docs/planning/ISSUE_REPORT_FORMAT.md`

---
_2026-06-22 CHANGELOG 思想 + main.js grep_
EOF
)"

gh issue edit 74 --body "$(cat <<'EOF'
## 目的

本番（`APP_ENV=production`）で弱いデフォルト・CORS 漏れを **起動時 fail-fast** で防ぐ。**#57 LINE 本番の思想的前提**。

---

## プロジェクトコンテキスト — オンボーディングとのギャップ

CHANGELOG 2026-06-18: オンボーディング「セキュリティ向上」に ✅ を追加。

| 表示 | 実装 | ギャップ |
|------|------|---------|
| オンボーディング ✅ | `admin123` デフォルト | **#88 で指摘済み** |
| 6/22 法務（記憶・削除） | infra ガードなし | 規約は進んだが **管理画面が裸** |
| 6/16 段階 QA 教訓 | production 起動チェックなし | 壊れた UI と同様、**弱 secret も本番に載せない** |

> β 版は「安全で分かりやすい」と約束している。**SECRET_KEY 未設定で起動できる本番** はその約束と矛盾する。

---

## 設計意図 — 安全はアプリ層だけでは足りない

CHANGELOG 2026-06 の安全関連:

- **ルーティング**: 危機・緊急・規制薬物の即時ブロック
- **LINE**: 危機対応は Flex ではなく安全テキスト
- **長期記憶**: PII playbook、ユーザー削除、プライバシーポリシー改定
- **管理画面**: 長期記憶パネルで `client_ip` 等を扱う

これらは **ADMIN が守られている前提** で成り立つ。`admin123` はその前提を無効化する。

---

## 詳細レポート（2026-06-22）

### エグゼクティブサマリー

- **結論**: ❌ **未着手**
- **優先度**: P1（**#57 ブロッカー推奨**）

### コード根拠

**S1 — ADMIN デフォルト**

```python
# src/services/admin_auth.py L11-13
return pwd if pwd else "admin123"
```

**S2 — SECRET_KEY フォールバック**

```python
# src/services/admin_auth.py L16-21
return (os.getenv("SECRET_KEY") or "").strip() or admin_password() or "dev-admin-secret"
```

**S4 — CORS**

```python
# config/app_config.py — medicine.yutok.dev 未登録
'origins': ['https://medicine-recommend-system.onrender.com', 'http://localhost:5000', ...]
```

| ファイル | 状態 |
|---------|------|
| `.env.example` | `SECRET_KEY` 行なし |
| fail-fast | ❌ 未実装 |

### 実装手順（推奨）

1. `validate_production_config()` — `APP_ENV=production` で SECRET_KEY / ADMIN_PASSWORD 必須・弱値拒否
2. CORS — `medicine.yutok.dev` + Cloud Run URL + `CORS_EXTRA_ORIGINS`
3. `.env.example` + `docs/security/PRODUCTION_CHECKLIST.md`
4. `tests/config/test_production_guard.py`

### 開発者メモ

- **8–12h** で #57 のリスクを大きく下げる。LINE を ON にする前の **誠実さのための作業**。
- 6/22 法務更新とセットで「技術的にも守る」状態にする。
- 着手順: **#74 → #52 → #57**（#88 / #71 ロードマップと一致）

### 受け入れ条件

- [ ] production + 弱 secret → 起動失敗
- [ ] CORS に本番 URL 登録
- [ ] doc + pytest

### 関連

`docs/planning/アプリケーションレビュー報告書.md` S1/S2/S4 | #57, #88, #71

---
_2026-06-22 CHANGELOG 思想 + 静的解析_
EOF
)"

gh issue edit 55 --body "$(cat <<'EOF'
## 元のメモ

がんばります

## Epic 概要

LINE Messaging API 連携 — **β版テスターが日常の相談導線として LINE を使える**状態まで。

---

## 設計思想（CHANGELOG 2026-06 集約）

| 価値 | 意図 | CHANGELOG 根拠 |
|------|------|---------------|
| **待たせない** | Reply 優先・loading・段階 Push | 2026-06-13 速度改善 |
| **信頼** | 二重返信防止、フィードバック永続化、記憶削除 | 2026-06-15, 2026-06-22 |
| **続きから** | 長期記憶 + Web 引き継ぎ Sage 統合 | 2026-06-22 |
| **慎重な本番** | dev 検証 → 法務 → 本番 ON | 2026-06-16 ロールバック教訓 |

> オンボーディング: 「β版（試験運用）— より**安全で分かりやすい**情報提供に向けて改善を続けています」

---

## 詳細レポート（2026-06-22）

| 指標 | 値 |
|------|-----|
| 実装進捗 | **~92%** |
| 本番 Webhook | ❌ `LINE_WEBHOOK_ENABLED=false`（**意図的保留**） |
| 残クリティカル | **#74** → **#56** → **#57** |

### Sub-issue 状態

| # | タスク | 状態 |
|---|--------|------|
| #87 | 長期記憶 doc | ✅ |
| #82 | Rich Menu | ✅ コード完了 |
| #60 | doc 同期 | ✅ |
| #56 | dev E2E | 🟡 |
| **#74** | セキュリティ | ❌ **本番 ON 前提** |
| **#57** | 本番ロールアウト | ❌ |
| #59 | 属性収集 | ❌ |
| #85 | 返信最適化 | 🟡 |
| #58 | Cloud Tasks | ❌ |

### 受け入れ条件（Epic クローズ）

- [ ] #57 本番 E2E
- [ ] #74 本番ガード
- [ ] オンボーディング「LINE連携」✅ が本番でも正当化される

## 関連: #88, #71, [`CHANGELOG.md`](https://github.com/32Lwk/medicine-recommend-system/blob/main/CHANGELOG.md)

---
_2026-06-22 CHANGELOG 思想同期_
EOF
)"

gh issue edit 88 --body "$(cat <<'EOF'
## 目的

オンボーディング 1 枚目「**現在開発中の主な内容**」を GitHub issue と CHANGELOG の単一の正として追跡する Epic。

---

## 思想 — チェックリストが語る優先順位

オンボーディング UI（`main.js`）の `defaultChecked: true` は **「利用者に約束済みの能力」** を表す。未チェックは **「まだ約束していない計画」**。

| 区分 | 項目数 | 意味 |
|------|--------|------|
| ✅ checked | 9 | CHANGELOG で実装が追いついた領域 |
| ☐ unchecked | 4 | 潜在空間・音声・体調推定・パーソナライズ（第2段階） |

CHANGELOG 2026-06-18: チェックリスト 5 項目に ✅ を追加（UI・カルーセル・LINE・画像・セキュリティ）。**表示と実装の同期**を意識した更新。

---

## チェックリスト ↔ Issue 対応（2026-06-22）

| 項目 | UI | Issue / 状態 |
|------|-----|-------------|
| Flask→FastAPI | ✅ | CHANGELOG 2026-05 完了 |
| GPT-5 系 | ✅ | CHANGELOG 2026-06-02 |
| ChatOrchestrator | ✅ | #75 |
| 潜在空間スコア | ☐ | #31 |
| UI・導線 | ✅ | #45, #51, #80 🟡 |
| カルーセル | ✅ | #84, Sage |
| LINE 連携 | ✅ | #55 🟡 本番待ち |
| LINE→Web 引き継ぎ | ✅ | #87 完了 |
| 画像 | ✅ | placeholder #27/#70 |
| セキュリティ | ✅ | **#74 未着手**（表示と実装のギャップ） |
| 音声入力 | ☐ | **#89** |
| 体調推定 | ☐ | **#90** |
| パーソナライズ | ☐ | **#91**（#87 が第1段階） |

### ギャップに関するメモ

「セキュリティ向上」に ✅ が付いているが **#74 は未着手** — オンボーディング表示と issue 状態の乖離。#74 完了後にチェックリストの正当性が取れる。

---

## Sub-issues

#89–#91（新規）| #31, #45, #55, #74, #84 | ロードマップ #71

---
_2026-06-22 CHANGELOG + オンボーディング UI 同期_
EOF
)"

gh issue comment 71 --body "$(cat <<'EOF'
## 詳細レポート（2026-06-22）— CHANGELOG 思想追記

#57 / #52 / #74 / #55 / #88 を CHANGELOG の設計思想・意図・開発者メモ付きで更新。

### 横断テーマ（CHANGELOG より）

| テーマ | 該当 issue |
|--------|-----------|
| 慎重な本番移行（6/16 ロールバック教訓） | #57, #74 |
| 待たせない / 読める UX の両立 | #52, #53 系 |
| 安全はアプリ層だけでなく infra 層も | #74 |
| 法務先行（6/22 プライバシー）→ 技術ガード | #74 → #57 |
| オンボーディング ✅ = 約束済み能力 | #88, #74 ギャップ |

### 推奨着手順（思想順）

**#74**（信頼の前提）→ **#52**（日常 UX の痛点）→ **#57**（β版への約束履行）
EOF
)"

echo "Done: #57 #52 #74 #55 #88 updated, #71 commented"
