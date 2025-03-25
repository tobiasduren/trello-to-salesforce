import json
from collections import defaultdict
from datetime import datetime

# Archivos
input_file = 'trello_export.json'
output_cases_file = 'salesforce_cases_to_post.json'
output_comments_file = 'comments_by_subject.json'

# Cargar JSON exportado desde Trello
with open(input_file, 'r', encoding='utf-8') as f:
    trello_data = json.load(f)

actions = trello_data.get('actions', [])
cards_info = trello_data.get('cards', [])

# 1) Crear un diccionario "cards" con una entrada para cada card del JSON
cards = {}

for c in cards_info:
    id_card = c["id"]
    cards[id_card] = {
        "SuppliedName": "",      # lo definiremos con acciones si existe
        "Status": "Nuevo",       # por defecto
        "Origin": "Web",         # por defecto
        "Subject": c.get("name", ""),  # Nombre de la card
        "Description": c.get("desc", "").strip() or "Sin descripción",
        "Comments": []
    }

# 2) Recorrer las acciones para actualizar o agregar datos a las tarjetas
for action in actions:
    tipo = action.get('type')
    data = action.get('data', {})
    member_creator = action.get('memberCreator', {})
    card_data = data.get('card', {})
    
    id_card = data.get('idCard') or card_data.get('id')
    if not id_card or id_card not in cards:
        # Si la acción se refiere a una card que no está en 'cards', la ignoramos.
        continue

    card_name = card_data.get('name', '')
    list_name = (data.get('list') or data.get('listAfter') or {}).get('name', '')
    author = member_creator.get('fullName', '')
    date_str = action.get('date', '')

    if tipo == 'createCard':
        # Si la card no tiene Subject o SuppliedName, las completamos
        if not cards[id_card]["Subject"]:
            cards[id_card]["Subject"] = card_name
        if not cards[id_card]["SuppliedName"]:
            cards[id_card]["SuppliedName"] = author

    elif tipo == 'updateCard':
        # Ajustar el Status según la lista
        if list_name.lower() in ['done', 'cerrado']:
            cards[id_card]["Status"] = "Cerrado"
        else:
            cards[id_card]["Status"] = "En Proceso"

    elif tipo == 'commentCard':
        comment_text = data.get('text', '').strip()
        if comment_text:
            # Intentar formatear la fecha
            try:
                fecha = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                formatted_date = fecha.strftime('%Y-%m-%dT%H:%M:%S')
            except Exception:
                formatted_date = date_str

            comment_obj = {
                "author": author,
                "date": formatted_date,
                "text": comment_text
            }
            cards[id_card]["Comments"].append(comment_obj)

        # Si la card no tiene Subject o SuppliedName, las completamos
        if not cards[id_card]["Subject"]:
            cards[id_card]["Subject"] = card_name
        if not cards[id_card]["SuppliedName"]:
            cards[id_card]["SuppliedName"] = author

# 3) Si no hay SuppliedName, asignar "No SuppliedName nro. X"
no_supplied_name_counter = 1
for c_id, data in cards.items():
    if not data["SuppliedName"]:
        data["SuppliedName"] = f"No SuppliedName nro. {no_supplied_name_counter}"
        no_supplied_name_counter += 1

# 4) Convertir el diccionario de cards en la lista final (cases_finales) y comments_por_subject
cases_finales = []
comments_por_subject = {}

for c_id, case_data in cards.items():
    subject = case_data["Subject"]
    # Construir la lista final de casos
    case_sin_comentarios = {
        "SuppliedName": case_data["SuppliedName"],
        "Status": case_data["Status"],
        "Origin": case_data["Origin"],
        "Subject": subject,
        "Description": case_data["Description"]
    }
    cases_finales.append(case_sin_comentarios)
    
    # Mapear el Subject a la lista de comentarios
    comments_por_subject[subject] = case_data["Comments"]

# Guardar JSON de casos
with open(output_cases_file, 'w', encoding='utf-8') as f:
    json.dump(cases_finales, f, indent=2, ensure_ascii=False)

# Guardar JSON de comentarios por subject
with open(output_comments_file, 'w', encoding='utf-8') as f:
    json.dump(comments_por_subject, f, indent=2, ensure_ascii=False)

print(f"{len(cases_finales)} casos procesados.")
print(f"Guardado en '{output_cases_file}' y '{output_comments_file}'")
