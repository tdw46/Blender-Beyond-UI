@echo off
cd /d "%~dp0.."
uv run ruff check beyond_ui tests tools examples
if errorlevel 1 exit /b %errorlevel%
uv run python -m compileall -q beyond_ui
if errorlevel 1 exit /b %errorlevel%
uv run python tools/check_custom_parity.py
exit /b %errorlevel%
