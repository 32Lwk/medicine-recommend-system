@echo off
REM 画像生成自動化スクリプト
REM TikZファイルからPDFを生成し、PNGに変換

setlocal enabledelayedexpansion

REM MiKTeXのパス（環境に応じて変更）
set MIKTEX_PATH=C:\Users\yutok\AppData\Local\Programs\MiKTeX\miktex\bin\x64
set XELATEX=%MIKTEX_PATH%\xelatex.exe

REM 作業ディレクトリ
set FIGURES_DIR=%~dp0..\figures
set PHOTO_DIR=%~dp0..\photo

REM ImageMagickのパス（インストールされている場合）
set MAGICK_CONVERT=magick convert

echo ========================================
echo 画像生成スクリプト開始
echo ========================================
echo.

REM 各TikZファイルをコンパイル
for %%f in ("%FIGURES_DIR%\*.tex") do (
    echo コンパイル中: %%~nxf
    "%XELATEX%" -output-directory="%PHOTO_DIR%" -interaction=nonstopmode "%%f"
    if !errorlevel! equ 0 (
        echo [OK] PDF生成成功: %%~nf.pdf
    ) else (
        echo [ERROR] PDF生成失敗: %%~nf.tex
    )
    echo.
)

REM ImageMagickが利用可能な場合、PDFをPNGに変換
where magick >nul 2>&1
if %errorlevel% equ 0 (
    echo ========================================
    echo PDFをPNGに変換中...
    echo ========================================
    echo.
    
    for %%f in ("%PHOTO_DIR%\*.pdf") do (
        echo 変換中: %%~nxf
        %MAGICK_CONVERT% -density 300 "%%f" -quality 100 "%%~nf.png"
        if !errorlevel! equ 0 (
            echo [OK] PNG生成成功: %%~nf.png
        ) else (
            echo [ERROR] PNG生成失敗: %%~nf.pdf
        )
        echo.
    )
) else (
    echo ImageMagickが見つかりません。
    echo PDFファイルは生成されましたが、PNGへの変換はスキップされます。
    echo ImageMagickをインストールするか、手動で変換してください。
    echo.
)

echo ========================================
echo 画像生成スクリプト完了
echo ========================================

pause

