import re
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional, Dict, Union
from config.settings import (
    GOOGLE_SHEETS_CREDENTIALS,
    SPREADSHEET_NAME,
    VALORES_WORKSHEET,
    SCOPES,
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_google_sheets():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            GOOGLE_SHEETS_CREDENTIALS, SCOPES
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open(SPREADSHEET_NAME)
        return spreadsheet
    except Exception as e:
        logger.error(f"Error detallado al inicializar Google Sheets: {str(e)}", exc_info=True)
        return None


def buscar_celular(spreadsheet, worksheet_name: str, busqueda: str) -> Optional[Union[Dict, str]]:
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)

        # Encabezados esperados
        if worksheet_name == VALORES_WORKSHEET:
            expected_headers = [
                "CELULAR",
                "CODIGO",
                "VENTA",
                "INICIAL FINANCIERA",
                "INICIAL REAL",
                "DESCUENTO",
                "PRECIO BASE",
                "PRECIO ADDI Y SUMAS",
                "CONTADO",
            ]
        else:
            expected_headers = [
                "CELULAR",
                "CODIGO",
                "VENTA",
                "INICIAL FINANCIERA",
                "INICIAL REAL",
                "DESCUENTO",
                "PRECIO BASE",
                "PRECIO ADDI Y SUMAS",
            ]

        cell_list = worksheet.get_all_values()
        actual_headers = cell_list[0]

        if not all(header in actual_headers for header in expected_headers):
            return None

        records = []
        for row in cell_list[1:]:
            record = {}
            for i, header in enumerate(actual_headers):
                if i < len(row):
                    record[header] = row[i] if row[i] != "" else "0"
                else:
                    record[header] = "0"
            records.append(record)

        # Normalización mejorada de la búsqueda
        busqueda = busqueda.upper().strip()
        
        # Normalización especial para modelos Samsung (A35 -> A 35)
        busqueda = re.sub(r"SAMSUNG\s*A\s*(\d+)", r"SAMSUNG A \1", busqueda)
        busqueda = re.sub(r"SAMSUNG\s*([A-Z]+)\s*(\d+)", r"SAMSUNG \1 \2", busqueda)
        
        # Normalización para modelos OPPO
        busqueda = re.sub(r"OPPO\s*A\s*(\d+)", r"OPPO A\1", busqueda)
        busqueda = re.sub(r"OPPO\s*([A-Z]+)\s*(\d+)", r"OPPO \1\2", busqueda)
        
        # Normalización de memoria
        busqueda = re.sub(r"(\d+)\s*GB\s*[/]?\s*(\d+)\s*GB", r"\1GB/\2GB", busqueda)
        busqueda = re.sub(r"(\d+)\s*GB\s*[/]?\s*(\d+)\s*RAM", r"\1GB/\2RAM", busqueda)
        busqueda = re.sub(r"(\d+)\s*GB", r"\1GB", busqueda)
        busqueda = re.sub(r"(\d+)\s*RAM", r"\1RAM", busqueda)
        busqueda = re.sub(r"\s+", " ", busqueda).strip()

        exact_matches = []
        partial_matches = []

        for record in records:
            celular = str(record.get("CELULAR", "")).upper()
            
            # Aplicar las mismas normalizaciones al registro
            celular = re.sub(r"SAMSUNG\s*A\s*(\d+)", r"SAMSUNG A \1", celular)
            celular = re.sub(r"SAMSUNG\s*([A-Z]+)\s*(\d+)", r"SAMSUNG \1 \2", celular)
            celular = re.sub(r"OPPO\s*A\s*(\d+)", r"OPPO A\1", celular)
            celular = re.sub(r"OPPO\s*([A-Z]+)\s*(\d+)", r"OPPO \1\2", celular)
            celular = re.sub(r"(\d+)\s*GB\s*[/]?\s*(\d+)\s*GB", r"\1GB/\2GB", celular)
            celular = re.sub(r"(\d+)\s*GB\s*[/]?\s*(\d+)\s*RAM", r"\1GB/\2RAM", celular)
            celular = re.sub(r"(\d+)\s*GB", r"\1GB", celular)
            celular = re.sub(r"(\d+)\s*RAM", r"\1RAM", celular)
            celular = re.sub(r"\s+", " ", celular).strip()
            
            # Coincidencia exacta (comparación normalizada)
            if busqueda == celular:
                exact_matches.append(record)
                continue
                
            # Coincidencia parcial (ignorando números)
            busqueda_parts = [part for part in re.split(r'\s+|/', busqueda) if part and not part.isdigit()]
            celular_parts = [part for part in re.split(r'\s+|/', celular) if part and not part.isdigit()]
            
            if all(part in celular_parts for part in busqueda_parts):
                partial_matches.append(record)
        
        # Priorizar coincidencias exactas
        if exact_matches:
            if len(exact_matches) == 1:
                return exact_matches[0]
            return {"multiple_options": exact_matches}
            
        # Si no hay exactas pero hay parciales
        if partial_matches:
            return {"multiple_options": partial_matches[:5]}  # Limitar a 5 opciones
            
        return None

    except Exception as e:
        logger.error(f"Error al buscar en {worksheet_name}: {str(e)}", exc_info=True)
        return None


