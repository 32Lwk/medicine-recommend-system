# JEV A-3 / D2 Policy Enforcement 医療一次レビュー

- 作成日: 2026-09-22
- Reviewer: Primary medical reviewer
- Role: AI medical adversarial review for policy copy only
- Scope:
  - `SF-E1`（既存 `build_system_error_status`）
  - `SF-E1-NM`（`SF-E1` + 「今回の操作では履歴や記録内容は変更されていません。」）
  - prescription boundary copy for content-only adapter
- Labels:
  - `ai_medical_adversarial_reviewed=true`
  - `human_medical_reviewed=false`

> 本報告は **A-3/D2 Policy Enforcement 用の AI 多重医療レビュー**であり、製品安全認証、人間医療監修、薬機法上の保証を意味しない。  
> 本文書で許可される呼称は **「AI多重医療監修済み候補」** のみとし、**「製品安全合格」** や **「人間医療監修」** は使用しない。

---

## 0. 一句裁定

prescription boundary copy は **Accept**。  
`SF-E1` と `SF-E1-NM` は、**医療文言そのものは概ね安全側**だが、**緊急判定より先に出さないこと**と、`SF-E1-NM` では **「変更されていません」真実性を厳格に証明できること**が前提であり、いずれも **Conditional** が妥当。

---

## 1. 評価対象

### 1.1 SF-E1

- title: `一時的なエラーが発生しました`
- message: `処理中に問題が発生しました。しばらく時間をおいてからもう一度お試しください。`
- hints:
  - `もう一度お試しください`
  - `問題が続く場合は薬剤師にご相談ください`

### 1.2 SF-E1-NM

- `SF-E1` の message + `今回の操作では履歴や記録内容は変更されていません。`
- 使用許可条件:
  - mutation never started
  - または memory rollback succeeded and DB unchanged confirmed
  - または DB compensation confirmed
- 使用禁止条件:
  - `db_commit_unknown`
  - rollback failed

### 1.3 Prescription boundary copy

`申し訳ありません。当サービスでは医師の処方箋が必要な医薬品の処方や処方の代行はできません。必要に応じて医療機関を受診してください。市販薬（OTC）についてのご相談であれば、具体的な症状やお困りごとをお書きください。`

---

## 2. 主要所見

## Critical Findings

1. **generic fallback を emergency / crisis 未解決状態で出す運用は不可**
   - `SF-E1` / `SF-E1-NM` 自体は非断定・非煽動で安全寄りだが、胸痛、呼吸困難、自傷他害、過量服薬などの高リスクが未確定の段階でこの文言に落とすと、**再試行案内が受診・救急案内を上書きする false negative** になる。
   - したがって本 2 文言は、**上位の SafetyGate が先に勝つ**、または **緊急/危機が十分否定済み** のときだけ使うべき。

2. **`SF-E1-NM` の「変更されていません」は、証拠がない限り出してはいけない**
   - 文言としては落ち着いていて有用だが、部分 commit、rollback 不全、`db_commit_unknown`、非同期 flush 未確定、補償未確認の状態で出すと、**事実誤認をユーザーへ断定する**。
   - 医療そのものの危険文言ではないが、**記録変更の有無は信頼と再受診判断に関わるため、虚偽 reassurance は Critical 運用リスク** とみなす。

## High Findings

1. **`SF-E1` の「薬剤師にご相談ください」は、純オペレーション失敗ではやや不自然**
   - 履歴確認、履歴削除、記録系操作、ポリシー拒否の fallback で出ると、ユーザーは「システムエラーなのに医療相談が必要なのか」と受け取りうる。
   - ただし、違法薬物利用者扱いをしたり、救急へ過剰誘導したりする害はなく、**医療安全上は許容範囲**。

2. **`SF-E1` を prescription / medical examination の最終境界文言の代替として常用してはいけない**
   - fallback として一時的に出すのは可でも、通常系の policy denial まで generic error に寄せると、**「今は失敗しただけで、あとで試せば処方/診察要求が通るかもしれない」** という誤学習を招く。
   - よって `SF-E1` / `SF-E1-NM` は **primary policy copy ではなく safe fallback 専用** が妥当。

3. **`SF-E1-NM` の「履歴や記録内容」は適用範囲を広く読まれやすい**
   - もし内部監査ログ、観測ログ、pending flag、session metadata などが更新されうるなら、ユーザーは「何も変わっていない」と広く理解する可能性がある。
   - 実運用で保証できるのが **会話履歴・保存属性・ユーザー向け記録** に限られるなら、その範囲で真実性を担保する必要がある。

## Medium Findings

1. **prescription boundary copy は医療安全上は良好だが、語感に軽い重複がある**
   - `処方や処方の代行` は意味上ほぼ同系反復で、やや硬い。
   - ただし害方向は小さく、**違法薬物・規制薬物の拒否文に寄っていない**点が重要で、このままでも安全。

2. **prescription boundary copy の受診勧奨は適切で、救急過剰化は見られない**
   - `必要に応じて医療機関を受診してください` は、緊急性のない境界案内として妥当。
   - 胸痛や自殺念慮のような救急群をここで扱う文ではないため、過剰な emergency escalation はない。

3. **drug-user labeling のリスクは今回 3 文言では低い**
   - 特に prescription boundary copy は、規制薬物・違法薬物テンプレと異なり、**相手を不正使用者として扱わない**。
   - ここは明確に良い点であり、医療相談再導入の導線も維持できている。

## Low Findings

1. **`問題が続く場合は薬剤師にご相談ください` は OTC 文脈では自然**
   - 文言はやや汎用的だが、OTC 相談サービスとしては破綻していない。
   - 「医師」まで足さないことで、不要な医療化を抑えている面もある。

