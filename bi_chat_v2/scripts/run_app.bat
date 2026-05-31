@echo off
if not exist venv\Scripts\python.exe (
  echo Virtualenv not found. Run scripts\setup_env.ps1 first.
  exit /b 1
)
venv\Scripts\python.exe -m streamlit run app.py
