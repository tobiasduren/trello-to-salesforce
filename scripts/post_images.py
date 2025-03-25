import json
import requests
import base64
import os
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options

# ----- Configuración de Selenium para usar tu perfil real de Edge -----
def get_trello_session():
    edge_options = Options()
    # Usa un directorio de perfil que ya tengas configurado y donde estés logueado en Trello.
    edge_options.add_argument(r"--user-data-dir=C:\Temp\EdgeProfile")  
    # Puedes agregar argumentos para reducir la detección de automatización
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Edge(options=edge_options)
    return driver

# ----- Configuración de Trello y Salesforce -----
# Estos datos se usan sólo para identificar las cards en el JSON de Trello;
# en esta versión no usás el key/token en la URL para la descarga, sino que usás la sesión autenticada.
trello_file = 'trello_export.json'         # JSON exportado de Trello
mapping_file = 'cases_posted_ids.json'      # Mapeo: Subject (nombre de la card) -> Salesforce Case ID

SALESFORCE_URL = 'https://smartsystems--dev.sandbox.my.salesforce.com'
ACCESS_TOKEN_SF = 'Bearer 00DSu000001nMI9!AQEAQMGB09r7__aQ8lnEodeCO7F097dhHPi7H7hdyBT8Ynf8CWCNcdsC.LI_2c_TrcFCoM70bkK3QzoYXc35l_Xk4xq_SxYl'
API_VERSION = 'v60.0'

headers_sf = {
    'Authorization': ACCESS_TOKEN_SF,
    'Content-Type': 'application/json'
}

# Encabezados para requests (para emular navegador)
headers_trello = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.141 Safari/537.36 Edg/116.0.1938.81',
    'Accept': '*/*',
    'Referer': 'https://trello.com/'
}

# ----- Obtener mapeo y JSON de Trello -----
with open(mapping_file, 'r', encoding='utf-8') as f:
    subject_to_sf_id = json.load(f)

with open(trello_file, 'r', encoding='utf-8') as f:
    trello_data = json.load(f)

cards = trello_data.get('cards', [])

# ----- Obtener cookies de sesión usando Selenium -----
print("Iniciando Edge para obtener cookies...")
driver = get_trello_session()

# Para obtener cookies, navegamos a una URL de Trello; por ejemplo, la página de un board.
# Esto asegurará que la sesión tenga las cookies necesarias.
driver.get("https://trello.com")
# time.sleep(5)  # Esperar unos segundos para que cargue la sesión
cookies = driver.get_cookies()
driver.quit()

# Crear sesión de requests y agregar las cookies
session = requests.Session()
for cookie in cookies:
    session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])
print("Cookies obtenidas, se procede a descargar imágenes...")

# ----- Procesar cada card y sus attachments -----
for card in cards:
    subject = card.get("name", "")
    # Usamos el subject para obtener el Salesforce Case ID
    sf_case_id = subject_to_sf_id.get(subject)
    if not sf_case_id:
        # print(f"⚠️ No se encontró Salesforce Case ID para el caso con Subject: {subject}")
        continue

    attachments = card.get("attachments", [])
    if not attachments:
        continue

    for attachment in attachments:
        # Filtrar solo attachments de imagen (según mimeType)
        mime_type = attachment.get("mimeType", "")
        if not mime_type.startswith("image/"):
            continue

        file_name = attachment.get("name") or attachment.get("fileName", "Attachment")
        base_url = attachment.get("url")
        if not base_url:
            continue

        # En este caso usamos la URL tal cual; asumimos que la URL exportada (ej. con dominio trello.com/1/) funciona con la sesión
        # O bien, si es necesario, la convertimos a api.trello.com/1/
        download_url = base_url.replace("https://trello.com/1/", "https://trello.com/1/")
        
        print(f"Descargando imagen: {file_name} del caso {subject}")
        resp = session.get(download_url, headers=headers_trello)
        if resp.status_code == 200:
            file_content = resp.content
            # Codificar en base64 para enviarlo a Salesforce
            encoded_body = base64.b64encode(file_content).decode('utf-8')
        else:
            print(f"❌ Error al descargar {download_url}: {resp.status_code}")
            continue

        # Preparar payload para el Attachment en Salesforce
        payload = {
            "ParentId": sf_case_id,
            "Name": file_name,
            "Body": encoded_body,
            "ContentType": mime_type if mime_type else "application/octet-stream"
        }

        url_sf = f"{SALESFORCE_URL}/services/data/{API_VERSION}/sobjects/Attachment"
        response_sf = requests.post(url_sf, headers=headers_sf, json=payload)
        if response_sf.status_code == 201:
            sf_attachment_id = response_sf.json().get("id")
            print(f"✅ Attachment creado para el caso {sf_case_id}: {sf_attachment_id}")
        else:
            print(f"❌ Error creando attachment para el caso {sf_case_id}: {response_sf.status_code} - {response_sf.text}")
