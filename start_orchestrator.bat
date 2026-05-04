@echo off
cd /d "C:\Users\bahma\Downloads\base-juridique-app"
echo === ORCHESTRATEUR LEXAVO - VAGUE 1 ===
echo Moniteur belge (300K) + Conseil d'Etat async (250K) + ConsConst (8K)
echo.
echo NE FERMEZ PAS CETTE FENETRE - l'orchestrateur tourne ici
echo Ctrl+C pour arreter proprement
echo.
python orchestrator.py
pause
