import pandas as pd
import streamlit as st
from datetime import datetime
from copy import deepcopy
from fuzzywuzzy import fuzz, process
import re

# Inicializar las claves de session_state si no existen
if "district_selected" not in st.session_state:
    st.session_state["district_selected"] = False

if "current_district" not in st.session_state:
    st.session_state["current_district"] = None

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Configuración inicial de la página
st.set_page_config(page_title="SazónBot", page_icon=":pot_of_food:")
st.title("🍲 SazónBot")

# Mensaje de bienvenida
intro = """¡Bienvenido a Sazón Bot, el lugar donde todos tus antojos de almuerzo se hacen realidad!"""
st.markdown(intro)

# Función para cargar el menú desde un archivo CSV
def load_menu(csv_file):
    menu = pd.read_csv(csv_file, delimiter=';')
    return menu

# Función para cargar los distritos de reparto desde otro CSV
def load_districts(csv_file):
    districts = pd.read_csv(csv_file)
    return districts

# Función para filtrar el menú por distrito
def filter_menu_by_district(menu, district_actual):
    if district_actual is None:
        return pd.DataFrame()  # Retornar un DataFrame vacío si el distrito es None
    return menu[menu['Distrito Disponible'].str.contains(district_actual, na=False)]

# Función para verificar el distrito con similitud
def verify_district(prompt, districts):
    if not prompt:
        return None

    district_list = districts['Distrito'].tolist()
    best_match, similarity = process.extractOne(prompt, district_list)
    if similarity > 75:
        return best_match
    return None

# Función mejorada para extraer el pedido y la cantidad usando similitud
def improved_extract_order_and_quantity(prompt, menu):
    if not prompt:
        return {}

    pattern = r"(\d+|uno|dos|tres|cuatro|cinco)?\s*([^\d,]+)"
    orders = re.findall(pattern, prompt.lower())

    order_dict = {}
    menu_items = menu['Plato'].tolist()

    num_text_to_int = {'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5}

    for quantity, dish in orders:
        dish_cleaned = dish.strip()
        dish_cleaned = normalize_dish_name(dish_cleaned)

        best_match, similarity = process.extractOne(dish_cleaned, menu_items, scorer=fuzz.token_set_ratio)

        if similarity > 65:
            if not quantity:
                quantity = 1
            elif quantity.isdigit():
                quantity = int(quantity)
            else:
                quantity = num_text_to_int.get(quantity, 1)

            order_dict[best_match] = quantity

    return order_dict

# Función para normalizar los nombres de los platos y manejar abreviaciones
def normalize_dish_name(dish_name):
    dish_name = dish_name.lower()

    dish_variations = {
        "ají de gallina": ["aji de gallina", "ajies de gallina", "gallina"],
        "anticuchos": ["anticucho", "antichucos", "antochucos"],
        "sopa a la minuta": ["sopa", "minuta"]
    }

    for standard_name, variations in dish_variations.items():
        if any(variation in dish_name for variation in variations):
            return standard_name

    return dish_name

# Función para verificar los pedidos contra el menú disponible
def verify_order_with_menu(order_dict, menu):
    available_orders = {}
    unavailable_orders = []

    for dish, quantity in order_dict.items():
        if dish in menu['Plato'].values:
            available_orders[dish] = quantity
        else:
            unavailable_orders.append(dish)

    return available_orders, unavailable_orders

# Función para mostrar el menú en un formato amigable
def format_menu(menu):
    if menu.empty:
        return "No hay platos disponibles."

    formatted_menu = []
    for idx, row in menu.iterrows():
        formatted_menu.append(
            f"**{row['Plato']}**  \n{row['Descripción']}  \n**Precio:** S/{row['Precio']}"
        )
    return "\n\n".join(formatted_menu)

# Cargar el menú y los distritos
menu = load_menu("carta.csv")
districts = load_districts("distritos.csv")

# Estado inicial del chatbot
initial_state = [
    {"role": "system", "content": "You are SazónBot. A friendly assistant helping customers with their lunch orders."},
    {
        "role": "assistant",
        "content": f"👨‍🍳 Antes de comenzar, ¿de dónde nos visitas? Por favor, menciona tu distrito (por ejemplo: Miraflores)."
    },
]

# Inicializar la conversación
if "messages" not in st.session_state:
    st.session_state["messages"] = deepcopy(initial_state)
    st.session_state["district_selected"] = False
    st.session_state["current_district"] = None

# Botón para limpiar la conversación
clear_button = st.button("Limpiar Conversación", key="clear")
if clear_button:
    st.session_state["messages"] = deepcopy(initial_state)
    st.session_state["district_selected"] = False
    st.session_state["current_district"] = None

# Mostrar el historial de la conversación
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"], avatar="🍲" if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# Entrada del usuario
if user_input := st.chat_input("Escribe aquí..."):
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    if not st.session_state["district_selected"]:
        district = verify_district(user_input, districts)
        if not district:
            response = f"Lo siento, pero no entregamos en ese distrito. Distritos disponibles: {', '.join(districts['Distrito'].tolist())}."
        else:
            st.session_state["district_selected"] = True
            st.session_state["current_district"] = district
            filtered_menu = filter_menu_by_district(menu, district)
            menu_display = format_menu(filtered_menu)

            response = f"Gracias por proporcionar tu distrito: **{district}**. Aquí está el menú disponible para tu área:\n\n{menu_display}\n\n**¿Qué te gustaría pedir?** Ejm: 2 Pescado a la Plancha."
    else:
        order_dict = improved_extract_order_and_quantity(user_input, menu)
        if not order_dict:
            response = "😊 No has seleccionado ningún plato del menú. Escribe la cantidad seguida del plato, ejm: 2 Pescado a la Plancha."
        else:
            available_orders, unavailable_orders = verify_order_with_menu(order_dict, menu)
            if unavailable_orders:
                response = f"Lo siento, los siguientes platos no están disponibles: {', '.join(unavailable_orders)}."
            else:
                response = f"Tu pedido ha sido registrado: {', '.join([f'{qty} x {dish}' for dish, qty in available_orders.items()])}. ¡Gracias!"

    # Mostrar la respuesta del asistente
    with st.chat_message("assistant", avatar="🍲"):
        st.markdown(response)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": response})

