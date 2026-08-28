"""Extrae el script principal del dashboard y busca todos los endpoints."""
import re
from bs4 import BeautifulSoup

with open('data/dashboard_raw.html', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')
scripts = soup.find_all('script')

# El script 9 es el principal (31935 bytes)
main_script = ''
for script in scripts:
    text = script.string or ''
    if len(text) > 1000:
        main_script = text
        break

# Guardar el script completo
with open('data/dashboard_script.js', 'w', encoding='utf-8') as f:
    f.write(main_script)

print(f'Script guardado: {len(main_script)} bytes')
print()

# Buscar todos los fetch() y URLs
fetches = re.findall(r"fetch\s*\(\s*`([^`]+)`", main_script)
fetches += re.findall(r'fetch\s*\(\s*"([^"]+)"', main_script)
fetches += re.findall(r"fetch\s*\(\s*'([^']+)'", main_script)

print('=== URLs en fetch() ===')
for u in fetches:
    print(' ', u)

# Buscar construcciones de URL con template literals
template_urls = re.findall(r"`([^`]*\$\{[^`]+\}[^`]*)`", main_script)
print()
print('=== Template literals con URL ===')
for u in template_urls[:20]:
    print(' ', u[:150])

# Buscar la URL base del dashboard
print()
print('=== Contexto de "indicadores" o "dashboard" en el script ===')
lines = main_script.split('\n')
for i, line in enumerate(lines):
    if any(kw in line.lower() for kw in ['fetch', 'indicador', 'ajax', 'url', 'endpoint', 'api']):
        start = max(0, i-1)
        end = min(len(lines), i+3)
        for l in lines[start:end]:
            if l.strip():
                print(f'  {l.rstrip()}')
        print()
