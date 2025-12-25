# Render.com デプロイメント設定ガイド

## 概要

このドキュメントでは、Render.comでのデプロイメント設定、特にGunicornのタイムアウト設定とワーカー設定について説明します。

### 現在の環境情報

- **プラン**: Hobby Plan - Starter
- **RAM**: 512MB per instance
- **CPU**: 0.5 per instance
- **インスタンス数**: 2（スケーリング）

## 問題: WORKER TIMEOUT エラー

### 症状
- ログに `[CRITICAL] WORKER TIMEOUT` が表示される
- 約30秒でタイムアウトが発生する
- `gunicorn_config.py`で`timeout = 120`に設定しているが反映されない

### 原因
1. **Render.comのプラットフォーム制約**: 無料プランでは30秒のタイムアウト制限がある場合がある
2. **設定ファイル未適用**: gunicornの起動時に設定ファイルが読み込まれていない
3. **デフォルト値の適用**: gunicornのデフォルトタイムアウト（30秒）が適用されている

## 解決方法

### 方法1: 起動スクリプトを使用（推奨）

#### 1. 起動スクリプトの作成
`start.sh`ファイルが既に作成されています。このスクリプトはコマンドライン引数でタイムアウトを明示的に指定します。

#### 2. Render.comでの設定

**オプションA: Render.comダッシュボードで設定**

1. Render.comダッシュボードにログイン
2. 該当するWebサービスを選択
3. **Settings** → **Build & Deploy** セクション
4. **Start Command** を以下のように設定:
   ```bash
   chmod +x start.sh && ./start.sh
   ```
   または直接コマンドを指定:
   ```bash
   gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 120 --graceful-timeout 30 --max-requests 1000 --max-requests-jitter 50 --keep-alive 5 --access-logfile - --error-logfile - --log-level info --name medicine-recommend-app app:app
   ```

**オプションB: render.yamlを使用**

1. プロジェクトルートに`render.yaml`ファイルを配置（既に作成済み）
2. Render.comダッシュボードで:
   - **Settings** → **Build & Deploy**
   - **Render YAML Path** に `render.yaml` を指定

### 方法2: 環境変数の設定

#### Render.comダッシュボードでの環境変数設定

1. Render.comダッシュボードにログイン
2. 該当するWebサービスを選択
3. **Settings** → **Environment** セクション
4. 以下の環境変数を追加:

| 環境変数名 | 値 | 説明 |
|----------|-----|------|
| `GUNICORN_TIMEOUT` | `120` | Gunicornのタイムアウト（秒） |
| `GUNICORN_GRACEFUL_TIMEOUT` | `30` | グレースフルタイムアウト（秒） |
| `GUNICORN_WORKERS` | `2` | ワーカープロセス数 |
| `GUNICORN_WORKER_CLASS` | `sync` | ワーカークラス |

#### 環境変数の優先順位

1. コマンドライン引数（`start.sh`で指定）
2. 環境変数（`GUNICORN_TIMEOUT`など）
3. 設定ファイル（`gunicorn_config.py`）
4. デフォルト値

### 方法3: Render.comのプラットフォーム設定確認

#### ヘルスチェック設定

1. **Settings** → **Advanced** セクション
2. **Health Check Path**: `/` または `/api/health`（存在する場合）
3. **Health Check Timeout**: 必要に応じて増加

#### プラットフォーム制約の確認

- **無料プラン**: 30秒のタイムアウト制限がある場合があります
- **有料プラン**: より長いタイムアウトが可能です

## 設定の確認方法

### 1. ログで確認

デプロイ後、ログで以下のメッセージを確認:

```
🚀 Starting Gunicorn with the following settings:
   - Timeout: 120s
   - Graceful Timeout: 30s
   - Workers: 2
   - Worker Class: sync
   - Port: 10000
```

### 2. 実際のタイムアウト時間の確認

ログで `WORKER TIMEOUT` エラーが発生した時間を確認:
- エラー発生時刻 - リクエスト開始時刻 = 実際のタイムアウト時間

### 3. 環境変数の確認

Render.comのログで環境変数が正しく読み込まれているか確認:
```bash
# ログに環境変数の値が表示される場合がある
```

## トラブルシューティング

### 問題1: 起動スクリプトが実行できない

**エラー**: `Permission denied` または `start.sh: command not found`

**解決方法**:
1. `start.sh`に実行権限があるか確認:
   ```bash
   chmod +x start.sh
   ```
2. Start Commandで明示的に権限を付与:
   ```bash
   chmod +x start.sh && ./start.sh
   ```

### 問題2: 環境変数が反映されない

**解決方法**:
1. 環境変数の名前が正しいか確認（大文字小文字を区別）
2. 環境変数を設定した後、サービスを再デプロイ
3. ログで環境変数の値が表示されているか確認

### 問題3: 30秒でタイムアウトが発生し続ける

**原因**: Render.comの無料プランの制約

**解決方法**:
1. 有料プランへのアップグレードを検討
2. 処理時間を短縮する（非同期処理、キャッシュの活用）
3. 長時間処理をバックグラウンドジョブに移行

## Gunicorn設定パラメータの説明

### GUNICORN_WORKERS（ワーカープロセス数）

**説明**: Gunicornが起動するワーカープロセスの数。各ワーカーは独立したプロセスとして動作し、リクエストを処理します。

**特徴**:
- ワーカー数が多いほど、同時に処理できるリクエスト数が増加
- ただし、メモリとCPUの使用量も比例して増加
- 各ワーカーは独立したメモリ空間を持つため、メモリ使用量 = ベースメモリ + (ワーカー数 × ワーカーあたりのメモリ)

**推奨計算式**:
```
推奨ワーカー数 = (CPU数 × 2) + 1
```

