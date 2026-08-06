# Physical 症状バースト分析（2026-08-05 10:00 JST〜）

**分析対象期間**: 2026-08-05 10:00 JST 以降（Physical burst 核心: **10:13–10:28 JST**）  
**環境**: AWS ECS `/ecs/medicine-recommend`（staging/prod 相当）、Neon prod `gentle-frog-62003272`  
**データソース**:
- AWS 抽出: `log/analysis/downloaded-aws-logs-20260805-20260805-20260805-020929/`
- ルーティング: `log/raw/downloaded-aws-logs-20260805-20260805-20260805-020942.json`（`dialogue_route_shadow`）
- パイプライン計測: `log/raw/downloaded-aws-logs-20260805-20260805-20260805-020939.json`（`PIPELINE_PERF`）
- Neon `sessions` テーブル（全8セッション照合済み）

**HTTP/テキストエラー**: 当該時間帯・当該セッションに **4xx/5xx・text_errors 共に 0 件**（`errors_http.json`）。

---

## バースト概要

| 指標 | 値 |
|------|-----|
| 分析セッション数 | 8 |
| 全件 `primary_route=Physical` | 8/8 |
| `sub_route=rule_based_recommend` | 6 |
| `sub_route=fever_flow` | 2（熱っぽい / 喉が痛く熱がある） |
| 推奨成功（3品表示） | 6 |
| 品質問題あり | 2（幼児鼻水 QA、脂漏性湿疹 no_candidates） |
| E2E 中央値（PIPELINE_PERF） | **~51 s**（28–58 s レンジ） |
| ボトルネック | `nlu_batch`（~19–26 s）+ `rb_explain_batch`（~10–13 s） |

10:13–10:16 に **頭痛系4件＋発熱1件＋幼児鼻水1件** が集中し、10:15–10:16 に偏頭痛・脂漏性湿疹、10:20 に複合発熱、10:27 にリダイレクト後頭痛が続くパターン。

---

## セッション別詳細

### 1. `1785892374721038147507` — 「頭痛い」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | 単純な頭痛の OTC 相談。属性未入力の初回相談。 |
| フロー | **Physical → rule_based_recommend**（guard, conf 0.94, subcategory: headache） |
| 応答品質 | **良好**。症状「頭痛」正しく抽出。推奨: **イブ / バファリンEX / カロナールA**（解熱鎮痛薬）。共感＋用法注意＋受診目安あり。偏頭痛特化ではないが初回頭痛として妥当。年齢未確認ペナルティ（completeness -0.15）で display_score 85 前後。 |
| 処理時間 | **E2E 53,070 ms**（pipeline total）。内訳: triage ~4.7 s, NLU batch ~26 s, rule_based+explain ~19 s, personalized_advice ~2.4 s。LLM 9 calls。 |
| エラー | なし。Neon に full `sage_reco` diagnosis 保存済み。 |

**Neon**: `2026-08-05T10:13:27+09:00` 送信 → 2 messages。

---

### 2. `1785892370895690177498` — 「頭痛がする」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | #1 と同型の頭痛相談（表現のみ異なる）。 |
| フロー | **Physical → rule_based_recommend**（guard, conf 0.94, headache） |
| 応答品質 | **良好**。#1 と同一推奨セット（イブ/バファリンEX/カロナールA）。critical_question で Red flag（吐き気・発熱・視界異常等）を確認。 |
| 処理時間 | **E2E 51,710 ms**。NLU batch ~26 s, explain batch ~11 s。LLM 9 calls。 |
| エラー | なし。 |

**Neon**: `2026-08-05T10:13:26+09:00` 送信。

---

### 3. `1785892798329357348510` — 「喉が痛く熱がある」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | 発熱＋咽頭痛の複合症状。風邪/インフル疑いの OTC 相談。 |
| フロー | **Physical → fever_flow**（gate, conf 0.95, subcategory: general_symptom）→ 実行は **rule_based** で **風邪薬** 系推奨 |
| 応答品質 | **良好（本バッチ最高クラス）**。症状「発熱＋のどの痛み」正しくマッピング。推奨: **新スカイブブロンゴールド微粒 / バファリンかぜEX錠 / カゼセブン内服液S**。multi_symptom_bonus・throat_bonus 適用。成分重複警告（カフェイン・ジヒドロコデイン）も表示。 |
| 処理時間 | **E2E 50,281 ms**。NLU batch ~19 s（他より短め）。LLM 9 calls。 |
| エラー | なし。fever_flow ゲート後に風邪薬スコアリングへ正常遷移。 |

