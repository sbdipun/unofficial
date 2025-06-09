import asyncio
import re
import html
import httpx
from bs4 import BeautifulSoup
from flask import Flask, Response

app = Flask(__name__)

# Updated Configuration
BASE_URL = "https://old-gods.8juncf.workers.dev/1749534372373/cat/Movies/1/"
HEADERS = {
    "authority": "old-gods.8juncf.workers.dev",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.7",
    "cache-control": "max-age=0",
    "cookie": "hashhackers_1337x_web_app=HauCWD+Kkoit9v19AHzEew==",
    "priority": "u=0, i",
    "sec-ch-ua": '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "sec-gpc": "1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
}

def clean_magnet_link(magnet):
    """Clean magnet links from tracker artifacts"""
    magnet = re.sub(r'(?<=dn=)\[1337x\.HashHackers\.Com\]', '', magnet)
    magnet = re.sub(r'&+', '&', magnet)
    return magnet.rstrip('&')

async def fetch_html(url):
    """Fetch HTML with exact headers required by the proxy"""
    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=30.0,
        follow_redirects=True,
        http2=True  # Important for some workers.dev proxies
    ) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code} for {url}")
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
        return None

async def fetch_title_links():
    """Scrape movie links from the main page"""
    html_content = await fetch_html(BASE_URL)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    
    # More robust table parsing
    table = soup.find('table', class_='table-list')
    if table:
        for row in table.find_all('tr')[1:14]:  # First 13 rows (skip header)
            link = row.find('a', href=re.compile(r'/torrent/'))
            if link and link.get('href'):
                links.append(f"https:{link['href']}")
    
    return links[:13]

async def fetch_page_details(link):
    """Extract torrent details from individual pages"""
    html_content = await fetch_html(link)
    if not html_content:
        return None, None, None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Title extraction
    title = "Unknown"
    if soup.title:
        title = soup.title.text.replace("Download", "").replace("Torrent", "").strip()
    
    # Magnet link extraction
    magnet = None
    for script in soup.find_all('script'):
        if script.string and 'mainMagnetURL' in script.string:
            match = re.search(r'var mainMagnetURL\s*=\s*"(magnet:[^"]+)"', script.string)
            if match:
                magnet = clean_magnet_link(match.group(1))
                break
    
    # File size extraction
    file_size = "N/A"
    for li in soup.find_all('li'):
        if 'Total size' in li.text:
            size_span = li.find('span')
            if size_span:
                file_size = size_span.text.strip()
                break
    
    return title, magnet, file_size

@app.route('/rss')
def generate_rss():
    """Generate RSS feed endpoint"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Fetch all data
        links = loop.run_until_complete(fetch_title_links())
        if not links:
            return Response("<error>No torrents found</error>", status=500, mimetype='application/xml')
        
        results = loop.run_until_complete(asyncio.gather(
            *[fetch_page_details(link) for link in links]
        ))
        
        # Build RSS items
        items = []
        for title, magnet, size in results:
            if title and magnet:
                items.append(f"""
                <item>
                    <title>{html.escape(title)}</title>
                    <link>{html.escape(magnet)}</link>
                    <description>Size: {html.escape(size)}</description>
                </item>
                """)
        
        # Complete RSS feed
        rss = f"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>1337x Torrent Feed</title>
                <link>{BASE_URL}</link>
                <description>Latest movies from 1337x</description>
                {''.join(items)}
            </channel>
        </rss>
        """
        
        return Response(rss, mimetype='application/rss+xml')
    
    except Exception as e:
        return Response(f"<error>{str(e)}</error>", status=500, mimetype='application/xml')

@app.route('/')
def home():
    return "1337x RSS Proxy Service - Use /rss endpoint"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
