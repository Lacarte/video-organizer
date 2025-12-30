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

class GalleryRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests (used for deletion)."""
        if self.path == '/api/delete':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                filename = data.get('filename')
                
                if not filename:
                    self.send_error(400, "Missing filename")
                    return

                # Security: prevent path traversal and ensure filename is just a filename
                if '/' in filename or '\\' in filename or '..' in filename:
                    self.send_error(403, "Invalid filename security check")
                    return
                # Check if file exists
                file_path = Path(DIRECTORY) / filename
                if file_path.exists() and file_path.is_file():
                    try:
                        trash_dir = Path(DIRECTORY) / "deleteVideos"
                        trash_dir.mkdir(exist_ok=True)
                        
                        destination = trash_dir / filename
                        shutil.move(str(file_path), str(destination))
                        print(f"🗑️ Moved to trash: {filename}")
                        
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True, "message": f"Moved {filename} to trash"}).encode('utf-8'))
                    except Exception as e:
                        print(f"❌ Error moving {filename}: {e}")
                        self.send_error(500, str(e))
                else:
                    self.send_error(404, "File not found")
                    
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
        else:
            self.send_error(404, "API endpoint not found")

    def do_GET(self):
        """Serve static files as usual, but suppress connection errors."""
        try:
            super().do_GET()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            # For other errors, we might want to know
            pass

class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    def service_actions(self):
        pass
    
    def handle_error(self, request, client_address):
        # Suppress annoying socket errors during video streaming
        pass

if __name__ == "__main__":
    # Ensure we are serving the correct directory
    # runner.bat switches to parent directory before running this, so os.getcwd() should be correct
    print(f"🚀 Starting Gallery Server on port {PORT}")
    print(f"📂 Serving directory: {os.getcwd()}")
    print("✨ POST /api/delete enabled")
    print("⚡ Multi-threaded mode enabled")
    
    # Use ThreadingTCPServer to handle multiple video loads simulatneously
    with ThreadedHTTPServer(("", PORT), GalleryRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped.")
