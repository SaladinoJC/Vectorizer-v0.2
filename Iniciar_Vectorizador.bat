@echo off
title Vectorizador de Logos para Tapetes Personalizados
echo =====================================================================
echo    INICIANDO VECTORIZADOR AUTOMATICO PARA TAPETES PERSONALIZADOS
echo =====================================================================
echo.
echo Abriendo aplicacion en tu navegador...
echo Si no se abre automaticamente, ingresa a: http://localhost:8501
echo.

cd /d "%~dp0"
python -m streamlit run app.py --server.headless=false

pause