**Neon**: `2026-08-05T10:20:45+09:00` 送信（バースト後半）。

---

### 4. `1785892367772563828651` — 「熱っぽい」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | 発熱感の訴え。体温・随伴症状は未提供。 |
| フロー | **Physical → fever_flow**（gate, conf 0.95, subcategory: feverish）→ 出力は **解熱鎮痛薬**（rule_based） |
| 応答品質 | **部分的に妥当、ルートとのギャップあり**。fever_flow に入ったが推奨は **イブ/バファリンEX/カロナールA**（単独解熱鎮痛）のみ。アドバイスは体温測定・水分補給を促す点は良い。複合症状（のど痛・咳）がなければ解熱鎮痛も選択肢だが、#3 と比べ fever_flow の「総合かぜ薬」期待とは異なる挙動。critical_question で体温確認は適切。 |
| 処理時間 | **E2E 47,608 ms**。LLM 9 calls。 |
| エラー | なし（ルーティング/出力の **意味的不一致** は品質観点で要監視）。 |

**Neon**: `2026-08-05T10:13:40+09:00` 送信。

---

### 5. `1785890421194005681438` — 💊 redirect → 「頭が痛いです。」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | ターン1（09:41）: 💊💊 → OTC 窓口リダイレクト。ターン2（**10:27**）: 頭痛相談。 |
| フロー | T1: **concierge redirect**（`sage_status`）。T2: **Physical → rule_based_recommend**（guard, headache） |
| 応答品質 | T1 **適切**（「OTC相談窓口です」と案内）。T2 **良好** — イブ/バファリンEX/カロナールA、46分間隔後も正常推奨。 |
| 処理時間 | T2 **E2E 57,521 ms**（最遅）。NLU batch ~25 s, explain ~13 s。LLM 9 calls。 |
| エラー | なし。セッション再利用（created 09:40 UTC）で問題なし。 |

**Neon**: 4 messages（redirect + 頭痛 reco 完備）。

---

### 6. `1785892416886105725292` — 「脂漏性湿疹で悩んでいます」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | 脂漏性湿疹の OTC 治療薬探索（皮膚疾患・要受診寄りの可能性）。 |
| フロー | **Physical → rule_based_recommend**（guard, conf 0.94, subcategory: skin_condition） |
| 応答品質 | **不十分**。`diagnosis.error.type=no_candidates` — 「該当する医薬品が見つかりませんでした」。推奨リスト空、personalized_advice 空。皮膚科受診・具体化を促す error recommendations のみ。ルートは Physical/rule_based だがスコアリング候補 0 件。 |
| 処理時間 | **E2E 34,849 ms**（最短）。rule_based が early stop（explain フェーズ未到達）。LLM 4 calls。 |
| エラー | **`no_candidates`（warn）** — アプリ例外ではなくビジネスロジック上の空結果。ユーザー体験としては dead-end。 |

**Neon**: error オブジェクト付き `sage_reco` 保存。

---

### 7. `1785892376941414913484` — 「偏頭痛があります」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | 偏頭痛の OTC 対処（トリプタン不可のため一般解熱鎮痛）。 |
| フロー | **Physical → rule_based_recommend**（guard, conf 0.94, headache） |
| 応答品質 | **概ね良好、偏頭痛特化は弱い**。症状正規化は「頭痛」（偏頭痛ラベル未保持）。推奨は汎用解熱鎮痛3品。critical_question は偏頭痛らしい随伴症状（光過敏・吐き気等）を **適切に** 質問。専用 OTC（例: イブメルト等）や受診勧奨の強調は限定的。 |
| 処理時間 | **E2E 53,906 ms**。LLM 9 calls。 |
| エラー | なし。 |

**Neon**: full recommendation 保存。

---

### 8. `1785892365553487814128` — 「幼児が使える鼻水止める薬を探してます」

