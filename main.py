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
    return menu[menu['Distrito Disponible'].str.contains(district_actual, na=False, case=False)]

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

    # Definir el patrón para capturar las cantidades y nombres de platos en la entrada del usuario
    pattern = r"(\d+|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)?\s*([^\d,]+)"
    orders = re.findall(pattern, prompt.lower())

    order_dict = {}
    menu_items = menu['Plato'].tolist()

    num_text_to_int = {
        'uno': 1,
        'una': 1,
        'dos': 2,
        'tres': 3,
        'cuatro': 4,
        'cinco': 5,
        'seis': 6,
        'siete': 7,
        'ocho': 8,
        'nueve': 9,
        'diez': 10,
        'media docena': 6,
        'docena': 12,
        'cien': 100,
        'mil': 1000,
        # Variaciones con errores ortográficos
        'un': 1,
        'uuno': 1,
        '5.': 5,
        '2 ': 2,
        'cinco!': 5,
        'och0': 8,
        'diez ': 10,
        'media': 6,  # Omitiendo "docena"
        'decena': 10,
        'doscenas': 24,  # Asumiendo que se refiere a 2 docenas
    }

    for quantity, dish in orders:
        dish_cleaned = dish.strip()
        dish_cleaned = normalize_dish_name(dish_cleaned)

        # Buscar la mejor coincidencia para el nombre del plato en el menú usando fuzzy matching
        best_match, similarity = process.extractOne(dish_cleaned, menu_items, scorer=fuzz.token_set_ratio)

        if similarity > 65:
            # Convertir el valor textual de la cantidad a número entero, si corresponde
            if not quantity:
                quantity = 1
            elif quantity.isdigit():
                quantity = int(quantity)
            else:
                quantity = num_text_to_int.get(quantity, 1)

            # Sumar la cantidad de pedidos si el plato ya ha sido mencionado previamente
            if best_match in order_dict:
                order_dict[best_match] += quantity
            else:
                order_dict[best_match] = quantity

    return order_dict

# Función para normalizar los nombres de los platos y manejar abreviaciones
def normalize_dish_name(dish_name):
    dish_name = dish_name.lower()

    # Diccionario con las variaciones de nombres de platos
