#!/bin/bash
# 翻訳APIベンチマーク実行スクリプト

echo "=========================================="
echo "翻訳APIベンチマーク実行"
echo "=========================================="
echo ""

# 環境変数の確認
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ 警告: OPENAI_API_KEYが設定されていません"
fi

if [ -z "$DEEPL_API_KEY" ]; then
    echo "⚠️ 警告: DEEPL_API_KEYが設定されていません（DeepLテストはスキップされます）"
fi

if [ -z "$GOOGLE_TRANSLATE_API_KEY" ] && [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "⚠️ 警告: Google翻訳APIキーが設定されていません（Google翻訳テストはスキップされます）"
fi

echo ""
echo "ベンチマークを開始します..."
echo ""

# Pythonスクリプトを実行
python3 benchmark_translation.py

echo ""
echo "=========================================="
echo "ベンチマーク完了"
echo "=========================================="
echo ""
echo "結果ファイル:"
ls -lh benchmark_*.json 2>/dev/null || echo "結果ファイルが見つかりません"

