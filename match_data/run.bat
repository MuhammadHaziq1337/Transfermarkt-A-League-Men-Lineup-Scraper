@echo off
echo Checking for virtual environment...

IF NOT EXIST "myenv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one...
    python -m venv myenv
)

echo Activating virtual environment...
call myenv\Scripts\activate.bat

echo Installing requirements...
pip install --upgrade pip
pip install -r requirements.txt

echo Running script...
python job_scraper.py

pause
