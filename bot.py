import logging
from flask import Flask, request
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
    if financiera == "recompra":
        data = buscar_celular(spreadsheet, RECOMPRA_WORKSHEET, modelo_celular)
        if data:
            response = (
                f"📱 {data.get('CELULAR', 'N/A')}\n\n"
                f"📊 Información para RECOMPRA 📊\n\n"
                f"Precio de Venta: {format_currency(data.get('VENTA', 'N/A'))}\n"
                f"Precio Total: {format_currency(data.get('PRECIO ADDI Y SUMAS', 'N/A'))}\n"
                f"💡 Sin inicial requerida"
            )
        else:
            response = (
                f"No se encontró información para recompra del modelo: {modelo_celular}"
            )
    elif financiera == "contado":
        data = buscar_celular(spreadsheet, VALORES_WORKSHEET, modelo_celular)
        if data:
            try:
                precio_base = clean_currency(data.get("PRECIO BASE", 0))
                VALOR_EXTRA = 180000
                precio_contado = precio_base + VALOR_EXTRA
                response = (
                    f"📱 {data.get('CELULAR', 'N/A')}\n\n"
                    f"💰 PRECIO DE CONTADO 💰\n\n"
                    # f"Precio Base: {format_currency(precio_base)}\n"
                    # f"Valor Adicional: $180.000\n"
                    # f"➖➖➖➖➖➖➖➖➖\n"
                    f"💵 Total Contado: {format_currency(precio_contado)}"
                )
            except Exception as e:
                logger.error(f"Error calculando precio contado: {e}")
                response = f"Error calculando el precio de contado para {modelo_celular}"
        else:
            response = f"No se encontró información para el modelo: {modelo_celular}"
    else:
        data = buscar_celular(spreadsheet, VALORES_WORKSHEET, modelo_celular)
        if data:
            if financiera in ["krediya", "adelantos"]:
                response = procesar_krediya(data, financiera)
            else:
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
        else:
            # Verificar si está en recompra
            data_recompra = buscar_celular(spreadsheet, RECOMPRA_WORKSHEET, modelo_celular)
            if data_recompra:
                # Verificar si hay coincidencia suficiente
                celular_recompra = str(data_recompra.get("CELULAR", "")).upper()
                if all(part in celular_recompra for part in modelo_celular.split()):
                    response = (
                        f"El modelo {modelo_celular} solo está disponible para RECOMPRA.\n\n"
                        f"📱 {celular_recompra}\n\n"
                        f"📊 Información para RECOMPRA 📊\n\n"
                        f"Precio de Venta: {format_currency(data_recompra.get('VENTA', 'N/A'))}\n"
                        f"Precio Total: {format_currency(data_recompra.get('PRECIO ADDI Y SUMAS', 'N/A'))}\n"
                        f"💡 Sin inicial requerida"
                    )
                else:
                    response = f"No se encontró información exacta para el modelo: {modelo_celular}"
            else:
                response = f"No se encontró información para el modelo: {modelo_celular}"

    msg.body(response)

    # Registrar la interacción
    logger.info(f"Consulta recibida de {user_number}: {incoming_msg}")

    return str(resp)


if __name__ == "__main__":
    # app.run(debug=True, port=5000) # para desarrollo
    app.run(host='0.0.0.0', debug=False, port=5000) # para producción
