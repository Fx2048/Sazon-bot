import pandas as pd
import streamlit as st
from datetime import datetime
from copy import deepcopy
from fuzzywuzzy import fuzz, process
 # Para similitud en nombres de distritos
import re
import openai  # Revisa que tengas instalado openai

# Inicializar las claves de session_state si no existen
if "district_selected" not in st.session_state:
    st.session_state["district_selected"] = False  # Indica si ya se seleccionó un distrito

if "current_district" not in st.session_state:
    st.session_state["current_district"] = None  # Almacena el distrito actual

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Cargar el API key de OpenAI desde Streamlit Secrets (si es necesario)
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configuración inicial de la página
st.set_page_config(page_title="SazónBot", page_icon=":pot_of_food:")
st.title("🍲 SazónBot")

# Mensaje de bienvenida
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

# Función mejorada para extraer el pedido y la cantidad usando similitud
def extract_order_and_quantity(prompt, menu):
    """
    Extrae la cantidad y el nombre de cada plato en el pedido del usuario utilizando coincidencias parciales.
    """

    if not prompt:
        return {}  # Retornar un diccionario vacío si el prompt es None

    # Expresión regular para identificar cantidades y nombres de platos
    pattern = r"(\d+)?\s*([^\d,]+)"  # Buscar 'cantidad opcional + nombre del plato'
    orders = re.findall(pattern, prompt.lower())  # Encontrar todas las coincidencias

    order_dict = {}
    menu_items = menu['Plato'].tolist()  # Convertir los platos del menú en una lista

    for quantity, dish in orders:
        dish_cleaned = dish.strip()
        # Usar fuzzy matching para encontrar la mejor coincidencia del plato en el menú
        best_match, similarity = process.extractOne(dish_cleaned, menu_items, scorer=fuzz.partial_ratio)
        if similarity > 75:  # Si la similitud es mayor a un 75%, consideramos que es una coincidencia válida
            if not quantity:
                quantity = 1  # Si no se especifica una cantidad, asumir 1
            else:
                quantity = int(quantity)
            order_dict[best_match] = quantity

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

# Ejemplo del menú
menu_df = pd.DataFrame({
    'Plato': ['Ceviche', 'Anticucho', 'Lomo Saltado', 'Causa', 'Sopa Criolla', 'Tortillas', 'Tallarines'],
    'Distrito Disponible': ['Miraflores', 'Miraflores', 'San Isidro', 'San Isidro', 'Miraflores', 'San Isidro', 'Miraflores']
})

# Pruebas con entradas variadas
print(improved_extract_order_and_quantity("Quiero 4 tortillas y dos tallarines.", menu_df))  # {'Tortillas': 4, 'Tallarines': 2}
print(improved_extract_order_and_quantity("Me gustaría tres ceviches y una sopa criolla.", menu_df))  # {'Ceviche': 3, 'Sopa Criolla': 1}
print(improved_extract_order_and_quantity("1 ceviche", menu_df))  # {'Ceviche': 1}
