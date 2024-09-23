# app.py

from flask import Flask, render_template, request, send_file, url_for, redirect
from sentiments import analyze_sentiment
from googlesearch import search
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from weasyprint import HTML
import io
import time

app = Flask(__name__)

def get_title(soup):
    """
    Extrae el título de una página web usando diferentes métodos.

    Args:
        soup (BeautifulSoup): Objeto BeautifulSoup de la página.

    Returns:
        str: Título de la página o 'Sin título'.
    """
    # Primero, intentar obtener el título estándar
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # Luego, intentar obtener el título de Open Graph
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title['content'].strip()
    # Luego, intentar obtener el título de Twitter Cards
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    if twitter_title and twitter_title.get('content'):
        return twitter_title['content'].strip()
    # Luego, intentar obtener el primer h1
    if soup.find('h1'):
        return soup.find('h1').get_text().strip()
    # Finalmente, intentar obtener el meta title
    meta_title = soup.find('meta', attrs={'name': 'title'})
    if meta_title and meta_title.get('content'):
        return meta_title['content'].strip()
    # Si no se encuentra ningún título
    return 'Sin título'

def get_top_urls_with_titles(keyword, lang="es", num_results=20):
    """
    Realiza una búsqueda en Google y obtiene las URLs y títulos principales.

    Args:
        keyword (str): Palabra clave para la búsqueda.
        lang (str): Código de idioma para la búsqueda (default: "es").
        num_results (int): Número de resultados a obtener (default: 20).

    Returns:
        list: Lista de diccionarios con 'title' y 'url'.
    """
    results = []
    try:
        print(f"Realizando búsqueda para: {keyword}")
        # **Corrección: Uso correcto de la función de búsqueda**
        search_results = search(keyword, lang=lang, num_results=num_results)

        if not search_results:
            print("No se encontraron resultados en la búsqueda.")

        for url in search_results:
            title = ''
            try:
                print(f"Obteniendo título para URL: {url}")
                response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                title = get_title(soup)
                if title != 'Sin título':
                    print(f"Título encontrado: {title}")
                else:
                    print(f"No se encontró título para la URL: {url}")
            except Exception as e:
                print(f"Error al obtener el título de {url}: {e}")
                title = 'Sin título'

            results.append({'title': title, 'url': url})
            time.sleep(1)  # Esperar para evitar ser bloqueado por Google

        print(f"URLs encontradas: {len(results)}")
        return results
    except Exception as e:
        print(f"Error al realizar la búsqueda: {e}")
        return []

def extract_text_from_url(url):
    """
    Extrae el texto principal de una página web.

    Args:
        url (str): La URL de la página web.

    Returns:
        str: Texto extraído de la página.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()

        # Extraer texto de múltiples fuentes
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'span', 'div'])
        text = ' '.join([elem.get_text(separator=' ', strip=True) for elem in text_elements])

        if not text.strip():
            text = soup.title.string if soup.title else ''

        return text
    except Exception as e:
        print(f"Error al extraer texto de {url}: {e}")
        return ""

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    current_year = datetime.now().year
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        if keyword:
            print(f"Palabra clave recibida: {keyword}")
            urls = get_top_urls_with_titles(keyword)
            print(f"URLs encontradas: {len(urls)}")
            if not urls:
                results = {'error': 'No se encontraron resultados.'}
            else:
                positive_links, negative_links, neutral_links = [], [], []

                for idx, result in enumerate(urls, 1):
                    url = result['url']
                    title = result['title']
                    serp_position = f"{idx}/1"  # Simplificado para página 1

                    print(f"Procesando ({serp_position}): {url}")
                    text = extract_text_from_url(url)
                    print(f"Texto extraído: {text[:200]}...")  # Muestra los primeros 200 caracteres

                    if not text:
                        print("No se pudo extraer texto de esta URL.\n")
                        continue

                    polarity, sentiment = analyze_sentiment(text)
                    print(f"Sentimiento: {sentiment} (Polaridad: {polarity})")

                    link_info = {
                        'serp_position': serp_position,
                        'title': title,
                        'url': url,
                        'polarity': polarity
                    }

                    if sentiment == 'Positivo':
                        positive_links.append(link_info)
                    elif sentiment == 'Negativo':
                        negative_links.append(link_info)
                    else:
                        neutral_links.append(link_info)

                results = {
                    'keyword': keyword,
                    'positive_links': positive_links,
                    'negative_links': negative_links,
                    'neutral_links': neutral_links,
                    'positive_count': len(positive_links),
                    'negative_count': len(negative_links),
                    'neutral_count': len(neutral_links)
                }
        else:
            results = {'error': 'Por favor, ingresa una palabra clave.'}

    return render_template('index.html', results=results, current_year=current_year)

@app.route('/download', methods=['POST'])
def download_pdf():
    """
    Genera y envía un PDF con los resultados del análisis de sentimientos.
    """
    keyword = request.form.get('keyword')
    if not keyword:
        return redirect(url_for('index'))

    urls = get_top_urls_with_titles(keyword)
    if not urls:
        return redirect(url_for('index', error='No se encontraron resultados.'))

    positive_links, negative_links, neutral_links = [], [], []

    for idx, result in enumerate(urls, 1):
        url = result['url']
        title = result['title']
        serp_position = f"{idx}/1"  # Simplificado para página 1

        print(f"Procesando ({serp_position}): {url}")
        text = extract_text_from_url(url)
        print(f"Texto extraído: {text[:200]}...")  # Muestra los primeros 200 caracteres

        if not text:
            print("No se pudo extraer texto de esta URL.\n")
            continue

        polarity, sentiment = analyze_sentiment(text)
        print(f"Sentimiento: {sentiment} (Polaridad: {polarity})")

        link_info = {
            'serp_position': serp_position,
            'title': title,
            'url': url,
            'polarity': polarity
        }

        if sentiment == 'Positivo':
            positive_links.append(link_info)
        elif sentiment == 'Negativo':
            negative_links.append(link_info)
        else:
            neutral_links.append(link_info)

    pdf_data = {
        'keyword': keyword,
        'positive_links': positive_links,
        'negative_links': negative_links,
        'neutral_links': neutral_links,
        'positive_count': len(positive_links),
        'negative_count': len(negative_links),
        'neutral_count': len(neutral_links),
        'current_year': datetime.now().year
    }

    rendered = render_template('pdf_template.html', **pdf_data)
    pdf_file = HTML(string=rendered).write_pdf()

    pdf_io = io.BytesIO(pdf_file)
    pdf_io.seek(0)

    return send_file(
        pdf_io,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'Análisis_de_Sentimientos_{keyword}.pdf'
    )

if __name__ == "__main__":
    # **Corrección: Cambiar el puerto para evitar conflictos**
    app.run(debug=True, port=5001)
