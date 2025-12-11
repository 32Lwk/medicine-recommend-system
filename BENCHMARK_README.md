# 翻訳APIベンチマーク

## 概要

このベンチマークスクリプトは、以下の3つの翻訳方法のパフォーマンスを比較します：

1. **ChatGPT API** (現在の実装)
2. **Google翻訳API**
3. **DeepL API**

## セットアップ

### 1. 必要なライブラリのインストール

```bash
# 基本ライブラリ（既にインストール済み）
pip install openai python-dotenv

# Google翻訳API
pip install google-cloud-translate

# DeepL API
pip install deepl
```

### 2. APIキーの設定

`.env`ファイルに以下のAPIキーを追加してください：

```env
# 既存のキー
OPENAI_API_KEY=your-openai-api-key

# Google翻訳API（オプション）
# 方法1: APIキーを使用
GOOGLE_TRANSLATE_API_KEY=your-google-api-key

# 方法2: サービスアカウントキーを使用（推奨）
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# DeepL API（オプション）
DEEPL_API_KEY=your-deepl-api-key
```

### 3. APIキーの取得方法

#### Google翻訳API
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを作成または選択
3. 「APIとサービス」→「ライブラリ」から「Cloud Translation API」を有効化
4. 「認証情報」→「認証情報を作成」→「APIキー」を作成
   - または「サービスアカウント」を作成してJSONキーをダウンロード

#### DeepL API
1. [DeepL API](https://www.deepl.com/pro-api)にアクセス
2. アカウントを作成（無料プランあり）
3. APIキーを取得

## 実行方法

### 基本的な実行

```bash
python benchmark_translation.py
```

### 特定のサイズのテキストのみテスト

スクリプトを編集して、`main()`関数内の`text_size`を変更：

```python
results = benchmark.run_benchmark(
    text_size='medium',  # 'short', 'medium', 'long'
    target_language='en',
    iterations=3
)
```

## ベンチマーク結果の見方

### 出力例

```
============================================================
ベンチマーク結果サマリー
============================================================

方法             平均時間(秒)     最小時間(秒)     最大時間(秒)     成功率(%)   
---------------------------------------------------------------------------
ChatGPT          5.23            4.89            5.67            100.0      
Google翻訳       0.45            0.42            0.48            100.0      
DeepL            0.38            0.35            0.41            100.0      

最速の方法: DeepL (0.38秒)
```

### 結果ファイル

各サイズのテスト結果は`benchmark_<size>.json`として保存されます。

## コスト比較（参考）

### ChatGPT API (gpt-4o-mini)
- **料金**: $0.15 / 1M input tokens, $0.60 / 1M output tokens
- **推定コスト**: 中程度のテキスト（約3000文字）で約$0.01-0.02

### Google翻訳API
- **料金**: $20 / 1M文字（最初の500,000文字/月は無料）
- **推定コスト**: 中程度のテキスト（約3000文字）で約$0.00006

### DeepL API
- **料金**: 
  - 無料プラン: 500,000文字/月
  - Proプラン: €4.99/月（1M文字まで）
- **推定コスト**: 中程度のテキスト（約3000文字）で約€0.0001（Proプラン）

## 推奨事項

### 速度重視の場合
- **DeepL API** が最速（通常0.3-0.5秒）
- Google翻訳APIも高速（通常0.4-0.6秒）

### コスト重視の場合
- **Google翻訳API** が最も安価（最初の500,000文字/月は無料）
- DeepL APIも無料プランあり

### 品質重視の場合
- **ChatGPT API** が最も柔軟（HTML構造の保持、医療用語の正確性）
- DeepL APIも高品質（特に医療用語の翻訳が優秀）

### 推奨実装
1. **デフォルト**: DeepL API（速度と品質のバランスが良い）
2. **フォールバック**: Google翻訳API（DeepLが失敗した場合）
3. **高品質が必要な場合**: ChatGPT API（HTML構造の保持が重要な場合）

## 注意事項

- 各APIにはレート制限があります
- 大量のリクエストを送信する場合は、適切なレート制限処理を実装してください
- コストは使用量に応じて変動します。定期的に使用量を監視してください

