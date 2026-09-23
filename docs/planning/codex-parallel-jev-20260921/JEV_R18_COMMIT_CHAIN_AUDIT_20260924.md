# JEV R18 Commit Chain Audit (2026-09-24)

対象レンジ: `9bcb882^..46d687b`  
対象コミット: `9bcb882`, `a40f353`, `67b8ea9`, `9ee28b4`, `74e4337`, `46d687b`  
監査モード: read-only で `git show` / `git diff` / 既存ファイル読取のみ。テスト再実行は未実施。

## 結論

**Verdict: Conditional**

- Critical: **0**
- High: **1**
- Medium: **2**

総評: tip (`46d687b`) 時点では `JEV_ENABLED` / `JEV_INTENT_ROUTER_SHADOW` / `JEV_INTENT_ROUTER_PRIMARY` / `POLICY_ENFORCEMENT_D2` がいずれも既定 OFF のままで、`.env` や明白な secret の混入、`tmp_*` 系、明確な unrelated user WIP の混入は確認できなかった。  
一方で、コミット列の途中には **readiness 根拠の前提を後続コミットで補正している箇所**があり、さらに docs/log 系の証跡コミットは再実行可能性よりアーカイブ性を優先しているため、**「各中間 SHA まで含めて常に本番投入可能」な鎖としては扱わない**のが妥当。

## Findings

### High

1. **`9bcb882` の readiness 評価前提が `a40f353` で補正されており、コミット列が per-commit production-ready ではない**
   - `a40f353` 自身の intent が「`raw accuracy` と `membership contracts` の強制」であり、評価 harness の `accuracy_gate_eligible=True` 契約、raw/effective 分離、eligible/ineligible 集計条件を明示的に修正している。
   - したがって `9bcb882` 単体の時点では、R18 readiness を支える評価指標の扱いがまだ固まっておらず、**チェーン先頭から順にどこで切っても安全**とは言えない。
   - 影響範囲は主に評価・監査の厳密性だが、R18 の go/no-go 判定に直結するため High。

### Medium

1. **`74e4337` は大容量の生成物 (`log/analysis/*.json`, `*.md`, `*.txt`) を本流に含めており、証跡としては有効でも監査面のノイズが大きい**
   - 39 files / 約 193k insertions の大半が `log/analysis/` 生成物。
   - リポジトリ方針上 `log/` 追跡は許容されるが、secret 漏えい・PII・再現性のレビューコストを押し上げる。
   - 今回の監査では明白な secret 値は検出しなかったが、**「安全だから問題なし」ではなく「赤旗は見えなかった」止まり**。

2. **docs-only の証跡コミット (`67b8ea9`, `74e4337`) は実行可能テストを同梱せず、監査上は“結果の保存”に依存している**
   - `67b8ea9` は 87 files すべて docs (`.md`/`.json`)。
   - `74e4337` も実質は docs/log アーカイブで、`tests/fixtures/...` 追加はあるが executable test ではない。
   - そのため「その SHA を checkout して直ちに再検証」より、「既に生成された証跡を読む」形に寄っており、commit-chain の追跡性としては一段弱い。

## Commit-by-Commit Audit

