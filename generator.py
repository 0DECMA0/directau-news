import feedparser
import google.generativeai as genai
import os
import re
import json
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

# 1. Configuración de Logging Profesional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 2. Configuración de Seguridad y API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logging.error("No se encontró GEMINI_API_KEY en el archivo .env")
    exit(1)

genai.configure(api_key=api_key)
# Seguimos usando el modelo de tu suscripción pro
model = genai.GenerativeModel('gemini-3-flash-preview')

RSS_URLS = [
    'https://www.abc.net.au/news/feed/51120/rss.xml',
    'https://www.9news.com.au/rss'
]

def crear_slug_seguro(texto: str) -> str:
    """Genera un nombre de archivo seguro eliminando caracteres especiales."""
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')[:40]

def editor_ia(titulo: str, resumen: str) -> Optional[Dict[str, str]]:
    """Envía la noticia a Gemini con reglas de seguridad para redes sociales."""
    prompt = f"""
    Actúa como Editor Jefe de DirectAU.news y Estratega de Redes Sociales.
    Basado en: "{titulo}" y "{resumen}", genera el siguiente contenido en inglés australiano:
    
    1. 'web_article': Un artículo profesional de 3 párrafos detallados. Debe incluir contexto sobre el impacto en Australia y un tono serio.
    2. 'reels_script': Un guion de 15-20 segundos de alto impacto. 
       REGLA DE ORO DE SEGURIDAD (Algoritmo): Prohibido usar palabras como 'killed', 'died', 'blood', 'murder' o 'accident' directamente. 
       Usa eufemismos profesionales como 'passed away', 'tragic loss', 'incident', 'unfortunate event' o 'sad news' para evitar el shadowban en TikTok/Reels.

    RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO:
    {{
        "web_article": "Texto extenso para la web...",
        "reels_script": "Guion optimizado para el algoritmo..."
    }}
    """
    try:
        response = model.generate_content(prompt)
        # Limpieza de formato markdown si la IA lo incluye
        respuesta_limpia = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(respuesta_limpia)
    except json.JSONDecodeError:
        logging.error(f"Error parseando JSON para el título: {titulo}")
        return None
    except Exception as e:
        logging.error(f"Error de IA: {e}")
        return None

def scraping_australia():
    directorio_salida = 'src/content/news'
    os.makedirs(directorio_salida, exist_ok=True)
    
    for url in RSS_URLS:
        logging.info(f"Conectando a: {url}")
        feed = feedparser.parse(url)
        
        for entry in feed.entries[:3]:
            logging.info(f"Procesando: {entry.title}")
            
            contenido_ia = editor_ia(entry.title, entry.summary)
            
            if contenido_ia and "web_article" in contenido_ia and "reels_script" in contenido_ia:
                slug = crear_slug_seguro(entry.title)
                ruta_archivo = os.path.join(directorio_salida, f"{slug}.md")
                
                # Inyectamos el guion "Safe" en el Frontmatter para tu uso personal
                markdown_content = f"""---
title: "{entry.title.replace('"', "'")}"
date: "{entry.published}"
reels_script: "{contenido_ia['reels_script'].replace('"', "'")}"
---

{contenido_ia['web_article']}
"""
                with open(ruta_archivo, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                logging.info(f"✅ Guardado con éxito: {slug}.md")
            else:
                logging.warning(f"⚠️ Falló la generación para: {entry.title}")

if __name__ == "__main__":
    logging.info("Iniciando motor de noticias inteligente DirectAU...")
    scraping_australia()
    logging.info("Proceso finalizado.")