def clean_currency(value):
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(".", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    elif isinstance(value, (int, float)):
        return float(value)
    return 0.0


def format_currency(value):
    try:
        value = clean_currency(value)
        return "${:,.0f}".format(value).replace(",", ".")
    except Exception as e:
        logger.error(f"Error al formatear valor: {e}")
        return str(value)


def procesar_krediya(data: Dict, financiera: str) -> str:
    try:
        celular = data.get("CELULAR", "N/A")
        venta = format_currency(data.get("VENTA", "N/A"))
        inicial_financiera = format_currency(data.get("INICIAL FINANCIERA", "N/A"))
        inicial_real = format_currency(data.get("INICIAL REAL", "N/A"))

        # Calcular el porcentaje real
        try:
            venta_valor = clean_currency(data.get("VENTA", 0))
            inicial_financiera_valor = clean_currency(data.get("INICIAL FINANCIERA", 0))
            porcentaje = (
                round((inicial_financiera_valor / venta_valor) * 100)
                if venta_valor != 0
                else 0
            )
        except ZeroDivisionError:
            porcentaje = 0

        response = (
            f"📱 {celular}\n"
            f"📊 Información para {financiera.upper()} 📊\n\n"
            f"Precio de Venta: {venta}\n"
            f"Inicial Financiera ({porcentaje}%): {inicial_financiera}\n"
            f"Inicial real: {inicial_real}"
        )
        return response
    except Exception as e:
        logger.error(f"Error procesando Krediya: {e}")
        return "Hubo un error al procesar la información de Krediya."


def parse_user_message(message: str) -> tuple:
    message = message.lower().strip()
    
    # Primero detectar si es una consulta de contado
    if "contado" in message:
        modelo = re.sub(r"(precios?|precio|info|informaci[oó]n|consulta|por|de|para|contado)", "", message)
        modelo = re.sub(r"[^a-zA-Z0-9\s]", "", modelo).upper()
        modelo = re.sub(r"\s+", " ", modelo).strip()
        return "contado", modelo
    
    # Patrón mejorado para extraer financiera y modelo
    pattern = re.compile(
        r"(?:precios?|precio|info|informaci[oó]n|consulta)\s*(?:por|de|para)?\s*"
        r"(krediya|kredi|credia|crediya|adelantos|adelanto|sumas\s*pay|sumaspay|sumas|addi|"
        r"banco\s*de\s*bogota|bancobogota|bogota|brilla|recompra|re\s*compra)\s*"
        r"(?:de|del|para|sobre)?\s*(.+)",
        re.IGNORECASE,
    )

    match = pattern.search(message)
    if match:
        financiera = match.group(1).lower()
        modelo = match.group(2).strip()

        financiera_map = {
            "kredi": "krediya",
            "credia": "krediya",
            "crediya": "krediya",
            "adelanto": "adelantos",
            "sumaspay": "sumas pay",
            "sumas": "sumas pay",
            "bancobogota": "banco de bogota",
            "bogota": "banco de bogota",
            "re compra": "recompra",
        }
        
        financiera = financiera_map.get(financiera, financiera)

        modelo = re.sub(r"(precios?|precio|info|informaci[oó]n|consulta|por|de|para)", "", modelo)
        modelo = re.sub(r"[^a-zA-Z0-9\s]", "", modelo).upper()
        modelo = re.sub(r"\s+", " ", modelo).strip()

        return financiera, modelo

    modelo = re.sub(r"(precios?|precio|info|informaci[oó]n|consulta|por|de|para)", "", message)
    modelo = re.sub(r"[^a-zA-Z0-9\s]", "", modelo).upper()
    modelo = re.sub(r"\s+", " ", modelo).strip()
    
    return None, modelo