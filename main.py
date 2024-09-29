import pandas as pd
import streamlit as st
import re
from fuzzywuzzy import fuzz, process

# Cargar el menú desde el archivo CSV
def load_menu(csv_file):
    return pd.read_csv(csv_file, delimiter=';')

# Función mejorada para extraer el pedido y la cantidad
def improved_extract_order_and_quantity(prompt, menu):
    if not prompt:
        return {}

    # Expresión regular mejorada para manejar números escritos y valores numéricos
    pattern = r"(\d+|uno|dos|tres|cuatro|cinco)?\s*([^\d,]+)"
    orders = re.findall(pattern, prompt.lower())  # Encuentra todas las coincidencias

    order_dict = {}
    menu_items = menu['Plato'].tolist()  # Lista de platos en el menú

    # Diccionario para convertir números escritos en texto a enteros
    num_text_to_int = {'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5}

    for quantity, dish in orders:
        dish_cleaned = dish.strip()  # Limpiar los espacios adicionales

        # Usar fuzz.token_sort_ratio para obtener la mejor coincidencia con el menú
        best_match, similarity = process.extractOne(dish_cleaned, menu_items, scorer=fuzz.token_sort_ratio)

        # Si la similitud es mayor al umbral del 60%
        if similarity > 60:
            # Si no se especifica cantidad, asignar 1
            if not quantity:
                quantity = 1
            # Convertir la cantidad en número, ya sea digitada o escrita
            elif quantity.isdigit():
                quantity = int(quantity)
            else:
                # Convertir el texto a número utilizando el diccionario
                quantity = num_text_to_int.get(quantity, 1)

            # Agregar al diccionario el plato con la cantidad correspondiente
            order_dict[best_match] = quantity

    return order_dict

# Cargar el menú y los distritos
menu = pd.DataFrame({
    'Plato': ['Ceviche', 'Anticucho', 'Lomo Saltado', 'Causa', 'Sopa Criolla', 'Tortillas', 'Tallarines'],
    'Distrito Disponible': ['Miraflores', 'Miraflores', 'San Isidro', 'San Isidro', 'Miraflores', 'San Isidro', 'Miraflores']
})

# Verificar si el pedido está en el menú
def verify_order_with_menu(order_dict, menu):
    available_orders = {}
    unavailable_orders = []

    for dish, quantity in order_dict.items():
        if dish in menu['Plato'].values:
            available_orders[dish] = quantity
        else:
            unavailable_orders.append(dish)
    
    return available_orders, unavailable_orders

# Simulación del chatbot (entrada del usuario y respuesta)
def run_chatbot(user_input):
    if not user_input:
        return "😊 No has seleccionado ningún plato del menú. Por favor revisa."

    # Extraer el pedido del usuario
    order_dict = improved_extract_order_and_quantity(user_input, menu)

    if not order_dict:
        return "😊 No has seleccionado ningún plato del menú. Por favor revisa."

    # Verificar si los platos están disponibles en el menú
    available_orders, unavailable_orders = verify_order_with_menu(order_dict, menu)

    if unavailable_orders:
        return f"Lo siento, los siguientes platos no están disponibles: {', '.join(unavailable_orders)}."
    else:
        return f"Tu pedido ha sido registrado: {', '.join([f'{qty} x {dish}' for dish, qty in available_orders.items()])}. ¡Gracias!"

# Streamlit UI
st.title("SazónBot - Prueba de pedidos")

# Entrada del usuario
user_input = st.text_input("Escribe tu pedido:")

# Generar respuesta
if user_input:
    response = run_chatbot(user_input)
    st.write(response)
