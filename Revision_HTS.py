import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Evaluación Calidad de Datos",
    layout="wide",
    page_icon="📊"
)

# --- AUTENTICACIÓN GOOGLE SHEETS ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=scope)
client = gspread.authorize(creds)

SPREADSHEET_ID = st.secrets["google_sheets"]["spreadsheet_id"]
hts_sheet_name = st.secrets["google_sheets"]["hts_sheet"]
txml_sheet_name = st.secrets["google_sheets"]["txml_sheet"]

# --- MENÚ ---
menu = st.sidebar.selectbox("Selecciona una sección:", ["HTS_TST", "TX_ML y TX_RTT"])
mostrar_historial = st.sidebar.checkbox("📄 Ver historial")

# --- HISTORIAL ---
if mostrar_historial:
    hoja = hts_sheet_name if menu == "HTS_TST" else txml_sheet_name
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(hoja)
        data = sheet.get_all_records()
        df_hist = pd.DataFrame(data)
        st.subheader("📊 Historial de evaluaciones")
        st.dataframe(df_hist.tail(10))
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")

# --- FORMULARIO HTS_TST ---
if menu == "HTS_TST":
    st.title("📋 Evaluación de Calidad de Datos - HTS_TST")

    with st.form(key="hts_form", clear_on_submit=True):
        st.header("💼 Datos generales")
        col1, col2, col3 = st.columns(3)
        with col1:
            pais = st.selectbox("País", ["Honduras", "Guatemala", "El Salvador", "Nicaragua", "Panamá"])
            mes_reporte = st.selectbox("Mes de reporte", list(pd.date_range("2025-01-01", periods=12, freq="MS").strftime("%B")))
        with col2:
            unidad = st.text_input("Nombre de la unidad")
            fecha_recepcion = st.date_input("Fecha de recepción")
        with col3:
            registros_revisados = st.number_input("Número de registros revisados", min_value=1)
            asesor = st.text_input("Nombre del asesor (revisor)")

        st.header("✅ Lista de chequeo HTS_TST")
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
                cumple = st.radio("Cumple", ["Sí", "No"], key=f"cumple_{i}")
            with col2:
                accion = st.radio("Acción correctiva realizada", ["Sí", "No"], key=f"accion_{i}")
            with col3:
                observacion = st.text_input("Observaciones", key=f"obs_{i}")

            respuestas.append({
                "criterio": criterio,
                "cumple": cumple,
                "accion_correctiva": accion,
                "observacion": observacion
            })

        if st.form_submit_button("📤 Enviar evaluación"):
            try:
                sheet = client.open_by_key(SPREADSHEET_ID).worksheet(hts_sheet_name)
                for fila in respuestas:
                    sheet.append_row([
                        pais, mes_reporte, unidad, str(fecha_recepcion), registros_revisados, asesor,
                        fila["criterio"], fila["cumple"], fila["accion_correctiva"], fila["observacion"]
                    ])
                st.success("✅ Evaluación enviada")

                # Mostrar tabla virtual
                registros = sheet.get_all_records()
                df = pd.DataFrame(registros)
                st.subheader("🗂️ Registros recientes")
                st.dataframe(df.tail(5))
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# --- FORMULARIO TX_ML Y TX_RTT ---
if menu == "TX_ML y TX_RTT":
    st.title("📋 Evaluación de TX_ML y TX_RTT")

    with st.form(key="txml_form", clear_on_submit=True):
        st.header("💼 Datos generales del evaluador")
        col1, col2 = st.columns(2)
        with col1:
            pais = st.selectbox("País", ["Honduras", "Guatemala", "El Salvador", "Nicaragua", "Panamá"], key="pais_tx")
            unidad = st.text_input("Nombre de la unidad", key="unidad_tx")
        with col2:
            asesor = st.text_input("Nombre del asesor", key="asesor_tx")
            fecha_eval = st.date_input("Fecha de evaluación", key="fecha_eval")

        st.header("📜 Datos del paciente")
        col1, col2 = st.columns(2)
        with col1:
            fecha_ultima = st.date_input("Fecha última visita")
            fecha_esperada = st.date_input("Fecha esperada de visita")
            fecha_recup = st.date_input("Fecha de recuperación", value=None)
        with col2:
            trimestre = st.selectbox("Trimestre", ["Q1", "Q2", "Q3", "Q4"])

        # --- Lógica TX_ML y TX_CURR ---
        trimestre_map = {
            "Q1": date(fecha_esperada.year, 12, 31),
            "Q2": date(fecha_esperada.year, 3, 31),
            "Q3": date(fecha_esperada.year, 6, 30),
            "Q4": date(fecha_esperada.year, 9, 30),
        }
        fin_trim = trimestre_map[trimestre]

        cuenta_txml = "NO"
        accion_tx = "NINGUNA"
        mensaje = ""
        estado = ""
        msg_recup = ""

        try:
            dias_perdido = (fecha_recup or date.today()) - fecha_esperada
            dias_perdido = dias_perdido.days

            if fecha_recup and fecha_recup < fecha_esperada:
                cuenta_txml = "ERROR"
                accion_tx = "Fecha recuperación < fecha esperada"
                estado = "⚠️ Error"
            elif dias_perdido < 28:
                estado = "Activo en la cohorte"
                msg_recup = "---"
            elif 28 <= dias_perdido < 90:
                estado = "Perdido en seguimiento"
                if fecha_recup and fecha_recup <= fin_trim:
                    msg_recup = "Se recuperó en el trimestre"
                elif fecha_recup:
                    msg_recup = "Se recuperó en otro trimestre"
                    cuenta_txml = "SÍ"
                    accion_tx = "RESTAR"
                else:
                    msg_recup = "No se recuperó en el trimestre"
                    cuenta_txml = "SÍ"
                    accion_tx = "RESTAR"
            else:
                estado = "En abandono"
                if fecha_recup and fecha_recup <= fin_trim:
                    msg_recup = "Se recuperó en el trimestre"
                elif fecha_recup:
                    msg_recup = "Se recuperó en otro trimestre"
                    cuenta_txml = "SÍ"
                    accion_tx = "RESTAR"
                else:
                    msg_recup = "No se recuperó en el trimestre"
                    cuenta_txml = "SÍ"
                    accion_tx = "RESTAR"

            mensaje = f"🔹 Estado del usuario: {estado} | {msg_recup}"
            st.success(mensaje)
            st.info(f"🗓️ Días perdidos: {dias_perdido} días")
            st.info(f"📉 TX_ML: {cuenta_txml} | Acción TX_CURR: {accion_tx}")

        except Exception as e:
            st.error(f"Error en evaluación: {e}")

        # --- GUARDAR EVALUACIÓN ---
        if st.form_submit_button("📤 Guardar evaluación"):
            try:
                sheet = client.open_by_key(SPREADSHEET_ID).worksheet(txml_sheet_name)

                if not sheet.get_all_values():
                    sheet.append_row([
                        "Fecha última visita", "Fecha esperada", "Fecha recuperación", "Trimestre",
                        "Estado usuario", "Mensaje recuperación", "TX_ML", "Acción TX_CURR",
                        "País", "Unidad", "Asesor", "Fecha evaluación"
                    ])

                sheet.append_row([
                    str(fecha_ultima), str(fecha_esperada), str(fecha_recup), trimestre,
                    estado, msg_recup, cuenta_txml, accion_tx,
                    pais, unidad, asesor, str(fecha_eval)
                ])
                st.success("✅ Evaluación guardada")

                # Tabla virtual
                registros = sheet.get_all_records()
                df = pd.DataFrame(registros)
                st.subheader("🗂️ Registros recientes")
                st.dataframe(df.tail(5))
            except Exception as e:
                st.error(f"Error al guardar en Google Sheets: {e}")








