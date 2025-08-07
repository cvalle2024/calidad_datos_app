import streamlit as st
import pandas as pd
from datetime import timedelta

st.set_page_config(page_title="Evaluación Calidad de Datos - HTS", layout="wide")

# --- Menú lateral
menu = st.sidebar.selectbox("Selecciona una sección:", [
    "HTS_TST",
    "TrianTX_RTT y TX_ML"
])

# --- HTS_TST ---

if st.sidebar.checkbox("📄 Ver historial HTS_TST"):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("credenciales.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Calidad_Datos").worksheet("HTS_TST")
        data = sheet.get_all_records()
        df_hist_hts = pd.DataFrame(data)
        st.subheader("📊 Historial de evaluaciones HTS_TST")
        st.dataframe(df_hist_hts)
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")
if menu == "HTS_TST":
    st.title("📋 Evaluación de Calidad de Datos - HTS_TST")

    # --- Sección A: Datos generales
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

    # --- Sección B: Lista de chequeo
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
        "Ingreso de variable embarazada únicamente en sexo femenino",
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
        import gspread
        from google.oauth2.service_account import Credentials
import os

        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        if not os.path.exists("credenciales.json"):
    st.error("❌ No se encontró el archivo 'credenciales.json'. Por favor colócalo en el mismo directorio.")
    st.stop()
creds = Credentials.from_service_account_file("credenciales.json", scopes=scope)
        client = gspread.authorize(creds)

        sheet = client.open("Calidad_Datos").worksheet("HTS_TST")

        if len(sheet.get_all_values()) == 0:
            headers = ["País", "Mes", "Unidad", "Fecha recepción", "Revisados", "Asesor", "Criterio", "Cumple", "Acción correctiva", "Observación"]
            sheet.append_row(headers)

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

# --- TrianTX_RTT y TX_ML ---

