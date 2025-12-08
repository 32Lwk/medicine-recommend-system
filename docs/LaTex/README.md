# 論文LaTeXファイル

## 概要

「第26回 理工系学生科学技術論文コンクール」向けの論文LaTeXファイルです。

- **テーマ**: 科学技術と日本の将来
- **副題**: AIを活用したセルフメディケーション支援システムの開発
- **文字数**: 2,630字（制限3,200字以内）

## ファイル構成

- `paper.tex`: メインのLaTeXファイル（表紙+本文、platex用）
- `paper_xelatex.tex`: XeLaTeX/LuaLaTeX用のLaTeXファイル（日本語フォント問題を回避）
- `count_chars.py`: 文字数カウント用スクリプト
- `compile.bat`: 自動コンパイル用バッチファイル
- `FONT_FIX.md`: 日本語フォント問題の解決方法

## LaTeXのインストール

### Windows

LaTeXがインストールされていない場合、以下のいずれかをインストールしてください：

1. **MiKTeX**（推奨・軽量）
   - https://miktex.org/download からダウンロード
   - インストール後、コマンドプロンプトまたはPowerShellを再起動

2. **TeX Live**（完全版）
   - https://www.tug.org/texlive/windows.html からダウンロード
   - インストール時間が長い（数GB）

3. **オンラインLaTeXコンパイラ（推奨・簡単）**
   - **Overleaf**: https://www.overleaf.com/
     - アカウント作成後、`paper.tex`をアップロードしてコンパイル
     - 日本語対応、リアルタイムプレビュー
   - **LaTeX Base**: https://latexbase.com/
   - **ShareLaTeX**: https://www.sharelatex.com/

### macOS

```bash
# Homebrewを使用
brew install --cask mactex

# または軽量版
brew install --cask basictex
```

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install texlive-lang-japanese texlive-latex-extra

# または完全版
sudo apt-get install texlive-full
```

## コンパイル方法

### 方法1: バッチファイルを使用（最も簡単・推奨）

**PDF生成用バッチファイル**（日本語フォント問題を自動解決）:

```bash
# compile_pdf.batをダブルクリックするか、PowerShellで実行
.\compile_pdf.bat
```

このバッチファイルは、XeLaTeX（推奨）またはplatex+dvipdfmxのいずれかを選択できます。

**XeLaTeX専用バッチファイル**:

```bash
# compile_xelatex.batをダブルクリックするか、PowerShellで実行
.\compile_xelatex.bat
```

**旧バッチファイル**（platex用）:

```bash
# compile.batをダブルクリックするか、PowerShellで実行
.\compile.bat
```

### 方法2: XeLaTeXを使用（日本語フォント問題を回避・推奨）

`paper_xelatex.tex`を使用すると、日本語フォントの問題を回避できます。

```powershell
# 現在のディレクトリに移動
cd D:\Programing\medicine-recommend\docs\LaTex

# XeLaTeXでコンパイル（直接PDFを生成）
xelatex paper_xelatex.tex
xelatex paper_xelatex.tex  # 2回実行
```

**注意**: 初回実行時に`xelatex`パッケージのインストールを求められる場合があります。MiKTeX Consoleでインストールしてください。

### 方法3: PowerShellを再起動してから実行（platex + dvipdfmx）

MiKTeXをインストールした後、**PowerShellを完全に閉じて再起動**してください。

```powershell
# 現在のディレクトリに移動
cd D:\Programing\medicine-recommend\docs\LaTex

# 日本語LaTeXでコンパイル
platex paper.tex
platex paper.tex  # 2回実行
dvipdfmx paper.dvi
```

**注意**: 日本語フォント（`gbm`）が見つからないエラーが発生する場合は、MiKTeX Consoleで日本語フォントパッケージをインストールするか、方法2（XeLaTeX）を使用してください。

### 方法3: 手動でパスを設定

```powershell
# MiKTeXのパスを追加（インストール場所に応じて変更）
$env:Path += ";C:\Program Files\MiKTeX\miktex\bin\x64"

# コンパイル
platex paper.tex
platex paper.tex
dvipdfmx paper.dvi
```

### Windows (MiKTeX / TeX Live)

```bash
# PDFを生成（platex + dvipdfmx）
platex paper.tex
platex paper.tex  # 2回実行（相互参照のため）
dvipdfmx paper.dvi
```

または

```bash
# LuaLaTeXを使用（推奨）
lualatex paper.tex
lualatex paper.tex  # 2回実行
```

### macOS / Linux

```bash
# PDFを生成
platex paper.tex
platex paper.tex  # 2回実行
dvipdfmx paper.dvi
```

または

```bash
# LuaLaTeXを使用（推奨）
lualatex paper.tex
lualatex paper.tex  # 2回実行
```

### オンラインコンパイラ（LaTeX未インストールの場合）

1. **Overleafを使用する場合**:
   - https://www.overleaf.com/ にアクセス
   - アカウントを作成（無料）
   - 「New Project」→「Upload Project」で`paper.tex`をアップロード
   - 「Recompile」ボタンをクリックしてPDFを生成
   - 「Download」からPDFをダウンロード

2. **LaTeX Baseを使用する場合**:
   - https://latexbase.com/ にアクセス
   - `paper.tex`の内容をコピー＆ペースト
   - 「Compile」ボタンをクリック
   - PDFをダウンロード

## 文字数確認

```bash
python count_chars.py
```

## 注意事項

- 表紙は1枚目に配置されています
- 本文は2枚目から開始されます
- 図表を使用する場合は、本文外でA4縦1枚以内に収めてください
- 使用しているパッケージ:
  - `jarticle`: 日本語論文用クラス
  - `geometry`: ページレイアウト設定
  - `graphicx`: 図表挿入用
  - `amsmath`: 数式用
  - `listings`: コードブロック用（使用していませんが、将来の拡張用）

## 論文構成

1. **はじめに**: 背景と目的
2. **システムの概要**: システムの特徴
3. **技術的アプローチ**: ハイブリッド推奨システム、安全性機能、スコアリングアルゴリズム、セキュリティ機能
4. **実装と評価**: 実装技術と評価結果
5. **社会的意義と将来展望**: 社会的意義と今後の展望
6. **おわりに**: まとめと今後の課題

