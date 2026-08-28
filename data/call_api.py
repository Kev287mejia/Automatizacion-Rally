"""Llama a los endpoints de API del dashboard y guarda las respuestas JSON."""
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

load_dotenv()

BASE = 'https://apprally.nicaraguainnova.gob.ni'
EDITION_UUID = '4f13f9a9-8bfc-44a3-99ac-a578e9908c9b'

s = requests.Session()
s.headers['User-Agent'] = 'RallyMonitor/1.0'

# Login
r = s.get(f'{BASE}/', timeout=15)
soup = BeautifulSoup(r.text, 'html.parser')
csrf = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
s.post(f'{BASE}/', data={
    'username': os.getenv('RALLY_USERNAME'),
    'password': os.getenv('RALLY_PASSWORD'),
    'csrfmiddlewaretoken': csrf,
}, timeout=15, headers={'Referer': f'{BASE}/'})

print('Login OK. Consultando APIs...')
print()

# --- API datos (indicadores) ---
params = {
    'edicion': EDITION_UUID,
    'institucion': '',
    'sede': '',  # Todas las sedes (luego filtraremos BICU)
}
r_datos = s.get(f'{BASE}/competencia/dashboard/datos/', params=params, timeout=15)
print(f'=== /competencia/dashboard/datos/ - HTTP {r_datos.status_code} ===')
print(f'Content-Type: {r_datos.headers.get("Content-Type")}')
try:
    datos_json = r_datos.json()
    print(json.dumps(datos_json, indent=2, ensure_ascii=False)[:3000])
    with open('data/api_datos.json', 'w', encoding='utf-8') as f:
        json.dump(datos_json, f, indent=2, ensure_ascii=False)
    print('(Guardado en data/api_datos.json)')
except Exception as e:
    print(f'No es JSON: {e}')
    print(r_datos.text[:500])

print()

# --- API sedes ---
r_sedes = s.get(f'{BASE}/competencia/dashboard/sedes/', params={'edicion': EDITION_UUID}, timeout=15)
print(f'=== /competencia/dashboard/sedes/ - HTTP {r_sedes.status_code} ===')
print(f'Content-Type: {r_sedes.headers.get("Content-Type")}')
try:
    sedes_json = r_sedes.json()
    print(json.dumps(sedes_json, indent=2, ensure_ascii=False)[:2000])
    with open('data/api_sedes.json', 'w', encoding='utf-8') as f:
        json.dump(sedes_json, f, indent=2, ensure_ascii=False)
    print('(Guardado en data/api_sedes.json)')
except Exception as e:
    print(f'No es JSON: {e}')
    print(r_sedes.text[:500])

print()

# --- API datos filtrado por BICU ---
# Primero necesitamos el ID de la sede BICU desde los sedes
print('=== Buscando sede BICU en la respuesta de sedes ===')
try:
    for sede in sedes_json.get('sedes', sedes_json if isinstance(sedes_json, list) else []):
        nombre = sede.get('nombre', '') or sede.get('name', '') or str(sede)
        print(f'  Sede: {nombre} | datos: {sede}')
except Exception as e:
    print(f'Error procesando sedes: {e}')
