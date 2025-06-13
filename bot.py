import logging
import re
from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from config.settings import RECOMPRA_WORKSHEET, VALORES_WORKSHEET

from utils.utils_methods import (
    init_google_sheets,
    buscar_celular,
    format_currency,
    procesar_krediya,
    parse_user_message,
    clean_currency,
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto por una clave segura en producción

def procesar_recompra(data):
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
        f"📱 {data.get('CELULAR', 'N/A')}\n\n"
        f"📊 Información para RECOMPRA 📊\n\n"
        f"Precio de Venta: {format_currency(data.get('VENTA', 'N/A'))}\n"
        f"Inicial Financiera ({porcentaje}%): {inicial_financiera}\n"
        f"Inicial real: {inicial_real}"
    )
    return response

def procesar_contado(data):
    try:
        precio_base = clean_currency(data.get("PRECIO BASE", 0))
        VALOR_EXTRA = 180000
        precio_contado = precio_base + VALOR_EXTRA
        response = (
            f"📱 {data.get('CELULAR', 'N/A')}\n\n"
            f"💰 PRECIO DE CONTADO 💰\n\n"
            f"💵 Total Contado: {format_currency(precio_contado)}"
        )
    except Exception as e:
        logger.error(f"Error calculando precio contado: {e}")
        response = f"Error calculando el precio de contado"
    return response

def procesar_financiera_generica(data, financiera):
    try:
        precio_base = clean_currency(data.get("PRECIO BASE", 0))
        precio_addi_sumas = clean_currency(data.get("PRECIO ADDI Y SUMAS", 0))
        total = precio_base + precio_addi_sumas

        response = (
            f"📱 {data.get('CELULAR', 'N/A')}\n\n"
            f"📊 Información para {financiera.upper()} 📊\n\n"
            f"💰 Total: {format_currency(total)}"
        )
    except Exception as e:
        logger.error(f"Error calculando precio para {financiera}: {e}")
        response = f"Error calculando el precio para {financiera}"
    return response

