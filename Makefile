# GitHub 自動 push/pull 用 Makefile
# 使い方:
#   make sync              # リモートから取得 → ローカル変更をプッシュ（推奨）
#   make sync MSG="fix: 〇〇を修正"  # メッセージを指定して同期
#   make pull              # リモートから最新の変更を取得
#   make push              # デフォルトメッセージで push
#   make push MSG="fix: 〇〇を修正"  # メッセージを指定して push

REMOTE ?= origin
BRANCH ?= $(shell git branch --show-current)
MSG ?= "Update: $(shell date '+%Y-%m-%d %H:%M')"

.PHONY: sync pull push add commit status status-verbose

# 完全同期: pull → add → commit → push
sync: pull commit
	git push $(REMOTE) $(BRANCH)
	@echo "Synced: Pulled from and pushed to $(REMOTE)/$(BRANCH)"

# リモートから最新の変更を取得
pull:
	git pull $(REMOTE) $(BRANCH) || true
	@echo "Pulled from $(REMOTE)/$(BRANCH)"

# 変更を add → commit → push まで一括実行
push: commit
	git push $(REMOTE) $(BRANCH)
	@echo "Pushed to $(REMOTE)/$(BRANCH)"

# 変更ファイルをステージング
add:
	git add -A
	@echo "Staged all changes"

# コミット（MSG でメッセージ指定可能）
commit: add
	git commit -m $(MSG) || true
	@echo "Committed with message: $(MSG)"

# 現在の git 状態を表示
status:
	git status

# リモートの状態も含めて確認
status-verbose: status
	@echo "---"
	git log -1 --oneline
	@echo "---"
	git remote -v
