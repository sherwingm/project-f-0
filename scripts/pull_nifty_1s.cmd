@echo off
rem Nightly copy of the server's NIFTY 1-second candles to this PC (index_data/pull_1s.py). Run by the Windows task
rem "fo NIFTY 1s pull" (16:00 daily, or at the next logon if the PC was off).
set INDEX_STORE=C:/Users/sherw/fo-index-data/data/index
set PYTHONPATH=C:\Users\sherw\project-f-0
set PYTHONIOENCODING=utf-8
cd /d C:\Users\sherw\project-f-0
C:\Users\sherw\.venvs\fo\Scripts\python.exe -W ignore -m index_data.pull_1s >> data\cache\index\pull_1s.log 2>&1