if st.sidebar.checkbox("📄 Ver historial TX_ML"):
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Calidad_Datos").worksheet("TX_ML")
        data = sheet.get_all_records()
        df_hist_tx = pd.DataFrame(data)
        st.subheader("📊 Historial de evaluaciones TX_ML")
        st.dataframe(df_hist_tx)
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")
elif menu == "TrianTX_RTT y TX_ML":
    st.header("🗂️ Datos generales")
    col1, col2, col3 = st.columns(3)
    with col1:
        pais_tx = st.selectbox("País", ["Honduras", "Guatemala", "El Salvador", "Nicaragua", "Panamá"], key="pais_tx")
        mes_reporte_tx = st.selectbox("Mes de reporte", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], key="mes_tx")
    with col2:
        unidad_tx = st.text_input("Nombre de la unidad", key="unidad_tx")
        fecha_recepcion_tx = st.date_input("Fecha de recepción", key="fecha_rx_tx")
    with col3:
        registros_revisados_tx = st.number_input("Número de registros revisados", min_value=1, step=1, key="rev_tx")
        asesor_tx = st.text_input("Nombre del asesor (revisor)", key="asesor_tx")

    st.title("🧪 Evaluación de TrianTX_RTT y TX_ML")
    st.title("🧪 Evaluación de TrianTX_RTT y TX_ML")

    st.subheader("📝 Ingreso manual de datos por paciente")
    registros = st.number_input("¿Cuántos registros deseas evaluar?", min_value=1, max_value=20, value=5, step=1)

    resultados = []
    for i in range(registros):
        st.markdown(f"---\n### Registro #{i+1}")
        col1, col2 = st.columns(2)

        with col1:
            fecha_esperada = st.date_input(f"📆 Fecha cita esperada", key=f"fecha_esperada_{i}")
            fecha_recuperacion = st.date_input(f"📆 Fecha de recuperación (si aplica)", key=f"fecha_recuperacion_{i}")

        with col2:
            trimestre = st.selectbox(f"📅 Trimestre de reporte", ["Q1 (Oct-Dic)", "Q2 (Ene-Mar)", "Q3 (Abr-Jun)", "Q4 (Jul-Sep)"], key=f"trimestre_{i}")
            abandono = st.radio(f"¿Paciente se perdió?", ["SI", "NO"], key=f"abandono_{i}")

        # Calcular fechas de fin de trimestre
        if trimestre.startswith("Q1"):
            fin_trimestre = pd.to_datetime("2024-12-31")
        elif trimestre.startswith("Q2"):
            fin_trimestre = pd.to_datetime("2025-03-31")
        elif trimestre.startswith("Q3"):
            fin_trimestre = pd.to_datetime("2025-06-30")
        else:
            fin_trimestre = pd.to_datetime("2025-09-30")

        dias_perdido = (fin_trimestre - pd.to_datetime(fecha_esperada)).days if abandono == "SI" and fecha_esperada else 0
        fue_recuperado = fecha_recuperacion and pd.to_datetime(fecha_recuperacion) <= fin_trimestre

        # --- Lógica TX_ML
        if fecha_recuperacion and fecha_recuperacion < fecha_esperada:
            cuenta_tx_ml = "ERROR"
            accion_tx_curr = "Fecha recuperación < fecha esperada"
            mensaje = "⚠️ Error: Fecha de recuperación es anterior a la cita esperada."
        elif abandono == "NO":
            cuenta_tx_ml = "NO"
            accion_tx_curr = "NINGUNA"
            mensaje = "✅ El paciente no se perdió, no aplica TX_ML."
        elif abandono == "SI" and dias_perdido > 28 and not fue_recuperado:
            cuenta_tx_ml = "SI"
            accion_tx_curr = "RESTAR"
            mensaje = "📌 El paciente se perdió y no fue recuperado en el trimestre. Se reporta en TX_ML."
        elif abandono == "SI" and fue_recuperado:
            cuenta_tx_ml = "NO"
            accion_tx_curr = "NINGUNA"
            mensaje = "🟢 El paciente se perdió pero fue recuperado en el mismo trimestre. No entra al TX_ML."
        else:
            cuenta_tx_ml = "NO"
            accion_tx_curr = "NINGUNA"
            mensaje = "🟡 El paciente no cumple condiciones para TX_ML."

        st.info(f"📉 TX_ML: {cuenta_tx_ml} | Acción TX_CURR: {accion_tx_curr}")
        if cuenta_tx_ml == "ERROR":
            st.warning(mensaje)
        else:
            st.success(mensaje)

        resultados.append({
            "registro": i+1,
            "fecha_esperada": str(fecha_esperada),
            "fecha_recuperacion": str(fecha_recuperacion),
            "trimestre": trimestre,
            "dias_perdido": dias_perdido,
            "tx_ml": cuenta_tx_ml,
            "accion_tx_curr": accion_tx_curr
        })

    if st.button("📤 Enviar validación", key="submit_tx_manual"):
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        client = gspread.authorize(creds)

        sheet = client.open("Calidad_Datos").worksheet("TX_ML")

        # Registrar encabezado si es la primera vez
        if len(sheet.get_all_values()) == 0:
            headers = [
                "País", "Mes", "Unidad", "Fecha recepción", "Revisados", "Asesor",
                "Registro", "Fecha esperada", "Fecha recuperación", "Trimestre", "Días perdido", "TX_ML", "Acción TX_CURR"
            ]
            sheet.append_row(headers)

        for fila in resultados:
            sheet.append_row([
                pais_tx, mes_reporte_tx, unidad_tx, str(fecha_recepcion_tx), registros_revisados_tx, asesor_tx,
                fila["registro"], fila["fecha_esperada"], fila["fecha_recuperacion"], fila["trimestre"],
                fila["dias_perdido"], fila["tx_ml"], fila["accion_tx_curr"]
            ])

        st.success("✅ Evaluación enviada y guardada en Google Sheets")
        st.write("### Resultados registrados:")
        df_resultados = pd.DataFrame(resultados)
        st.dataframe(df_resultados)
        st.download_button("⬇️ Descargar resultados como Excel", data=df_resultados.to_csv(index=False).encode('utf-8'), file_name="TX_ML_resultados.csv", mime="text/csv")
