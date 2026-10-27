@echo off
cd /d "%~dp0.."
uv run python -m unittest discover -s tests
exit /b %errorlevel%
