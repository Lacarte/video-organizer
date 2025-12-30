import shutil
import http.server
import socketserver
import os
import json
import urllib.parse
import subprocess
import hashlib
import re
from pathlib import Path

# Config
PORT = 8001
DIRECTORY = "."  # Current directory (should be parent folder containing videos)
SCRIPT_DIR = Path(__file__).parent.resolve()  # Directory where server.py is located

# Extensions to look for
VIDEO_EXT = {'.mp4', '.webm', '.avi', '.mov', '.mkv'}
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
MEDIA_EXT = VIDEO_EXT | IMAGE_EXT

class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    Adds support for HTTP 'Range' requests to SimpleHTTPRequestHandler.
    Allows seeking in video files.
    """
    def send_head(self):
        if 'Range' not in self.headers:
            self.range = None
            return super().send_head()
        
        try:
            self.range = re.search(r'bytes=(\d+)-(\d*)', self.headers['Range'])
        except ValueError:
            self.range = None
            return super().send_head()
            
        if not self.range:
            return super().send_head()
            
        path = self.translate_path(self.path)
        f = None
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, "File not found")
            return None

        # Get file size
        try:
            fs = os.fstat(f.fileno())
            file_len = fs[6]
        except:
            f.close()
            return None

        # Parse range
        start, end = self.range.groups()
        start = int(start)
        if end:
            end = int(end)
        else:
            end = file_len - 1
            
        # Validate
        if start >= file_len:
            self.send_error(416, "Requested Range Not Satisfiable")
            self.send_header("Content-Range", f"bytes */{file_len}")
            self.end_headers()
            f.close()
            return None

        self.send_response(206)
        self.send_header("Content-type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_len}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        
        # Position file
        f.seek(start)
        return f

    def copyfile(self, source, outputfile):
        """
        Custom copyfile that respects self.range limits if present.
        """
        if not hasattr(self, 'range') or not self.range:
            return super().copyfile(source, outputfile)
            
        # If range is present, we need to limit the read.
        # But SimpleHTTPRequestHandler.copyfile does: shutil.copyfileobj(source, outputfile)
        # We can't control it easily unless source is a wrapper.
        # So we rely on send_head returning a LimitedFileWrapper.
        super().copyfile(source, outputfile)

class LimitedFileWrapper:
    def __init__(self, f, length):
        self.f = f
        self.length = length
        self.read_so_far = 0
        
    def read(self, size=-1):
        if self.read_so_far >= self.length:
            return b""
            
        if size < 0:
            remaining = self.length - self.read_so_far
            data = self.f.read(remaining)
            self.read_so_far += len(data)
            return data
            
        remaining = self.length - self.read_so_far
        to_read = min(size, remaining)
        data = self.f.read(to_read)
        self.read_so_far += len(data)
        return data

class GalleryRequestHandler(RangeHTTPRequestHandler):
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

    def send_head(self):
        f = super().send_head()
        if f and hasattr(self, 'range') and self.range:
             # Calculate length again to wrap it
             try:
                 start, end = self.range.groups()
                 start = int(start)
                 fs = os.fstat(f.fileno())
                 file_len = fs[6]
                 if end: end = int(end) 
                 else: end = file_len - 1
                 
                 length = end - start + 1
                 return LimitedFileWrapper(f, length)
             except:
                 pass
        return f

    def do_GET(self):
        """Serve static files, mapping app route to the correct file."""
        if self.path == '/' or self.path == '/video-organizer.html':
            # Serve the HTML file from the script directory (where server.py is located)
            html_path = SCRIPT_DIR / "video-organizer.html"

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
                    self.send_error(500, f"Error loading HTML: {e}")
                    return
            else:
                print(f"HTML file not found at: {html_path}")
                self.send_error(404, f"HTML file not found at {html_path}")
                return

        # Use RangeHTTPRequestHandler logic for files
        try:
            super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            print(f"Error serving file: {e}")

class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    def service_actions(self):
        pass
    
    def handle_error(self, request, client_address):
        pass

if __name__ == "__main__":
    print(f"🚀 Video Organizer Server on port {PORT}")
    print(f"📂 Serving directory: {os.getcwd()}")
    print(f"📄 HTML file location: {SCRIPT_DIR / 'video-organizer.html'}")
    with ThreadedHTTPServer(("", PORT), GalleryRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped.")
