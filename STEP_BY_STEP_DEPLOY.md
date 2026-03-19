# PredictMaint Pro — Complete Deployment Guide
# Follow these steps exactly — from zero to live website!

═══════════════════════════════════════════════════════════════
STEP 1 — INSTALL GIT ON YOUR LAPTOP
═══════════════════════════════════════════════════════════════

1. Go to: https://git-scm.com/downloads
2. Click "Download for Windows"
3. Run the installer → click Next on everything → Finish
4. To verify: open Command Prompt → type:  git --version
   You should see something like: git version 2.43.0

═══════════════════════════════════════════════════════════════
STEP 2 — CREATE A GITHUB ACCOUNT
═══════════════════════════════════════════════════════════════

1. Go to: https://github.com
2. Click "Sign up"
3. Enter your email, create a password, choose a username
4. Verify your email (check inbox for GitHub email)
5. Choose the FREE plan

═══════════════════════════════════════════════════════════════
STEP 3 — EXTRACT YOUR PROJECT
═══════════════════════════════════════════════════════════════

1. Find the file: predictive_maintenance_v7_DEPLOY.zip
2. Right-click → Extract All → choose a folder (e.g. C:\Projects\)
3. You will get a folder called: pm_v7
4. Inside pm_v7 you should see: app.py, models.py, templates/, etc.

═══════════════════════════════════════════════════════════════
STEP 4 — OPEN COMMAND PROMPT
═══════════════════════════════════════════════════════════════

Press Win + R on keyboard → type cmd → press Enter
A black window opens. This is Command Prompt.

═══════════════════════════════════════════════════════════════
STEP 5 — NAVIGATE TO YOUR PROJECT FOLDER
═══════════════════════════════════════════════════════════════

Type this (change the path to wherever you extracted):

  cd C:\Projects\pm_v7

Press Enter. The prompt should now show C:\Projects\pm_v7>

To verify you are in the right folder, type:
  dir

You should see app.py, models.py, templates, etc. listed.

═══════════════════════════════════════════════════════════════
STEP 6 — SET UP GIT (ONE TIME ONLY — EVER)
═══════════════════════════════════════════════════════════════

Type these two commands (replace with YOUR name and email):

  git config --global user.name "Vinay"
  git config --global user.email "your@gmail.com"

Press Enter after each one. No output = success.

═══════════════════════════════════════════════════════════════
STEP 7 — INITIALIZE GIT IN YOUR PROJECT
═══════════════════════════════════════════════════════════════

Type:
  git init

You should see: Initialized empty Git repository in C:/Projects/pm_v7/.git/

═══════════════════════════════════════════════════════════════
STEP 8 — ADD ALL FILES
═══════════════════════════════════════════════════════════════

Type:
  git add .

(The dot means "add everything". No output = success.)

═══════════════════════════════════════════════════════════════
STEP 9 — SAVE A SNAPSHOT (COMMIT)
═══════════════════════════════════════════════════════════════

Type:
  git commit -m "PredictMaint Pro v7 Hackathon"

You should see a list of files being committed. That is success!

═══════════════════════════════════════════════════════════════
STEP 10 — CREATE REPO ON GITHUB WEBSITE
═══════════════════════════════════════════════════════════════

1. Go to: https://github.com
2. Click the + button (top right corner)
3. Click "New repository"
4. Repository name: predictmaint-pro
5. Description: Industrial Predictive Maintenance System
6. Select: Public (so Render can access it free)
7. DO NOT tick "Add README" or anything else
8. Click the green "Create repository" button

═══════════════════════════════════════════════════════════════
STEP 11 — CONNECT AND UPLOAD TO GITHUB
═══════════════════════════════════════════════════════════════

GitHub will show you a page with commands.
Copy the commands under "…or push an existing repository from the command line"

They will look like this (with YOUR username):
  git remote add origin https://github.com/YOURNAME/predictmaint-pro.git
  git branch -M main
  git push -u origin main

Type/paste each one in Command Prompt and press Enter.

When it asks for username → type your GitHub username
When it asks for password → use a Personal Access Token (see below)

HOW TO GET A PERSONAL ACCESS TOKEN:
1. GitHub → click your profile picture (top right) → Settings
2. Scroll down → click "Developer settings" (bottom left)
3. Personal access tokens → Tokens (classic) → Generate new token (classic)
4. Note: "Deploy token", Expiration: 90 days
5. Tick the box next to "repo"
6. Click "Generate token"
7. COPY the token immediately (you only see it once!)
8. Paste this token as your password in Command Prompt

After push, refresh github.com/YOURNAME/predictmaint-pro
You should see all your files! ✅

═══════════════════════════════════════════════════════════════
STEP 12 — DEPLOY ON RENDER.COM
═══════════════════════════════════════════════════════════════

1. Go to: https://render.com
2. Click "Get Started for Free"
3. Sign up with your GitHub account (easiest)
4. Click "New +" → "Web Service"
5. Click "Connect" next to your predictmaint-pro repo
6. Fill in these settings:

   Name:          predictmaint-pro
   Region:        Singapore (closest to India)
   Branch:        main
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn wsgi:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT

7. Select: Free plan
8. Click "Create Web Service"

═══════════════════════════════════════════════════════════════
STEP 13 — ADD ENVIRONMENT VARIABLES ON RENDER
═══════════════════════════════════════════════════════════════

