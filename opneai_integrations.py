import openai
import logging
from config.settings import OPENAI_API_KEY
from typing import Optional, Dict, List

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configurar la API de OpenAI
openai.api_key = OPENAI_API_KEY

def analyze_user_query(query: str, context: str = "") -> Dict:
    """
    Analiza la consulta del usuario usando OpenAI para extraer intención y parámetros.
    """
    try:
        prompt = f"""
        Eres un asistente especializado en consultas sobre precios de celulares y financieras.
        Analiza la siguiente consulta del usuario y extrae:
        1. La financiera solicitada (krediya, adelantos, sumas pay, addi, banco de bogotá, brilla, recompra, contado)
        2. El modelo exacto del celular (incluyendo capacidad de almacenamiento y RAM si se menciona)
        3. La intención principal (consultar precio, comparar, etc.)

        Contexto: {context}
        Consulta: "{query}"

        Devuelve la respuesta en formato JSON con las claves: financiera, modelo, intencion.
        Si no se puede determinar algún valor, usa null.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente especializado en análisis de consultas sobre precios de celulares."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        # Extraer y parsear la respuesta JSON
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError:
            logger.error("Error al parsear la respuesta de OpenAI")
            return {"financiera": None, "modelo": None, "intencion": None}
            
    except Exception as e:
        logger.error(f"Error en OpenAI API: {e}")
        return {"financiera": None, "modelo": None, "intencion": None}

def enhance_response_with_ai(original_response: str, user_query: str, data: Dict) -> str:
    """
    Mejora la respuesta original con información contextual usando OpenAI.
    """
    try:
        prompt = f"""
        Eres un asistente de ventas de celulares. El usuario preguntó: "{user_query}".
        
        Esta es la información que encontramos en la hoja de cálculo:
        {data}
        
        Esta fue la respuesta original que planeábamos enviar:
        "{original_response}"
        
        Mejora esta respuesta para que sea más natural, útil y persuasiva, manteniendo toda la información técnica.
        Incluye recomendaciones relevantes si es apropiado.
        Responde en el mismo idioma que la consulta del usuario.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente de ventas especializado en celulares y planes de financiación."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error al mejorar respuesta con OpenAI: {e}")
        return original_response

def suggest_alternatives(user_query: str, available_options: List[Dict]) -> str:
    """
    Sugiere alternativas relevantes usando OpenAI cuando no se encuentra exactamente lo que busca el usuario.
    """
    try:
        options_str = "\n".join([f"{i+1}. {opt.get('CELULAR', 'Desconocido')}" for i, opt in enumerate(available_options)])
        
        prompt = f"""
        El usuario buscó: "{user_query}" pero no encontramos una coincidencia exacta.
        
        Estas son las opciones disponibles que podrían interesarle:
        {options_str}
        
        Genera un mensaje amigable que:
        1. Explique que no encontramos exactamente lo que buscaba
        2. Presente las opciones disponibles de manera clara
        3. Sugiera cuál podría ser la mejor opción basada en la consulta del usuario
        4. Pida al usuario que seleccione una opción o reformule su búsqueda
        
        El mensaje debe ser conciso (máximo 3 párrafos) y en el mismo idioma de la consulta.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente de ventas especializado en celulares."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=350
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error al generar sugerencias con OpenAI: {e}")
        # Respuesta por defecto si falla OpenAI
        default_response = "📱 Encontramos varias opciones similares:\n\n"
        default_response += options_str
        default_response += "\n\nPor favor responde con el número de la opción que deseas consultar."
        return default_response