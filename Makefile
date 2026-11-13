# 課題 III.2 の Makefile
# 依存関係の管理には uv を使う（https://docs.astral.sh/uv/）

MAIN    := pac-man.py
CONFIG  := config.json
UV      := uv
PYTHON  := $(UV) run python

MYPY_FLAGS := --warn-return-any --warn-unused-ignores --ignore-missing-imports \
              --disallow-untyped-defs --check-untyped-defs

.PHONY: all install run debug clean lint lint-strict test

all: install

# 依存関係（pygame-ce・迷路生成パッケージ・開発用ツール）を .venv に入れる
install:
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "uv が見つかりません。次のコマンドでインストールしてください:"; \
		echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 1; }
	$(UV) sync

# ゲームを起動する
run:
	$(PYTHON) $(MAIN) $(CONFIG)

# Python 組み込みのデバッガー pdb の上でゲームを起動する
debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

# 一時ファイルとキャッシュを消す
clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
	rm -rf .mypy_cache .pytest_cache

# 課題で指定されたフラグで flake8 と mypy を実行する
lint:
	$(UV) run flake8 .
	$(UV) run mypy . $(MYPY_FLAGS)

# 任意：より厳しい検査
lint-strict:
	$(UV) run flake8 .
	$(UV) run mypy . --strict

# テストを実行する（課題の必須ルールではない）
test:
	$(UV) run pytest
