@echo off
echo ============================================================
echo  LegalTech Scraper Web - Push to GitHub
echo ============================================================
echo.
echo STEP 1: Go to https://github.com/new and create a repo named:
echo         legaltech-scraper-web
echo         (under NetDocuments org, set to Public, NO readme)
echo.
echo Press any key once the repo is created...
pause > nul

cd /d %~dp0

git init
git add .
git commit -m "Initial commit - LegalTech News Scraper web edition"
git branch -M main
git remote add origin https://github.com/NetDocuments/legaltech-scraper-web.git
git push -u origin main

echo.
echo Done! Repo is live at:
echo https://github.com/NetDocuments/legaltech-scraper-web
echo.
pause