After creating the service:
1. Click "Environment" in the left menu
2. Click "Add Environment Variable" for each one below:

   Key: SECRET_KEY
   Value: PredictMaintPro2024SecureKey!

   Key: RENDER
   Value: true

   Key: MAIL_USERNAME
   Value: (your Gmail address, e.g. yourname@gmail.com)

   Key: MAIL_PASSWORD
   Value: (your Gmail App Password — see STEP 14 below)

   Key: GEMINI_API_KEY
   Value: (from aistudio.google.com — see STEP 15 below)

   Key: TELEGRAM_BOT_TOKEN
   Value: (optional — from @BotFather on Telegram)

   Key: TELEGRAM_CHAT_ID
   Value: (optional — your Telegram chat ID)

3. Click "Save Changes"
4. Render will automatically redeploy

═══════════════════════════════════════════════════════════════
STEP 14 — GET GMAIL APP PASSWORD (FOR OTP TO WORK)
═══════════════════════════════════════════════════════════════

Your regular Gmail password does NOT work. You need an App Password.

1. Go to: https://myaccount.google.com
2. Click "Security" in the left menu
3. Under "How you sign in to Google", click "2-Step Verification"
4. Enable it if not already on
5. Scroll down → "App passwords"
6. Select app: Mail | Select device: Windows Computer
7. Click "Generate"
8. Copy the 16-character password (like: abcd efgh ijkl mnop)
9. Use this (without spaces) as MAIL_PASSWORD on Render

═══════════════════════════════════════════════════════════════
STEP 15 — GET GEMINI API KEY (FOR AI CHATBOT)
═══════════════════════════════════════════════════════════════

1. Go to: https://aistudio.google.com
2. Sign in with your Google account
3. Click "Get API Key" → "Create API Key"
4. Copy the key (starts with AIzaSy...)
5. Add it as GEMINI_API_KEY on Render

(Free tier: 60 requests/minute — more than enough)

═══════════════════════════════════════════════════════════════
STEP 16 — ADD FREE POSTGRESQL DATABASE (OPTIONAL BUT RECOMMENDED)
═══════════════════════════════════════════════════════════════

For a real production database instead of SQLite:

1. In Render dashboard → click "New +" → "PostgreSQL"
2. Name: predictmaint-db
3. Select: Free plan
4. Click "Create Database"
5. In the database page → copy "Internal Database URL"
6. Go back to your Web Service → Environment
7. Add new variable:
   Key: DATABASE_URL
   Value: (paste the Internal Database URL)
8. Save → Render redeploys with PostgreSQL automatically!

═══════════════════════════════════════════════════════════════
STEP 17 — YOUR WEBSITE IS LIVE! 🎉
═══════════════════════════════════════════════════════════════

After deployment (takes 3-5 minutes first time):
Your website URL: https://predictmaint-pro.onrender.com

Login credentials:
  Username: admin
  Password: Admin@123
  Then: enter OTP from your Gmail inbox

IMPORTANT: First visit after the free plan sleeps takes 30-60 seconds to wake up.
After that it runs normally.

═══════════════════════════════════════════════════════════════
STEP 18 — UPDATING YOUR WEBSITE (FUTURE CHANGES)
═══════════════════════════════════════════════════════════════

Whenever you change code and want to update the live site:

  git add .
  git commit -m "describe your change here"
  git push

Render auto-detects the push and redeploys in ~2 minutes. Done!

═══════════════════════════════════════════════════════════════
TROUBLESHOOTING COMMON ERRORS
═══════════════════════════════════════════════════════════════

❌ "git is not recognized"
   → Git not installed properly. Restart Command Prompt and try again.
   → Or reinstall Git from git-scm.com

❌ "Authentication failed" when pushing
   → Use Personal Access Token (not your GitHub password)
   → See STEP 11 for how to get the token

❌ "Application error" on Render
   → Check Render logs (click "Logs" in left menu)
   → Most common: missing environment variable
   → Make sure SECRET_KEY and RENDER=true are set

❌ OTP not arriving in Gmail
   → Check MAIL_USERNAME is correct
   → Make sure MAIL_PASSWORD is the App Password (not Gmail password)
   → Check spam folder

❌ App slow to start
   → Free Render plan sleeps after 15 minutes
   → First request after sleep takes 30-60 seconds — normal!
   → Upgrade to paid plan ($7/month) for always-on

❌ ChatBot says "quota exceeded"
   → Gemini free quota is 60 requests/minute
   → Wait 1 minute and try again
   → The rule-based fallback still works perfectly without Gemini

═══════════════════════════════════════════════════════════════
ALTERNATIVE PLATFORMS
═══════════════════════════════════════════════════════════════

If Render does not work, try these (all free):

RAILWAY.APP:
  1. Go to railway.app
  2. New Project → Deploy from GitHub repo
  3. Add same environment variables
  4. railway.toml is already in your project!
  URL: https://predictmaint-pro.up.railway.app

PYTHONANYWHERE.COM:
  1. Go to pythonanywhere.com → Free account
  2. Dashboard → Bash console
  3. git clone https://github.com/YOURNAME/predictmaint-pro.git
  4. pip3 install --user -r requirements.txt
  5. Web tab → Add new web app → Flask → Python 3.11
  6. Set source: /home/YOURNAME/predictmaint-pro/wsgi.py
  URL: https://YOURNAME.pythonanywhere.com

═══════════════════════════════════════════════════════════════
QUICK REFERENCE — ALL COMMANDS IN ORDER
═══════════════════════════════════════════════════════════════

cd C:\Projects\pm_v7
git config --global user.name "Your Name"
git config --global user.email "your@gmail.com"
git init
git add .
git commit -m "PredictMaint Pro v7"
git remote add origin https://github.com/YOURNAME/predictmaint-pro.git
git branch -M main
git push -u origin main

Then go to render.com and follow Steps 12-16 above.
