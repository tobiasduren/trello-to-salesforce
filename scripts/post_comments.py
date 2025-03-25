import json
import requests

# Archivos
mapping_file = 'cases_posted_ids.json'       # Mapeo: Subject (nombre del caso) -> Salesforce Case ID
comments_file = 'comments_by_subject.json'     # Comentarios mapeados por Subject 
# Ejemplo de estructura de comments_by_subject.json:
# {
#   "Case-682 de GUZZINI JORGE": [
#       {
#           "author": "Cristian Soto",
#           "username": "cristiansoto29",
#           "date": "2025-03-21T12:20:39",
#           "text": "#hipporello Automated Message: Hola JORGE, ..."
#       },
#       ...
#   ],
#   "Case-681 de Clementi Aberturas": [ ... ]
# }

# Configuración de Salesforce (ajustar según tu sandbox)
SALESFORCE_URL = 'https://smartsystems--dev.sandbox.my.salesforce.com'
ACCESS_TOKEN = 'Bearer 00DSu000001nMI9!AQEAQMGB09r7__aQ8lnEodeCO7F097dhHPi7H7hdyBT8Ynf8CWCNcdsC.LI_2c_TrcFCoM70bkK3QzoYXc35l_Xk4xq_SxYl'
API_VERSION = 'v60.0'

headers = {
    'Authorization': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

# Cargar el mapeo Subject -> Salesforce Case ID
with open(mapping_file, 'r', encoding='utf-8') as f:
    subject_to_sf_id = json.load(f)

# Cargar el archivo de comentarios (por Subject)
with open(comments_file, 'r', encoding='utf-8') as f:
    comments_by_subject = json.load(f)

# Enviar cada comentario
for subject, comments in comments_by_subject.items():
    sf_case_id = subject_to_sf_id.get(subject)
    if not sf_case_id:
        # print(f"No se encontró Salesforce ID para el caso con Subject: {subject}")
        continue

    for comment in reversed(comments):
        payload = {
            "ParentId": sf_case_id,
            "CommentBody": comment["text"],
            "IsPublished": True
        }
        url = f"{SALESFORCE_URL}/services/data/{API_VERSION}/sobjects/CaseComment"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 201:
            sf_comment_id = response.json().get("id")
            print(f"Comentario creado para el caso {sf_case_id}: {sf_comment_id}")
        else:
            print(f"Error al crear comentario para el caso {sf_case_id}: {response.status_code} - {response.text}")
