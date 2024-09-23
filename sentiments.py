from textblob import TextBlob
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import requests
from bs4 import BeautifulSoup

# Descargar los recursos necesarios de NLTK (solo la primera vez)
nltk.download('punkt', quiet=True)
nltk.download('vader_lexicon', quiet=True)

# Inicializar el analizador VADER
sid = SentimentIntensityAnalyzer()

# Listas de frases clave
negative_phrases = [
    "mal servicio", "peor restaurante", "horrible comida", "desagradable ambiente",
    "pésimo trato", "queja constante", "error en la reserva", "insatisfacción total",
    "fatal experiencia", "desastre gastronómico", "terrible atención",
    "inaceptable calidad", "lamentable manejo", "malo en todos los aspectos",
    "deficiente personal", "insuficiente limpieza", "incompetente administración",
    "injusto precio", "incorrecto pedido", "peor opción", "fallo en la entrega",
    "servicio lento", "comida fría", "atención descuidada", "reservación fallida",
    "precio exagerado", "ambiente ruidoso", "personal grosero"
]
positive_phrases = [
    "excelente servicio", "fantástico restaurante", "recomendado por todos",
    "buena comida", "mejor opción", "sorprendente ambiente", "maravilloso trato",
    "genial atención", "positivo ambiente", "agradable experiencia",
    "increíble calidad", "perfecto manejo", "superior atención",
    "fabuloso personal", "extraordinario servicio", "eficiente administración",
    "exitoso evento", "beneficioso plan", "afortunada elección",
    "brillante ejecución", "rápido servicio", "comida deliciosa", "amable personal",
    "limpieza impecable", "ambiente acogedor", "precio justo", "atención excelente",
    "excelente relación calidad-precio"
]

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

        # Eliminar scripts y estilos
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()

        # Extraer texto de las etiquetas relevantes
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3'])
        text = ' '.join([elem.get_text(separator=' ', strip=True) for elem in text_elements])

        # Si el texto está vacío, intentar usar el título de la página
        if not text.strip():
            text = soup.title.string if soup.title else ''

        return text
    except Exception as e:
        print(f"Error al extraer texto de {url}: {e}")
        return ""

def classify_sentiment(text):
    """
    Clasifica el sentimiento basado en frases clave.

    Args:
        text (str): Texto a analizar.

    Returns:
        str: Sentimiento clasificado ('Positivo', 'Negativo' o 'Neutro').
    """
    text_lower = text.lower()  # Convertir el texto a minúsculas

    # Contadores para frases clave
    negative_count = sum(phrase in text_lower for phrase in negative_phrases)
    positive_count = sum(phrase in text_lower for phrase in positive_phrases)

    # Determinar el sentimiento basado en conteos
    if negative_count > positive_count:
        return 'Negativo'
    elif positive_count > negative_count:
        return 'Positivo'
    else:
        return 'Neutro'

def analyze_sentiment(text):
    """
    Analiza el sentimiento del texto proporcionado utilizando VADER y frases clave.

    Args:
        text (str): Texto a analizar.

    Returns:
        tuple: Polaridad (float) y Sentimiento (str).
    """
    # Análisis con VADER
    scores = sid.polarity_scores(text)
    polarity = scores['compound']

    # Clasificación basada en VADER
    if polarity >= 0.05:
        vader_sentiment = 'Positivo'
    elif polarity <= -0.05:
        vader_sentiment = 'Negativo'
    else:
        vader_sentiment = 'Neutro'

    # Clasificación basada en frases clave
    keyword_sentiment = classify_sentiment(text)

    # Priorizar la clasificación basada en frases clave sobre VADER
    if keyword_sentiment == 'Negativo':
        return polarity, 'Negativo'
    elif keyword_sentiment == 'Positivo':
        return polarity, 'Positivo'
    else:
        return polarity, vader_sentiment
