import re
import html
from flask import Flask, jsonify, Response
from bs4 import BeautifulSoup
import cloudscraper

app = Flask(__name__)

BASE_URL = "https://old-gods.8juncf.workers.dev/1749534372373/cat/Movies/1/"
COOKIES = {'hashhackers_1337x_web_app': 'HauCWD+Kkoit9v19AHzEew=='}
HEADERS = {
    "authority": "old-gods.8juncf.workers.dev",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "cookie": "hashhackers_1337x_web_app=HauCWD+Kkoit9v19AHzEew==",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
}

scraper = cloudscraper.create_scraper()

def clean_magnet_link(magnet):
    magnet = re.sub(r'(?<=dn=)\[1337x\.HashHackers\.Com\]', '', magnet)
    magnet = re.sub(r'&+', '&', magnet)
    return magnet.rstrip('&')

def fetch_html(url):
    try:
        res = scraper.get(url, headers=HEADERS, cookies=COOKIES, timeout=10)
        if res.status_code == 200:
            return res.text
        print(f"❌ Failed to fetch {url} - Status Code: {res.status_code}")
        return None
    except Exception as e:
        print(f"🔥 Error fetching {url}: {e}")
        return None

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
