import re
import httpx
from bs4 import BeautifulSoup
from quart import Quart, jsonify

app = Quart(__name__)

BASE_URL = "https://old-gods.hashl02mn.workers.dev/1737267564929/cat/Movies/1/"
COOKIES = {'hashhackers_1337x_web_app': 'QBcphs7Xe/KJWn1RnYQNlQ=='}
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}

async def fetch_html(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, cookies=COOKIES, headers=HEADERS)
        return response.text if response.status_code == 200 else None

async def fetch_title_links():
    html = await fetch_html(BASE_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    tbody = soup.find('tbody')
    if not tbody:
        return []
    return [
        'https:' + a.find_next_sibling('a')['href']
        for a in tbody.find_all('a', class_='icon')
        if a.find_next_sibling('a') and a.find_next_sibling('a')['href'].startswith('//')
    ]

async def fetch_page_title_and_magnet(link):
    html = await fetch_html(link)
    if not html:
        return None, None
    soup = BeautifulSoup(html, 'html.parser')
    title = (soup.title.string or '').replace("Download", "").replace("Torrent", "").strip()
    magnet = next(
        (m.group(1) for s in soup.find_all('script') if s.string and (m := re.search(r'var mainMagnetURL\s*=\s*"(magnet:[^"]+)"', s.string))),
        None
    )
    return title, magnet

@app.route('/')
async def home():
    return "Welcome to the Async Flask Web Scraper!"

@app.route('/rss', methods=['GET'])
async def rss():
    title_links = await fetch_title_links()
    data = [{"title": title, "magnet": magnet} for link in title_links if (title := (await fetch_page_title_and_magnet(link))[0]) and (magnet := (await fetch_page_title_and_magnet(link))[1])]
    return jsonify(data)

if __name__ == "__main__":
    import hypercorn.asyncio
    import asyncio
    config = hypercorn.Config()
    config.bind = ["0.0.0.0:8000"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
