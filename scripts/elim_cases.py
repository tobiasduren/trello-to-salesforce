import requests
import sys
import time

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
        print()  # Nueva línea al finalizar

# Configuración de Salesforce (ajustá según tu sandbox)
SALESFORCE_URL = 'https://smartsystems--dev.sandbox.my.salesforce.com'
ACCESS_TOKEN = 'Bearer 00DSu000001nMI9!AQEAQMGB09r7__aQ8lnEodeCO7F097dhHPi7H7hdyBT8Ynf8CWCNcdsC.LI_2c_TrcFCoM70bkK3QzoYXc35l_Xk4xq_SxYl'
API_VERSION = 'v60.0'

headers = {
    'Authorization': ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

# Consulta SOQL para obtener los IDs de los casos
soql_query = "SELECT Id FROM Case"
query_url = f"{SALESFORCE_URL}/services/data/{API_VERSION}/query/?q={soql_query}"

print("Consultando casos en Salesforce...")
response = requests.get(query_url, headers=headers)
if response.status_code != 200:
    print(f"Error al consultar los casos: {response.status_code} - {response.text}")
    sys.exit(1)

data = response.json()
cases = data.get("records", [])
total_cases = len(cases)
print(f"Se encontraron {total_cases} casos.")
print("Procediendo a eliminar los casos...")

for i, record in enumerate(cases):
    case_id = record.get("Id")
    delete_url = f"{SALESFORCE_URL}/services/data/{API_VERSION}/sobjects/Case/{case_id}"
    del_response = requests.delete(delete_url, headers=headers)
    # Actualizamos la barra de progreso sin imprimir cada mensaje individual
    print_progress_bar(i + 1, total_cases, prefix='Progreso', suffix='completado', length=50)
    time.sleep(0.1)  # Opcional, para visualizar la actualización

print("\nProceso completado.")
