import shutil
import http.server
import socketserver
import os
import json
import urllib.parse
import subprocess
import hashlib
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
                    if item.name.startswith('.'): continue
                    files.append(item.name)
            
            files.sort()

            # Scan directories
            dirs = []
            raw_dirs = []
            
            for item in root.iterdir():
                if item.is_dir():
                    name = item.name
                    if name.startswith('.') or name in {'trash', 'deleteVideos', '.git'}:
                        continue
                    raw_dirs.append(name)
            
            # Sort directories by name
            raw_dirs.sort()

            # Assign shortcuts
            import random
            import string
            
            used_shortcuts = set()
            assignments = {} # name -> shortcut
            
            # 1. Preferred: First Letter
            unassigned = []
            for name in raw_dirs:
                first = name[0].upper()
                if first.isalpha() and first not in used_shortcuts:
                    assignments[name] = first
                    used_shortcuts.add(first)
                else:
                    unassigned.append(name)
            
            # 2. Fallback: Random Available Letter for unassigned
            available_letters = [c for c in string.ascii_uppercase if c not in used_shortcuts]
            
            still_unassigned = []
            for name in unassigned:
                if available_letters:
                    # Pick random
                    param = random.choice(available_letters)
                    assignments[name] = param
                    used_shortcuts.add(param)
                    available_letters.remove(param)
                else:
                    still_unassigned.append(name)

            # 3. Fallback: Numbers 0-9 if all letters taken
            available_numbers = [str(d) for d in range(10) if str(d) not in used_shortcuts]
            
            for name in still_unassigned:
                if available_numbers:
                    param = random.choice(available_numbers)
                    assignments[name] = param
                    used_shortcuts.add(param)
                    available_numbers.remove(param)
                else:
                    # No shortcut available
                    assignments[name] = None

            # Build result list
            for name in raw_dirs:
                dirs.append({
                    "name": name,
                    "shortcut": assignments.get(name)
                })

            self.send_json({
                "files": files, 
                "dirs": dirs,
                "cwd": str(Path(DIRECTORY).resolve())
            })

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
            # IMPORTANT: Use .name to ensure we don't accidentally nest paths if filename has a folder
            dst = dst_dir / Path(filename).name

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
            # Use .name for safety
            dst = trash_dir / Path(filename).name

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
        # Allow / and \ for subdirectories (needed for undo), but ABSOLUTELY NO ..
        if '..' in name:
            self.send_error(403, "Invalid filename (traversal detected)")
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
