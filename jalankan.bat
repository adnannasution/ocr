@echo off
title Dokumen Ekstraksi AI — ABBYY OCR
color 0A
echo.
echo  ============================================
echo   Dokumen Ekstraksi AI — ABBYY OCR
echo  ============================================
echo.
echo  Menginstall dependency...
pip install -r requirements.txt --quiet
echo.
echo  Menjalankan server...
echo  Browser akan terbuka otomatis.
echo.
python app.py
pause
