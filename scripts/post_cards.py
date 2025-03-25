import json
import requests
import sys

# Ruta al archivo de casos que generaste
input_file = 'salesforce_cases_to_post.json'
output_ids_file = 'cases_posted_ids.json'

# Tu instancia y token de Salesforce (ajustar según tu sandbox)
SALESFORCE_URL = 'https://smartsystems--dev.sandbox.my.salesforce.com'
ACCESS_TOKEN = 'Bearer 00DSu000001nMI9!AQEAQMGB09r7__aQ8lnEodeCO7F097dhHPi7H7hdyBT8Ynf8CWCNcdsC.LI_2c_TrcFCoM70bkK3QzoYXc35l_Xk4xq_SxYl'
API_VERSION = 'v60.0'

headers = {
    'Authorization': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

def print_progress_bar(iteration, total, prefix='Progreso:', suffix='', length=50):
    """
    Imprime una barra de progreso en la consola.
    iteration: número actual de la iteración (1-based)
    total: total de iteraciones
    prefix: texto que aparece antes de la barra
    suffix: texto que aparece al final de la barra
    length: longitud de la barra en caracteres
    """
    percent = iteration / total * 100
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    # \r vuelve al inicio de la línea, end='' evita salto de línea
    # flush para que se imprima inmediatamente
    sys.stdout.write(f'\r{prefix} |{bar}| {percent:.2f}%  {suffix}')
    sys.stdout.flush()
    if iteration == total:
        # al terminar, saltar de línea
        print()

# Cargar los casos
with open(input_file, 'r', encoding='utf-8') as f:
    cases = json.load(f)

cases_count = len(cases)
id_map = {}  # Mapeo: Subject -> Salesforce ID

print(f"Se crearán {cases_count} casos en Salesforce...\n")

for i, case in enumerate(cases, start=1):
    subject = case.get("Subject")
    
    # Eliminamos cualquier campo no permitido (si hubiese, por ejemplo "idCard")
    case.pop("idCard", None)
    payload = json.dumps(case, ensure_ascii=False)
    url = f"{SALESFORCE_URL}/services/data/{API_VERSION}/sobjects/Case"

    response = requests.post(url, headers=headers, data=payload.encode('utf-8'))

    if response.status_code == 201:
        sf_id = response.json().get("id")
        # Mensaje opcional (podrías eliminarlo si no querés saturar la consola)
        # print(f"Caso creado con ID: {sf_id}")
        if subject:
            id_map[subject] = sf_id
    else:
        print(f"\nError al crear caso: {response.status_code} - {response.text}")

    # Actualizar la barra de progreso
    print_progress_bar(i, cases_count, prefix='Progreso:', suffix=f'({i}/{cases_count})')

# Guardar el mapeo Subject → SalesforceId
with open(output_ids_file, 'w', encoding='utf-8') as f:
    json.dump(id_map, f, indent=2)

print(f"\nIDs de casos guardados en '{output_ids_file}'")