| Commit | Intent | File types | secrets / `.env` risk | log/tmp inclusion | default flags still OFF | unrelated user WIP | tests associated | Audit note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `9bcb882` | JEV local shadow + D2 foundation を default-OFF で凍結 | `.py` x64, `.yaml` x1 | `.env` 追加なし。JEV secret は `JEV_API_KEY` のみ参照し、値の commit 痕跡なし | `log/` / `tmp_*` なし | **Yes**。`JEV_ENABLED`, `JEV_INTENT_ROUTER_SHADOW`, `JEV_INTENT_ROUTER_PRIMARY`, `POLICY_ENFORCEMENT_D2` は explicit OFF | 観測なし | **Yes**。36 test files 同梱 | 大規模基盤投入としてはテスト厚め。ただし後続 `a40f353` が eval 契約を補正しており、この SHA 単体の readiness 主張は弱い |
| `a40f353` | eval harness の raw accuracy / membership 契約修正 | `.py` x4 | `.env` / secret 追加なし | `log/` / `tmp_*` なし | **Yes**。フラグ変更なし、OFF 維持 | 観測なし | **Yes**。2 test files で harness 契約を補強 | `9bcb882` 後の即時補正。commit と tests は整合している |
| `67b8ea9` | R7-R16 / Gate A / overnight docs のアーカイブ | `.md` x84, `.json` x3 | `.env` なし。secret 名の記述はあるが値はなし | `log/` なし、`tmp_*` なし | **Yes**。コード未変更 | 観測なし。manifest 系でも除外方針を明記 | **Evidence only**。新規 executable test なし | 本番 enablement は行わない docs commit。監査資料としては有用だが再実行性はない |
| `9ee28b4` | shadow payload 縮小、persona holdout / offline E2E 追加 | `.py` x5, `.yaml` x2, `.md` x1 | `.env` / secret 追加なし | `log/` / `tmp_*` なし | **Yes**。フラグ変更なし、OFF 維持 | 観測なし | **Yes**。test + fixtures 追加 | 変更意図とテスト/fixture が素直に対応。production flag を触らず評価面を前進 |
| `74e4337` | overnight convergence evidence と holdout 結果の記録 | `.md` x18, `.json` x11, `.txt` x10 | `.env` なし。監査範囲では raw secret pattern 不一致 | **`log/analysis` 29 files 追加**。`tmp_*` はなし | **Yes**。コード未変更 | 観測なし | **Evidence only**。pytest 出力や holdout 結果はあるが新規 executable test なし | 大量証跡 commit。repo 方針には沿うが、chain safety という意味ではノイズ源 |
| `46d687b` | Jev wire payload の空 `meta` 除去、criteria 文言整理 | `.py` x4, `.md` x1 | `.env` / secret 追加なし。`Bearer` をログへ出さない方針維持 | `log/` / `tmp_*` なし | **Yes**。フラグ変更なし、OFF 維持 | 観測なし | **Yes**。`jev_client` と eval test を更新 | tip 候補としては小さく閉じた修正。manifest 更新は `74e4337` 反映までで、自分自身 (`46d687b`) は manifest に未列挙 |

## Specific Checks

### Default flags

監査対象チェーンで production-enable を既定 ON に変える変更は確認できなかった。  
少なくとも現行 tip では以下が既定 OFF:

- `JEV_ENABLED`
- `JEV_INTENT_ROUTER_SHADOW`
- `JEV_INTENT_ROUTER_PRIMARY`
- `POLICY_ENFORCEMENT_D2`

加えて `is_jev_intent_router_primary_enabled()` の docstring でも、Phase 1 では実行 route を変えてはならない旨が維持されている。

### Secrets / `.env`

- 監査対象コミットに `.env` 系ファイル追加は **0**
- secret 値らしき追加を commit patch / docs / `log/analysis` で spot-check した範囲では **未検出**
- 露出しているのは `JEV_API_KEY`, `OPENAI_API_KEY`, `TYPESAFE_API_KEY` などの**変数名や運用方針**が中心
- `46d687b` の `jev_client` でも Authorization Bearer のログ抑止方針は維持

### Log / tmp inclusion

- `tmp_*` / `.tmp` / 一時ファイルの混入: **なし**
- `log/analysis` の混入: **`74e4337` のみ有り**
- これは repo 方針違反ではないが、R18 の「本番準備チェーン」としては evidence-heavy

### Unrelated user WIP

監査対象 6 commits の file list には、少なくとも現在ワークツリーで見えている以下の unrelated 群は入っていないことを確認:

- `..bfg-report/`
- `local_outputs/`
- `docs/planning/notebooklm-history/`
- `docs/planning/ux-pdca-20260922/`

`JEV_OVERNIGHT_COMMIT_MANIFEST_20260924.md` でも `.env` / secrets / `tmp_*` / unrelated user WIP 除外方針が明記されており、実際の commit file list とも整合している。  
ただし manifest 自体は `46d687b` を列挙しておらず、tip 時点の自己記述性は完全ではない。

## Verdict Rationale

**Conditional** とする理由:

1. tip は default-OFF を維持し、明白な secret / `.env` / tmp / unrelated WIP 混入も見えず、個別コミットの intent も大筋で一貫している。
2. ただし `9bcb882` の後に `a40f353` で評価契約を補正しているため、**チェーン途中の SHA をそのまま本番 readiness の根拠に使うのは危険**。
3. docs/log 証跡コミットは有用だが、再実行可能な検証よりアーカイブに寄っており、production-readiness の commit chain としては完全にクリーンとは言い切れない。

したがって、この 6-commit chain は **tip 基準では概ね安全寄り**だが、**「全中間コミットを含めて Pass」ではなく「条件付きで採用可」**が妥当。
