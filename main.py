import pandas as pd
import streamlit as st
from datetime import datetime
from copy import deepcopy
from openai import OpenAI
import re
from fuzzywuzzy import process  # Para similitud en nombres de distritos

# Cargar el API key de OpenAI desde Streamlit Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configuración inicial de la página
st.set_page_config(page_title="SazónBot", page_icon=":pot_of_food:")
st.title("🍲 SazónBot")

# Mostrar mensaje de bienvenida
intro = """¡Bienvenido a Sazón Bot, el lugar donde todos tus antojos de almuerzo se hacen realidad!

Comienza a chatear con Sazón Bot y descubre qué puedes pedir, cuánto cuesta y cómo realizar tu pago. ¡Estamos aquí para ayudarte a disfrutar del mejor almuerzo!."""
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


# Función para verificar el distrito
def verify_district(prompt, districts):
    districts=districts['Distrito'].tolist()
    for word in districts:  # Iterar sobre la lista de distritos
        if word in prompt:  # Comprobar si el distrito está en el texto del prompt
            return True  # Retorna el distrito encontrado
    return None

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

# Función para clasificar el plato
def classify_order(prompt, menu):
    for word in prompt.split(","):
        if word in menu['Plato'].values:
            return word  # Retorna el nombre del plato encontrado
    return None

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
            response = f"Lo siento, pero no entregamos en ese distrito. Estos son los distritos disponibles: {', '.join(districts)}."
        else:
            st.session_state["district_selected"] = True
            st.session_state["current_district"] = user_input
            # Filtrar el menú por distrito y mostrarlo
            filtered_menu = filter_menu_by_district(menu, user_input)
            menu_display = format_menu(filtered_menu)

            response = f"Gracias por proporcionar tu distrito: **{user_input}**. Aquí está el menú disponible para tu área:\n\n{menu_display}\n\n**¿Qué te gustaría pedir?**"
    else:       
        filtered_menu = filter_menu_by_district(menu, st.session_state["current_district"])
        order = classify_order(user_input, menu)  # Asegúrate de que `classify_order` considere el menú filtrado
        if not order:
            response = "😊 No has seleccionado ningún plato del menú. Por favor revisa."
        else:
            response = f"Tu pedido ha sido registrado: **{order}**. ¡Gracias!"
            st.session_state["last_order"] = order
    
    # Mostrar la respuesta del asistente
    with st.chat_message("assistant", avatar="🍲"):
        st.markdown(response)
        
     # Guardar el mensaje en la sesión
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": response})


# Función para extraer el pedido y la cantidad usando expresiones regulares
def extract_order_and_quantity(prompt, menu):
    if prompt is None:
        return {}  # Retornar un diccionario vacío si el prompt es None
    
    # Expresión regular para identificar cantidades (e.g., "2 lomo saltado, 1 ceviche")
    pattern = r"(\d+)\s*([^\d,]+)"
    orders = re.findall(pattern, prompt.lower())  # Encontrar todas las coincidencias
    
    order_dict = {}
    for quantity, dish in orders:
        # Limpiar los nombres de los platos para evitar errores de mayúsculas/minúsculas
        dish_cleaned = dish.strip()
        # Buscar si el plato está en el menú
        for menu_item in menu['Plato']:
            if dish_cleaned in menu_item.lower():  # Verificar si el nombre coincide
                order_dict[menu_item] = int(quantity)  # Añadir al diccionario con la cantidad
    
    return order_dict


# Modificación de la función classify_order para manejar múltiples platos
def classify_order(prompt, menu):
    order_dict = extract_order_and_quantity(prompt, menu)
    return order_dict if order_dict else None
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



# Modificar la función verify_district para manejar valores None
def verify_district(prompt, districts):
    if prompt is None or districts is None:
        return None  # Retorna None si el prompt o districts son None
    
    district_list = districts['Distrito'].tolist()
    best_match, similarity = process.extractOne(prompt, district_list)
    if similarity > 75:  # Usar un umbral de similitud (75%)
        return best_match
    return None


# Sistema de estados basado en etapas del flujo de conversación
def update_conversation_state(state, response):
    if state == "awaiting_district":
        return "awaiting_order"  # Si se confirmó el distrito, se pasa a esperar el pedido
    elif state == "awaiting_order":
        return "order_confirmed"  # Si se confirmó el pedido, se pasa al estado final
    return state

# Modificar el flujo del chatbot para que cambie de estado dinámicamente
if not st.session_state["district_selected"]:
    district = verify_district(user_input, districts)
    if not district:
        response = f"Lo siento, pero no entregamos en ese distrito. Estos son los distritos disponibles: {', '.join(districts['Distrito'].tolist())}."
    else:
        st.session_state["district_selected"] = True
        st.session_state["current_district"] = district
        st.session_state["state"] = update_conversation_state("awaiting_district", district)
        filtered_menu = filter_menu_by_district(menu, district)
        menu_display = format_menu(filtered_menu)
        response = f"Gracias por proporcionar tu distrito: **{district}**. Aquí está el menú disponible para tu área:\n\n{menu_display}\n\n**¿Qué te gustaría pedir?**"
else:
    order_dict = classify_order(user_input, filtered_menu)
    if not order_dict:
        response = "😊 No has seleccionado ningún plato del menú. Por favor revisa."
    else:
        available_orders, unavailable_orders = verify_order_with_menu(order_dict, filtered_menu)
        if unavailable_orders:
            response = f"Lo siento, los siguientes platos no están disponibles: {', '.join(unavailable_orders)}."
        else:
            response = f"Tu pedido ha sido registrado: {', '.join([f'{qty} x {dish}' for dish, qty in available_orders.items()])}. ¡Gracias!"
            st.session_state["state"] = update_conversation_state("awaiting_order", response)

# Plantillas de respuesta
response_templates = {
    "awaiting_district": "Por favor, indícanos tu distrito para comenzar.",
    "invalid_district": "Lo siento, no entregamos en ese distrito. Aquí están los disponibles: {available_districts}.",
    "awaiting_order": "Gracias por confirmar tu distrito. Aquí está el menú disponible: {menu}. ¿Qué te gustaría pedir?",
    "order_confirmed": "Tu pedido ha sido registrado. ¿Te gustaría agregar algo más?",
    "invalid_order": "Los siguientes platos no están disponibles: {unavailable_orders}.",
}