@app.route("/bot", methods=["POST"])
def bot():
    incoming_msg = request.values.get("Body", "").strip()
    user_number = request.values.get("From", "")
    resp = MessagingResponse()
    msg = resp.message()

    # Inicializar conexión con Google Sheets
    spreadsheet = init_google_sheets()
    if not spreadsheet:
        msg.body("Error de conexión con Google Sheets")
        return str(resp)

    # Mensaje de bienvenida si el mensaje está vacío o es un saludo
    if not incoming_msg or incoming_msg.lower() in [
        "hola",
        "hi",
        "hello",
        "buenos dias",
    ]:
        welcome_msg = (
            "¡Hola! 👋\n\n"
            "Soy tu asistente para consultar precios de celulares con diferentes financieras.\n\n"
            "Para consultar precios, escribe:\n"
            "'precios por [financiera] de [modelo del celular]'\n\n"
            "Ejemplo:\n"
            "'precios por krediya de redmi A2 64gb 2gb'\n\n"
            "Financieras disponibles:\n"
            "- Krediya\n- Adelantos\n- Sumas Pay\n- Addi\n- Banco de Bogotá\n- Brilla\n- Recompra"
        )
        msg.body(welcome_msg)
        return str(resp)

    # Si el usuario está respondiendo a opciones
    if incoming_msg.isdigit() and 'pending_options' in session:
        selected = session['pending_options'].get(incoming_msg)
        if selected:
            financiera = session['pending_financiera']
            # Limpiar la sesión
            session.pop('pending_options', None)
            session.pop('pending_financiera', None)
            
            # Procesar la selección normalmente
            if financiera == "recompra":
                response = procesar_recompra(selected)
            elif financiera == "contado":
                response = procesar_contado(selected)
            elif financiera in ["krediya", "adelantos"]:
                response = procesar_krediya(selected, financiera)
            else:
                response = procesar_financiera_generica(selected, financiera)
            
            msg.body(response)
            return str(resp)

    # Procesar consulta de precios
    financiera, modelo_celular = parse_user_message(incoming_msg)

    if not financiera or not modelo_celular:
        error_msg = (
            "No entendí tu consulta. Por favor usa el formato:\n"
            "'precios por [financiera] de [modelo del celular]'\n\n"
            "Ejemplo:\n"
            "'precios por krediya de redmi A2 64gb 2gb'\n\n"
            "O simplemente escribe el modelo del celular que deseas consultar."
        )
        msg.body(error_msg)
        return str(resp)

    # Buscar información del celular
    data = buscar_celular(spreadsheet, 
                         RECOMPRA_WORKSHEET if financiera == "recompra" else VALORES_WORKSHEET, 
                         modelo_celular)
    
    # Manejar los resultados de la búsqueda
    if isinstance(data, dict) and "multiple_options" in data:
        options = data["multiple_options"]
        # Verificar si hay una coincidencia exacta entre las opciones
        exact_match = next((opt for opt in options if opt.get("CELULAR", "").upper().strip() == modelo_celular.upper().strip()), None)
        
        if exact_match:
            # Si encontramos una coincidencia exacta entre las opciones, mostrarla directamente
            if financiera == "recompra":
                response = procesar_recompra(exact_match)
            elif financiera == "contado":
                response = procesar_contado(exact_match)
            elif financiera in ["krediya", "adelantos"]:
                response = procesar_krediya(exact_match, financiera)
            else:
                response = procesar_financiera_generica(exact_match, financiera)
        else:
            # Mostrar opciones si no hay coincidencia exacta
            response = "📱 Encontramos varias opciones similares:\n\n"
            for i, option in enumerate(options[:5], 1):
                celular = option.get("CELULAR", "Desconocido")
                response += f"{i}. {celular}\n"
            response += "\nPor favor responde con el número de la opción que deseas consultar."
            session['pending_options'] = {str(i): opt for i, opt in enumerate(options[:5], 1)}
            session['pending_financiera'] = financiera
    elif data:
        # Procesar el único resultado encontrado
        if financiera == "recompra":
            response = procesar_recompra(data)
        elif financiera == "contado":
            response = procesar_contado(data)
        elif financiera in ["krediya", "adelantos"]:
            response = procesar_krediya(data, financiera)
        else:
            response = procesar_financiera_generica(data, financiera)
    else:
        # Verificar si está en la otra hoja
        other_worksheet = VALORES_WORKSHEET if financiera == "recompra" else RECOMPRA_WORKSHEET
        other_data = buscar_celular(spreadsheet, other_worksheet, modelo_celular)
        
        if other_data:
            if isinstance(other_data, dict) and "multiple_options" in other_data:
                options = other_data["multiple_options"]
                exact_match = next((opt for opt in options if opt.get("CELULAR", "").upper().strip() == modelo_celular.upper().strip()), None)
                
                if exact_match:
                    celular = exact_match.get("CELULAR", "N/A")
                    if financiera == "recompra":
                        response = f"El modelo {celular} no está disponible para RECOMPRA, pero está en otras financieras."
                    else:
                        response = f"El modelo {celular} solo está disponible para RECOMPRA."
                else:
                    response = "📱 Encontramos opciones similares en otras financieras:\n\n"
                    for i, option in enumerate(options[:5], 1):
                        celular = option.get("CELULAR", "Desconocido")
                        response += f"{i}. {celular}\n"
                    response += "\nPor favor responde con el número de la opción que deseas consultar."
                    session['pending_options'] = {str(i): opt for i, opt in enumerate(options[:5], 1)}
                    session['pending_financiera'] = "recompra" if financiera != "recompra" else "valores"
            else:
                celular = other_data.get("CELULAR", "N/A")
                if financiera == "recompra":
                    response = (
                        f"El modelo {celular} no está disponible para RECOMPRA, pero tenemos:\n\n"
                        f"📱 {celular}\n\n"
                        f"📊 Información disponible en otras financieras 📊\n\n"
                        f"Precio de Venta: {format_currency(other_data.get('VENTA', 'N/A'))}\n"
                        f"Precio con financiación: {format_currency(other_data.get('PRECIO ADDI Y SUMAS', 'N/A'))}\n"
                        f"💡 Consulta por financieras como Krediya, Adelantos, etc."
                    )
                else:
                    response = (
                        f"El modelo {celular} solo está disponible para RECOMPRA.\n\n"
                        f"📱 {celular}\n\n"
                        f"📊 Información para RECOMPRA 📊\n\n"
                        f"Precio de Venta: {format_currency(other_data.get('VENTA', 'N/A'))}\n"
                        f"Precio Total: {format_currency(other_data.get('PRECIO ADDI Y SUMAS', 'N/A'))}\n"
                        f"💡 Sin inicial requerida"
                    )
        else:
            response = f"No se encontró información para el modelo: {modelo_celular}"

    msg.body(response)

    # Registrar la interacción
    logger.info(f"Consulta recibida de {user_number}: {incoming_msg}")

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True, port=5000) # para desarrollo
    # app.run(host='0.0.0.0', debug=False, port=5000) # para producción