| 項目 | 内容 |
|------|------|
| ユーザー意図 | **幼児向け** 鼻水止め OTC の探索（年齢制限が最重要）。 |
| フロー | T1: **medicine_qa early route**（`sage_qa` placeholder?）。T2: **Physical → rule_based_recommend** 経由で **medicine_information_qa**（`sage_qa`, kind=medicine_qa） |
| 応答品質 | **重大な品質問題**。① 主成分分類が誤り — フェキソフェナジン等を **「解熱鎮痛」** とラベル。② 推奨3品（スカイブブロンHI/NAスプレー/ゴールド）は HTML 年齢制限で **15歳以上** と明記され、**幼児要件と矛盾**。③ 「解熱鎮痛薬/アセトアミノフェンで絞り込み」という誤誘導。幼児向け鼻水薬（例: 小児用ドリエル等）への誘導・薬剤師相談が必要。 |
| 処理時間 | **E2E 28,283 ms**。`medicine_information_qa` ~21 s。LLM 1 call。 |
| エラー | なし（HTTP/exception）。**回答内容の factual error** が主問題。 |

**Neon**: T2 bot message に誤分類 QA 全文保存。

---

## 横断所見

### ルーティング
- 全件 **Physical** 確定。guard（headache/skin/runny_nose）vs gate（fever_flow）の使い分けは入力パターンに沿う。
- **fever_flow の出力一貫性**: 複合症状（#3）は風邪薬、単独「熱っぽい」（#4）は解熱鎮痛のみ — 仕様通りなら OK、ユーザー期待とのギャップは UX 確認要。

### パフォーマンス
- **28–58 s** と遅い。共通ボトルネックは **NLU batch（19–26 s）** と **rb_explain_batch（10–13 s）**。
- `user_sessions.json` transcript では E2E/pipeline が null（counseling_detail のみ抽出）だが、raw `PIPELINE_PERF` で補完可能。
- 同時多発（10:13–10:16）時も個別セッションは完走 — 503/timeout なし。

### 推奨品質パターン
- 頭痛系4件は **同一3品**（イブ/バファリンEX/カロナールA）— スコアリング安定だが差別化弱い。
- 年齢未入力ペナルティは全 Physical reco で一貫（-0.15 completeness）。

### 要フォローアップ
1. **幼児鼻水 QA** — 成分分類・年齢適合チェックのガード追加
2. **脂漏性湿疹** — skin_condition で no_candidates 時の皮膚科/受診エスカレーション強化
3. **fever_flow 単独発熱** — 解熱鎮痛 vs 風邪薬の分岐基準のドキュメント化
4. **レイテンシ** — NLU batch 並列化またはキャッシュ（burst 時 UX）

---

## サマリー表

| session_id | 入力 (JST) | ルート | 推奨/応答 | 品質 | E2E (ms) | エラー |
|------------|-----------|--------|-----------|------|----------|--------|
| 1785892374721038147507 | 10:13:27 頭痛い | Physical / rule_based | イブ, バファリンEX, カロナールA | ◎ | 53,070 | なし |
| 1785892370895690177498 | 10:13:26 頭痛がする | Physical / rule_based | 同上 | ◎ | 51,710 | なし |
| 1785892367772563828651 | 10:13:40 熱っぽい | Physical / **fever_flow** | イブ, バファリンEX, カロナールA（解熱鎮痛） | △ | 47,608 | なし |
| 1785892365553487814128 | 10:14:16 幼児鼻水 | Physical / rule_based → **medicine_qa** | スカイブブロン3品（15歳以上） | ✗ | 28,283 | 内容誤り |
| 1785892376941414913484 | 10:15:32 偏頭痛 | Physical / rule_based | イブ, バファリンEX, カロナールA | ○ | 53,906 | なし |
| 1785892416886105725292 | 10:15:36 脂漏性湿疹 | Physical / rule_based | no_candidates | ✗ | 34,849 | no_candidates |
| 1785892798329357348510 | 10:20:45 喉痛+熱 | Physical / **fever_flow** | スカイブブロンG, バファリンかぜEX, カゼセブンS | ◎ | 50,281 | なし |
| 1785890421194005681438 | 10:27:13 頭痛（T2） | T1 redirect / T2 rule_based | イブ, バファリンEX, カロナールA | ◎ | 57,521 | なし |

**品質凡例**: ◎ 意図に合致 / ○ 概ね OK / △ ギャップあり / ✗ 問題あり

---

*Generated: 2026-08-05 — AWS logs + Neon prod cross-analysis*