# Definir un diccionario para manejar las variaciones de nombres de platos
    dish_variations = {
        "Arroz con Pollo": [
            "arroz con pollo", "arroz cn pollo", "arroz conpllo", "Arroz Con Pollo",
            "ARROZ CON POLLO", "arr0z con pollo", "arroz c/ pollo", "arroz pollo",
            "arrozconpollo", "arroz, pollo"
        ],
        "Tallarines Verdes": [
            "tallarines verdes", "talarines verdes", "tallarinesv verdes", "Tallarines Verdes",
            "TALLARINES VERDES", "tallarines vrdes", "tallarines vrd", "tallarine$ verdes","tallarines",
        ],
        "Lomo Saltado": [
            "lomo saltado", "lomo$altado", "lomo saltado", "Lomo Saltado",
            "LOMO SALTADO", "lomo sltado", "lomo s/tado", "lomosaltado","lomo",
        ],
        "Causa Limeña": [
            "causa limena", "causalimeña", "Causa Limeña", "CAUSA LIMEÑA",
            "causa limena", "causa limeña", "cau$a limeña","causa",
        ],
        "Ají de Gallina": [
            "aji de gallina", "aji de gallina", "aji gallina", "ají de gallina",
            "AJI DE GALLINA", "ajies de gallina", "ajis de gallina", "aji de gallin","ajies","ajíes",
            "ajis", "aji's", "ajíé de gallina"
        ],
        "Pollo a la Brasa": [
            "pollo a la brasa", "polloala brasa", "pollo a la brasa", "Pollo a la Brasa",
            "POLLO A LA BRASA", "pollo brasa", "pollo brasa", "p0llo a la brasa","brasa",
        ],
        "Seco de Cordero": [
            "seco de cordero", "sec0 de cordero", "Seco de Cordero", "SECO DE CORDERO",
            "seco cordero", "sec0 cordero","seco","SECO","Seco",
        ],
        "Pachamanca": [
            "pachamanca", "pachamanc", "pachamanca", "Pachamanca",
            "PACHAMANKA", "pacha manka", "pacha mnka","pacha manca","Pacha manca",
        ],
        "Tacu Tacu": [
            "tacu tacu", "tacutacu", "tacu-tacu", "Tacu Tacu",
            "TACU TACU", "tacutac", "tacutac$"
        ],
        "Sopa a la Minuta": [
            "sopa a la minuta", "sopaala minuta", "sopa a la mnuta", "Sopa a la Minuta",
            "SOPA A LA MINUTA", "sopa min", "sopa mn","sopa","sopas",
        ],
        "Rocoto Relleno": [
            "rocoto relleno", "rocoto rellen", "rocoto relleno", "Rocoto Relleno",
            "ROCOTO RELLENO", "rocotorellen", "rocoto rllen"
        ],
        "Chicharrón de Cerdo": [
            "chicharron de cerdo", "chicharrones cerdo", "chicharrones", "Chicharrón de Cerdo",
            "CHICHARRÓN DE CERDO", "chicharron", "chicharron cerdo", "chicharron d cerdo"
        ],
        "Sanguchito de Chicharrón": [
            "sanguchito de chicharron", "sanguchito chicharrón", "sanguchitos chicharrón",
            "Sanguchito de Chicharrón", "SANGUCHITO DE CHICHARRÓN", "sanguchito", "sanguchitodechicharrón"
        ],
        "Pescado a la Plancha": [
            "pescado a la plancha", "pesacado a la plancha", "pescado plancha",
            "Pescado a la Plancha", "PESCADO A LA PLANCHA", "pesca d a la plancha"
        ],
        "Bistec a la parrilla": [
            "bistec a la parrilla", "bistec la parrilla", "bistec parrilla",
            "Bistec a la Parrilla", "BISTEC A LA PARRILLA", "bistec a la prrilla", "bistec parrila"
        ],
        "Tortilla de Huauzontle": [
            "tortilla de huauzontle", "tortilla huauzontle", "tortilla de huauzonlte",
            "Tortilla de Huauzontle", "TORTILLA DE HUAUZONTLE", "tortila de huauzontle"
        ],
        "Ceviche Clásico": [
            "ceviche clasico", "ceviche clasico", "cevichelásico", "Ceviche Clásico",
            "CEVICHE CLÁSICO", "cevi chclásico", "ceviche clsc"
        ],
        "Sopa Criolla": [
            "sopa criolla", "sopacriolla", "sopa criolla", "Sopa Criolla",
            "SOPA CRIOLLA", "sopa crll", "sopa c.",
        ],
        "Pollo en Salsa de Cacahuate": [
            "pollo en salsa de cacahuate", "pollo en salsa cacahuate", "pollo s/cacahuate",
            "Pollo en Salsa de Cacahuate", "POLLO EN SALSA DE CACAHUATE", "polloen salsacahuate","salsa de cacahuate",
        ],
        "Ensalada de Quinoa": [
            "ensalada de quinoa", "ensalada quinoa", "ensalqdadequinoa", "Ensalada de Quinoa",
            "ENSALADA DE QUINOA", "ensalada d quinoa", "ensaladas quinoa","ensalada", "quinoa",
        ],
        "Anticuchos": [
            "anticuchos", "anticucho", "antichucos", "antochucos", "Anticuchos",
            "ANTICUCHOS", "anticuhos", "anticuchos$"
        ],
        "Bebidas Naturales": [
            "bebidas naturales", "bebida$ naturales", "bebida natural", "Bebidas Naturales",
            "BEBIDAS NATURALES", "bebidn naturales", "beidas natrales", "bebidas",
        ]
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
    {"role": "assistant", "content": "👨‍🍳 Antes de comenzar, ¿de dónde nos visitas? Por favor, menciona tu distrito (por ejemplo: Miraflores)."}
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
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Procesar la entrada del usuario
user_input = st.chat_input("Escribe tu mensaje...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    user_input_cleaned = user_input.lower().strip()

    if not st.session_state.district_selected:
        # Verificar el distrito
        district = verify_district(user_input_cleaned, districts)
        if district:
            st.session_state.district_selected = True
            st.session_state.current_district = district
            st.session_state.messages.append({"role": "assistant", "content": f"✅ Distrito verificado: {district}."})
            # Filtrar el menú por el distrito seleccionado
            filtered_menu = filter_menu_by_district(menu, district)
            menu_display = format_menu(filtered_menu)
            st.session_state.messages.append({"role": "assistant", "content": menu_display})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "❌ No reconozco ese distrito. Por favor, menciona tu distrito nuevamente."})
    else:
        # Procesar el pedido
        order_dict = improved_extract_order_and_quantity(user_input_cleaned, menu)
        available_orders, unavailable_orders = verify_order_with_menu(order_dict, filter_menu_by_district(menu, st.session_state.current_district))

        # Responder al usuario sobre los pedidos disponibles y no disponibles
        if available_orders:
            available_orders_msg = "Tus pedidos disponibles son:"
            for dish, quantity in available_orders.items():
                available_orders_msg += f"\n- {quantity}x {dish}"
            st.session_state.messages.append({"role": "assistant", "content": available_orders_msg})
        if unavailable_orders:
            unavailable_orders_msg = "Los siguientes platos no están disponibles:"
            for dish in unavailable_orders:
                unavailable_orders_msg += f"\n- {dish}"
            st.session_state.messages.append({"role": "assistant", "content": unavailable_orders_msg})

        if not available_orders and not unavailable_orders:
            st.session_state.messages.append({"role": "assistant", "content": "❌ No encontré nada en tu pedido."})


