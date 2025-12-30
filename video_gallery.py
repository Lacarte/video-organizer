#!/usr/bin/env python3
"""
Video Gallery Generator
Scans parent directory for MP4 and WebM files and creates a beautiful HTML gallery.
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote
import json

def get_video_files(directory: Path) -> list:
    """Scan directory for MP4 and WebM files."""
    video_extensions = {'.mp4', '.webm'}
    videos = []
    
    for file in directory.iterdir():
        if file.is_file() and file.suffix.lower() in video_extensions:
            videos.append(file)
    
    return sorted(videos, key=lambda x: x.stat().st_mtime, reverse=True)

def generate_html(videos: list, output_path: Path) -> str:
    """Generate HTML gallery with client-side pagination to handle thousands of files."""
    
    # Create the list of filenames for JS
    # We only need the filename, assuming they are in the same dir as the HTML
    video_list_js = json.dumps([v.name for v in videos])
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Gallery ({len(videos):,} videos)</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background-color: #0a0a0a;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 20px;
            min-height: 100vh;
            color: #fff;
            display: flex;
            flex-direction: column;
        }}
        
        .header {{
            text-align: center;
            padding: 20px;
            margin-bottom: 20px;
        }}
        
        .header h1 {{
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        /* Pagination Controls */
        .controls {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin-bottom: 30px;
            position: sticky;
            top: 20px;
            z-index: 100;
            background: rgba(10, 10, 10, 0.9);
            padding: 15px;
            border-radius: 50px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}

        .btn {{
            background: #2a2a2a;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 5px;
        }}

        .btn:hover:not(:disabled) {{
            background: #667eea;
            transform: translateY(-2px);
        }}

        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            background: #1a1a1a;
        }}
        
        .page-info {{
            font-family: monospace;
            font-size: 1.1rem;
            color: #ccc;
        }}

        #page-input {{
            background: #1a1a1a;
            border: 1px solid #333;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            width: 60px;
            text-align: center;
            font-size: 1rem;
        }}

        /* Grid Layout */
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            max-width: 1800px;
            width: 100%;
            margin: 0 auto;
            flex: 1;
        }}
        
        .video-card {{
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            background: #1a1a1a;
            cursor: pointer;
            text-decoration: none;
            display: block;
            aspect-ratio: 1 / 1;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            opacity: 0;
            animation: fadeIn 0.5s forwards;
        }}

        @keyframes fadeIn {{
            to {{ opacity: 1; }}
        }}
        
        .video-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            z-index: 2;
        }}
        
        .video-element {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        
        .video-overlay {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 40px 12px 12px;
            background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%);
            opacity: 0;
            transition: opacity 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .video-card:hover .video-overlay {{
            opacity: 1;
        }}
        
        .video-name {{
            color: #fff;
            font-size: 0.85rem;
            font-weight: 500;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 80%;
        }}

        .delete-btn {{
            background: rgba(255, 68, 68, 0.2);
            color: #ff4444;
            border: 1px solid rgba(255, 68, 68, 0.3);
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 1.2rem;
            margin-left: 10px;
        }}

        .delete-btn:hover {{
            background: #ff4444;
            color: white;
            border-color: #ff4444;
            transform: scale(1.1);
        }}

        .error-message {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #ff5555;
            font-size: 0.8rem;
            text-align: center;
            display: none;
            width: 100%;
            padding: 0 10px;
        }}
        
        /* Masonry-like varied heights for visual interest */
        .video-card:nth-child(5n+1) {{ aspect-ratio: 3 / 4; }}
        .video-card:nth-child(5n+2) {{ aspect-ratio: 1 / 1; }}
        .video-card:nth-child(5n+3) {{ aspect-ratio: 4 / 5; }}
        .video-card:nth-child(5n+4) {{ aspect-ratio: 3 / 4; }}
        .video-card:nth-child(5n+5) {{ aspect-ratio: 1 / 1; }}

        @media (max-width: 768px) {{
            .gallery {{
                grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                gap: 10px;
            }}
            .header h1 {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 Video Gallery</h1>
        <p>{len(videos):,} videos available</p>
    </div>

    <!-- Navigation Controls -->
    <div class="controls">
        <button class="btn" id="btn-first" title="First Page">«</button>
        <button class="btn" id="btn-prev" title="Previous Page">‹ Prev</button>
        
        <div class="page-info">
            Page <input type="number" id="page-input" min="1" value="1"> of <span id="total-pages">--</span>
        </div>
        
        <button class="btn" id="btn-next" title="Next Page">Next ›</button>
        <button class="btn" id="btn-last" title="Last Page">»</button>
    </div>
    
    <div class="gallery" id="gallery-grid">
        <!-- Videos will be injected here by JS -->
    </div>
    
    <script>
        // Data injected from Python
        let videoList = {video_list_js};
        
        // Configuration
        const ITEMS_PER_PAGE = 50; // Keep DOM light
        let currentPage = 1;
        let totalPages = Math.ceil(videoList.length / ITEMS_PER_PAGE);

        // Elements
        const grid = document.getElementById('gallery-grid');
        const pageInput = document.getElementById('page-input');
        const totalPagesSpan = document.getElementById('total-pages');
        const btnPrev = document.getElementById('btn-prev');
        const btnNext = document.getElementById('btn-next');
        const btnFirst = document.getElementById('btn-first');
        const btnLast = document.getElementById('btn-last');

        // Observer for lazy loading/playing
        const observerOptions = {{
            root: null,
            rootMargin: '100px',
            threshold: 0.1
        }};

        // Observer removed in favor of hover-to-play/thumbnails

        async function deleteVideo(filename, cardElement, event) {{
            // Prevent clicking the link
            event.preventDefault();
            event.stopPropagation();
            
            if (!confirm(`Are you sure you want to PERMANENTLY delete "${{filename}}"?`)) {{
                return;
            }}

            try {{
                const btn = cardElement.querySelector('.delete-btn');
                btn.innerHTML = '⏳';
                
                const response = await fetch('/api/delete', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ filename: filename }})
                }});

                if (response.ok) {{
                    // Remove from UI
                    cardElement.style.transition = 'all 0.5s';
                    cardElement.style.transform = 'scale(0)';
                    setTimeout(() => cardElement.remove(), 500);
                    
                    // Remove from list
                    const index = videoList.indexOf(filename);
                    if (index > -1) {{
                        videoList.splice(index, 1);
                    }}
                    
                    // Update header count if we wanted to (optional)
                    
                }} else {{
                    const err = await response.text();
                    alert(`Error deleting file: ${{err}}`);
                    btn.innerHTML = '🗑️';
                }}
            }} catch (error) {{
                console.error(error);
                alert('Network error deleting file');
            }}
        }}

        function renderPage(page) {{
            // Recalculate total pages in case items deleted
            totalPages = Math.ceil(videoList.length / ITEMS_PER_PAGE);
            
            // Clamp page
            if (page < 1) page = 1;
            if (page > totalPages && totalPages > 0) page = totalPages;
            if (totalPages === 0) page = 1;
            currentPage = page;

            // Update UI
            pageInput.value = page;
            totalPagesSpan.textContent = totalPages || 1;
            btnPrev.disabled = page === 1;
            btnFirst.disabled = page === 1;
            btnNext.disabled = page === totalPages || totalPages === 0;
            btnLast.disabled = page === totalPages || totalPages === 0;

            // Clear Grid
            grid.innerHTML = '';
            
            if (videoList.length === 0) {{
                grid.innerHTML = '<div style="color: #666; text-align: center; grid-column: 1/-1; padding: 50px;">No videos found</div>';
                return;
            }}
            
            // Slice Data
            const start = (page - 1) * ITEMS_PER_PAGE;
            const end = start + ITEMS_PER_PAGE;
            const pageVideos = videoList.slice(start, end);

            // Generate Nodes
            const fragment = document.createDocumentFragment();
            
            pageVideos.forEach((filename, index) => {{
                const videoName = filename.replace(/\.[^/.]+$/, ""); // remove extension
                const midjourneyUrl = `https://www.midjourney.com/jobs/${{encodeURIComponent(videoName)}}?index=0`;
                
                const card = document.createElement('a');
                card.className = 'video-card';
                card.href = midjourneyUrl;
                card.target = '_blank';
                
                // Varied aspect ratios setup (repeating pattern logic in JS if needed, 
                // but CSS nth-child handles it fine even with dynamic elements)

                card.innerHTML = `
                    <video 
                        loop 
                        playsinline 
                        muted
                        preload="none"
                        class="video-element"
                        poster="/thumbnails/${{encodeURIComponent(filename)}}.jpg"
                        src="${{encodeURIComponent(filename)}}"
                    ></video>
                    <div class="video-overlay">
                        <span class="video-name">${{videoName}}</span>
                        <button class="delete-btn" title="Delete Video" onclick="deleteVideo('${{filename.replace(/'/g, "\\'")}}', this.closest('.video-card'), event)">🗑️</button>
                    </div>
                    <div class="error-message">Failed to load</div>
                `;

                const video = card.querySelector('video');
                
                // Error handling
                video.onerror = () => {{
                    video.style.opacity = '0.1';
                    card.querySelector('.error-message').style.display = 'block';
                    card.style.border = '1px solid #ff4444';
                }};

                // Hover to play
                card.addEventListener('mouseenter', () => {{
                   video.play().catch(() => {{}});
                }});
                
                card.addEventListener('mouseleave', () => {{
                   video.pause();
                   video.currentTime = 0; // Reset to start
                }});
                fragment.appendChild(card);
            }});

            grid.appendChild(fragment);
            
            // Scroll to top of grid
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        // Event Listeners
        btnPrev.addEventListener('click', () => renderPage(currentPage - 1));
        btnNext.addEventListener('click', () => renderPage(currentPage + 1));
        btnFirst.addEventListener('click', () => renderPage(1));
        btnLast.addEventListener('click', () => renderPage(totalPages));
        
        pageInput.addEventListener('change', (e) => {{
            let val = parseInt(e.target.value);
            if (val) renderPage(val);
        }});

        // Initial Load
        renderPage(1);
    </script>
</body>
</html>'''
    
    return html_content


def main():
    # Helper script is in display-files/
    # Target videos are in parent directory ../
    script_dir = Path(__file__).parent.resolve()
    target_dir = script_dir.parent.resolve()
    
    print(f"📁 Scanning parent directory: {target_dir}")
    
    if not target_dir.exists():
        print(f"❌ Directory not found: {target_dir}")
        sys.exit(1)
    
    videos = get_video_files(target_dir)
    print(f"🎬 Found {len(videos)} video(s)")
    
    # OUTPUT NOW GOES INTO THE PARENT DIRECTORY (next to the videos)
    output_file = target_dir / "gallery.html"
    html_content = generate_html(videos, output_file)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Gallery created: {output_file}")
    print(f"   Open this file in your browser to view the gallery")


if __name__ == "__main__":
    main()
