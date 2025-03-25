import json
import requests
import base64
import os
import time
import uuid
import sys
from selenium import webdriver
from selenium.webdriver.edge.options import Options
import boto3
from botocore.exceptions import NoCredentialsError

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    """
    Imprime o actualiza la barra de progreso en la misma línea (stdout).
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        print()

# ---------------------------
# Configuración de archivos de entrada
# ---------------------------
trello_file = 'trello_export.json'         # JSON exportado de Trello (con cards y attachments)
mapping_file = 'cases_posted_ids.json'      # Mapeo: Subject -> Salesforce Case ID

# ---------------------------
# Configuración de Salesforce
# ---------------------------
SALESFORCE_URL = 'https://smartsystems--dev.sandbox.my.salesforce.com'
ACCESS_TOKEN_SF = 'Bearer 00DSu000001nMI9!AQEAQMGB09r7__aQ8lnEodeCO7F097dhHPi7H7hdyBT8Ynf8CWCNcdsC.LI_2c_TrcFCoM70bkK3QzoYXc35l_Xk4xq_SxYl'
API_VERSION = 'v60.0'
headers_sf = {
    'Authorization': ACCESS_TOKEN_SF,
    'Content-Type': 'application/json'
}

# ---------------------------
# Configuración de Trello (para descarga de attachments)
# ---------------------------
headers_trello = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.141 Safari/537.36 Edg/116.0.1938.81',
    'Accept': '*/*',
    'Referer': 'https://trello.com/'
}

# ---------------------------
# Configuración de AWS S3 (Bucket público)
# ---------------------------
BUCKET_NAME = "salesforce-cases-attachments"
def upload_to_s3_put(file_content, object_name, content_type):
    """
    Sube file_content a S3 usando un simple PUT request y retorna la URL pública.
    """
    url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"
    headers = {"Content-Type": content_type}
    response = requests.put(url, data=file_content, headers=headers)
    if response.status_code in (200, 201):
        return url
    else:
        # Se elimina el print para la barra de progreso
        # print(f"Error subiendo a S3: {response.status_code} - {response.text}")
        return None

# ---------------------------
# Función para obtener cookies de sesión de Trello con Selenium
# ---------------------------
def get_trello_session():
    from selenium.webdriver.edge.options import Options
    edge_options = Options()
    edge_options.add_argument(r"--user-data-dir=C:\Temp\EdgeProfile")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Edge(options=edge_options)
    return driver

# ---------------------------
# Obtener cookies de sesión usando Selenium
# ---------------------------
print("Iniciando Edge para obtener cookies de Trello...")
driver = get_trello_session()
driver.get("https://trello.com")
# time.sleep(5)  # Esperar para que se cargue la sesión
cookies = driver.get_cookies()
driver.quit()
session = requests.Session()
for cookie in cookies:
    session.cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])
print("Cookies obtenidas.")

# ---------------------------
# Cargar mapeo y JSON de Trello
# ---------------------------
with open(mapping_file, 'r', encoding='utf-8') as f:
    subject_to_sf_id = json.load(f)
with open(trello_file, 'r', encoding='utf-8') as f:
    trello_data = json.load(f)
cards = trello_data.get('cards', [])

# ---------------------------
# Calcular el total de attachments a procesar
# ---------------------------
total_attachments = 0
for card in cards:
    attachments = card.get("attachments", [])
    if attachments:
        for attachment in attachments:
            if attachment.get("url"):
                total_attachments += 1
print(f"Se procesarán {total_attachments} archivos adjuntos.")

# ---------------------------
# Procesar cada card: descargar attachments y subir a S3
# ---------------------------
attachments_by_subject = {}
processed_count = 0

for card in cards:
    subject = card.get("name", "")
    sf_case_id = subject_to_sf_id.get(subject)
    if not sf_case_id:
        continue
    attachments = card.get("attachments", [])
    if not attachments:
        continue
    s3_urls = []
    for attachment in attachments:
        if not attachment.get("url"):
            processed_count += 1
            print_progress_bar(processed_count, total_attachments, prefix="Progreso", suffix="completado", length=50)
            continue
        mime_type = attachment.get("mimeType", "")
        file_name = attachment.get("name") or attachment.get("fileName", "Attachment")
        base_url = attachment.get("url")
        # Usamos la URL tal cual (puedes ajustarla si es necesario)
        download_url = base_url.replace("https://trello.com/1/", "https://trello.com/1/")
        # Se quita el print de descarga
        resp = session.get(download_url, headers=headers_trello)
        if resp.status_code == 200:
            file_content = resp.content
        else:
            processed_count += 1
            print_progress_bar(processed_count, total_attachments, prefix="Progreso", suffix="completado", length=50)
            continue
        # Generar un nombre único agregando un prefijo aleatorio al nombre original
        s3_object_name = f"{uuid.uuid4().hex}_{file_name}"
        s3_url = upload_to_s3_put(file_content, s3_object_name, mime_type)
        if s3_url:
            s3_urls.append(s3_url)
        processed_count += 1
        print_progress_bar(processed_count, total_attachments, prefix="Progreso", suffix="completado", length=50)
    if s3_urls:
        attachments_by_subject[subject] = s3_urls

# ---------------------------
# Publicar un comentario en Salesforce con los enlaces de los attachments
# ---------------------------
for subject, s3_urls in attachments_by_subject.items():
    sf_case_id = subject_to_sf_id.get(subject)
    if not sf_case_id:
        continue
    lines = [f"{i+1}. {url}" for i, url in enumerate(s3_urls)]
    comment_body = "Archivos adjuntos:\n" + "\n".join(lines)
    payload = {
        "ParentId": sf_case_id,
        "CommentBody": comment_body,
        "IsPublished": True
    }
    url_sf = f"{SALESFORCE_URL}/services/data/{API_VERSION}/sobjects/CaseComment"
    response_sf = requests.post(url_sf, headers=headers_sf, json=payload)
    # Se quita el print detallado del comentario
print("\nProceso completado.")
