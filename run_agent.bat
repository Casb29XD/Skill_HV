@echo off
echo Installing Python dependencies...
pip install -r requirements.txt
echo Running Skill_HV...
if "%1"=="" (
  python main.py --candidates-dir data/candidates
) else (
  python main.py --candidates-dir data/candidates --notion-page-id %1
)
pause
