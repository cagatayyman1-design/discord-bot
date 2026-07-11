@echo off
title Discord Bot Loop
cd /d "%~dp0"
:loop
echo Bot baslatiliyor...
python bot.py
echo Bot coktu, 5 saniye icinde tekrar baslatiliyor...
timeout /t 5 >nul
goto loop
