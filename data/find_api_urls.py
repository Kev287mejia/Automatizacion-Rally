"""Extrae las URLs de API del elemento dashboard."""
from bs4 import BeautifulSoup

with open('data/dashboard_raw.html', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')

# El elemento que contiene las URLs
dashboard_el = soup.find(id='dashboardSeguimiento')
if dashboard_el:
    print('=== Atributos del #dashboardSeguimiento ===')
    for attr, val in dashboard_el.attrs.items():
        print(f'  {attr} = {val}')
else:
    print('No se encontro #dashboardSeguimiento')
    # Buscar cualquier elemento con data-url
    for el in soup.find_all(True):
        attrs = el.attrs
        data_attrs = {k: v for k, v in attrs.items() if k.startswith('data-url') or 'url' in k.lower()}
        if data_attrs:
            print(f'  {el.name} id={el.get("id")} class={el.get("class")} -> {data_attrs}')

# También buscar el formulario de filtros del dashboard
form = soup.find(id='formFiltrosDashboard')
if form:
    print()
    print('=== Atributos del #formFiltrosDashboard ===')
    for attr, val in form.attrs.items():
        print(f'  {attr} = {val}')
    # Ver los select/inputs del form
    for inp in form.find_all(['select', 'input']):
        print(f'  input/select: name={inp.get("name")} id={inp.get("id")} value={str(inp.get("value",""))[:50]}')
        # Opciones del select
        for opt in inp.find_all('option'):
            print(f'    option: value={opt.get("value")} text={opt.get_text(strip=True)[:60]}')
