import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from flask import Flask, jsonify, Response, stream_with_context

app = Flask(__name__)

# ✅ Define URLs and Headers
BASE_URL = "https://old-gods.hashl02mn.workers.dev/1737267564929/cat/Movies/1/"
COOKIES = {'hashhackers_1337x_web_app': 'QBcphs7Xe/KJWn1RnYQNlQ=='}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "DNT": "1",
}

async def fetch_html(url):
    """ Fetch HTML content with async httpx """
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url, cookies=COOKIES, headers=HEADERS)
            if response.status_code == 200:
                return response.text
            print(f"❌ Failed: {url} - {response.status_code}")
        except Exception as e:
            print(f"🔥 Error: {url} - {e}")
    return None

async def fetch_title_links():
    """ Scrape all movie title links from the main page """
    html = await fetch_html(BASE_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    tbody = soup.find('tbody')
    if not tbody:
        print("⚠️ <tbody> not found in HTML")
        return []

    links = []
    for a in tbody.find_all('a', class_='icon'):
        title_link = a.find_next_sibling('a')
        if title_link and title_link['href'].startswith('//'):
            links.append('https:' + title_link['href'])
    
    print(f"✅ Found {len(links)} movie links")
    return links[:5]  # ⚡ Limit results to avoid timeout

async def fetch_page_title_and_magnet(link):
    """ Extract movie title and magnet link from a movie page """
    html = await fetch_html(link)
    if not html:
        return None, None

    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.replace("Download", "").replace("Torrent", "").strip() if soup.title else "No title"

    magnet = None
    for script in soup.find_all('script'):
        if script.string:
            match = re.search(r'var mainMagnetURL\s*=\s*"(magnet:[^"]+)"', script.string)
            if match:
                magnet = match.group(1)
                break

    return title, magnet

@app.route('/')
def home():
    return "✅ Async Flask Scraper is Running!"

@app.route('/rss', methods=['GET'])
def rss():
    """ Fetch movie titles and magnet links as JSON """
    async def generate():
        title_links = await fetch_title_links()
        if not title_links:
            yield jsonify({"error": "No links found"}).get_data(as_text=True)
            return

        yield '{"movies": ['
        first = True
        for link in title_links:
            title, magnet = await fetch_page_title_and_magnet(link)
            if title and magnet:
                if not first:
                    yield ','
                yield jsonify({"title": title, "magnet": magnet}).get_data(as_text=True)
                first = False
            await asyncio.sleep(1)  # 🔄 Prevent hitting server limits
        yield ']}'

    return Response(stream_with_context(generate()), content_type='application/json')

if __name__ == "__main__":
    app.run(debug=True)
