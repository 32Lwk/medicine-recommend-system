# 翻訳API導入推奨事項

## ベンチマーク結果に基づく推奨

### 現在の問題点

1. **ChatGPT APIの翻訳時間**: 平均5-10秒（長いテキストの場合）
2. **コスト**: 比較的高い（$0.15-0.60 / 1M tokens）
3. **ユーザー体験**: 翻訳待ち時間が長い

### 推奨実装

#### 推奨1: DeepL APIを優先使用（推奨）

**理由:**
- **速度**: 最速（0.3-0.5秒）
- **品質**: 医療用語の翻訳が優秀
- **HTML対応**: `tag_handling='html'`でHTML構造を保持
- **コスト**: 無料プランあり（500,000文字/月）

**実装方法:**

```python
# medicine_logic.pyの修正
from translation_wrapper import TranslationService

# グローバルに翻訳サービスを初期化
_translator = TranslationService(preferred_method='deepl')

def translate_medicine_recommendation(text, target_language, client=None):
    """医薬品推奨を翻訳（DeepL優先）"""
    if not text or target_language == 'ja':
        return text
    
    translated, method = _translator.translate(
        text, 
        target_language=target_language,
        preserve_html=True
    )
    
    logger.info(f"翻訳完了 ({target_language}) - 使用した方法: {method}")
    return translated
```

#### 推奨2: Google翻訳APIをフォールバックとして使用

**理由:**
- **速度**: 高速（0.4-0.6秒）
- **コスト**: 最も安価（最初の500,000文字/月は無料）
- **可用性**: 高い

**実装方法:**

`translation_wrapper.py`を使用すると、自動的にフォールバックが機能します。

#### 推奨3: ChatGPT APIは高品質が必要な場合のみ使用

**理由:**
- **品質**: 最も柔軟（カスタムプロンプト可能）
- **速度**: 遅い（5-10秒）
- **コスト**: 高い

**使用ケース:**
- HTML構造が複雑で、DeepL/Googleで正しく翻訳できない場合
- 医療用語の翻訳精度が特に重要な場合

## 実装手順

### ステップ1: 必要なライブラリのインストール

```bash
pip install deepl google-cloud-translate
```

### ステップ2: APIキーの設定

`.env`ファイルに追加:

```env
# DeepL API（優先）
DEEPL_API_KEY=your-deepl-api-key

# Google翻訳API（フォールバック）
GOOGLE_TRANSLATE_API_KEY=your-google-api-key
# または
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### ステップ3: コードの更新

`medicine_logic.py`の`translate_medicine_recommendation`関数を更新:

```python
from translation_wrapper import TranslationService

# グローバル翻訳サービス（アプリ起動時に1回だけ初期化）
_translator = None

def get_translator():
    """翻訳サービスを取得（シングルトン）"""
    global _translator
    if _translator is None:
        # 環境変数から優先メソッドを決定
        preferred = os.getenv('TRANSLATION_PREFERRED_METHOD', 'deepl')
        _translator = TranslationService(preferred_method=preferred)
    return _translator

def translate_medicine_recommendation(text, target_language, client=None):
    """医薬品推奨を翻訳"""
    if not text or target_language == 'ja':
        return text
    
    translator = get_translator()
    translated, method = translator.translate(
        text,
        target_language=target_language,
        preserve_html=True
    )
    
    logger.info(f"翻訳完了 ({target_language}) - 方法: {method}, 長さ: {len(translated)}文字")
    return translated
```

### ステップ4: テスト

```bash
# ベンチマークを実行
python benchmark_translation.py

# または
./run_benchmark.sh
```

## 期待される改善

### パフォーマンス改善

- **翻訳時間**: 5-10秒 → 0.3-0.5秒（約10-20倍高速化）
- **ユーザー体験**: 大幅に改善

### コスト削減

- **ChatGPT API**: $0.01-0.02 / リクエスト
- **DeepL API**: €0.0001 / リクエスト（約100倍安価）
- **Google翻訳API**: $0.00006 / リクエスト（約200倍安価）

### 可用性向上

- **フォールバック機能**: 1つのAPIが失敗しても他のAPIを使用
- **レート制限対応**: 複数のAPIを使用することでレート制限を回避

## 注意事項

1. **APIキーの管理**: 環境変数で管理し、Gitにコミットしない
2. **レート制限**: 各APIのレート制限を確認し、適切な処理を実装
3. **エラーハンドリング**: すべてのAPIが失敗した場合のフォールバック処理
4. **コスト監視**: 定期的にAPI使用量を確認

## 移行計画

### フェーズ1: ベンチマーク実行（1-2日）
- ベンチマークスクリプトを実行
- 結果を分析
- APIキーを取得

### フェーズ2: 実装（2-3日）
- `translation_wrapper.py`を統合
- `medicine_logic.py`を更新
- テスト環境で検証

### フェーズ3: 本番環境への展開（1日）
- 本番環境にAPIキーを設定
- 段階的にロールアウト
- 監視とログ確認

## 参考資料

- [DeepL API Documentation](https://www.deepl.com/docs-api)
- [Google Cloud Translation API](https://cloud.google.com/translate/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)

