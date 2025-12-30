# Video Gallery 🎬

A high-performance, local HTML gallery for browsing and managing large collections of video files (MP4, WebM).

## Features

-   **🚀 High Performance**: Capable of handling libraries with 35,000+ videos using efficient client-side pagination.
-   **⚡ Lazy Loading**: Videos are loaded only when they scroll into view, keeping memory usage low.
-   **🗑️ Soft Delete**: Directly delete videos from the gallery interface. Deleted files are moved to a `deleteVideos` "trash" folder for safety.
-   **📅 Recent Sort**: Videos are automatically sorted by modification date, showing your newest generations first.
-   **🔗 Midjourney Integration**: Click any video card to open its corresponding job on Midjourney.com.

## How to Use

1.  Ensure you have **Python 3** installed.
2.  Navigate to the `display-files` folder.
3.  Double-click **`runner.bat`**.
    -   This script will scan your parent folder for videos.
    -   It will generate/update the `gallery.html` file.
    -   It will launch a local web server handling concurrent connections.
    -   Your browser will automatically open the gallery.

> **Note**: If you add new videos or move files, run `runner.bat` again to update the gallery index.

## Directory Structure

-   `runner.bat`: The entry point script to start the gallery.
-   `video_gallery.py`: Python script that scans directories and generates the HTML.
-   `server.py`: A multi-threaded HTTP server that handles video streaming and file operations (deletion).
-   `../`: The parent directory is expected to contain your video files.

## Troubleshooting

-   **"Site can't be reached"**: Ensure the black server window is open. If it closed, run `runner.bat` again.
-   **Delete not working**: Ensure you are running the gallery via `runner.bat` (localhost) and not just opening the HTML file directly.
