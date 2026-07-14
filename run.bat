@echo off
echo Запуск Сириус.Аренда...
call venv\Scripts\activate
uvicorn app.main:app --reload
pause