# 今後のコンパイル方法

## 推奨方法：XeLaTeXを使用

`paper_xelatex.tex`を使用すると、日本語フォントの問題を回避できます。

### 方法1: コマンドラインで実行（推奨）

```powershell
cd D:\Programing\medicine-recommend\docs\LaTex

# 1回目のコンパイル
xelatex paper_xelatex.tex

# 2回目のコンパイル（相互参照のため）
xelatex paper_xelatex.tex
```

**注意**: `xelatex`コマンドが認識されない場合は、フルパスを使用：
```powershell
$miktexPath = "C:\Users\yutok\AppData\Local\Programs\MiKTeX\miktex\bin\x64"
& "$miktexPath\xelatex.exe" paper_xelatex.tex
& "$miktexPath\xelatex.exe" paper_xelatex.tex
```

### 方法2: バッチファイルを使用

`compile_pdf.bat`をダブルクリックし、**方法1（XeLaTeX）**を選択してください。

または、`compile_xelatex.bat`をダブルクリックしてください。

### 方法3: オンラインコンパイラ（Overleaf）

1. https://www.overleaf.com/ にアクセス
2. `paper_xelatex.tex`をアップロード
3. 「Recompile」をクリック
4. PDFをダウンロード

## ファイルの使い分け

- **`paper.tex`**: `platex` + `dvipdfmx`用（日本語フォントパッケージが必要）
- **`paper_xelatex.tex`**: XeLaTeX用（推奨・日本語フォント問題を回避）

## コンパイル後のファイル

- **`paper_xelatex.pdf`**: 生成されたPDFファイル（提出用）
- **`paper_xelatex.aux`**: 相互参照用の補助ファイル（自動生成）
- **`paper_xelatex.log`**: コンパイルログ（エラー確認用）

## トラブルシューティング

### XeLaTeXが見つからない場合

```powershell
# MiKTeX Consoleでxelatexパッケージをインストール
# または、フルパスを使用
$miktexPath = "C:\Users\yutok\AppData\Local\Programs\MiKTeX\miktex\bin\x64"
& "$miktexPath\xelatex.exe" paper_xelatex.tex
```

### フォントの警告が出る場合

「Some font shapes were not available」という警告は無視して問題ありません。PDFは正常に生成されます。

### 内容を修正した場合

1. `paper_xelatex.tex`を編集
2. 上記のコンパイル方法で再コンパイル
3. `paper_xelatex.pdf`が更新されます

