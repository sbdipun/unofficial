import re
import html
from flask import Flask, jsonify, Response
from bs4 import BeautifulSoup
import cloudscraper

app = Flask(__name__)

import asyncio
import re
import html
import lxml
from xml.sax.saxutils import escape
import httpx
from bs4 import BeautifulSoup
from flask import Flask, jsonify, Response

app = Flask(__name__)

# Proxy configuration
PROXY_URL = "http://ogais4d6kcfVkEyuGy3nz1mT:GuRA1qAXgoi85mW9GZYJsJKN@in160.nordvpn.com:89"

# ✅ Updated URL and Headers
BASE_URL = "https://old-gods.8juncf.workers.dev/1749534372373/cat/Movies/1/"
COOKIES = {'hashhackers_1337x_web_app': 'HauCWD+Kkoit9v19AHzEew=='}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def clean_magnet_link(magnet):
    """Remove specific tracker domain from the magnet link."""
    magnet = re.sub(r'(?<=dn=)\[1337x\.HashHackers\.Com\]', '', magnet)
    magnet = re.sub(r'&+', '&', magnet)
    if magnet.endswith('&'):
        magnet = magnet[:-1]
    return magnet

async def fetch_html(url):
    """ Fetch HTML content with error handling and timeout """
    async with httpx.AsyncClient(
        timeout=10,
        proxies=PROXY_URL,
        transport=httpx.AsyncHTTPTransport(retries=3)  # Add retries for better reliability
    ) as client:
        try:
            response = await client.get(url, cookies=COOKIES, headers=HEADERS)
            if response.status_code != 200:
                print(f"❌ Failed to fetch {url} - Status Code: {response.status_code}")
                return None
            return response.text
        except httpx.TimeoutException:
            print(f"⏳ Timeout fetching {url}")
            return None
        except Exception as e:
            print(f"🔥 Error fetching {url}: {e}")
            return None

# ... [rest of your existing code remains the same] ...

def fetch_title_links():
    html_text = fetch_html(BASE_URL)
    if not html_text:
        return []

    soup = BeautifulSoup(html_text, 'html.parser')
    tbody = soup.find('tbody')
    if not tbody:
        print("⚠️ <tbody> not found")
        return []

    links = []
    for a in tbody.find_all('a', class_='icon'):
        title_link = a.find_next_sibling('a')
        if title_link and title_link['href'].startswith('//'):
            links.append('https:' + title_link['href'])

    return links[:13]

def fetch_page_details(link):
    html_text = fetch_html(link)
    if not html_text:
        return None, None, None

    soup = BeautifulSoup(html_text, 'html.parser')
    title = soup.title.string.replace("Download", "").replace("Torrent", "").strip() if soup.title else "No title"

    magnet = None
    for script in soup.find_all('script'):
        if script.string:
            match = re.search(r'var mainMagnetURL\s*=\s*"(magnet:[^"]+)"', script.string)
            if match:
                magnet = clean_magnet_link(match.group(1))
                break

    file_size = None
    for ul in soup.find_all("ul", class_="list"):
        for li in ul.find_all("li"):
            if (li.find("strong") and li.find("span")
                and li.find("strong").text.strip() == "Total size"):
                file_size = li.find("span").text.strip()
                break

    return title, magnet, file_size

@app.route('/')
def home():
    return "✅ 1337x Scraper (Cloudscraper) Is Running"

@app.route('/rss', methods=['GET'])
def rss():
    title_links = fetch_title_links()
    if not title_links:
        return jsonify({"error": "No links found"}), 500

    rss_items = ""
    for link in title_links:
        title, magnet, size = fetch_page_details(link)
        if title and magnet:
            description = f"Size: {size if size else 'Unknown'}"
            rss_items += f"""
            <item>
                <title>{html.escape(title)}</title>
                <link>{html.escape(magnet)}</link>
                <description>{html.escape(description)}</description>
            </item>
            """

    base_url = "https://www.1377x.to/cat/Movies/1/"
    rss_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>1337x RSS Feed</title>
            <link>{base_url}</link>
            <description>Latest Movies and TV Shows</description>
            {rss_items}
        </channel>
    </rss>
    """

    return Response(rss_feed, content_type='application/rss+xml')

if __name__ == "__main__":
    app.run(debug=True)
