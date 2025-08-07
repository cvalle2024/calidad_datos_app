import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Evaluación Calidad de Datos",
    layout="wide",
    page_icon="📊"  # Favicon personalizado (puedes reemplazar este emoji con uno que represente mejor tu app)
)

# --- Cargar credenciales desde st.secrets ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=scope)
client = gspread.authorize(creds)

# --- Obtener ID de hoja desde secrets
SPREADSHEET_ID = st.secrets["google_sheets"]["spreadsheet_id"]
hts_sheet_name = st.secrets["google_sheets"]["hts_sheet"]
txml_sheet_name = st.secrets["google_sheets"]["txml_sheet"]

# --- Menú lateral
menu = st.sidebar.selectbox("Selecciona una sección:", ["HTS_TST", "TX_ML y TX_RTT"])
mostrar_historial = st.sidebar.checkbox("📄 Ver historial")

# --- Ver historial ---
if mostrar_historial:
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(hts_sheet_name if menu == "HTS_TST" else txml_sheet_name)
        data = sheet.get_all_records()
        df_hist = pd.DataFrame(data)
        st.subheader("📊 Historial de evaluaciones")
        st.dataframe(df_hist)
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")

# --- HTS_TST Formulario ---
if menu == "HTS_TST":
    st.title("📋 Evaluación de Calidad de Datos - HTS_TST")

    # --- Datos generales
    st.header("🗂️ Datos generales")
    col1, col2, col3 = st.columns(3)
    with col1:
        pais = st.selectbox("País", ["Honduras", "Guatemala", "El Salvador", "Nicaragua", "Panamá"])
        mes_reporte = st.selectbox("Mes de reporte", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
    with col2:
        unidad = st.text_input("Nombre de la unidad")
        fecha_recepcion = st.date_input("Fecha de recepción")
    with col3:
        registros_revisados = st.number_input("Número de registros revisados", min_value=1, step=1)
        asesor = st.text_input("Nombre del asesor (revisor)")

    # --- Lista de chequeo
    st.header("✅ Lista de chequeo HTS_TST")
    st.write("Marca para cada criterio si **cumple** o **no cumple**, y anota observaciones si aplica.")

    criterios = [
        "Numeración correlativa (no celdas ocultas)",
        "Variables ingresadas según catálogo",
        "Ingreso de nombre de sitio aledaño cuando corresponde",
        "Fecha de diagnóstico corresponde a período de evaluación",
        "Ingreso de variables de Dx positivo únicamente en registros positivos",
        "Ingreso de lugar de vinculación a pacientes vinculados",
        "Fecha inicio de TARV posterior a fecha de Diagnóstico",
        "Fecha de CD4 con coherencia lógica según fecha de Dx",
        "Fecha de CV con coherencia lógica según fecha de Dx",
        "Ingreso de variable embarazada únicamente en sexo femenino"
    ]

    respuestas = []
    for i, criterio in enumerate(criterios, 1):
        st.subheader(f"{i}. {criterio}")
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            cumple = st.radio(f"Cumple", ["Sí", "No"], key=f"cumple_{i}")
        with col2:
            accion = st.radio(f"Acción correctiva realizada", ["Sí", "No"], key=f"accion_{i}")
        with col3:
            observacion = st.text_input("Observaciones", key=f"obs_{i}")

        respuestas.append({
            "criterio": criterio,
            "cumple": cumple,
            "accion_correctiva": accion,
            "observacion": observacion
        })

    if st.button("📤 Enviar evaluación", key="submit_hts"):
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(hts_sheet_name)

        for fila in respuestas:
            sheet.append_row([
                pais, mes_reporte, unidad, str(fecha_recepcion), registros_revisados, asesor,
                fila["criterio"], fila["cumple"], fila["accion_correctiva"], fila["observacion"]
            ])

        st.success("✅ Evaluación enviada y guardada en Google Sheets")
        st.write("### Resumen enviado:")
        df_resumen = pd.DataFrame(respuestas)
        st.dataframe(df_resumen)
        st.download_button("⬇️ Descargar resultados como Excel", data=df_resumen.to_csv(index=False).encode('utf-8'), file_name="HTS_TST_resultados.csv", mime="text/csv")

# --- TX_ML y TX_RTT Formulario ---
elif menu == "TX_ML y TX_RTT":
    st.title("📋 Evaluación de TX_ML y TX_RTT")

    st.header("🧾 Datos del paciente")
    col1, col2 = st.columns(2)
    with col1:
        fecha_ultima_visita = st.date_input("Fecha última visita")
        fecha_esperada = st.date_input("Fecha esperada de visita")
        fecha_recuperacion = st.date_input("Fecha de recuperación", value=None)
    with col2:
        trimestre = st.selectbox("Trimestre", ["Q1", "Q2", "Q3", "Q4"])
        abandono = st.radio("¿Abandono?", ["Sí", "No"])
        recuperado = st.radio("¿Recuperado en el trimestre?", ["Sí", "No"])

    trimestre_map = {
        "Q1": datetime(fecha_esperada.year if fecha_esperada else datetime.today().year, 12, 31),
        "Q2": datetime(fecha_esperada.year if fecha_esperada else datetime.today().year, 3, 31),
        "Q3": datetime(fecha_esperada.year if fecha_esperada else datetime.today().year, 6, 30),
        "Q4": datetime(fecha_esperada.year if fecha_esperada else datetime.today().year, 9, 30),
    }
    fin_trimestre = trimestre_map[trimestre]

    cuenta_tx_ml = "NO"
    accion_tx_curr = "NINGUNA"

    if abandono == "Sí" and fecha_esperada:
        try:
            dias_perdido = (fin_trimestre - fecha_esperada).days
            fue_recuperado = recuperado == "Sí" and fecha_recuperacion is not None and fecha_recuperacion <= fin_trimestre
            if dias_perdido > 28 and not fue_recuperado:
                cuenta_tx_ml = "SÍ"
                accion_tx_curr = "RESTAR"
        except Exception as e:
            st.error(f"Error en el cálculo de días perdidos: {e}")

    mensaje = f"📉 TX_ML: {cuenta_tx_ml} | Acción TX_CURR: {accion_tx_curr}"
    if cuenta_tx_ml == "SÍ":
        st.warning(mensaje)
    else:
        st.success(mensaje)

    st.subheader("🗂️ Datos generales del evaluador")
    col1, col2 = st.columns(2)
    with col1:
        pais_tx = st.selectbox("País", ["Honduras", "Guatemala", "El Salvador", "Nicaragua", "Panamá"], key="pais_tx")
        unidad_tx = st.text_input("Nombre de la unidad", key="unidad_tx")
    with col2:
        asesor_tx = st.text_input("Nombre del asesor", key="asesor_tx")
        fecha_registro = st.date_input("Fecha de evaluación", key="fecha_registro")

    if st.button("📤 Guardar evaluación", key="submit_txml"):
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(txml_sheet_name)
        sheet.append_row([
            str(fecha_ultima_visita), str(fecha_esperada), str(fecha_recuperacion), trimestre,
            abandono, recuperado, cuenta_tx_ml, accion_tx_curr,
            pais_tx, unidad_tx, asesor_tx, str(fecha_registro)
        ])

        st.success("✅ Evaluación guardada correctamente")





