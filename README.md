# 🤖 WhatsApp-bot-credicell conectado a Google Sheet

Este es un bot de WhatsApp que utiliza el modelo de lenguaje de Twilio para generar respuestas a los mensajes de los usuarios.

## 🖥️ Instalación

1. Clona este repositorio
2. Instala las dependencias con `pip install -r requirements.txt`
3. Descarga ngrok en la siguiente página https://ngrok.com/downloads/windows?tab=download
4. Configura ngrok en tu SO (windows).
   - Descomprimir el archivo de descarga de ngrok, se vera el archivo ngrok.exe
   - Ahora crea una carpeta en el el disco C con el nombre de ngrok y copia y pega el ejecutable dentro (C:\ngrok\ngrok.exe)
   - Configura la variable de entorno, para esto ejecuta el atajo de teclado win + r y escribe el siguiente comando sysdm.cpl y aceptar.
   - Ahora ve a la pestaña opciones avanzadas -> variables de entorno -> y busca la variable path.
   - Ahora se le da en la opción editar -> nuevo y creas la variable así: C:\ngrok\
   - Por último aceptar.
5. Abre el terminal y ejecuta el bot con `python bot.py`
6. Abre otro terminal y dirijete al disco C donde creaste la carpeta de ngrok (C:\ngrok) y ejecuta el comando ngrok.exe http 5000
7. Crea un proyecto en google cloud. https://console.cloud.google.com/
8. Crear un archivo .env en la raiz del proyecto, con la siguiente información:
   - GOOGLE_SHEETS_CREDENTIALS=
   - SPREADSHEET_NAME=
   - VALORES_WORKSHEET=
   - RECOMPRA_WORKSHEET=

   # Configuración de alcance para Google Sheets
   - SCOPES=

9. ## Errores
   - 2025-05-26 16:17:09,218 - utils.utils_methods - ERROR - Error al inicializar Google Sheets: <Response [200]>
   2025-05-26 16:17:09,227 - werkzeug - INFO - 127.0.0.1 - - [26/May/2025 16:17:09] "POST /bot HTTP/1.1" 200 -
   ## Rta:/ Esto es porque el archivo de excel no está como una hoja de cálculo, abre el archivo, y en la parte de archivo dale guardar como hoja de cálculo. y tambien se debe compartir el archivo al email que está en las credenciales json "client_email"
