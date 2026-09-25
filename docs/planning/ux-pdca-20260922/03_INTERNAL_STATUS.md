# 03 社内 UX 現状（監査合成）

**監査日**: 2026-09-22  
**根拠**: リポジトリ docs/flags/コード契約、先行棚卸、監査エージェント `a3229cb1`

---

## 0. 判決

**技術エンジンとしては「強い」。プロダクト UX としては「直したつもりが本番に届いていない」状態。**  
コード上の改善フラグと、本番ユーザーが浴びる体験が乖離している。

---

## 1. チャネル機能マトリクス

| 機能 | Web | LINE | キオスク |
|------|-----|------|----------|
| 入口 | `/` SSE Sage | Webhook Flex | 専用 UI なし（緊急文言フラグのみ） |
| 進捗 | 段階ラベル | テキスト待ち中心 | — |
| 推奨 | Diagnosis v1 カード | Flex carousel | — |
| TTS/STT | あり | なし | — |
| 長期記憶 | handoff 時のみ | あり | — |
| SessionOps 削除 pending | あり（**medical cancel なし**） | あり（**medical cancel あり**） | — |
| 緊急文言 | フラグ ON で公的窓口 | 同左 | フラグ ON でスタッフ |
| handoff | 受信 | 発行（**プロセス内トークン**） | — |

---

## 2. アイデンティティ

| 層 | 現状 | 呼ばれ方の罠 |
|----|------|--------------|
| Web | Cookie `sid` 匿名 | 「ユーザー情報登録」＝属性。会員ではない |
| 同意 | `localStorage.onboardingCompleted` | サーバ監査なし |
| LINE | `line:{userId}` + 長期記憶 | 唯一の安定継続 ID |
| `username_input.html` | **ルート未接続残骸** | 復活させるな（要設計し直し） |

---

## 3. 既存計画の到達

| 施策 | 状態 |
|------|------|
| UX 品質改善 v2 Phase0–3, 4a/4b | コード完了。PRIMARY 等は本番 ON 寄り |
| UX 十二種（`_ux_rollout_flag`） | **dev ON / 本番未設定 OFF** |
| `LATENCY_*` | 多く明示 ON のみ。本番効いていない可能性 |
| e2e p95 &lt;5s | **未達**（≈24s） |
| `p4-unify` legacy 物理削除 | pending |
| 候補 0 件 UX | 完了（蕁麻疹実推奨は部分） |
| VH / UI 方向 C | 未着手 |

---

## 4. サイト UI

- Sage Terrace（プロト 54）本番定着。方向 B 系譜。
- About はトークン統一・4 言語。一般向け「入口」は薄い。
- 未移植で効きそう: **36 薬剤師ストリップ / 39 ウィザード進捗 / 44 トリアージ入口 / 42 リカバリー a11y**。
- プロト乱造は移植負債。選択移植のみ。

---

## 5. 計測の穴（致命）

測れていない／弱いもの:

1. Emergency FP 後の**再入場・ケア放棄**
2. handoff **成功率・失効理由**
3. 「登録」ボタンの**離脱寄与**
4. UX 十二種の**本番オン/オフ差分**
5. 多言語 UI と**本文言語不一致**率
6. SessionOps FP（「消して」「まとめて」）

あるもの: pipeline 区間ログ、local v2 chat test、Jev shadow（default OFF）。

---

## 6. 優先ギャップ Top 15

1. Web pending medical/crisis cancel 欠落（安全）
2. UX 十二種・緊急チャネル分割の本番 OFF
3. Physical p95 ≈24s
4. handoff プロセス内トークン
5. 「登録」文言のアカウント誤解
6. Emergency FP の恐怖コピー＋再入場欠落
7. Counseling overcapture / OTC 再入場
8. 同意のサーバ未記録
9. 返信自動翻訳停止 vs UI 4 言語
10. 薬剤師要請デモの誤認リスク
11. LINE 待ち UX の貧弱さ
12. 属性未入力時の安全ポリシー説明不足
13. legacy UI 残存と dual DOM
14. プロト未移植の迷い（優先未決定）
15. キオスク概念の曖昧さ

---

## 7. 参考パス

- `.cursor/plans/ux品質改善計画v2_7fab4ed6.plan.md`
- `config/llm_flags.py`
- `docs/ui/DIAGNOSIS_V1.md`
- `docs/dev/PHYSICAL_SYMPTOM_E2E.md`
- `docs/ops/LINE_LONG_TERM_MEMORY.md`
- `docs/planning/codex-parallel-jev-20260921/JEV_SAFETY_ACTION_AI_REVIEW_20260922.md`（F5）
- `docs/planning/notebooklm-history/CLAUDE_改善ロードマップ_20260914.md`
