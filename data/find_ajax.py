"""Script para encontrar endpoints AJAX en el dashboard HTML."""
import re
from bs4 import BeautifulSoup

with open('data/dashboard_raw.html', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')
scripts = soup.find_all('script')
print(f'Total scripts: {len(scripts)}')
print()

for i, script in enumerate(scripts):
    text = script.string or ''
    if not text.strip():
        src = script.get('src', '')
        if src:
            print(f'Script {i} [externo]: {src}')
        continue

    # Buscar URLs de API
    fetches = re.findall(r"fetch\s*\(\s*[\"'`]([^\"'`]+)[\"'`]", text)
    ajax_urls = re.findall(r"url\s*:\s*[\"'`]([^\"'`]+)[\"'`]", text)
    slash_urls = re.findall(r"[\"'](/competencia/[^\"'\s<>]+)[\"']", text)

    all_found = list(set(fetches + ajax_urls + slash_urls))
    api_urls = [u for u in all_found if len(u) > 3]

    if api_urls or len(text) > 300:
        print(f'--- Script {i} (len={len(text)}) ---')
        if api_urls:
            print('URLs encontradas:', api_urls)
        print(text.strip()[:800])
        print()
