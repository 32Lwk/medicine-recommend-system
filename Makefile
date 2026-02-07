# GitHub 自動 push 用 Makefile
# 使い方:
#   make push              # デフォルトメッセージで push
#   make push MSG="fix: 〇〇を修正"  # メッセージを指定して push

REMOTE ?= origin
BRANCH ?= $(shell git branch --show-current)
MSG ?= "Update: $(shell date '+%Y-%m-%d %H:%M')"

.PHONY: push add commit status sync untrack-makefile

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

# リモートと同期（未コミット変更は stash → pull → push → stash pop）
sync:
	@git stash push -m "make sync" 2>/dev/null || true; \
	git pull $(REMOTE) $(BRANCH) --rebase; \
	git push $(REMOTE) $(BRANCH); \
	if git stash list | grep -q "make sync"; then git stash pop; fi; \
	echo "Synced with $(REMOTE)/$(BRANCH)"

# Makefile の追跡をやめる（1回だけ実行。以降 Makefile は GitHub に含まれない）
untrack-makefile:
	git rm --cached Makefile 2>/dev/null || true
	@echo "Makefile の追跡を解除しました。次回 commit でリモートから削除されます。"

# 現在の git 状態を表示
status:
	git status

# リモートの状態も含めて確認
status-verbose: status
	@echo "---"
	git log -1 --oneline
	@echo "---"
	git remote -v
