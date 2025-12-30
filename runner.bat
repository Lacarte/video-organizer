@echo off
cd /d "%~dp0"
echo Updating gallery...
python video_gallery.py

echo Starting local server...
echo Serving from parent directory to access videos...
cd ..
start "" "http://localhost:8000/gallery.html"
python -m http.server 8000
