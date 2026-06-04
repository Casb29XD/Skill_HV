---
name: Skill_HV
description: Evaluación de candidatos y publicación en Notion vía MCP
install:
  - pip install -r requirements.txt
run:
  command: python main.py --candidates-dir data/candidates
entrypoint: main.py
env:
  - NOTION_API_KEY
  - NOTION_PAGE_ID
  - GEMINI_API_KEY
scripts:
  - run_agent.sh
  - run_agent.bat
examples:
  - bash: ./run_agent.sh
  - windows: .\run_agent.bat  [NOTION_PAGE_ID]
---

# Agent: Skill_HV

Este archivo contiene la metadata YAML necesaria para ejecutar el agente. La documentación de uso, requisitos y ejemplos de ejecución se han movido a `README.md`.

Para instrucciones completas y ejemplos, ver [README.md](README.md#L1-L200).
