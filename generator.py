import feedparser
import google.generativeai as genai
import os
import re
import json
import logging
import time
import requests 
from typing import Dict, Optional
from dotenv import load_dotenv

# 1. Configuración de Logging 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 2. Configuración de Seguridad y API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logging.critical(" No se encontró GEMINI_API_KEY en el archivo .env")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3-flash-preview')

RSS_URLS = [
    'https://www.abc.net.au/news/feed/51120/rss.xml',
    'https://www.9news.com.au/rss'
]

def crear_slug_seguro(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')[:50]

def extraer_url_imagen(entry) -> Optional[str]:
    """Busca en las profundidades del RSS el enlace de la imagen original."""
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0].get('url')
    
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        for enclosure in entry.enclosures:
            if 'image' in enclosure.get('type', ''):
                return enclosure.get('href')
                
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        return entry.media_thumbnail[0].get('url')
        
    return None

def descargar_imagen(url: str, slug: str) -> str:
    """Descarga la imagen de internet y la guarda en la carpeta public/ de Astro."""
    if not url:
        return "/placeholder-news.jpg" 
        
    try:
        directorio_imagenes = os.path.join('public', 'news-images')
        os.makedirs(directorio_imagenes, exist_ok=True)
        
        ruta_local = os.path.join(directorio_imagenes, f"{slug}.jpg")
        ruta_astro = f"/news-images/{slug}.jpg" 
        
        respuesta = requests.get(url, stream=True, timeout=10)
        if respuesta.status_code == 200:
            with open(ruta_local, 'wb') as f:
                for chunk in respuesta.iter_content(1024):
                    f.write(chunk)
            logging.info(f"Imagen guardada con éxito: {slug}.jpg")
            return ruta_astro
            
    except Exception as e:
        logging.warning(f"Error al descargar la imagen {url}: {e}")
        
    return "/placeholder-news.jpg"
# --- FIN DE LA MAGIA DE IMÁGENES ---

def editor_ia(titulo: str, resumen: str) -> Optional[Dict[str, str]]:
    """El cerebro del periodista veterano. Ingeniería de Prompt para forzar saltos de línea."""
    prompt = f"""
    Actúa como un Periodista Veterano y Editor en Jefe de un prestigioso diario de Australia con 20 años de experiencia.
    Basado en el titular y resumen: "{titulo}" / "{resumen}".
    Genera el contenido en INGLÉS AUSTRALIANO respetando estas reglas:

    1. 'web_article': 
       - Usa la "Pirámide Invertida" y un tono sobrio, imparcial y de autoridad impecable.
       - REGLA DE FORMATO MARKDOWN ESTRICTO: Para que la web renderice correctamente, debes separar CADA párrafo con dobles saltos de línea (\\n\\n).
       - CITA DESTACADA: Entre el segundo y tercer párrafo, inventa una frase analítica profunda. DEBE estar rodeada por dobles saltos de línea, empezar con el símbolo `> ` y estar entre comillas.
    2. 'reels_script': Guion de 15-20 seg. REGLA SECOPS: Evita palabras baneables (killed, blood, murder) usando eufemismos para evadir filtros.
    3. 'seo_description': Un resumen cautivador de máximo 2 líneas.
    4. 'category': Clasifica en UNA de estas: Politics, Tech, Business, World, Sports, Local.

    RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO CON ESTA ESTRUCTURA EXACTA (Nota cómo la cita lleva \\n\\n antes y después para no romper el Markdown):
    {{
        "web_article": "Párrafo 1 (El Lead).\\n\\nPárrafo 2 (El Contexto).\\n\\n> \\"Frase analítica y profunda que resuma la gravedad del asunto.\\"\\n\\nPárrafo 3 (El Cierre).",
        "reels_script": "El guion seguro para redes...",
        "seo_description": "El resumen corto...",
        "category": "Local"
    }}
    """
    try:
        response = model.generate_content(prompt)
        respuesta_limpia = response.text.strip()
        
        if respuesta_limpia.startswith("```json"):
            respuesta_limpia = respuesta_limpia[7:]
        elif respuesta_limpia.startswith("```"):
            respuesta_limpia = respuesta_limpia[3:]
            
        if respuesta_limpia.endswith("```"):
            respuesta_limpia = respuesta_limpia[:-3]
            
        return json.loads(respuesta_limpia.strip())
    
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando JSON para el título '{titulo}': {e}")
        return None
    except Exception as e:
        logging.error(f"Error de conexión/IA: {e}")
        return None

def scraping_australia():
    directorio_salida = 'src/content/news'
    os.makedirs(directorio_salida, exist_ok=True)
    
    for url in RSS_URLS:
        logging.info(f"Conectando a fuente: {url}")
        feed = feedparser.parse(url)
        
        # Mantengo tu límite de 3 noticias por fuente
        for entry in feed.entries[:3]:
            logging.info(f"Redactando noticia: {entry.title}")
            
            slug = crear_slug_seguro(entry.title)
            url_imagen = extraer_url_imagen(entry)
            ruta_imagen = descargar_imagen(url_imagen, slug)
            
            contenido_ia = editor_ia(entry.title, entry.summary)
            
            if contenido_ia and "web_article" in contenido_ia and "seo_description" in contenido_ia:
                ruta_archivo = os.path.join(directorio_salida, f"{slug}.md")
                
                titulo_seguro = entry.title.replace('"', "'")
                desc_segura = contenido_ia['seo_description'].replace('"', "'")
                script_seguro = contenido_ia['reels_script'].replace('"', "'")
                categoria = contenido_ia.get('category', 'Local').replace('"', "'")
                
                markdown_content = f"""---
                title: "{titulo_seguro}"
                date: "{entry.published}"
                description: "{desc_segura}"
                category: "{categoria}"
                image: "{ruta_imagen}"
                reels_script: "{script_seguro}"
                ---
                {contenido_ia['web_article']}
                """
                with open(ruta_archivo, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                logging.info(f"Publicación lista: {slug}.md")
                
                logging.info("Esperando 20 segundos para evitar bloqueos de API gratuita...")
                time.sleep(20)
                
            else:
                logging.warning(f"Se omitió por error de redacción: {entry.title}")

if __name__ == "__main__":
    logging.info("Iniciando Motor Periodístico DirectAU (v3.0)...")
    scraping_australia()
    logging.info("Redacción finalizada.")