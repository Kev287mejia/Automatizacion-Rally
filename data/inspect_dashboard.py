from bs4 import BeautifulSoup

with open('data/dashboard_raw.html', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

# 1. Estructura card inscritos
print('=== CARD INSCRITOS ===')
card = soup.find(class_='dashboard-card-borde-inscritos')
if card:
    print(card.prettify()[:800])
else:
    print('No encontrado')

# 2. Todos los dashboard-card-valor
print()
print('=== dashboard-card-valor (todos) ===')
for el in soup.find_all(class_='dashboard-card-valor'):
    print(repr(el))

# 3. Resumen equipos
print()
print('=== dashboard-resumen (equipos) ===')
resumen = soup.find(class_='dashboard-resumen')
if resumen:
    print(resumen.prettify()[:1500])
else:
    print('No encontrado - buscando alternativas...')
    for el in soup.find_all(class_=lambda c: c and 'resumen' in ' '.join(c) if isinstance(c, list) else 'resumen' in str(c)):
        print('Encontrado:', el.get('class'), '->', el.get_text(strip=True)[:100])

# 4. Tablas
print()
print('=== TABLAS en el dashboard ===')
tablas = soup.find_all('table')
print('Total tablas encontradas:', len(tablas))
for i, t in enumerate(tablas):
    tid = t.get('id', 'sin-id')
    tcls = t.get('class', [])
    print(f'Tabla {i}: id={tid} class={tcls}')
    print(t.prettify()[:400])
    print()
