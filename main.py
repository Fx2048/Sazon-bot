# Función mejorada para extraer el pedido y la cantidad usando similitud
def extract_order_and_quantity(prompt, menu):
    """
    Extrae la cantidad y el nombre de cada plato en el pedido del usuario utilizando coincidencias parciales.

    Ejemplos de entrada y salida:
    Entrada: “Quiero pedir 2 ceviches y 3 causas.”
    Respuesta: {“Ceviche”: 2, “Causa”: 3}

    Entrada: “Me gustaría 1 lomo saltado y 4 anticuchos.”
    Respuesta: {“Lomo Saltado”: 1, “Anticuchos”: 4}

    Restricciones:
    - La similitud debe ser mayor al 75% para considerar una coincidencia válida.
    - Si el prompt es None, retornar un diccionario vacío.
    - Los nombres de los platos deben coincidir con los del menú proporcionado.
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
            # Si no se especifica una cantidad, asumir 1
            if not quantity:
                quantity = 1
            else:
                quantity = int(quantity)
            order_dict[best_match] = quantity

    return order_dict

# Interfaz para el usuario cuando aún no ha hecho el pedido
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

        # Mostrar menú con ejemplos de pedidos
        response = f"Gracias por proporcionar tu distrito: **{district}**. Aquí está el menú disponible para tu área:\n\n{menu_display}\n\n**¿Qué te gustaría pedir?**\n\nEjemplo: 'Quiero solicitar un plato de tallarines' (esto se interpretará como 1 unidad de tallarines)."

else:
    # Procesar el pedido con cantidades específicas o no
    order_dict = extract_order_and_quantity(user_input, menu)
    if not order_dict:
        response = f"😊 No has seleccionado ningún plato del menú. Por favor revisa: 'Ejemplo de solicitud: 1 Pescado a la Plancha o Quiero un lomo saltado'."
    else:
        available_orders, unavailable_orders = verify_order_with_menu(order_dict, menu)
        if unavailable_orders:
            response = f"Lo siento, los siguientes platos no están disponibles: {', '.join(unavailable_orders)}."
        else:
            response = f"Tu pedido ha sido registrado: {', '.join([f'{qty} x {dish}' for dish, qty in available_orders.items()])}. ¡Gracias!"

