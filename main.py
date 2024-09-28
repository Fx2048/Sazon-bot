import pandas as pd
import streamlit as st
from datetime import datetime
from copy import deepcopy
from openai import OpenAI

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
    return districts['Distrito'].tolist()

# Función para filtrar el menú por distrito
def filter_menu_by_district(menu, district):
    # Filtramos menú por la columna "Distrito Disponible" y vemos que platos tienen disponibles
    id_distrito = districts.loc[districts['Distrito'] == district, "ID"].values
    regex_pattern = r'(^|,){}(,|$)'.format(id_distrito)
    return menu[menu['Distrito Disponible'].str.contains(regex_pattern)] 

# Función para verificar el distrito
def verify_district(prompt, districts):
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

# Inicializar la conversación si no existe en la sesión
if "messages" not in st.session_state:
    st.session_state["messages"] = deepcopy(initial_state)

# Botón para limpiar la conversación
clear_button = st.button("Limpiar Conversación", key="clear")
if clear_button:
    st.session_state["messages"] = deepcopy(initial_state)

# Mostrar el historial de la conversación
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"], avatar="🍲" if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# Entrada del usuario para el distrito
if district_input := st.chat_input("¿De dónde nos visitas?"):
    with st.chat_message("user", avatar="👤"):
        st.markdown(district_input)

    # Verificar el distrito
    district = verify_district(district_input, districts)

    if not district:
        response = f"Lo siento, pero no entregamos en ese distrito. Estos son los distritos disponibles: {', '.join(districts)}."
    else:
        # Filtrar el menú por distrito y mostrarlo
        filtered_menu = filter_menu_by_district(menu, district)
        menu_display = format_menu(filtered_menu)

        response = f"Gracias por proporcionar tu distrito: **{district}**. Aquí está el menú disponible para tu área:\n\n{menu_display}\n\n**¿Qué te gustaría pedir?**"

    # Mostrar la respuesta del asistente
    with st.chat_message("assistant", avatar="🍲"):
        st.markdown(response)

# Entrada del usuario para el pedido
if prompt := st.chat_input("¿Qué te gustaría pedir?"):
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Procesar el pedido
    order = classify_order(prompt, menu)  # Asegúrate de que `classify_order` considere el menú filtrado
    if not order:
        response = "😊 No has seleccionado ningún plato del menú. Por favor revisa."
    else:
        response = f"Tu pedido ha sido registrado: **{order}**. ¡Gracias!"

    # Mostrar la respuesta del asistente
    with st.chat_message("assistant", avatar="🍲"):
        st.markdown(response)

    # Guardar el pedido en el estado
    st.session_state["last_order"] = prompt
