✅ Full Instructions (Step-by-Step)
✅ 1. Sign in With the Correct Google Account
Go to https://console.cloud.google.com/.

In the top right, click your profile photo > "Sign out" or "Add another account".

Sign in using your work email address (the account you want the project under).

✅ 2. Create a New Project
After signing in with your work email, click the project dropdown (top bar).

Click "New Project".

Name your project (e.g., WorkSheetsAPI) and select an organization if prompted.

Click Create.

✅ 3. Enable Google Sheets API
From the left sidebar, go to APIs & Services > Library.

In the search bar, type "Google Sheets API".

Click it, then click Enable.

✅ 4. (Optional but Recommended) Enable Google Drive API
This allows for reading file metadata or sharing spreadsheets if needed.

In the same API Library, search for "Google Drive API".

Click it > Enable.

✅ 5. Configure OAuth Consent Screen
Go to APIs & Services > OAuth Consent Screen.

Choose External and click Create.

Fill out the form:

App Name: Anything like “Work API App”

Support Email: Your work email

Developer Contact Info: Your work email again

Click Save and Continue through the scopes for now (you'll add one later).

✅ 6. Add Required API Scopes
Click “Add or Remove Scopes”, then add:


Scope	Description
https://www.googleapis.com/auth/spreadsheets	Read and write access to Sheets
https://www.googleapis.com/auth/drive	(Optional) Access Drive files metadata
Click Update, then Save and Continue.

✅ 7. Add Test Users
Since the app is not published, it must be tested with authorized users:

Go to the Test Users section.

Click "Add Users", and add your work email (and anyone else who should have access).

Click Save and Continue.

✅ 8. Create OAuth Credentials
Go to APIs & Services > Credentials.

Click “+ CREATE CREDENTIALS” > “OAuth client ID”.

Choose Desktop App as the application type.

Give it a name like “Work Sheets Access”.

Click Create.

✅ 9. Download the Credentials File
After creating the credentials, you’ll see a button: Download JSON.

Download it and rename it if you like (e.g., work_credentials.json).

This file is used by your Python script to authenticate with Google.

✅ 10. Replace Old Credentials in Your Project
Delete the old credentials.json (from personal Gmail).

Move the new downloaded JSON into your project folder.

Make sure your Python code points to the correct file (e.g., credentials.json or whatever name you saved).