@echo off
REM 日本語フォント問題を解決してPDFを生成するバッチファイル

echo LaTeX PDF生成を開始します...

REM MiKTeXの一般的なインストールパスを確認
set MIKTEX_BIN=
if exist "%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\platex.exe" (
    set MIKTEX_BIN=%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64
) else if exist "C:\Program Files\MiKTeX\miktex\bin\x64\platex.exe" (
    set MIKTEX_BIN=C:\Program Files\MiKTeX\miktex\bin\x64
) else if exist "C:\Program Files (x86)\MiKTeX\miktex\bin\x64\platex.exe" (
    set MIKTEX_BIN=C:\Program Files (x86)\MiKTeX\miktex\bin\x64
) else (
    echo MiKTeXが見つかりません。
    pause
    exit /b 1
)

echo MiKTeXのパス: %MIKTEX_BIN%

REM パスを追加
set PATH=%MIKTEX_BIN%;%PATH%

echo.
echo 方法1: XeLaTeXを使用（推奨・日本語フォント問題を回避）
echo 方法2: platex + dvipdfmx（日本語フォントパッケージが必要）
echo.
set /p method="使用する方法を選択 (1 or 2): "

if "%method%"=="1" (
    echo.
    echo XeLaTeXでコンパイルします...
    if not exist "%MIKTEX_BIN%\xelatex.exe" (
        echo エラー: xelatexが見つかりません。
        echo MiKTeX Consoleでxelatexパッケージをインストールしてください。
        pause
        exit /b 1
    )
    
    echo 1回目のコンパイル...
    "%MIKTEX_BIN%\xelatex.exe" paper_xelatex.tex
    if %ERRORLEVEL% NEQ 0 (
        echo エラーが発生しました。
        pause
        exit /b 1
    )
    
    echo 2回目のコンパイル...
    "%MIKTEX_BIN%\xelatex.exe" paper_xelatex.tex
    if %ERRORLEVEL% NEQ 0 (
        echo エラーが発生しました。
        pause
        exit /b 1
    )
    
    if exist "paper_xelatex.pdf" (
        echo.
        echo ✓ PDFが生成されました: paper_xelatex.pdf
        echo ファイル名をpaper.pdfにリネームしますか？ (Y/N)
        set /p rename="> "
        if /i "%rename%"=="Y" (
            copy /Y paper_xelatex.pdf paper.pdf
            echo paper.pdfにリネームしました。
        )
        start paper_xelatex.pdf
    ) else (
        echo エラー: PDFファイルが生成されませんでした。
    )
    
) else if "%method%"=="2" (
    echo.
    echo platex + dvipdfmxでコンパイルします...
    
    echo 1回目のplatex...
    "%MIKTEX_BIN%\platex.exe" paper.tex
    if %ERRORLEVEL% NEQ 0 (
        echo エラーが発生しました。
        pause
        exit /b 1
    )
    
    echo 2回目のplatex...
    "%MIKTEX_BIN%\platex.exe" paper.tex
    if %ERRORLEVEL% NEQ 0 (
        echo エラーが発生しました。
        pause
        exit /b 1
    )
    
    if not exist "%MIKTEX_BIN%\dvipdfmx.exe" (
        echo エラー: dvipdfmxが見つかりません。
        pause
        exit /b 1
    )
    
    echo dvipdfmxでPDFに変換...
    "%MIKTEX_BIN%\dvipdfmx.exe" paper.dvi
    
    if exist "paper.pdf" (
        echo.
        echo ✓ PDFが生成されました: paper.pdf
        start paper.pdf
    ) else (
        echo.
        echo エラー: PDFファイルが生成されませんでした。
        echo 日本語フォントの問題が発生している可能性があります。
        echo MiKTeX Consoleで以下のパッケージをインストールしてください:
        echo   - japanese-otf または japanese-otf-uptex
        echo   - pxjahyper
        echo.
        echo または、方法1（XeLaTeX）を使用してください。
    )
) else (
    echo 無効な選択です。
)

pause

