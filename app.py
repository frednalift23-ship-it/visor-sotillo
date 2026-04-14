import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd 
import os
import base64
from streamlit_gsheets import GSheetsConnection
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# Configuración de la página
st.set_page_config(page_title="Visor Territorial Sotillo", layout="wide")

# --- NUEVO: LA DIRECCIÓN DE LA CARPETA DE FOTOS ---
FOLDER_ID_FOTOS = '1m5P3in3Si_fNYNN9nnkmdo1iKRROPCJ_'

# Rutas de archivo
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_EJES = os.path.join(DIRECTORIO_ACTUAL, "datos", "ejes_sotillo.geojson")
RUTA_EXCEL = os.path.join(DIRECTORIO_ACTUAL, "datos", "trabajadores.xlsx")
RUTA_LOGO = os.path.join(DIRECTORIO_ACTUAL, "datos","logo_alcaldia.jpeg")
RUTA_CSS = os.path.join(DIRECTORIO_ACTUAL, "style.css") 

# ---  CARGAR ESTILOS CSS EXTERNOS ---
try:
    with open(RUTA_CSS, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("⚠️ No se encontró el archivo style.css")

# conversion logo a binario:

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            return encoded_string
    except FileNotFoundError:
        return None

encoded_logo = get_base64_image(RUTA_LOGO)

# --- CABECERA CON EFECTO MEDALLA SUPERPUESTA ---
if encoded_logo:
    header_html = f"""
<div style="position: relative; width: 100%; height: 90px; margin-top: 20px; margin-bottom: 40px;">
    <div style="position: absolute; top: 15px; left: 0; width: 100%; height: 75px; background-color: #242F49; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid #384358; display: flex; align-items: center; justify-content: center; z-index: 1;">
        <h2 style="color: #FFFFFF; margin: 0; font-family: sans-serif; font-size: 24px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px;">Sistema de Salas de Autogobierno <span style="color: #FFA586;">| Sotillo</span></h2>
    </div>
    <div style="position: absolute; top: -15px; left: 40px; z-index: 2; padding: 5px; background-color: white; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.6); border: 2px solid #E5E7EB;">
        <img src="data:image/jpeg;base64,{encoded_logo}" style="width: 115px; height: auto; border-radius: 8px; display: block;">
    </div>
</div>
"""
    st.markdown(header_html, unsafe_allow_html=True)
else:
    st.markdown("<h2 style='text-align: center; color: #FFA586; text-transform: uppercase; font-weight: bold;'>Sistema de Salas de Autogobierno - Municipio Sotillo</h2>", unsafe_allow_html=True)

# --- CARGAR DATOS ---
df_trabajadores = pd.DataFrame()
lista_cedulas = ["Seleccione una cédula..."]

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Leemos la hoja. El ttl="5m" hace que el mapa busque cambios cada 5 minutos
    df_trabajadores = conn.read(ttl="5m")
    
    #  limpieza de datos 
    df_trabajadores = df_trabajadores.fillna('N/A') # rellena vacíos
    df_trabajadores.columns = ['Nombre', 'Cedula', 'Cargo', 'Telefono', 'Sector', 'Direccion', 'Eje', 'Comuna']
    
    # Limpieza de datos
    df_trabajadores['Nombre'] = df_trabajadores['Nombre'].astype(str).str.strip()
    df_trabajadores['Cedula'] = df_trabajadores['Cedula'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_trabajadores['Cargo'] = df_trabajadores['Cargo'].astype(str).str.strip() 
    df_trabajadores['Comuna'] = df_trabajadores['Comuna'].astype(str).str.replace('\n', ' ').str.strip()
    df_trabajadores['Eje'] = df_trabajadores['Eje'].astype(str).str.replace('\n', ' ').str.strip()
    
    cedulas_limpias = sorted(df_trabajadores['Cedula'].unique().tolist())
    lista_cedulas.extend(cedulas_limpias)
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

# --- FUNCION QUE BUSCA LAS FOTO DE LOS TRABAJADORES ---

@st.cache_data(ttl="1h") 
def obtener_bytes_foto(cedula):
    try:
        from google.oauth2 import service_account 
        
        info_llaves = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            info_llaves,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        # --- EL ARREGLO MÁGICO ---
        # Ahora el robot busca la cédula sola, con .jpg, con .jpeg o con .png
        query = f"(name='{cedula}' or name='{cedula}.jpg' or name='{cedula}.jpeg' or name='{cedula}.png') and '{FOLDER_ID_FOTOS}' in parents and trashed=false"
        
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            file_id = files[0]['id']
            request = drive_service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return file.getvalue()
            
        return None 
        
    except Exception as e:
        return None
        # ----------------------------------------------------------
        

        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            file_id = files[0]['id']
            request = drive_service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return file.getvalue()
            
        return None # No encontró la foto, pero no hubo error de sistema
        
    except Exception as e:
        # ¡EL MICRÓFONO! Si algo técnico falla, lo mostrará en pantalla
        st.error(f"Error del robot buscando foto de {cedula}: {e}")
        return None

#  Base de Datos de Comunas
COMUNAS_POR_EJE = {
    "Eje 1": [{"nombre": "Unidos las delicias", "lat": 10.19031, "lon": -64.63106}],
    "Eje 2": [
        {"nombre": "María Teresa Del Toro", "lat": 10.18140, "lon": -64.64060},
        {"nombre": "El Gigante de América", "lat": 10.18133, "lon": -64.63978},
        {"nombre": "Esteban Díaz", "lat": 10.19500, "lon": -64.61000},
        {"nombre": "Corazón de mi Patria siglo XXI", "lat": 10.19361, "lon": -64.63404}
    ],
    "Eje 3": [
        {"nombre": "Gran Mariscal de Ayacucho", "lat": 10.20625, "lon": -64.63781},
        {"nombre": "Teresita De Alfonzo", "lat": 10.19690, "lon": -64.62265},
        {"nombre": "Por amor a Chávez", "lat": 10.19750, "lon": -64.62400}
    ],
    "Eje 4": [
        {"nombre": "Ezequiel Zamora", "lat": 10.19785, "lon": -64.61346},
        {"nombre": "Don Simón Rodríguez", "lat": 10.18900, "lon": -64.59200}
    ],
    "Eje 5": [
        {"nombre": "El Rostro de Bolívar", "lat": 10.11500, "lon": -64.58000},
        {"nombre": "El legado De Chávez", "lat": 10.11000, "lon": -64.60000},
        {"nombre": "Batalla de Bolívar", "lat": 10.12900, "lon": -64.59100},
        {"nombre": "Josefa Camejo", "lat": 10.11350, "lon": -64.59200}
    ],
    "Eje 6": [
        {"nombre": "Ciudad sotillo", "lat": 10.11600, "lon": -64.58400},
        {"nombre": "Socialista Robert Serra 25", "lat": 10.14100, "lon": -64.60800}
    ],
    "Eje 7": [
        {"nombre": "Bahía pozuelos en Revolución", "lat": 10.21650, "lon": -64.63496},
        {"nombre": "Guerreros De Bello Monte", "lat": 10.19350, "lon": -64.61562}
    ],
    "Eje 8": [
        {"nombre": "José Antonio Anzoátegui 25", "lat": 10.20884, "lon": -64.64597},
        {"nombre": "El Paraíso", "lat": 10.22079, "lon": -64.64033},
        {"nombre": "Productiva 19 de Abril", "lat": 10.20720, "lon": -64.62840}
    ]
}

LAT_EXTERNO = 10.2215
LON_EXTERNO = -64.6315

# Vista general
if 'eje_seleccionado' not in st.session_state:
    st.session_state['eje_seleccionado'] = None
if 'comuna_seleccionada' not in st.session_state:
    st.session_state['comuna_seleccionada'] = None
if 'trabajador_resaltado' not in st.session_state:
    st.session_state['trabajador_resaltado'] = None

#............... barra de busqueda
def procesar_busqueda():
    cedula_buscada = st.session_state['buscador']
    if cedula_buscada != "Seleccione una cédula...":
        datos = df_trabajadores[df_trabajadores['Cedula'] == cedula_buscada].iloc[0]
        
        if "externo" in str(datos['Eje']).lower():
            st.session_state['eje_seleccionado'] = "Personal Externo"
            st.session_state['comuna_seleccionada'] = "Grupo Especial"
        else:
            st.session_state['eje_seleccionado'] = datos['Eje']
            st.session_state['comuna_seleccionada'] = datos['Comuna']
            
        st.session_state['trabajador_resaltado'] = cedula_buscada 
    else:
        st.session_state['trabajador_resaltado'] = None

# estrcutura de pantalla (Dividiendo el Lienzo)
col_mapa, col_info = st.columns([7, 3])

# --- COLUMNA IZQUIERDA: EL MAPA ---
with col_mapa:
    if st.session_state['eje_seleccionado']:
        if st.button("🔙 Volver al Mapa General"):
            st.session_state['eje_seleccionado'] = None
            st.session_state['comuna_seleccionada'] = None
            st.session_state['trabajador_resaltado'] = None 
            if 'buscador' in st.session_state:
                st.session_state['buscador'] = "Seleccione una cédula..." 
            st.rerun()

# --- LÓGICA DE CENTRADO DE CÁMARA ---
    lat_centro = 10.1980
    lon_centro = -64.6150
    zoom_inicial = 12
    eje_actual = st.session_state['eje_seleccionado']
    
    if eje_actual == "Personal Externo":
        lat_centro, lon_centro = LAT_EXTERNO, LON_EXTERNO
        zoom_inicial = 15 
    elif eje_actual and eje_actual in COMUNAS_POR_EJE:
        comunas_del_eje = COMUNAS_POR_EJE[eje_actual]
        lat_centro = sum(c['lat'] for c in comunas_del_eje) / len(comunas_del_eje)
        lon_centro = sum(c['lon'] for c in comunas_del_eje) / len(comunas_del_eje)
        zoom_inicial = 14
# Diseño exacto de Google Maps
    mapa_sotillo = folium.Map(
        location=[lat_centro, lon_centro], 
        zoom_start=zoom_inicial, 
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google"
    )

    estilo_tooltip = "background-color: #242F49; color: #FFFFFF; border: 1px solid #FFA586; padding: 10px; border-radius: 5px; font-family: sans-serif;"
#--------------------- estructura y logicas del mapa con ejes y sus comunas
    try:
        if eje_actual != "Personal Externo":
            gdf_ejes = gpd.read_file(RUTA_EJES)
            
            if eje_actual:
                gdf_ejes = gdf_ejes[gdf_ejes['nombre_eje'] == eje_actual]

            folium.GeoJson(
                gdf_ejes,
                style_function=lambda feature: {
                    'fillColor': '#384358', 'color': '#FFA586', 'weight': 1.5, 'fillOpacity': 0.3
                },
                highlight_function=lambda feature: {
                    'fillColor': '#941A2E', 'color': '#FFA586', 'weight': 2.5, 'fillOpacity': 0.6
                }
            ).add_to(mapa_sotillo)

            for indice, fila in gdf_ejes.iterrows():
                centro = fila.geometry.centroid
                folium.Marker(
                    location=[centro.y, centro.x],
                    tooltip=folium.Tooltip(
                        f"<div style='min-width: 200px;'><b>Eje:</b> {fila['nombre_eje']}<br><b>Sala:</b> {fila['nombre_oficial']}<br><b>Zona:</b> {fila['nombre_zona']}</div>", 
                        style=estilo_tooltip
                    ), 
                    icon=folium.Icon(color='lightblue', icon='info-sign') 
                ).add_to(mapa_sotillo)

            if eje_actual and eje_actual in COMUNAS_POR_EJE:
                for comuna in COMUNAS_POR_EJE[eje_actual]:
                    color_pin = 'orange' if st.session_state['comuna_seleccionada'] == comuna['nombre'] else 'red'
                    folium.Marker(
                        location=[comuna['lat'], comuna['lon']],
                        tooltip=folium.Tooltip(f"<b>Comuna:</b> {comuna['nombre']}", style=estilo_tooltip),
                        icon=folium.Icon(color=color_pin, icon='home')
                    ).add_to(mapa_sotillo)

        if not eje_actual or eje_actual == "Personal Externo":
            folium.Marker(
                location=[LAT_EXTERNO, LON_EXTERNO],
                tooltip=folium.Tooltip(
                    "<div style='min-width: 200px;'><b style='color:#FFA586;'>★ Grupo Especial:</b><br>Personal Externo / Otras Comunas</div>", 
                    style=estilo_tooltip
                ), 
                icon=folium.Icon(color='orange', icon='star') 
            ).add_to(mapa_sotillo)

    except Exception as e:
        st.error(f"Error al cargar el mapa.")

    mapa_renderizado = st_folium(mapa_sotillo, use_container_width=True, height=600, key="mapa_interactivo")
#-------------------------------------------------

# --- DETECTOR DE CLICS ---
    if mapa_renderizado:
        clic_coordenadas = mapa_renderizado.get("last_object_clicked")
        if clic_coordenadas:
            lat_c = clic_coordenadas.get("lat")
            lon_c = clic_coordenadas.get("lng")

# 1. Verificación del Personal Externo (Coordenadas fijas)
            
            if abs(LAT_EXTERNO - lat_c) < 0.002 and abs(LON_EXTERNO - lon_c) < 0.002:
                if st.session_state['eje_seleccionado'] != "Personal Externo":
                    st.session_state['eje_seleccionado'] = "Personal Externo"
                    st.session_state['comuna_seleccionada'] = "Grupo Especial"
                    st.session_state['trabajador_resaltado'] = None
                    if 'buscador' in st.session_state:
                        st.session_state['buscador'] = "Seleccione una cédula..."
                    st.rerun()

# 2. Búsqueda de la Comuna más cercana
            else:
                comuna_clicada = None
                distancia_minima = float('inf') 
                
                if eje_actual and eje_actual in COMUNAS_POR_EJE:
                    for comuna in COMUNAS_POR_EJE[eje_actual]:
                        # El Teorema de Pitágoras
                        distancia = ((comuna['lat'] - lat_c)**2 + (comuna['lon'] - lon_c)**2)**0.5
                        if distancia < 0.005 and distancia < distancia_minima:
                            distancia_minima = distancia
                            comuna_clicada = comuna['nombre']
                
# 3. Actualizar la memoria si encontramos una comuna:
                if comuna_clicada and comuna_clicada != st.session_state['comuna_seleccionada']:
                    st.session_state['comuna_seleccionada'] = comuna_clicada
                    st.session_state['trabajador_resaltado'] = None 
                    if 'buscador' in st.session_state:
                        st.session_state['buscador'] = "Seleccione una cédula..."
                    st.rerun()
                    
                elif not comuna_clicada and not eje_actual:
                    eje_clicado = None
                    distancia_minima_eje = float('inf')
                    try:
                        gdf_completo = gpd.read_file(RUTA_EJES)
                        for indice, fila in gdf_completo.iterrows():
                            centro = fila.geometry.centroid
                            distancia_eje = ((centro.y - lat_c)**2 + (centro.x - lon_c)**2)**0.5
                            if distancia_eje < 0.015 and distancia_eje < distancia_minima_eje:
                                distancia_minima_eje = distancia_eje
                                eje_clicado = fila['nombre_eje']
                                
                        if eje_clicado:
                            st.session_state['eje_seleccionado'] = eje_clicado
                            st.session_state['comuna_seleccionada'] = None 
                            st.session_state['trabajador_resaltado'] = None
                            if 'buscador' in st.session_state:
                                st.session_state['buscador'] = "Seleccione una cédula..."
                            st.rerun()
                    except Exception:
                        pass

# --- COLUMNA DERECHA: PANEL DE INFORMACIÓN ---
with col_info:
    
    st.markdown("<h4 style='color: #FFA586; margin-top: 0;'>🔍 Búsqueda Rápida</h4>", unsafe_allow_html=True)
    st.selectbox(
        "Busca por Cédula de Identidad:", 
        options=lista_cedulas, 
        key='buscador',
        on_change=procesar_busqueda 
    )
    
    st.markdown("<hr style='border: 1px solid #384358;'>", unsafe_allow_html=True)

    # --- ESCENARIO 1: PERSONAL EXTERNO ---
    if st.session_state['eje_seleccionado'] == "Personal Externo":
        # 1. Obtenemos a toda la gente de esta área primero
        df_base_area = pd.DataFrame() if df_trabajadores.empty else df_trabajadores[df_trabajadores['Eje'].str.contains('externo', case=False, na=False)]
        
        # 2. Creamos el Filtro Inteligente de Cargos
        if not df_base_area.empty:
            cargos_unicos = ["Todos los cargos"] + sorted(df_base_area['Cargo'].unique().tolist())
            st.markdown("<p style='color: #A0AEC0; font-size: 14px; margin-bottom: 2px;'><b>Filtro Operativo:</b></p>", unsafe_allow_html=True)
            cargo_seleccionado = st.selectbox("Filtrar por Cargo", options=cargos_unicos, key="filtro_ext", label_visibility="collapsed")
            
            # 3. Filtramos la tabla según lo que el usuario eligió
            if cargo_seleccionado != "Todos los cargos":
                df_filtrado = df_base_area[df_base_area['Cargo'] == cargo_seleccionado]
            else:
                df_filtrado = df_base_area
        else:
            df_filtrado = df_base_area
            
        total_externos = len(df_filtrado)
        
        # 4. Mostramos el Dashboard Estadístico (Ahora se actualiza solo)
        st.markdown(f"""
            <div style='background-color: #242F49; padding: 15px; border-radius: 10px; color: white; margin-bottom: 20px; border-left: 5px solid #FFA586; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-top: 15px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h4 style='margin: 0; color: #FFFFFF;'>★ Personal Externo</h4>
                        <p style='margin: 5px 0 0 0; font-size: 14px; color: #A0AEC0;'>Apoyo de otras jurisdicciones.</p>
                    </div>
                    <div style='text-align: center; background-color: #101E2E; padding: 5px 15px; border-radius: 8px; border: 1px solid #384358;'>
                        <span style='font-size: 11px; color: #A0AEC0; display: block;'>Registrados</span>
                        <span style='font-size: 22px; font-weight: bold; color: #FFA586;'>{total_externos}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if df_base_area.empty:
            st.info("Aún no hay trabajadores externos registrados en el Excel.")
        elif df_filtrado.empty:
            st.warning(f"No hay personas con el cargo '{cargo_seleccionado}' en esta área.")
        else:
            # Reorganizar para mostrar al buscado primero
            if st.session_state['trabajador_resaltado'] in df_filtrado['Cedula'].values:
                df_vip = df_filtrado[df_filtrado['Cedula'] == st.session_state['trabajador_resaltado']]
                df_resto = df_filtrado[df_filtrado['Cedula'] != st.session_state['trabajador_resaltado']]
                df_filtrado = pd.concat([df_vip, df_resto])
            
            for index, trabajador in df_filtrado.iterrows():
                nombre = trabajador.get('Nombre', 'Sin Nombre')
                cedula = trabajador.get('Cedula', 'N/A')
                cargo = trabajador.get('Cargo', 'N/A')
                telefono = trabajador.get('Telefono', 'N/A')
                sector = trabajador.get('Sector', 'N/A')
                direccion = trabajador.get('Direccion', 'N/A')

                # --- CONFIGURACION DE LAS FOTOS ---
                bytes_foto = obtener_bytes_foto(cedula)
                if bytes_foto:
                    b64_foto = base64.b64encode(bytes_foto).decode()
                    img_html = f'<img src="data:image/jpeg;base64,{b64_foto}" style="width: 80px; height: 80px; border-radius: 50%; border: 2px solid #FFA586; object-fit: cover; flex-shrink: 0;">'
                else:
                    img_html = '<div style="width: 80px; height: 80px; border-radius: 50%; border: 2px dashed #384358; background-color: #101E2E; display: flex; align-items: center; justify-content: center; color: #A0AEC0; font-size: 24px; flex-shrink: 0;">👤</div>'
                # ------------------------
                
                if st.session_state['trabajador_resaltado'] == cedula:
                    borde_estilo = "border: 2px solid #EB1A2B; background-color: #1A2235;"
                    color_nombre = "#EB1A2B"
                    etiqueta_resaltado = "<span style='background-color: #EB1A2B; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 10px;'>Encontrado</span>"
                else:
                    borde_estilo = "border: 1px solid #384358; background-color: #242F49;"
                    color_nombre = "#FFA586"
                    etiqueta_resaltado = ""
                
               # --- NUEVO DISEÑO: FORMATO A PRUEBA DE INDENTACIÓN (NOMBRES COMPLETOS) ---
                html_tarjeta = (
                    f'<div style="padding: 15px; border-radius: 8px; {borde_estilo} box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin-bottom: 15px;">'
                    f'<div style="display: flex; gap: 15px; align-items: flex-start;">'
                    f'<div style="display: flex; flex-direction: column; align-items: center;">{img_html}</div>'
                    f'<div style="flex-grow: 1; min-width: 0;">'
                    # Aquí quitamos el nowrap y el ellipsis, y añadimos un line-height para que si el nombre usa dos líneas, se vea ordenado
                    f'<h5 style="margin: 0 0 8px 0; color: {color_nombre}; font-size: 16px; line-height: 1.3;">{nombre} {etiqueta_resaltado}</h5>'
                    f'<div style="font-size: 13px; color: #FFFFFF; margin-bottom: 5px;">'
                    f'<span style="display: block; margin-bottom: 3px;"><b style="color:#A0AEC0;">C.I.:</b> {cedula}</span>'
                    f'<span style="display: block; margin-bottom: 3px;"><b style="color:#A0AEC0;">Cargo:</b> {cargo}</span>'
                    f'<span style="display: block;"><b style="color:#A0AEC0;">Tel.:</b> {telefono}</span>'
                    f'</div></div></div>'
                    f'<div style="font-size: 12px; color: #E2E8F0; border-top: 1px dashed #384358; padding-top: 8px; margin-top: 10px;">'
                    f'<span style="display: block; margin-bottom: 3px;"><b style="color:#A0AEC0;">📍 Sector:</b> {sector}</span>'
                    f'<span style="display: block;"><b style="color:#A0AEC0;">🏠 Dir.:</b> {direccion}</span>'
                    f'</div></div>'
                )
                
                st.markdown(html_tarjeta, unsafe_allow_html=True)
                
    # --- ESCENARIO 2: EJE Y COMUNA SELECCIONADOS ---
    elif st.session_state['eje_seleccionado'] and st.session_state['comuna_seleccionada']:
        comuna_actual = st.session_state['comuna_seleccionada']
        eje = st.session_state['eje_seleccionado']
        
        # 1. Obtenemos a la gente de esta comuna
        df_base_area = pd.DataFrame() if df_trabajadores.empty else df_trabajadores[df_trabajadores['Comuna'] == comuna_actual]
        
        # 2. Creamos el Filtro Inteligente de Cargos
        if not df_base_area.empty:
            cargos_unicos = ["Todos los cargos"] + sorted(df_base_area['Cargo'].unique().tolist())
            st.markdown("<p style='color: #A0AEC0; font-size: 14px; margin-bottom: 2px;'><b>Filtro Operativo:</b></p>", unsafe_allow_html=True)
            cargo_seleccionado = st.selectbox("Filtrar por Cargo", options=cargos_unicos, key="filtro_comuna", label_visibility="collapsed")
            
            # 3. Filtramos
            if cargo_seleccionado != "Todos los cargos":
                df_filtrado = df_base_area[df_base_area['Cargo'] == cargo_seleccionado]
            else:
                df_filtrado = df_base_area
        else:
            df_filtrado = df_base_area
            
        total_comuna = len(df_filtrado)
        
        # 4. Dashboard Estadístico Dinámico
        st.markdown(f"""
            <div style='background-color: #242F49; padding: 15px; border-radius: 10px; color: white; margin-bottom: 20px; border-left: 5px solid #EB1A2B; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-top: 15px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h4 style='margin: 0; color: #FFFFFF;'>{eje} / {comuna_actual}</h4>
                        <p style='margin: 5px 0 0 0; font-size: 14px; color: #A0AEC0;'>Personal asignado a esta comuna.</p>
                    </div>
                    <div style='text-align: center; background-color: #101E2E; padding: 5px 15px; border-radius: 8px; border: 1px solid #384358;'>
                        <span style='font-size: 11px; color: #A0AEC0; display: block;'>Registrados</span>
                        <span style='font-size: 22px; font-weight: bold; color: #EB1A2B;'>{total_comuna}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if df_base_area.empty:
            st.info(f"Aún no hay trabajadores registrados en el Excel para la comuna: {comuna_actual}.")
        elif df_filtrado.empty:
            st.warning(f"No hay personas con el cargo '{cargo_seleccionado}' en esta comuna.")
        else:
            if st.session_state['trabajador_resaltado'] in df_filtrado['Cedula'].values:
                df_vip = df_filtrado[df_filtrado['Cedula'] == st.session_state['trabajador_resaltado']]
                df_resto = df_filtrado[df_filtrado['Cedula'] != st.session_state['trabajador_resaltado']]
                df_filtrado = pd.concat([df_vip, df_resto])

            for index, trabajador in df_filtrado.iterrows():
                nombre = trabajador.get('Nombre', 'Sin Nombre')
                cedula = trabajador.get('Cedula', 'N/A')
                cargo = trabajador.get('Cargo', 'N/A')
                telefono = trabajador.get('Telefono', 'N/A')
                sector = trabajador.get('Sector', 'N/A')
                direccion = trabajador.get('Direccion', 'N/A')

             # --- CONFIGURACION DE LAS FOTOS ---
                bytes_foto = obtener_bytes_foto(cedula)
                if bytes_foto:
                    b64_foto = base64.b64encode(bytes_foto).decode()
                    img_html = f'<img src="data:image/jpeg;base64,{b64_foto}" style="width: 80px; height: 80px; border-radius: 50%; border: 2px solid #FFA586; object-fit: cover; flex-shrink: 0;">'
                else:
                    img_html = '<div style="width: 80px; height: 80px; border-radius: 50%; border: 2px dashed #384358; background-color: #101E2E; display: flex; align-items: center; justify-content: center; color: #A0AEC0; font-size: 24px; flex-shrink: 0;">👤</div>'
                # ------------------------
                
                if st.session_state['trabajador_resaltado'] == cedula:
                    borde_estilo = "border: 2px solid #EB1A2B; background-color: #1A2235;"
                    color_nombre = "#EB1A2B"
                    etiqueta_resaltado = "<span style='background-color: #EB1A2B; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 10px;'>Encontrado</span>"
                else:
                    borde_estilo = "border: 1px solid #384358; background-color: #242F49;"
                    color_nombre = "#FFA586"
                    etiqueta_resaltado = ""
              
                # --- NUEVO DISEÑO: FORMATO A PRUEBA DE INDENTACIÓN (NOMBRES COMPLETOS) ---
                html_tarjeta = (
                    f'<div style="padding: 15px; border-radius: 8px; {borde_estilo} box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin-bottom: 15px;">'
                    f'<div style="display: flex; gap: 15px; align-items: flex-start;">'
                    f'<div style="display: flex; flex-direction: column; align-items: center;">{img_html}</div>'
                    f'<div style="flex-grow: 1; min-width: 0;">'
                    # Aquí quitamos el nowrap y el ellipsis, y añadimos un line-height para que si el nombre usa dos líneas, se vea ordenado
                    f'<h5 style="margin: 0 0 8px 0; color: {color_nombre}; font-size: 16px; line-height: 1.3;">{nombre} {etiqueta_resaltado}</h5>'
                    f'<div style="font-size: 13px; color: #FFFFFF; margin-bottom: 5px;">'
                    f'<span style="display: block; margin-bottom: 3px;"><b style="color:#A0AEC0;">C.I.:</b> {cedula}</span>'
                    f'<span style="display: block; margin-bottom: 3px;"><b style="color:#A0AEC0;">Cargo:</b> {cargo}</span>'
                    f'<span style="display: block;"><b style="color:#A0AEC0;">Tel.:</b> {telefono}</span>'
                    f'</div></div></div>'
                    f'<div style="font-size: 12px; color: #E2E8F0; border-top: 1px dashed #384358; padding-top: 8px; margin-top: 10px;">'
                    f'<span style="display: block; margin-bottom: 3px;"><b style="color:#A0AEC0;">📍 Sector:</b> {sector}</span>'
                    f'<span style="display: block;"><b style="color:#A0AEC0;">🏠 Dir.:</b> {direccion}</span>'
                    f'</div></div>'
                )
                
                st.markdown(html_tarjeta, unsafe_allow_html=True)
        
    # --- ESCENARIO 4: MAPA GENERAL ---
    else:
        total_general = len(df_trabajadores) if not df_trabajadores.empty else 0
        
        st.markdown(f"""
            <div style='background-color: #242F49; padding: 20px; border-radius: 10px; border-left: 5px solid #384358; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-top: 15px;'>
                <h4 style='color: #FFFFFF; margin-top: 0;'>Instrucciones</h4>
                <p style='color: #A0AEC0;'>Puedes usar el <b>Buscador Rápido</b> arriba para encontrar a un trabajador por su cédula, o hacer clic sobre un <b>marcador en el mapa</b> para explorar el territorio.</p>
                <div style='margin-top: 15px; padding: 12px; background-color: #101E2E; border-radius: 8px; border: 1px solid #384358; text-align: center;'>
                    <span style='font-size: 14px; color: #A0AEC0; text-transform: uppercase; letter-spacing: 0.5px;'>Total Trabajadores Registrados</span><br>
                    <span style='font-size: 28px; font-weight: 900; color: #FFFFFF;'>{total_general}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