2. **prescription boundary copy は false emergency を起こしにくい**
   - 強い危険語、違法性断定、依存ラベリング、威圧的禁止がなく、content-only adapter 向けとして扱いやすい。

---

## 3. copy 別 verdict

### 3.1 SF-E1

- Verdict: **Conditional**
- 呼称: **AI多重医療監修済み候補（条件付き）**

#### 判定理由

- 良い点:
  - システム障害として素直で、**診察要求を drug misuse 扱いしない**。
  - 救急を乱発せず、panic をあおらない。
  - retry と対人相談の両方を残しており、医療判断を AI が断定しない。
- 条件:
  - **emergency / crisis / overdose / severe physical red flags より後段でのみ** 使用すること。
  - **policy の通常拒否文言の代替として常用しない**こと。
  - 純オペレーション系 fallback でも使うなら、「薬剤師相談」は UX 上やや不自然であることを許容すること。

#### 医療レビュー結論

文言単体は危険ではないが、**出すタイミングを誤ると false negative を作る**。したがって Accept ではなく Conditional。

### 3.2 SF-E1-NM

- Verdict: **Conditional**
- 呼称: **AI多重医療監修済み候補（条件付き）**

#### 判定理由

- 良い点:
  - 「変更されていません」を添えることで、履歴削除・記録変更系の失敗時に**ユーザー不安を下げる**効果がある。
  - 文言自体は非攻撃的で、診断・処方・違法性を誤示しない。
- 条件:
  - `mutation never started`、または `rollback succeeded + DB unchanged confirmed`、または `DB compensation confirmed` の **いずれかを機械的に証明できる場合に限定**。
  - `db_commit_unknown`、rollback failed、partial mutation unresolved では **絶対に使用しない**。
  - もし内部的に変更が残りうるのが監査・観測ログのみでも、ユーザーが読む「記録内容」の射程と食い違わないことを確認すること。

#### 医療レビュー結論

この文言の争点は医療助言ではなく **truthfulness**。  
真実性が担保される実装契約とセットなら妥当だが、そうでなければ即座に Reject 側へ転ぶため、Conditional が妥当。

### 3.3 Prescription boundary copy

- Verdict: **Accept**
- 呼称: **AI多重医療監修済み候補**

#### 判定理由

- 良い点:
  - **処方箋医薬品の境界**を明示しつつ、相手を違法薬物ユーザー扱いしない。
  - `必要に応じて医療機関を受診してください` は、**救急へ過剰誘導せず、受診線だけを示す**ので適切。
  - 最後に `市販薬（OTC）についてのご相談であれば...` と戻し先を示しており、**会話継続の安全な再導線**がある。
  - system error と誤認しにくく、診察依頼とも区別しやすい。
- 留意点:
  - `処方や処方の代行` はやや重複的だが、医療安全上の欠陥ではない。

#### 医療レビュー結論

content-only adapter 用の固定文として、**過剰救急化・依存者ラベリング・system error 混同のいずれも小さい**。この 3 案の中で最も素直に採用しやすい。

---

## 4. 焦点別レビュー

### 4.1 False negatives

- 最大の懸念は文言そのものより **表示順序**。
- `SF-E1` / `SF-E1-NM` が emergency/crisis 判定未完了の入力を覆うなら false negative。
- prescription boundary copy 自体は false negative を作りにくいが、当然ながら **胸痛・呼吸苦・希死念慮などの高危険入力の primary 応答には使わない**。

### 4.2 Over-escalation to emergency

- 3 文言とも **過剰な emergency escalation は見られない**。
- 特に prescription boundary copy は非緊急の受診線にとどまっており、穏当。

### 4.3 Mislabeling as drug user

- prescription boundary copy は **良好**。
- 違法薬物・規制薬物の文脈を持ち込んでおらず、処方要求ユーザーを依存・不正使用者に見立てていない。
- `SF-E1` / `SF-E1-NM` もこの誤ラベルは起こさない。

### 4.4 Confusing exam request with system error

- prescription boundary copy は明確に境界説明であり、system error とは混同しにくい。
- 一方 `SF-E1` / `SF-E1-NM` は、medical examination / prescription の通常拒否に常用すると混同を招くため、**fallback 限定運用**が必要。

### 4.5 Unnatural pharmacist guidance

- `SF-E1` の pharmacist guidance は、症状相談系には自然、記録操作系にはやや不自然。
- ただし「医師へ直行」よりは非過剰で、OTC サービスの tone としてはまだ許容。

### 4.6 Truthfulness of 「変更されていません」

- ここは本レビューの最重要点。
- `SF-E1-NM` は、**文言の良し悪しより、裏の状態確認が完了しているか** が全て。
- 真偽不明状態で出すなら Reject 相当、真実性が機械的に担保されるなら Conditional で許容。

---

## 5. 最終裁定

| Copy | Verdict | 呼称可否 | コメント |
| --- | --- | --- | --- |
| `SF-E1` | **Conditional** | **AI多重医療監修済み候補（条件付き）** | 上位安全判定後のみ。primary policy copy 代用は禁止 |
| `SF-E1-NM` | **Conditional** | **AI多重医療監修済み候補（条件付き）** | 「変更されていません」は厳格証明が前提 |
| prescription boundary copy | **Accept** | **AI多重医療監修済み候補** | 非攻撃的・非救急過剰・非ラベリングで良好 |

---

## 6. Supervisor 向け一行

**Prescription boundary は Accept、SF-E1 / SF-E1-NM は医療文言としては安全寄りだが、前者は上位 Safety 完了後のみ、後者は「変更なし」真実性証明済みの場合に限るため Conditional。**
