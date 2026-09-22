# Boundary staging repair + jev_router regression diagnosis

- Date: 2026-09-22
- commit / push / live: **not executed**
- Gate A-accuracy: **Not Passed** / Gate B: **Hard No-Go** / live: **Blocked**

## Candidate split（報告分離）

| Candidate | Status |
| --- | --- |
| **boundary commit candidate** | Manifest 改訂済み。`crisis_detection.py` 除外。実行承認 **保留** |
| **medical safety commit candidate** | `crisis_detection.py` BR-C01/H02、`medical_examination_request.py` BR-H01、専用テスト |
| **policy/security runtime commit candidate** | H03/H05（設計のみ・未実装） |
| **Gate B contract/fixture candidate** | H04（runtime と分離・金ラベル自動変更禁止） |
| **test-mock hygiene candidate** | 下記 2 件の patch 契約修正（境界・医療と別） |

---

## Phase 1 — staging manifest 修復（結果）

### Measured

- WT 正で再監査。`src/core/crisis_detection.py` の `git diff HEAD` は:
  - BR-H02: `死にたかった` / `死にたくなっ`
  - BR-C01: `_AFFIRMATIVE_DOUBLE_NEGATION_*` + matcher
  - Option A: **NOTE コメントのみ**（機能 hunk なし）
- 旧 manifest の `git add … crisis_detection.py` は医療 BR を stage し、境界-only 契約に違反。

### Act

- 境界 candidate から `crisis_detection.py` を **EXCLUDE**。
- Option A（否定 soft を Jev 差分に載せない）は **HEAD 挙動維持 = ファイル変更不要**。
- 非対話 hunk 分割は「境界だけ」を安全に証明できないため不採用（統合延期ではなく、**医療ファイルを外して境界を維持**）。

### Dry-run stage（commit なし・即 unstage）

- 改訂 INCLUDE 列挙で `git add` → `git diff --cached --name-only` に `crisis_detection.py` / `medical_examination_request.py` / BR 専用テスト **なし**（measured）。
- staged `*.py` に `_AFFIRMATIVE_DOUBLE_NEGATION` / `死にたかった` 等の実装マーカー **なし**（measured）。
- docs/JSON に BR-ID の OUT OF SCOPE 言及は残る（実装混入ではない）。
- その後 `git restore --staged` で破棄。**commit 未実行**。

### Unresolved risk

- `gate.py` / `jev_router.py` 等に、境界以前の Phase1 Jev WT 差分が同一ファイル内共存し得る（従来どおり）。境界 commit は「境界修復後ファイル状態の凍結」であり、interactive hunk 分割は行わない。

---

## Phase 2 — 回帰 2 件の診断（修正未実施）

### Measured

```text
pytest tests/dialogue/routing/test_jev_router.py
2 failed, 21 passed

FAILED test_sync_path_mocked_client_no_session_change  (assert mock_rec.called)
FAILED test_queue_saturation_records_not_eligible_and_returns_false  (assert mock_rec.called)
```

順序依存（測定）:

- `test_schedule_with_flags_on_does_not_mutate_session` → 直後の sync テストが失敗。
- 単独実行ではしばしば成功。

計装時の決定的観測:

```text
patch_binds: False
mock_id != jm_attr_id
jm_type: function          # patch が作った MagicMock がモジュール属性に載っていない
ok / client / parse: True  # worker は走っている（実 record_shadow_event 側）
```

### 確認事項への回答

| 仮説 | 判定 | 根拠 |
| --- | --- | --- |
| `record_shadow_event` の import 方式 | **実装は local import（正しい）** | `_shadow_worker` / `_record_schedule_skip` は関数内 `from src.services.jev_metrics import record_shadow_event` |
| module-level alias による patch 先不一致 | **否定（jev_router 側）** | モジュール先頭での metrics 束縛なし |
| `sys.modules` 差し替え後の参照キャッシュ | **部分的に該当（テスト側）** | 先行テストが `patch.dict(sys.modules, {jev_client, jev_decisions})` を使用。`patch.dict` の exit は **`sys.modules` 全体を clear→snapshot restore** |
| テスト順序依存 | **該当（測定）** | schedule 系の後に再現 |
| 実装不具合 vs mock 契約陳腐化 | **mock 契約 / テスト汚染が主因** | 本番パスは metrics を呼ぶ。patch がモジュールに bind されず `mock_rec.called` だけが False |

### Root cause（inferred + measured の接続）

1. **Measured:** `patch("src.services.jev_metrics.record_shadow_event")` が返す `mock_rec` と、実行時に見える `jev_metrics.record_shadow_event` が不一致。
2. **Inferred:** `unittest.mock.patch` のターゲット解決は `_importer` → `__import__` + **`getattr(package, submodule)`**であり、`sys.modules[...]` 直参照ではない。`patch.dict(sys.modules)` の全クリア復元のあと、package 属性と `sys.modules` の対応が歪むと、patch の setattr 先と worker の local import 先がずれ得る。
3. **Not claimed as product bug:** shadow worker / schedule_skip の本番ロジック欠陥とは断定しない。

### Fix candidate（別変更単位・未実装）

推奨（テストのみ）:

1. `patch.dict(sys.modules, …)` で client/decisions を差し替えない。  
   → 先に実モジュールを import し `patch("src.services.jev_client.evaluate_system_one", …)` 等。
2. metrics は `import src.services.jev_metrics as jm` + **`patch.object(jm, "record_shadow_event", …)`**。
3. どうしても `patch.dict(sys.modules)` を使う場合は、exit 後に package 属性の再同期を明示（それでも非推奨）。

**境界 commit / 医療 commit に混ぜない。**

---

## Phase 3 ポインタ

H03–H05 Option A 設計: `JEV_BR_H03_H05_OPTION_A_DESIGN_20260922.md`  
（本ファイルは staging + 回帰診断に限定）
