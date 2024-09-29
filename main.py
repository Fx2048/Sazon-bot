import pandas as pd
import streamlit as st
from datetime import datetime
from fuzzywuzzy import fuzz, process
import re

# Inicializar las claves de session_state si no existen
if "order_placed" not in st.session_state:
    st.session_state["order_placed"] = False
if "district_selected" not in st.session_state:
    st.session_state["district_selected"] = False
if "current_district" not in st.session_state:
    st.session_state["current_district"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Configuración inicial de la página
st.set_page_config(page_title="SazónBot", page_icon=":pot_of_food:")
st.title("🍲 SazónBot")

# Mostrar mensaje de bienvenida
intro = """¡Bienvenido a Sazón Bot, el lugar donde todos tus antojos de almuerzo se hacen realidad!
Comienza a chatear con Sazón Bot y descubre qué puedes pedir, cuánto cuesta y cómo realizar tu pago. ¡Estamos aquí para ayudarte a disfrutar del mejor almuerzo!"""
st.markdown(intro)

# Función para cargar el menú desde un archivo CSV
def load_menu(csv_file):
    return pd.read_csv(csv_file, delimiter=';')

# Función para cargar los distritos de reparto desde otro CSV
def load_districts(csv_file):
    return pd.read_csv(csv_file)

# Función para verificar el distrito con similitud
def verify_district(prompt, districts):
    district_list = districts['Distrito'].tolist()
    best_match, similarity = process.extractOne(prompt, district_list)
    if similarity > 65:
        return best_match
    return None

# Función para guardar el pedido en un archivo CSV
def save_order_to_csv(order_dict, district, filename="orders.csv"):
    orders_list = []
    for dish, quantity in order_dict.items():
        orders_list.append({
            'Fecha y Hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Distrito': district,
            'Plato': dish,
            'Cantidad': quantity
        })
    df_orders = pd.DataFrame(orders_list)
    df_orders.to_csv(filename, mode='a', header=False, index=False)
# Función mejorada para extraer el pedido y la cantidad usando similitud
def improved_extract_order_and_quantity(prompt, menu):
    if not prompt:
        return {}

    # Definir el patrón para capturar las cantidades y nombres de platos en la entrada del usuario
    pattern = r"(\d+|uno|dos|tres|cuatro|cinco)?\s*([^\d,]+)"
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
    'seis': 6,
    'siete': 7,
    'ocho': 8,
    'nueve': 9,
    'diez': 10,
    'once': 11,
    'doce': 12,
    'media docena': 6,
    'media docena': 6,
    'media docena de huevos': 6,
    'docena': 12,
    'docena de huevos': 12,
    'cien': 100,
    'doscientos': 200,
    'trescientos': 300,
    'cuatrocientos': 400,
    'quinientos': 500,
    'seiscientos': 600,
    'setecientos': 700,
    'ochocientos': 800,
    'novecientos': 900,
    'mil': 1000,
    'mil uno': 1001,
    'mil dos': 1002,
    'mil tres': 1003,
    # Variaciones con errores ortográficos
    'un': 1,
    'uno ': 1,
    'uuno': 1,
    'dos ': 2,
    'tres.': 3,
    'cuatro ': 4,
    'cinco!': 5,
    'siex': 6,
    'siete ': 7,
    'och0': 8,
    'nueve!': 9,
    'diez ': 10,
    'media': 6,  # Omitiendo "docena"
    'docena ': 12,
    'decena': 10,
    'doscenas': 24,  # Asumiendo que se refiere a 2 docenas
    'media docena': 6,
    'media': 6,  # Omitiendo "docena"
    '5.': 5,     # Puntuación al final
    '2 ': 2,
    'tres': 3,
    'cuatro.': 4,
    'cinco': 5,
    'seis!': 6,
    'siete,': 7,
    'ocho.': 8,
    'nueve ': 9,
    'diez': 10,
    'once ': 11,
    'doce.': 12,
    'docena': 12,
    'cien ': 100,
    'ciento': 100,
    'mil ': 1000,
    'mil uno': 1001,
    'mil y uno': 1001,
    'mil dos': 1002,
    'mil tres': 1003,
    'mil cuatro': 1004,
    'mil cinco': 1005
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

    # Definir un diccionario para manejar las variaciones de nombres de platos
    dish_variations = {
    "Arroz con Pollo": [
        "arroz con pollo", "arroz cn pollo", "arroz conpllo", "Arroz Con Pollo",
        "ARROZ CON POLLO", "arr0z con pollo", "arroz c/ pollo", "arroz pollo",
        "arrozconpollo", "arroz",
    ],
    "Tallarines Verdes": [
        "tallarines verdes", "talarines verdes", "tallarinesv verdes", "Tallarines Verdes",
        "TALLARINES VERDES", "tallarines vrdes", "tallarines vrd", "tallarine$ verdes","tallarines",
    ],
    "Lomo Saltado": [
        "lomo saltado", "lomo$altado", "lomo saltado", "Lomo Saltado",
        "LOMO SALTADO", "lomo sltado", "lomo s/tado", "lomosaltado","lomo","lomos"
    ],
    "Causa Limeña": [
        "causa limena", "causalimeña", "Causa Limeña", "CAUSA LIMEÑA",
        "causa limena", "causa limeña", "cau$a limeña","causa","causas"
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
        "seco cordero", "sec0 cordero","seco","SECO","Seco","secos",
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
        "SOPA A LA MINUTA", "sopa min", "sopa mn"
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
        "SOPA CRIOLLA", "sopa crll", "sopa c."
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
district_variations = {
    "Miraflores": ["miraflores", "miraflr", "mira flores", "miraflores", "mflrs", "miraflo", "miraflrs", "miraflorez"],
    "San Isidro": ["san isidro", "sn isidro", "san i$idro", "s anisidro", "isidro", "s. isidro", "san isid", "san isidro", "snisidro"],
    "La Molina": ["la molina", "lamolina", "la molna", "la molin", "la molin@", "la molin4", "lamolna", "la molinaz"],
    "San Borja": ["san borja", "sn borja", "san borj@", "san borj4", "s. borja", "san borj", "san borj4", "s4n borja"],
    "Santiago de Surco": ["santiago de surco", "stgo de surco", "sant de surco", "santiago surco", "sant surco", "santiago d surco", "sant d surco"],
    "Surquillo": ["surquillo", "surquill@", "surquill0", "surquill", "surquillo", "surquill0", "surquilloz"],
    "San Juan de Miraflores": ["san juan de miraflores", "sn juan de miraflores", "san juan miraflores", "s juan de miraflores", "san juan d miraflores", "s juan miraflores"],
    "Villa María del Triunfo": ["villa maría del triunfo", "villa maria del triunfo", "v. maria del triunfo", "villa m del triunfo", "villa maria triunfo", "v maria del triunfo"],
    "Lima Cercado": ["lima cercado", "lima cercad@", "lima cercad0", "lima cercad", "lima cercad0", "lima cercadaz"],
    "San Luis": ["san luis", "sn luis", "san luis", "s. luis", "san luis", "san luis", "s4n luis"],
    "Barranco": ["barranco", "barranc@", "barranc0", "barranc", "barranc0", "barrancoz"],
    "Chorrillos": ["chorrillos", "chorrill@", "chorrill0", "chorrill", "chorrill0", "chorrilloz"],
    "San Martín de Porres": ["san martín de porres", "san martin de porres", "sn martin de porres", "san martin porres", "s. martin de porres", "san martin d porres"],
    "Los Olivos": ["los olivos", "los oliv@", "los oliv0s", "los oliv", "los oliv0s", "los oliv0z"],
    "Comas": ["comas", "com@s", "com4s", "comaz", "comas", "com4s"],
    "Puente Piedra": ["puente piedra", "puente piedr@", "puente piedr0", "puente piedr", "puente piedr0", "puente piedraz"],
    "Ventanilla": ["ventanilla", "ventanill@", "ventanill0", "ventanill", "ventanill0", "ventanillaz"],
    "Callao": ["callao", "call@", "call4o", "callao", "call4o", "callaoz"]
}

def normalize_district_name(district_name):
    district_name = district_name.lower()

    for standard_name, variations in district_variations.items():
        if any(variation in district_name for variation in variations):
            return standard_name
    return district_name

def preprocess_district(district_name):
    # Convertir a minúsculas y eliminar caracteres especiales
    district_name = re.sub(r"[^a-zA-Z\s]", "", district_name.lower())
    return district_name.strip()

def verify_district(prompt, districts):
    prompt = preprocess_district(prompt)
    district_list = [preprocess_district(d) for d in districts['Distrito'].tolist()]
    best_match, similarity = process.extractOne(prompt, district_list)
    if similarity > 65:
        return best_match
    return None

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
    formatted_menu = [f"**{row['Plato']}**  \n{row['Descripción']}  \n**Precio:** S/{row['Precio']}" for idx, row in menu.iterrows()]
    return "\n\n".join(formatted_menu)

# Cargar el menú y los distritos
menu = load_menu("carta.csv")
districts = load_districts("distritos.csv")

# Botón para limpiar la conversación
clear_button = st.button("Limpiar Conversación", key="clear")
if clear_button:
    st.session_state["order_placed"] = False
    st.session_state["district_selected"] = False
    st.session_state["current_district"] = None
    st.session_state["messages"] = []

# Mostrar el historial de la conversación
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🍲" if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# Entrada del usuario
user_input = st.chat_input("Escribe aquí...")

# Procesar la conversación
if not st.session_state["order_placed"]:
    if user_input:
        order_dict = improved_extract_order_and_quantity(user_input, menu)
        if not order_dict:
            response = "😊 No has seleccionado ningún plato del menú. Escribe la cantidad seguida del plato.\n\n"
            response += format_menu(menu)
        else:
            available_orders, unavailable_orders = verify_order_with_menu(order_dict, menu)
            if unavailable_orders:
                response = f"Lo siento, los siguientes platos no están disponibles: {', '.join(unavailable_orders)}."
            else:
                st.session_state["order_placed"] = True
                st.session_state["current_order"] = available_orders
                response = f"Tu pedido ha sido registrado: {', '.join([f'{qty} x {dish}' for dish, qty in available_orders.items()])}. ¿De qué distrito nos visitas? Por favor, menciona tu distrito (por ejemplo: Miraflores)."
else:
    if user_input:
        district = verify_district(user_input, districts)
        if not district:
            response = f"Lo siento, pero no entregamos en ese distrito. Distritos disponibles: {', '.join(districts['Distrito'].tolist())}."
        else:
            st.session_state["district_selected"] = True
            st.session_state["current_district"] = district
            save_order_to_csv(st.session_state["current_order"], district)
            response = f"Gracias por tu pedido desde **{district}**. ¡Tu pedido ha sido registrado con éxito! 🍽️"

# Mostrar la respuesta del asistente
if user_input:
    with st.chat_message("assistant", avatar="🍲"):
        st.markdown(response)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": response})



