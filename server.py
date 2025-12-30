import shutil
import http.server
import socketserver
import os
import json
import urllib.parse
from pathlib import Path

# Config
PORT = 8001
DIRECTORY = "."  # Current directory (should be parent folder containing videos)

# Extensions to look for
VIDEO_EXT = {'.mp4', '.webm', '.avi', '.mov', '.mkv'}
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MEDIA_EXT = VIDEO_EXT | IMAGE_EXT

class GalleryRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        """Handle JSON API requests."""
        if self.path == '/api/list':
            self.handle_list()
        elif self.path == '/api/move':
            self.handle_move()
        elif self.path == '/api/delete':
            self.handle_delete()
        else:
            self.send_error(404, "API endpoint not found")

    def handle_list(self):
        """Scan directory for media and folders."""
        try:
            root = Path(DIRECTORY)
            
            # Scan files
            files = []
            for item in root.iterdir():
                if item.is_file() and item.suffix.lower() in MEDIA_EXT:
                    # Ignore hidden files
                    if item.name.startswith('.'):
                        continue
                    files.append(item.name)
            
            # Sort files naturally-ish (by name)
            files.sort()

            # Scan directories for shortcuts
            dirs = []
            known_shortcuts = set()
            
            for item in root.iterdir():
                if item.is_dir():
                    name = item.name
                    # Ignore hidden dirs or specific system dirs if needed
                    if name.startswith('.') or name in {'trash', 'deleteVideos', '.git'}:
                        continue
                        
                    # Assign shortcut
                    shortcut = None
                    # Try first letter
                    first = name[0].upper()
                    if first.isalpha() and first not in known_shortcuts:
                        shortcut = first
                    
                    # If first letter taken, just leave it blank (or could be smarter, but spec says "A unique underlined letter")
                    # For simplicity, if collision, we might skip shortcut or simple first-come-first-serve
                    if shortcut:
                        known_shortcuts.add(shortcut)
                    
                    dirs.append({
                        "name": name,
                        "shortcut": shortcut
                    })
            
            # Sort directories by name
            dirs.sort(key=lambda x: x['name'])

            self.send_json({"files": files, "dirs": dirs})

        except Exception as e:
            self.send_error(500, str(e))

    def handle_move(self):
        """Move file to a subdirectory."""
        data = self.read_json()
        if not data: return

        filename = data.get('filename')
        target_dir = data.get('target')

        if not filename or not target_dir:
            self.send_error(400, "Missing filename or target")
            return

        if not self.validate_filename(filename) or not self.validate_filename(target_dir):
            return

        try:
            src = Path(DIRECTORY) / filename
            dst_dir = Path(DIRECTORY) / target_dir
            dst = dst_dir / filename

            if not src.exists():
                self.send_error(404, "File not found")
                return
            
            if not dst_dir.exists():
                dst_dir.mkdir(exist_ok=True) # Should exist based on list, but safety

            shutil.move(str(src), str(dst))
            print(f"📂 Moved {filename} to {target_dir}")
            self.send_json({"success": True})
        except Exception as e:
            print(f"❌ Error moving {filename}: {e}")
            self.send_error(500, str(e))

    def handle_delete(self):
        """Move file to trash."""
        data = self.read_json()
        if not data: return
        
        filename = data.get('filename')
        if not filename:
            self.send_error(400, "Missing filename")
            return
            
        if not self.validate_filename(filename):
            return

        try:
            src = Path(DIRECTORY) / filename
            trash_dir = Path(DIRECTORY) / "trash"
            dst = trash_dir / filename

            if not src.exists():
                self.send_error(404, "File not found")
                return

            trash_dir.mkdir(exist_ok=True)
            shutil.move(str(src), str(dst))
            print(f"🗑️ Moved to trash: {filename}")
            self.send_json({"success": True})
        except Exception as e:
            print(f"❌ Error moving {filename}: {e}")
            self.send_error(500, str(e))

    def read_json(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return None

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def validate_filename(self, name):
        if '/' in name or '\\' in name or '..' in name:
            self.send_error(403, "Invalid filename")
            return False
        return True

    def do_GET(self):
        """Serve static files, mapping app route to the correct file."""
        if self.path == '/' or self.path == '/video-organizer.html':
            # Serve the HTML file from the script directory
            # We are running from parent, so file is in video-organizer/video-organizer.html
            html_path = Path("video-organizer") / "video-organizer.html"
            if html_path.exists():
                try:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    with open(html_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
                except Exception as e:
                    print(f"Error serving HTML: {e}")
            else:
                 # Fallback if structure is different
                 pass

        try:
            super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            pass

class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    def service_actions(self):
        pass
    
    def handle_error(self, request, client_address):
        pass

if __name__ == "__main__":
    print(f"🚀 Video Organizer Server on port {PORT}")
    print(f"📂 Serving directory: {os.getcwd()}")
    with ThreadedHTTPServer(("", PORT), GalleryRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped.")
