from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()
# Configuración de OpenAI desde variables de entorno
# openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuración de Google Sheets desde variables de entorno
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
VALORES_WORKSHEET = os.getenv("VALORES_WORKSHEET")
RECOMPRA_WORKSHEET = os.getenv("RECOMPRA_WORKSHEET")

# Configuración de alcance para Google Sheets
SCOPES = os.getenv("SCOPES").split(",")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
