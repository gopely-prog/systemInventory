import streamlit as st
import pandas as pd
from st_keyup import st_keyup

st.set_page_config(page_title="Cuadre de Licorería", layout="wide", initial_sidebar_state="collapsed")

# Inicializar almacenamiento persistente para evitar que los conteos se borren al filtrar
if 'conteos_guardados' not in st.session_state:
    st.session_state['conteos_guardados'] = {}

def guardar_conteo(id_prod, key):
    st.session_state['conteos_guardados'][id_prod] = st.session_state[key]

# Optimizaciones CSS específicas para iPhone 14 Pro / Safari
st.markdown("""
<style>
/* 1. Prevenir el Auto-Zoom en Safari (iOS hace zoom si el font-size es < 16px) */
input, textarea, select {
    font-size: 16px !important;
}

/* 2. Agrandar los botones de + y - en los inputs numéricos para toques en móvil */
div[data-testid="stNumberInput"] button {
    width: 2.8rem !important;
    height: 2.8rem !important;
}

/* 3. Mejorar los márgenes laterales en pantallas de celular para aprovechar el espacio */
.block-container {
    padding-top: 1.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

st.title("📦 Cuadre de Inventario")

# 1. Subir el Excel del POS
archivo_subido = st.file_uploader("Sube el reporte de stock (Excel)", type=["xlsx", "xls"])

if archivo_subido:
    # 2. Leer los datos (Solo nos importan la columna B y E del Excel)
    try:
        # Columna B es índice 'B', Columna E es índice 'E'
        df = pd.read_excel(archivo_subido, usecols="B,E")
        df.columns = ["Producto", "Stock Anterior"]
    except Exception as e:
        st.error(f"Error al leer el Excel. Verifica que tenga columnas B y E. Detalle: {e}")
        st.stop()
        
    # Limpieza básica
    df = df.dropna(subset=['Producto'])
    df['Producto'] = df['Producto'].astype(str).str.strip()
    df = df[df['Producto'] != ""] # Omitir espacios en blanco/vacíos
    
    # Omitir categorías / familias de productos
    categorias_excluidas = [
        "abarrotes", "aguas", "aseo personal", "bazares", "cervezas", 
        "comida", "condimentos", "embutidos", "energizantes", "gaseosas", 
        "golosinas", "lacteos", "licores", "limpiezas", "nectares", 
        "panaderia", "snackes", "tabacos", "columa2", "descripcio",
        "columna2", "descripcion"
    ]
    df = df[~df['Producto'].str.lower().isin(categorias_excluidas)]
    
    df['Stock Anterior'] = pd.to_numeric(df['Stock Anterior'], errors='coerce').fillna(0)
    
    # Agregamos un ID único por fila para que cada caja de Streamlit mantenga su estado al filtrar
    df = df.reset_index(names=['ID_Unico'])
    
    st.divider()
    
    # 3. Filtros
    col1, col2 = st.columns(2)
    
    with col1:
        # Búsqueda por nombre en tiempo real (mientras escribes)
        busqueda = st_keyup("🔍 Buscar por nombre del producto:")
        
    # Aplicar el filtro de búsqueda PRIMERO
    if busqueda:
        # Limpiar espacios extra de la búsqueda por si acaso
        busqueda_limpia = busqueda.strip()
        df_filtrado = df[df['Producto'].astype(str).str.contains(busqueda_limpia, case=False, na=False)].copy()
    else:
        df_filtrado = df.copy()
        
    with col2:
        # Filtrado por cantidad muestra SOLO las cantidades de la búsqueda actual
        cantidades_unicas = sorted(df_filtrado['Stock Anterior'].unique())
        filtro_cantidad = st.multiselect(
            "📊 Filtrar por cantidad (Stock de la semana anterior):", 
            options=cantidades_unicas,
            default=[] # Vacío = muestra todos
        )
        
    if filtro_cantidad:
        # Si el usuario selecciona cantidades, filtramos por ellas
        df_filtrado = df_filtrado[df_filtrado['Stock Anterior'].isin(filtro_cantidad)]
        
    st.write(f"Mostrando **{len(df_filtrado)}** productos.")
    st.write("---")
    
    # 4. Mostrar en Módulos (Cajas por producto)
    # Mostrar en una cuadrícula de 3 columnas para aprovechar el espacio
    cols_por_fila = 3 
    productos = df_filtrado.to_dict('records')
    
    for i in range(0, len(productos), cols_por_fila):
        cols = st.columns(cols_por_fila)
        for j, col in enumerate(cols):
            if i + j < len(productos):
                prod = productos[i + j]
                nombre = prod['Producto']
                stock_ant = prod['Stock Anterior']
                id_unico = prod['ID_Unico']
                
                with col:
                    # Contenedor con borde que actúa como caja del producto
                    with st.container(border=True):
                        st.subheader(f"{nombre}")
                        st.write(f"**Stock Semana Anterior:** {stock_ant}")
                        
                        # Recuperar valor guardado o iniciar en 0
                        valor_guardado = st.session_state['conteos_guardados'].get(id_unico, 0)
                        
                        # Campo numérico para el stock contado
                        key_input = f"stock_{id_unico}"
                        nuevo_stock = st.number_input(
                            "Stock que voy a contar:", 
                            min_value=0, 
                            step=1, 
                            value=valor_guardado,
                            key=key_input,
                            on_change=guardar_conteo,
                            args=(id_unico, key_input)
                        )
                        
                        # Mostrar alerta de diferencia en tiempo real
                        diff = nuevo_stock - stock_ant
                        if nuevo_stock > 0 or diff != 0:
                            if diff == 0:
                                st.success("🟢 Cuadra exacto")
                            elif diff > 0:
                                st.warning(f"🟡 Sobra {diff}")
                            else:
                                st.error(f"🔴 Falta {abs(diff)}")