**例**:
- 0.5 CPUの場合: (0.5 × 2) + 1 = 2ワーカー
- 1 CPUの場合: (1 × 2) + 1 = 3ワーカー
- 2 CPUの場合: (2 × 2) + 1 = 5ワーカー

**メモリ制約の考慮**:
- 各ワーカーは約50-100MBのメモリを使用（アプリケーションの複雑さによる）
- 512MB RAMの場合: 512MB ÷ 100MB = 約5ワーカーが上限
- 安全のため、メモリの70-80%を目安に設定

### GUNICORN_WORKER_CLASS（ワーカークラス）

**説明**: ワーカーがリクエストを処理する方式を指定します。

**主な種類**:

1. **`sync`（同期）** - デフォルト、推奨
   - 各ワーカーが1つのリクエストを順次処理
   - シンプルで安定性が高い
   - CPU集約的な処理に適している
   - メモリ使用量が予測しやすい
   - **推奨**: 医薬品推奨システムのようなCPU集約的な処理

2. **`gevent`（非同期）**
   - 1つのワーカーで複数のリクエストを並行処理
   - I/O待機が多い処理に適している（API呼び出し、データベースクエリなど）
   - メモリ効率が良い
   - ただし、CPU集約的な処理には不向き
   - 追加パッケージ（`gevent`）が必要

3. **`gthread`（スレッド）**
   - スレッドベースの並行処理
   - PythonのGIL（Global Interpreter Lock）の制約を受ける
   - I/O待機が多い処理に適している

**推奨**: 医薬品推奨システムでは`sync`を推奨（CPU集約的な処理が多いため）

## 推奨設定

### 現在の環境（Hobby Plan - Starter 512MB RAM, 0.5 CPU, 2インスタンス）

**リソース情報**:
- RAM: 512MB per instance
- CPU: 0.5 per instance
- インスタンス数: 2

**推奨設定**:

```bash
# 環境変数
GUNICORN_TIMEOUT=120
GUNICORN_GRACEFUL_TIMEOUT=30
GUNICORN_WORKERS=2          # (0.5 × 2) + 1 = 2（メモリ制約も考慮）
GUNICORN_WORKER_CLASS=sync  # CPU集約的処理に適している

# Start Command
chmod +x start.sh && ./start.sh
```

**設定理由**:
- **ワーカー数2**: 0.5 CPUでは2ワーカーが適切。メモリ制約（512MB）も考慮すると2が安全
- **sync**: CPU集約的な医薬品推奨処理に最適
- **2インスタンス**: 合計4ワーカー（2インスタンス × 2ワーカー）で負荷分散

**メモリ使用量の目安**:
- ベースメモリ: 約100MB
- ワーカーあたり: 約50-100MB
- 合計: 約200-300MB（安全マージンあり）

### 本番環境（1 CPU以上、1GB RAM以上）

```bash
# 環境変数
GUNICORN_TIMEOUT=120
GUNICORN_GRACEFUL_TIMEOUT=30
GUNICORN_WORKERS=3          # (1 × 2) + 1 = 3
GUNICORN_WORKER_CLASS=sync

# Start Command
chmod +x start.sh && ./start.sh
```

### 高負荷環境（2 CPU以上、2GB RAM以上）

```bash
# 環境変数
GUNICORN_TIMEOUT=180
GUNICORN_GRACEFUL_TIMEOUT=60
GUNICORN_WORKERS=5          # (2 × 2) + 1 = 5
GUNICORN_WORKER_CLASS=sync

# Start Command
chmod +x start.sh && ./start.sh
```

### スケーリング戦略

**現在の構成（2インスタンス）**:
- インスタンス1: 2ワーカー
- インスタンス2: 2ワーカー
- **合計**: 4ワーカー

**負荷が高い場合**:
1. インスタンス数を増やす（3-4インスタンス）
2. 各インスタンスのワーカー数を増やす（メモリとCPUに余裕がある場合）
3. より大きなプランにアップグレード

**注意**: ワーカー数を増やしすぎると、メモリ不足やコンテキストスイッチのオーバーヘッドでパフォーマンスが低下する可能性があります。

## 同時アクセス数の見積もり

### 現在の環境での能力

**環境情報**:
- インスタンス数: 2
- ワーカー数: 2 per instance（合計4ワーカー）
- 平均処理時間: 約27.5秒（ログ分析より）

**同時アクセス数**:
- **ピーク時**: **3-4人**（ワーカー数に基づく）
- **通常時**: **2-3人**（安全マージンを考慮）

**処理能力**:
- **1時間あたり**: 約500リクエスト
- **1日あたり**: 約12,000リクエスト

**詳細**: `docs/CAPACITY_PLANNING.md` を参照してください。

### 20人同時アクセスへのスケーリング

20人程度の同時アクセスと10人程度の同時利用に対応するための詳細ガイド:
- **詳細**: `docs/SCALING_TO_20_USERS.md` を参照してください。

**推奨アプローチ**:
- **プラン**: Standard Plan（1 CPU, 1GB RAM）
- **インスタンス数**: 4
- **ワーカー数**: 5 per instance（合計20ワーカー）
- **ワーカークラス**: gevent（非同期処理）
- **期待値**: 同時アクセス数20-25人、1時間あたり約4,000リクエスト

## 関連ファイル

- `start.sh`: Gunicorn起動スクリプト
- `render.yaml`: Render.com設定ファイル
- `config/gunicorn_config.py`: Gunicorn設定ファイル（環境変数対応）
- `docs/CAPACITY_PLANNING.md`: キャパシティプランニングガイド
- `docs/GUNICORN_WORKERS_GUIDE.md`: Gunicorn Workers設定ガイド

## 参考リンク

- [Render.com Documentation](https://render.com/docs)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html)

