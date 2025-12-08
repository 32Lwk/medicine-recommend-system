# カスタムフォント設定ガイド

## 現在の設定

`paper_xelatex.tex`では、以下のカスタムフォントを使用しています：

### 日本語フォント: BIZ UDP Gothic
- **通常**: `BIZUDPGothic-Regular.ttf`
- **太字**: `BIZUDPGothic-Bold.ttf`
- **パス**: `C:/Users/yutok/Downloads/BIZ_UDPGothic/`

### 欧文フォント: Times New Roman
- **ファイル**: `times-new-roman.ttf`
- **パス**: `C:/Users/yutok/Downloads/times-new-roman_freefontdownload_org/`

## 設定内容

```latex
% 日本語フォント: BIZ UDP Gothic
\setCJKmainfont[
    BoldFont=BIZUDPGothic-Bold.ttf,
    Path=C:/Users/yutok/Downloads/BIZ_UDPGothic/
]{BIZUDPGothic-Regular.ttf}

% 欧文フォント: Times New Roman
\setmainfont[
    Path=C:/Users/yutok/Downloads/times-new-roman_freefontdownload_org/
]{times-new-roman.ttf}
```

## フォントファイルの場所

### 現在の設定
- 日本語フォント: `C:\Users\yutok\Downloads\BIZ_UDPGothic\`
- 欧文フォント: `C:\Users\yutok\Downloads\times-new-roman_freefontdownload_org\`

### フォントファイルを移動する場合

フォントファイルを別の場所に移動した場合は、`paper_xelatex.tex`の`Path`を更新してください。

例：
```latex
% フォントを C:\Fonts\ に移動した場合
\setCJKmainfont[
    BoldFont=BIZUDPGothic-Bold.ttf,
    Path=C:/Fonts/BIZ_UDPGothic/
]{BIZUDPGothic-Regular.ttf}
```

## コンパイル方法

```powershell
cd D:\Programing\medicine-recommend\docs\LaTex
xelatex paper_xelatex.tex
xelatex paper_xelatex.tex  # 2回実行
```

## トラブルシューティング

### フォントが見つからないエラー

```
LaTeX Font Warning: Font "BIZUDPGothic-Regular.ttf" not found.
```

**解決方法:**
1. フォントファイルのパスが正しいか確認
2. パス区切り文字は `/` を使用（Windowsでも `/` が正しい）
3. フォントファイルが存在するか確認

### パスの確認方法

```powershell
# 日本語フォントの確認
Test-Path "C:\Users\yutok\Downloads\BIZ_UDPGothic\BIZUDPGothic-Regular.ttf"

# 欧文フォントの確認
Test-Path "C:\Users\yutok\Downloads\times-new-roman_freefontdownload_org\times-new-roman.ttf"
```

### フォントの警告

```
LaTeX Font Warning: Some font shapes were not available, defaults substituted.
```

この警告は無視して問題ありません。PDFは正常に生成されます。

## フォントの変更

### 別のフォントを使用する場合

1. フォントファイルをダウンロードまたはインストール
2. `paper_xelatex.tex`のフォント設定を編集
3. 再コンパイル

### システムフォントに戻す場合

```latex
% 日本語フォントをシステムフォントに戻す
\setCJKmainfont{MS Mincho}

% 欧文フォントをシステムフォントに戻す
\setmainfont{Times New Roman}
```

## まとめ

- **日本語**: BIZ UDP Gothic（カスタムフォント）
- **欧文**: Times New Roman（カスタムフォント）
- **設定ファイル**: `paper_xelatex.tex`の7-16行目
- **コンパイル**: XeLaTeXを使用

