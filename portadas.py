import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import db

# API pública de búsqueda de iTunes (no requiere clave)
URL_API = 'https://itunes.apple.com/search'

# Si hay un error de red, no volvemos a intentarlo durante unos segundos
ESPERA_TRAS_FALLO = 60
_ultimo_fallo = 0


def normalizar(texto):
    """Minúsculas, sin tildes, sin paréntesis ni signos: 'Abbey Road (Remastered)' -> 'abbey road'."""
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r'[\(\[].*?[\)\]]', ' ', texto)
    texto = re.sub(r'[^a-z0-9 ]+', ' ', texto)
    return ' '.join(texto.split())


def _consultar_api(termino, pais, timeout):
    params = {'term': termino, 'entity': 'album', 'limit': 25}
    if pais:
        params['country'] = pais
    url = f'{URL_API}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r).get('results', [])


def elegir_mejor(resultados, artista, titulo):
    """Elige el resultado que más se parece al disco. Devuelve None si ninguno."""
    t = normalizar(titulo)
    a = normalizar(artista)
    palabras_t = set(t.split())
    mejor, mejor_punt = None, 0

    for r in resultados:
        if not r.get('artworkUrl100'):
            continue
        nombre = normalizar(r.get('collectionName', ''))
        art = normalizar(r.get('artistName', ''))

        punt = 0
        if nombre == t:
            punt += 10
        elif t in nombre or nombre in t:
            punt += 6
        elif palabras_t and len(palabras_t & set(nombre.split())) / len(palabras_t) >= 0.6:
            punt += 3
        else:
            continue  # el título no se parece: descartamos

        if a and (a in art or art in a or a.split()[0] in art):
            punt += 5
        if 'single' in r.get('collectionName', '').lower():
            punt -= 2

        if punt > mejor_punt:
            mejor, mejor_punt = r, punt

    return mejor


def buscar_portada(artista, titulo, timeout=5):
    """Busca la portada de un álbum y devuelve la URL de la imagen (600x600).

    - Devuelve la URL si la encuentra.
    - Devuelve '' si el álbum no aparece en la búsqueda.
    - Devuelve None si ha habido un error de red (se reintentará más tarde).
    """
    global _ultimo_fallo
    try:
        # Primero buscamos en la tienda española; si no hay nada, en la global
        for pais in ('ES', None):
            resultados = _consultar_api(f'{artista} {titulo}', pais, timeout)
            mejor = elegir_mejor(resultados, artista, titulo)
            if mejor:
                return mejor['artworkUrl100'].replace('100x100bb', '600x600bb')
        return ''
    except Exception as e:
        _ultimo_fallo = time.time()
        print(f'[portadas] No se pudo buscar "{artista} - {titulo}": {e}', flush=True)
        return None


def completar_portadas(discos):
    """Rellena la columna portada_url de los discos que todavía no la tienen.

    portada_url = NULL  -> aún no se ha buscado
    portada_url = ''    -> buscada pero no encontrada (se usa la portada CSS)
    """
    if time.time() - _ultimo_fallo < ESPERA_TRAS_FALLO:
        return

    pendientes = [d for d in discos if d.get('portada_url') is None]
    if not pendientes:
        return

    # Las búsquedas se hacen en paralelo para que la primera carga sea rápida
    with ThreadPoolExecutor(max_workers=6) as pool:
        resultados = list(pool.map(
            lambda d: buscar_portada(d['artista'], d['titulo']), pendientes))

    for d, url in zip(pendientes, resultados):
        if url is None:
            continue
        print(f'[portadas] {d["artista"]} - {d["titulo"]}: '
              f'{"OK" if url else "no encontrada"}', flush=True)
        db.ejecutar('UPDATE discos SET portada_url = %s WHERE id = %s',
                    (url, d['id']))
        d['portada_url'] = url


if __name__ == '__main__':
    # Diagnóstico: docker compose exec web python portadas.py
    # Borra las portadas guardadas, las vuelve a buscar y muestra el resultado.
    db.ejecutar('UPDATE discos SET portada_url = NULL')
    discos = db.consultar('SELECT * FROM discos ORDER BY id')
    completar_portadas(discos)
    ok = sum(1 for d in discos if d['portada_url'])
    print(f'\nPortadas encontradas: {ok} de {len(discos)}')
