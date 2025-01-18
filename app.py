import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from flask import Flask, jsonify

app = Flask(__name__)

# ✅ Updated URL and Headers
BASE_URL = "https://old-gods.hashl02mn.workers.dev/1737267564929/cat/Movies/1/"
COOKIES = {'hashhackers_1337x_web_app': 'QBcphs7Xe/KJWn1RnYQNlQ=='}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

async def fetch_html(url):
    """ Fetch HTML content with error handling and timeout """
    async with httpx.AsyncClient(timeout=10) as client:
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

async def fetch_title_links():
    """ Scrape the first 5 movie title links from the page """
    html = await fetch_html(BASE_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    tbody = soup.find('tbody')
    if not tbody:
        print("⚠️ <tbody> not found in the HTML")
        return []

    links = []
    for a in tbody.find_all('a', class_='icon'):
        title_link = a.find_next_sibling('a')
        if title_link and title_link['href'].startswith('//'):
            links.append('https:' + title_link['href'])

    return links[:15]  # ✅ Scrape only first 5 movies

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

    # ✅ Remove [1337x.HashHackers.Com] from the magnet link if it exists
    if magnet and "[1337x.HashHackers.Com]" in magnet:
        magnet = magnet.replace("[1337x.HashHackers.Com]", "").strip()

    return title, magnet


@app.route('/')
def home():
    return "✅ Async Flask Scraper is Running!"

@app.route('/rss', methods=['GET'])
def rss():
    """ Fetch first 5 movie titles and magnet links as JSON """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    title_links = loop.run_until_complete(fetch_title_links())
    if not title_links:
        return jsonify({"error": "No links found"}), 500

    # ✅ Run multiple tasks asynchronously
    tasks = [fetch_page_title_and_magnet(link) for link in title_links]
    results = loop.run_until_complete(asyncio.gather(*tasks))

    data = [{"title": title, "magnet": magnet} for title, magnet in results if title and magnet]

    if not data:
        return jsonify({"error": "No valid data scraped"}), 500

    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
