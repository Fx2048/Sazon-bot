import pandas as pd
import streamlit as st
from datetime import datetime
from copy import deepcopy
from fuzzywuzzy import process  # Para similitud en nombres de distritos
import re

# Cargar el API key de OpenAI desde Streamlit Secrets (si se requiere para otros fines)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configuración inicial de la página
st.set_page_config(page_title="SazónBot", page_icon=":pot_of_food:")
st.title("🍲 SazónBot")

# Mostrar mensaje de bienvenida
intro = """¡Bienvenido a Sazón Bot, el lugar donde todos tus antojos de almuerzo se hacen realidad!

Comienza a chatear con Sazón Bot y descubre qué puedes pedir, cuánto cuesta y cómo realizar tu pago. ¡Estamos aquí para ayudarte a disfrutar del mejor almuerzo!"""
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
        return None  # Retornar None si el prompt es None

    district_list = districts['Distrito'].tolist()
    best_match, similarity = process.extractOne(prompt, district_list)
    if similarity > 75:  # Usar un umbral de similitud del 75%
        return best_match
    return None

# Función para extraer el pedido y la cantidad usando expresiones regulares
def extract_order_and_quantity(prompt, menu):
    if not prompt:
        return {}  # Retornar un diccionario vacío si el prompt es None
    
    # Expresión regular para identificar cantidades y nombres de platos
    pattern = r"(\d+)\s*([^\d,]+)"  # Buscar 'cantidad + nombre del plato'
    orders = re.findall(pattern, prompt.lower())  # Encontrar todas las coincidencias
    
    order_dict = {}
    for quantity, dish in orders:
        # Limpiar los nombres de los platos para evitar errores de mayúsculas/minúsculas
        dish_cleaned = dish.strip()
        # Buscar si el plato está en el menú usando coincidencia parcial
        for menu_item in menu['Plato']:
            if dish_cleaned in menu_item.lower():  # Verificar si el nombre coincide
                order_dict[menu_item] = int(quantity)  # Añadir al diccionario con la cantidad
    
    return order_dict

# Función para verificar los pedidos contra el menú disponible
def verify_order_with_menu(order_dict, menu):
    available_orders = {}
    unavailable_orders = []

    # Iterar sobre el diccionario de pedidos y verificar con el menú
    for dish, quantity in order_dict.items():
        if dish in menu['Plato'].values:
            available_orders[dish] = quantity
        else:
            unavailable_orders.append(dish)
    
    return available_orders, unavailable_orders

# Función para mostrar el menú en un formato más amigable
def format_menu(menu):
    if menu.empty:
        return "No hay platos disponibles."
    
    formatted_menu = []
    for idx, row in menu.iterrows():
        formatted_menu.append(
            f"**{row['Plato']}**  \n{row['Descripción']}  \n**Precio:** S/{row['Precio']}"
        )
    return "\n\n".join(formatted_menu)

# Cargar el menú y los distritos desde archivos CSV
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
if "current_district" not in st.session_state:
    st.session_state["current_district"] = None

# Inicializar la conversación si no existe en la sesión
if "messages" not in st.session_state:
    st.session_state["messages"] = deepcopy(initial_state)
    st.session_state["district_selected"] = False  # Indica si ya se seleccionó un distrito
    st.session_state["current_district"] = None  # Almacena el distrito actual

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
        # Verificar el distrito
        district = verify_district(user_input, districts)
        if not district:
            response = f"Lo siento, pero no entregamos en ese distrito. Estos son los distritos disponibles: {', '.join(districts['Distrito'].tolist())}."
        else:
            st.session_state["district_selected"] = True
            st.session_state["current_district"] = district
            # Filtrar el menú por distrito y mostrarlo
            filtered_menu = filter_menu_by_district(menu, district)
            menu_display = format_menu(filtered_menu)

            response = f"Gracias por proporcionar tu distrito: **{district}**. Aquí está el menú disponible para tu área:\n\n{menu_display}\n\n**¿Qué te gustaría pedir?**"
    else:
        # Procesar el pedido con cantidades específicas
        order_dict = extract_order_and_quantity(user_input, menu)
        if not order_dict:
            response = "😊 No has seleccionado ningún plato del menú. Por favor revisa."
        else:
            available_orders, unavailable_orders = verify_order_with_menu(order_dict, menu)
            if unavailable_orders:
                response = f"Lo siento, los siguientes platos no están disponibles: {', '.join(unavailable_orders)}."
            else:
                response = f"Tu pedido ha sido registrado: {', '.join([f'{qty} x {dish}' for dish, qty in available_orders.items()])}. ¡Gracias!"

    # Mostrar la respuesta del asistente
    with st.chat_message("assistant", avatar="🍲"):
        st.markdown(response)
        
    # Guardar el mensaje en la sesión
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": response})
