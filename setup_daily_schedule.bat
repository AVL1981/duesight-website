@echo off
REM DueSight Daily GEO Harvest — Windows Task Scheduler Setup
REM Run this script AS ADMINISTRATOR to create the scheduled task.
REM
REM Creates a daily task at 03:00 that runs:
REM   1. SE Ranking backlink delta (30 API calls, ~2 min)
REM   2. GEO Monitor via Gemini (20 queries, ~5 min)

schtasks /create /tn "DueSight_Daily_GEO_Harvest" ^
  /tr "python C:\Users\arian\Promptwatch_clone\gego\scripts\daily_geo_harvest.py" ^
  /sc daily ^
  /st 03:00 ^
  /f

echo.
echo ================================================================
echo Task Scheduler setup complete!
echo Schedule: Daily at 03:00
echo Script:   daily_geo_harvest.py
echo Log:      gego\data\daily_harvest_log.txt
echo.
echo To test immediately, run:
echo   python C:\Users\arian\Promptwatch_clone\gego\scripts\daily_geo_harvest.py
echo ================================================================
pause
