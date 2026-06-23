# GitLab 一時移行運用（GitHub 停止中）

**期間**: 2026-06-22 〜 GitHub アカウント [@32Lwk](https://github.com/32Lwk) 復旧まで  
**背景**: [GITHUB_ACCOUNT_SUSPENSION_2026-06.md](./GITHUB_ACCOUNT_SUSPENSION_2026-06.md)  
**GitLab リポジトリ**: [blank2703726/medicine-recommend](https://gitlab.com/blank2703726/medicine-recommend)  
**GCP プロジェクト番号**: `340042923793`

本書は、GitHub アカウント停止に伴う **Git リモート切替** と **Cloud Build（dev のみ）の GitLab 連携** について、実施した変更・日常運用・GitHub 復旧手順をまとめたものです。

---

## 1. 移行の範囲

| 領域 | 移行したか | 備考 |
|------|-----------|------|
| Git プッシュ先 | ✅ GitLab | `gitlab` リモート / upstream `gitlab/main` |
| Cloud Build **dev** | ✅ GitLab | `medicine-recommend-dev` へ `main` push でデプロイ |
| Cloud Build **本番** | ❌ 未移行 | 旧 GitHub トリガーのまま（停止中は動作しない） |
| GitHub Issues / `gh` | ❌ 利用不可 | 停止中は GitLab Issues またはローカル doc |
| GitLab CI（`.gitlab-ci.yml`） | ❌ 未導入 | Cloud Build を継続利用 |
| Cloud Run URL | 変更なし | 既存サービス名へリビジョン追加デプロイのみ |

**方針**: ステージング（dev）だけを GitLab 経由で継続デプロイし、本番は GitHub 復旧まで既存リビジョンを維持。急ぎの本番 hotfix は GCP コンソールまたは `gcloud builds submit` で対応。

---

## 2. リポジトリ内の変更（コード・設定）

### 2.1 Git リモート（ローカル・各開発マシン）

| リモート | URL | 役割（移行期間中） |
|----------|-----|-------------------|
| `gitlab` | `https://gitlab.com/blank2703726/medicine-recommend` | **プライマリ** — `git pull` / `git push` |
| `origin` | `https://github.com/32Lwk/medicine-recommend-system.git` | 参照用に残置。停止中は fetch / push 不可（403） |

```powershell
git remote -v
git branch -vv   # main が [gitlab/main] を追跡していること
```

日常コマンド:

```powershell
git pull
git push                 # upstream が gitlab/main なら引数不要
git push gitlab main     # 明示する場合
```

Cursor エージェント向けルール: [`.cursor/rules/git-remote.mdc`](../../.cursor/rules/git-remote.mdc)（`alwaysApply: true`）

### 2.2 `cloudbuild.yaml`（2026-06-23 修正）

**目的**: GitLab 連携トリガーからリポジトリ内の `cloudbuild.yaml` を参照するようになったため、dev / 本番の両方で共通利用する。

**変更内容**:

1. コメントを「GitHub push」から「Git push」に一般化
2. **bash ローカル変数の `$$` エスケープ** — Cloud Build が `${COMMIT_DATE}` / `${IMAGE}` を置換変数と誤認識し、次のエラーになる問題を修正:
   ```
   invalid value for 'build.substitutions': key in the template "COMMIT_DATE" is not a valid built-in substitution
   ```

| 変数 | Cloud Build 置換 | cloudbuild.yaml での書き方 |
|------|-----------------|---------------------------|
| `COMMIT_SHA`, `PROJECT_ID`, `REPO_NAME` | 組み込み | `${COMMIT_SHA}` 等（そのまま） |
| `_SERVICE_NAME`, `_DEPLOY_REGION` 等 | ユーザー定義（`_` 接頭） | `${_SERVICE_NAME}` 等（そのまま） |
| `COMMIT_DATE`, `IMAGE` | **該当なし**（bash のみ） | `$${COMMIT_DATE}`, `$${IMAGE}` |

**デフォルト置換**（ファイル内 `substitutions:`）は **本番** 向け:

```yaml
_SERVICE_NAME: medicine-recommend
_DEPLOY_REGION: asia-northeast1
_AR_REPOSITORY: cloud-run-source-deploy
_AR_HOSTNAME: asia-northeast1-docker.pkg.dev
```

dev トリガー側で `_SERVICE_NAME=medicine-recommend-dev` に上書きする（後述 §3.3）。

**ビルド手順の概要**（3 ステップ）:

1. `scripts/write_build_meta.py` で `static/build-meta.json` 生成（コミット日・ハッシュ）
2. Docker ビルド → Artifact Registry へ push
3. `gcloud run deploy` で Cloud Run へデプロイ

関連: [`.cursor/rules/onboarding-last-updated.mdc`](../../.cursor/rules/onboarding-last-updated.mdc)、[`CLOUD_RUN_LLM_ENV.md`](./CLOUD_RUN_LLM_ENV.md)

### 2.3 リポジトリに含まれない変更（GCP コンソール）

以下は GCP / GitLab のコンソールで実施。インフラ as code には未反映。

| リソース | 内容 |
|----------|------|
| GitLab Personal Access Token | `api` スコープ（接続管理）と `read_api` スコープ（ソース取得）の 2 つ |
| Secret Manager | 上記トークンと Webhook シークレットを自動保存 |
| Cloud Build ホスト接続 | GitLab.com、リージョン **`asia-northeast1`** |
| リンク済みリポジトリ | `blank2703726-medicine-recommend`（表示名は `blank2703726-medicine-recommend` 等） |

---

## 3. GCP Cloud Build 設定（dev のみ）

### 3.1 トリガー一覧（移行後の想定状態）

| トリガー名 | ソース | ブランチ | デプロイ先 | 状態 |
|-----------|--------|---------|-----------|------|
| `medicine-recommend-dev-gitlab-main` | GitLab `blank2703726/medicine-recommend` | `^main$` | `medicine-recommend-dev` | **有効**（新規） |
| `rmgpgab-medicine-recommend-dev-asia-northeast1-32Lwk-medicinsut`（旧名） | GitHub `32Lwk/medicine-recommend-system` | `^main$` | `medicine-recommend-dev` | **無効化推奨** |
| 本番用 GitHub トリガー | GitHub | `^main$` | `medicine-recommend` | 有効のまま（停止中は動かない） |

### 3.2 新規トリガー `medicine-recommend-dev-gitlab-main`

[Cloud Build → トリガー](https://console.cloud.google.com/cloud-build/triggers) で作成。

| 設定項目 | 値 |
|----------|-----|
| 名前 | `medicine-recommend-dev-gitlab-main` |
| リージョン | **`asia-northeast1`**（第2世代 GitLab 接続と同じ。`global` ではない） |
| イベント | ブランチに push する |
| リポジトリ サービス | Cloud Build リポジトリ |
| 世代 | **第 2 世代** |
| リポジトリ | `blank2703726-medicine-recommend` |
| ブランチ（正規表現） | `^main$` |
| 構成 | リポジトリ内 `cloudbuild.yaml` |
| 承認 | オフ |
| サービス アカウント | 旧 dev トリガーと同じ（例: `340042923793-compute@developer.gserviceaccount.com`） |

### 3.3 トリガー側の置換変数（dev 必須）

`cloudbuild.yaml` のデフォルトは本番サービス名のため、**dev トリガーでは必ず上書き**する。

| 変数 | dev トリガーでの値 |
|------|-------------------|
| `_SERVICE_NAME` | `medicine-recommend-dev` |
| `_DEPLOY_REGION` | `asia-northeast1` |
| `_AR_REPOSITORY` | `cloud-run-source-deploy` |
| `_AR_HOSTNAME` | `asia-northeast1-docker.pkg.dev` |

`_SERVICE_NAME` を誤って `medicine-recommend` のままにすると **本番へデプロイ** するため要注意。

### 3.4 Cloud Run URL が変わらない理由

`gcloud run deploy medicine-recommend-dev --region=asia-northeast1` は **既存サービスの新リビジョン** を作成するだけ。サービス名・プロジェクト・リージョンが同じなら URL（`https://medicine-recommend-dev-....asia-northeast1.run.app`）は不変。

LINE webhook 等で dev URL を登録済みの場合も、そのまま利用できる（[`LINE_WEBHOOK_SETUP.md`](./LINE_WEBHOOK_SETUP.md)）。

### 3.5 Artifact Registry のイメージパス

`cloudbuild.yaml` 内:

```
${_AR_HOSTNAME}/${PROJECT_ID}/${_AR_REPOSITORY}/${REPO_NAME}/${_SERVICE_NAME}:${COMMIT_SHA}
```

GitHub 連携時の `REPO_NAME`（例: `medicine-recommend-system`）から GitLab リンク名（例: `blank2703726-medicine-recommend`）に変わると **イメージの格納パス** は変わるが、デプロイと Cloud Run URL には影響しない。古いパス上のイメージは手動削除するまで残る。

---

## 4. 日常運用（停止期間中）

### 4.1 開発 → dev デプロイの流れ

```
ローカルでコミット
  → git push gitlab main
  → Cloud Build トリガー（medicine-recommend-dev-gitlab-main）起動
  → medicine-recommend-dev に新リビジョンデプロイ
```

### 4.2 本番を更新したい場合

GitHub トリガーは停止中動作しない。次のいずれか:

- **GCP コンソール**から Cloud Run `medicine-recommend` を手動デプロイ（既存イメージまたは新規ビルド）
- ローカルから手動ビルド:
  ```bash
  gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=_SERVICE_NAME=medicine-recommend,_DEPLOY_REGION=asia-northeast1,_AR_REPOSITORY=cloud-run-source-deploy,_AR_HOSTNAME=asia-northeast1-docker.pkg.dev
  ```

### 4.3 オンボーディング「最終更新日・コミット」表示

dev / 本番とも `cloudbuild.yaml` が `GIT_COMMIT` / `GIT_COMMIT_DATE` を渡す。push 前の `static/build-meta.json` 更新は [onboarding-last-updated ルール](../../.cursor/rules/onboarding-last-updated.mdc) を参照。

### 4.4 GitLab PAT の有効期限

ホスト接続に使った Personal Access Token が失効するとトリガーが切れる。GitLab → Settings → Access tokens で期限を確認し、必要なら Secret Manager 上のシークレットをローテーション（[公式: Rotate tokens](https://cloud.google.com/build/docs/automating-builds/gitlab/connect-host-gitlab#rotate-old-or-expired-gitlab-access-tokens)）。

---

## 5. トラブルシューティング

### 5.1 `COMMIT_DATE` is not a valid built-in substitution

**原因**: `cloudbuild.yaml` 内の bash 変数 `${COMMIT_DATE}` が Cloud Build 置換と衝突。  
**対処**: `$${COMMIT_DATE}` / `$${IMAGE}` にエスケープ済み（§2.2）。修正コミットを `gitlab main` に push してから再実行。

### 5.2 リポジトリがトリガー画面に出ない

- トリガー作成画面の **リージョン** を `asia-northeast1` に変更
- [リポジトリ](https://console.cloud.google.com/cloud-build/repositories) の **第2世代** タブでリンク済みか確認

### 5.3 ブランチ一覧が「一致するブランチはありません」

GitHub 停止で旧トリガーがリポジトリにアクセスできない場合に発生。GitLab 用 **新規トリガー** を作成し、正規表現 `^main$` を手入力する。

### 5.4 デプロイ先が本番になった

トリガーの `_SERVICE_NAME` が `medicine-recommend-dev` になっているか確認。誤デプロイ時は Cloud Run コンソールで前リビジョンへロールバック。

### 5.5 環境変数が消えた（OPENAI / LINE Webhook 503 等）

**原因**: `gcloud run deploy --set-env-vars` は**既存の環境変数をすべて置き換える**（`GIT_COMMIT` / `GIT_COMMIT_DATE` だけ残り、他が消える）。2026-06-24 時点の GitLab デプロイでこの事象が発生した。

**恒久対策**: `cloudbuild.yaml` は `--update-env-vars` を使用（他キーを保持したまま Git メタのみ更新）。

**復旧手順**（dev 例）:

1. GCP コンソール → Cloud Run → `medicine-recommend-dev` → **リビジョン** → 直前の正常リビジョンから環境変数一覧を控える（または Secret Manager / 手元メモから再設定）
2. **変数とシークレット** タブで最低限以下を再設定:
   - `OPENAI_API_KEY_STAGING`（または `OPENAI_API_KEY`）
   - `APP_ENV=development`
   - `LINE_WEBHOOK_ENABLED=true`
   - `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN`
   - `DATABASE_URL`（Neon pooler、利用時）
3. 確認: `GET https://<dev-url>/line/webhook/status` → `enabled: true`, `channel_secret_configured: true`
4. 修正済み `cloudbuild.yaml` を push して再デプロイ（以降は env が消えない）

---

## 6. GitHub 復旧時の手続き

復旧日を **`GITHUB_ACCOUNT_SUSPENSION_2026-06.md` の更新履歴** と **本書 §8** に記録する。

### 6.1 事前確認

```powershell
git fetch origin          # 403 でなければ復旧
gh auth login             # CLI 再認証
gh issue list --limit 1   # API 動作確認
```

### 6.2 Git 履歴の同期（GitLab → GitHub）

停止期間中に GitLab にだけ存在するコミットを GitHub に反映する。

```powershell
# 双方の先端を確認
git fetch gitlab
git fetch origin
git log --oneline gitlab/main -5
git log --oneline origin/main -5

# GitLab が進んでいる場合の例（fast-forward で取り込めるとき）
git checkout main
git merge gitlab/main     # または git cherry-pick で個別反映
git push origin main

# GitHub 側だけに欠けているコミットがある場合は、先に origin/main を取り込んでから gitlab へ mirror
git push gitlab main      # 双方向同期が完了するまで必要に応じて繰り返す
```

**確認**: `git log gitlab/main..origin/main` と `git log origin/main..gitlab/main` がどちらも空になること。

### 6.3 ローカル upstream の復帰

```powershell
git branch --set-upstream-to=origin/main main
git pull
```

### 6.4 Cloud Build トリガーの整理

| 手順 | 作業 |
|------|------|
| 1 | [トリガー一覧](https://console.cloud.google.com/cloud-build/triggers) を開く |
| 2 | **dev**: GitHub 旧トリガー `rmgpgab-medicine-recommend-dev-...` を **再有効化** するか、GitLab トリガーを使い続けるか **どちらか一方** を選択 |
| 3 | 使わない方の dev トリガーを **無効化または削除**（二重デプロイ防止） |
| 4 | **本番**: GitHub 連携トリガーが有効で、`32Lwk/medicine-recommend-system` の `^main$` を監視していることを確認 |
| 5 | 本番トリガーが **インライン YAML** のままなら、必要に応じて `cloudbuild.yaml` 参照に統一（置換 `_SERVICE_NAME=medicine-recommend`） |
| 6 | `git push origin main` で本番・dev それぞれのトリガーが意図どおり発火するかテスト |

**推奨（シンプルに戻す場合）**:

- dev / 本番とも GitHub トリガーに戻す
- `medicine-recommend-dev-gitlab-main` を無効化
- GitLab ホスト接続は残してもよいが、使わないなら接続解除で PAT 露出面を減らす

**GitLab を正本のまま残す場合**:

- upstream は `origin/main` に戻しつつ、日常 push は GitLab → GitHub mirror 運用にする（非推奨・手順が増える）

### 6.5 Cursor / ドキュメントの後片付け

| ファイル | 復旧後の扱い |
|----------|-------------|
| [`.cursor/rules/git-remote.mdc`](../../.cursor/rules/git-remote.mdc) | 削除、または `alwaysApply: false` |
| 本書 `GITLAB_TEMPORARY_MIGRATION.md` | §8 に復旧日を追記。アーカイブとして残す |
| [`GITHUB_ACCOUNT_SUSPENSION_2026-06.md`](./GITHUB_ACCOUNT_SUSPENSION_2026-06.md) | GitLab 節・更新履歴に復旧日。必要なら「解決済み」と明記 |
| [`.cursor/rules/onboarding-last-updated.mdc`](../../.cursor/rules/onboarding-last-updated.mdc) | 「GitLab プッシュ時」の注記を通常運用に戻す |

### 6.6 復旧後にやり直す作業（停止中にブロックされていたもの）

- `gh auth login` 後、未反映の issue 更新（`scripts/update_issues_changelog_philosophy.sh` は **分割実行**）
- GitHub Education 再認証（法定名 Kawashima Yuto でプロフィール・請求名を一致）
- 公開 doc 内のリポジトリ URL が `github.com/32Lwk/...` のままか確認（GitLab URL に誤って変えていないか）

### 6.7 復旧チェックリスト（印刷用）

```
[ ] git fetch origin 成功
[ ] gh auth login / gh issue list 成功
[ ] gitlab/main と origin/main の差分ゼロ
[ ] git push origin main 成功
[ ] upstream を origin/main に戻した
[ ] dev Cloud Build トリガーが一方のみ有効（意図したソース）
[ ] 本番 Cloud Build トリガーが GitHub で動作
[ ] medicine-recommend-dev / medicine-recommend の URL 変化なし
[ ] LINE webhook（dev）動作確認
[ ] git-remote.mdc 無効化
[ ] インシデント doc に復旧日追記
```

---

## 7. 参考リンク

| 種別 | URL |
|------|-----|
| GitLab ミラー | https://gitlab.com/blank2703726/medicine-recommend |
| GitHub（復旧後） | https://github.com/32Lwk/medicine-recommend-system |
| Cloud Build リポジトリ | https://console.cloud.google.com/cloud-build/repositories |
| Cloud Build トリガー | https://console.cloud.google.com/cloud-build/triggers |
| Cloud Run（dev） | https://console.cloud.google.com/run?project=340042923793 |
| GitLab ホスト接続（公式） | https://cloud.google.com/build/docs/automating-builds/gitlab/connect-host-gitlab |
| GitLab トリガー作成（公式） | https://cloud.google.com/build/docs/automating-builds/gitlab/build-repos-from-gitlab |
| インシデント記録 | [GITHUB_ACCOUNT_SUSPENSION_2026-06.md](./GITHUB_ACCOUNT_SUSPENSION_2026-06.md) |

---

## 8. 更新履歴

| 日付 | 内容 |
|------|------|
| 2026-06-23 | 初版 — Git リモート移行、Cloud Build dev の GitLab 連携、`cloudbuild.yaml` の `$$` エスケープ、復旧手順 |
| （復旧日） | GitHub 復旧 — 本節と `GITHUB_ACCOUNT_SUSPENSION_2026-06.md` に日付を記入 |

---

_一時移行の正本ドキュメント。GitHub 復旧後も手順の参照用として残す。_
