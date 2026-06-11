#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDFファイルをPNG画像に変換するスクリプト
"""
import fitz  # PyMuPDF
import os
import sys
from pathlib import Path

# Windows環境でのUnicode出力をサポート
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def pdf_to_png(pdf_path, output_dir=None, dpi=300):
    """
    PDFファイルをPNG画像に変換
    
    Args:
        pdf_path: PDFファイルのパス
        output_dir: 出力ディレクトリ（Noneの場合はPDFと同じディレクトリ）
        dpi: 解像度（デフォルト300）
    
    Returns:
        生成されたPNGファイルのパス
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")
    
    if output_dir is None:
        output_dir = pdf_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # PDFを開く
    pdf_document = fitz.open(pdf_path)
    
    png_files = []
    
    # 各ページをPNGに変換
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        
        # スケールファクターを計算（DPIに基づく）
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        # ページを画像に変換
        pix = page.get_pixmap(matrix=mat)
        
        # 出力ファイル名を生成
        if len(pdf_document) == 1:
            # 1ページのみの場合はページ番号を付けない
            output_filename = pdf_path.stem + ".png"
        else:
            # 複数ページの場合はページ番号を付ける
            output_filename = f"{pdf_path.stem}_page_{page_num + 1}.png"
        
        output_path = output_dir / output_filename
        
        # PNGとして保存
        pix.save(str(output_path))
        png_files.append(output_path)
        print(f"変換完了: {output_path}")
    
    pdf_document.close()
    return png_files

if __name__ == "__main__":
    # 変換するPDFファイルのリスト
    pdf_files = [
        "dataflow_detailed.pdf",
        "defense_layers.pdf",
        "flowchart_detailed.pdf",
        "sequence_detailed.pdf"
    ]
    
    # スクリプトのディレクトリを取得
    script_dir = Path(__file__).parent
    
    # 各PDFファイルを変換
    for pdf_file in pdf_files:
        pdf_path = script_dir / pdf_file
        if pdf_path.exists():
            try:
                print(f"\n変換中: {pdf_file}")
                png_files = pdf_to_png(pdf_path, dpi=300)
                print(f"[OK] {pdf_file} の変換が完了しました")
            except Exception as e:
                print(f"[ERROR] {pdf_file} の変換に失敗しました: {e}")
        else:
            print(f"[ERROR] ファイルが見つかりません: {pdf_file}")
    
    print("\nすべての変換が完了しました。")
