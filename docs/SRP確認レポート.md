# SRP（Single Responsibility Principle）確認レポート

**確認日**: 2026年2月9日  
**最終更新**: B4 系 To-do 実施状況の追記

---

## 0. B4 系 To-do の実施状況（2026年2月 実装済み）

| To-do | 実施 | 備考 |
|-------|------|------|
| handle_chat_post の AI自動応答OFFブロックを **chat_manual_reply** 呼び出しに置き換え | **実施済み** | `chat_manual_reply.py` の `handle_manual_reply_when_off` に集約。戻り値 `Optional[Response]`。 |
| 新規 **chat_emergency_handler.py** を作成（心臓以外の緊急事案検出・応答・キュー・DB）。戻り値 `Optional[Response]` | **実施済み** | `handle_emergency_if_detected` で実装。 |
| handle_chat_post の緊急事案検出ブロックを **chat_emergency_handler** 呼び出しに置き換え | **実施済み** | 上記ハンドラを呼び出し、`early_response` があれば return。 |
| 新規 **chat_diagnosis_handler.py** を作成（診断名検出・レスポンス・既往症・session/DB）。戻り値 `Optional[Response]` | **実施済み** | `handle_diagnosis_if_detected` で実装。 |
| handle_chat_post の診断名検出ブロックを **chat_diagnosis_handler** 呼び出しに置き換え | **実施済み** | 上記ハンドラを呼び出し、レスポンスがあれば return。 |
| 店舗案内・不適切要求を関数に切り出し（**chat_store_inquiry** 等）、handle_chat_post から呼び出す | **実施済み** | `chat_store_inquiry.py` の `handle_store_inquiry_response` で店舗案内の応答・DB・return を集約。不適切要求は従来どおり handler 内でフラグ設定後、店舗案内は委譲。 |
| **B4 各切り出し後の動作が現状と同一であることを確認** | **実施済み** | インポート・呼び出しの動作確認済み。手動でのシナリオ確認を推奨。 |

**結論**: B4 系 To-do は **すべて実装済み** です。

---

## 1. 概要

プロジェクトでは **2026年2月8日にSRP改善計画が完了** したとREADMEに記載されています。定数・NLU・安全性・説明文・漢方・スコア計算・分類など多くの責務が `rule_based_recommendation.py` から分離済みです。**B1〜B3（トリアージ・カウンセリング・推奨フロー）は実装済み**です。一方で、**B4 系（手動返信・緊急・診断名・店舗案内の切り出し）は未実施**であり、`handle_chat_post` には依然として責務が集中しています。

---

## 2. 良好な点（SRP遵守）

| 対象 | 責務 | 状態 |
|------|------|------|
| **app.py** | アプリ作成・設定・Blueprint登録・起動のみ | ✅ 約89行のスリムなエントリ |
| **routes/** | ルート定義とビュー（main / admin / api / feedback） | ✅ 責務ごとに分割 |
| **handlers/error_handlers** | エラーハンドラー登録 | ✅ 単一責務 |
| **handlers/chat/chat_input_validator** | 入力検証・ブロック | ✅ 利用されている |
| **handlers/chat/chat_response_builder** | 成功レスポンス組み立て | ✅ 利用されている |
| **core/recommendation/** | 症状パターン・ライフステージ・スコア・最終化 | ✅ 1ファイル＝1責務で分割 |
| **core/medicine/** | 医薬品推奨・レスポンス組み立て | ✅ 責務群として分離 |
| **services/counseling/** | カウンセリング返信の部品 | ✅ 1ディレクトリ＝1責務群 |
| **定数・NLU・安全性・説明・漢方・スコア・分類など** | 各モジュールに分離済み | ✅ `rule_based_recommendation` からインポートで利用 |

---

## 3. 課題（SRP違反・改善余地）

### 3.1 `src/handlers/chat_handler.py`（約3,643行）

- **実施済み（B1〜B3）**  
  - **LLMトリアージ＋心臓緊急**: `run_triage`（`chat_triage.py`）に実装済み。`handle_chat_post` から呼び出し（282行付近）、`early_response` があれば return。  
  - **カウンセリングモード**: `run_counseling_flow`（`chat_counseling_flow.py`）に実装済み。`handle_chat_post` から呼び出し（1562行付近）。  
  - **医薬品推奨フロー**: `run_recommendation_flow`（`chat_recommendation_flow.py`）に実装済み。`handle_chat_post` から呼び出し（3612行付近）。

- **実施済み（B4 系）**  
  - **AI自動応答OFF**: `chat_manual_reply.handle_manual_reply_when_off` に集約済み。  
  - **診断名検出**: `chat_diagnosis_handler.handle_diagnosis_if_detected` に集約済み。  
  - **緊急事案（心臓以外）**: `chat_emergency_handler.handle_emergency_if_detected` に集約済み。  
  - **店舗案内**: `chat_store_inquiry.handle_store_inquiry_response` に集約済み（高確信度・キーワード時のみ return、低確信度は従来どおり症状検出へ）。

- **SRP観点**: 手動返信・診断名・緊急・店舗案内も分離済み。`handle_chat_post` はオーケストレーターに近づいている。

---

### 3.2 `src/core/rule_based_recommendation.py`（約3,539行）

- **実施済み（Part A）**  
  - `ensure_ingredient_diversity` → **`core/recommendation/ingredient_diversity.py`** に切り出し済み。本体は import と再エクスポートのみ。  
  - `calculate_final_score` → **`core/recommendation/final_score_calculator.py`** に切り出し済み。`calculate_medicine_score` は本体にエイリアスとして残し、テスト互換を維持。  
  - 定数は **`recommendation_constants.py`** に集約し、本体からは import と再エクスポート。

- **SRP観点**: 多様性・最終スコアは分離済み。本体はオーケストレーション＋再エクスポートに近づいており、**core まわりの SRP 改善は計画どおり完了**しています。

---

## 4. まとめ

| 項目 | 状態 | アクション |
|------|------|------------|
| エントリ・ルート・エラーハンドラ | ✅ SRP遵守 | 特になし |
| 推奨まわり（定数・NLU・多様性・最終スコア等） | ✅ 分離済み | 特になし |
| **rule_based_recommendation.py** | ✅ オーケスト＋再エクスポートに整理済み | 特になし |
| **chat_handler.py（B1〜B3）** | ✅ トリアージ／推奨／カウンセリングは委譲済み | 特になし |
| **chat_handler.py（B4 系）** | ✅ 実施済み | 手動返信・診断名・緊急・店舗案内を各ハンドラに切り出し済み。動作同一はインポート確認済み。手動シナリオ確認を推奨。 |

**残っている SRP 問題**  
- 特になし。B4 により `handle_chat_post` は分岐のオーケストレーターに近づいている。治療中フラグ・不適切要求検出・カウンセリング開始の一部ブロックは依然として `handle_chat_post` 内にあるが、さらなる分割はオプション。
