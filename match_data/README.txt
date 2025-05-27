Job Scraper Project Setup and Running Instructions
============================================

1. Python Installation
---------------------
- Go to https://www.python.org/downloads/
- Click on "Download Python" (get the latest version)
- Run the downloaded installer
- IMPORTANT: Check the box that says "Add Python to PATH" during installation
- Click "Install Now"
- Wait for the installation to complete
- Click "Close" when finished

2. Verify Python Installation
---------------------------
- Open Command Prompt (cmd)
- Type: python --version
- You should see the Python version number
- If you see an error, Python is not properly installed or not in PATH

3. Project Setup
---------------
- Create a new folder for your project
- Copy these files into the folder:
  * job_scraper.py
  * requirements.txt
  * run.bat

4. Running the Project
--------------------
- Double-click the run.bat file
- The script will:
  * Create a virtual environment
  * Install required packages
  * Run the job scraper
- If you see any errors, make sure:
  * Python is properly installed
  * You have internet connection
  * All files are in the same folder

5. Troubleshooting
----------------
Common issues and solutions:
- "Python is not recognized": Reinstall Python with "Add to PATH" checked
- "pip is not recognized": Python installation may be incomplete
- "Module not found": Run pip install -r requirements.txt manually
- "Virtual environment error": Make sure you have permissions to create folders

6. Manual Setup (if run.bat fails)
--------------------------------
Open Command Prompt and run these commands:
1. python -m venv myenv
2. myenv\Scripts\activate
3. pip install -r requirements.txt
4. python job_scraper.py

For any issues, please check:
- Python version (should be 3.6 or higher)
- Internet connection
- File permissions
- Antivirus software (may block script execution)

7. Google Sheets Setup
--------------------
To set up Google Sheets integration:
🔹 Step 1: Create a Google Cloud Project
Go to Google Cloud Console.

Click the project dropdown (top bar) > New Project.

Name your project (e.g., "WebScrapingToSheets").

Click Create.

Select your new project from the top dropdown.

🔹 Step 2: Enable Google Sheets API
With your project selected, go to Navigation Menu > APIs & Services > Library.

Search for Google Sheets API, click it, then click Enable.

(Optional but recommended) Repeat and enable "Google Drive API" too, if you want to access or create spreadsheets programmatically.

🔹 Step 3: Set Up OAuth 2.0 Consent Screen
Go to APIs & Services > OAuth consent screen.

Choose External user type > Click Create.

Fill in:

App name (e.g., “Sheets Writer App”)

User support email (your email)

Developer contact info (your email)

Click Save and Continue (you can skip Scopes and Test Users for now — we'll come back).

🔹 Step 4: Add Scopes
On the OAuth consent screen, click Edit App.

Scroll to Scopes > Click Add or Remove Scopes.

Add these scopes:

.../auth/spreadsheets — For Google Sheets access

.../auth/drive — If you want to create/read spreadsheets from Drive

Click Update to save.

🔹 Step 5: Add Test Users
Still in the OAuth consent screen, go to Test Users tab.

Click Add Users.

Add your own Google email address (and others if needed).

Save.

🔹 Step 6: Create OAuth 2.0 Client ID Credentials
Go to APIs & Services > Credentials.

Click Create Credentials > OAuth client ID.

Choose Application type: Desktop app.

Name it (e.g., "Python Sheet Writer").

Click Create.

Download the JSON file by clicking the Download icon next to your new credential.