import re
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional, Dict
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


# Inicializar conexión con Google Sheets
def init_google_sheets():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            GOOGLE_SHEETS_CREDENTIALS, SCOPES
        )
        client = gspread.authorize(creds)
        # logger.info("Autenticación con Google Sheets exitosa")
        
        spreadsheet = client.open(SPREADSHEET_NAME)
        # logger.info(f"Hoja de cálculo '{SPREADSHEET_NAME}' encontrada")
        return spreadsheet
    except Exception as e:
        logger.error(f"Error detallado al inicializar Google Sheets: {str(e)}", exc_info=True)
        return None


def buscar_celular(spreadsheet, worksheet_name: str, busqueda: str) -> Optional[Dict]:
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)

        # Encabezados esperados (se mantiene tu validación original)
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
                # "GANACIA",
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
                # "GANACIA",
            ]

        # Obtener todos los valores (incluyendo fórmulas calculadas)
        cell_list = worksheet.get_all_values()
        actual_headers = cell_list[0]
        # logger.info(f"Headers encontrados en {worksheet_name}: {actual_headers}")

        # Verificar que los headers coincidan
        if not all(header in actual_headers for header in expected_headers):
            # logger.error("Los headers en la hoja no coinciden con los esperados")
            return None

        # Procesar registros manteniendo los valores calculados
        records = []
        for row in cell_list[1:]:
            record = {}
            for i, header in enumerate(actual_headers):
                if i < len(row):
                    record[header] = row[i] if row[i] != "" else "0"
                else:
                    record[header] = "0"
            records.append(record)

        # Búsqueda flexible
        busqueda = busqueda.upper().strip()
        busqueda_clean = re.sub(r"[^A-Z0-9\s]", "", busqueda)
        busqueda_parts = re.sub(r"[^a-zA-Z0-9\s]", "", busqueda).split()
        
        # Eliminar espacios extras y estandarizar GB
        busqueda_normalized = ' '.join(busqueda_parts).replace("GB", "GB ").replace("  ", " ")

        best_match = None
        best_score = 0

        for record in records:
            celular = str(record.get("CELULAR", "")).upper()
            celular_clean = re.sub(r"[^A-Z0-9\s]", "", celular)
            celular_normalized = ' '.join(celular_clean.split()).replace("GB", "GB ").replace("  ", " ")

            # Coincidencia exacta
            if busqueda_normalized == celular_normalized:
                return record

            # Coincidencia parcial estricta
            match_all_parts = all(part in celular_normalized for part in busqueda_parts)
            if match_all_parts:
                # Priorizar coincidencias más cercanas
                score = sum(1 for part in busqueda_parts if part in celular_normalized)
                if score > best_score:
                    best_score = score
                    best_match = record

        # Solo devolver el mejor match si al menos coincide con la mayoría de las partes
        if best_match and best_score >= len(busqueda_parts) * 0.7:  # 70% de coincidencia
            return best_match
        return None

    except Exception as e:
        logger.error(f"Error al buscar en {worksheet_name}: {str(e)}", exc_info=True)
        return None


# Limpiar y formatear valores monetarios
def clean_currency(value):
    if isinstance(value, str):
        # Eliminar símbolos de moneda y puntos de mil
        cleaned = value.replace("$", "").replace(".", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    elif isinstance(value, (int, float)):
        return float(value)
    return 0.0


# Formatear número como moneda
def format_currency(value):
    try:
        value = clean_currency(value)
        return "${:,.0f}".format(value).replace(",", ".")
    except Exception as e:
        logger.error(f"Error al formatear valor: {e}")
        return str(value)


# Procesar consulta de Krediya
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


# Analizar el mensaje del usuario para extraer financiera y modelo
def parse_user_message(message: str) -> tuple:
    message = message.lower().strip()

    # Patrón para extraer financiera y modelo
    pattern = re.compile(
        r"(?:precios?|precio|info|informaci[oó]n|consulta)\s*(?:por|de|para)?\s*"
        r"(krediya|kredi|credia|crediya|adelantos|adelanto|sumas\s*pay|sumaspay|sumas|addi|"
        r"banco\s*de\s*bogota|bancobogota|bogota|brilla|recompra|re\s*compra|contado)\s*"
        r"(?:de|del|para|sobre)?\s*(.+)",
        re.IGNORECASE,
    )

    match = pattern.search(message)
    if match:
        financiera = match.group(1).lower()
        modelo = match.group(2).strip()

        # Normalizar nombres de financieras
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
            "contado": "contado",
        }

        financiera = financiera_map.get(financiera, financiera)

        # Limpiar el modelo de celular
        modelo = re.sub(r"[^a-zA-Z0-9\s]", "", modelo).upper()
        modelo = modelo.replace("GB", "GB ").replace("  ", " ").strip()

        return financiera, modelo

    return None, None
