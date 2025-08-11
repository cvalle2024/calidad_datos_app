import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Evaluación Calidad de Datos", layout="wide", page_icon="📊")

# --- Cargar credenciales desde st.secrets ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=scope)
client = gspread.authorize(creds)

# --- Obtener ID de hoja desde secrets ---
SPREADSHEET_ID = st.secrets["google_sheets"]["spreadsheet_id"]
hts_sheet_name = st.secrets["google_sheets"]["hts_sheet"]
txml_sheet_name = st.secrets["google_sheets"]["txml_sheet"]

# --- Menú lateral ---
menu = st.sidebar.selectbox("Selecciona una sección:", ["HTS_TST", "TX_ML y TX_RTT"])
mostrar_historial = st.sidebar.checkbox("📄 Ver historial")

# --- Ver historial ---
if mostrar_historial:
    sheet_name = hts_sheet_name if menu == "HTS_TST" else txml_sheet_name
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    data = sheet.get_all_records()
    df_hist = pd.DataFrame(data)
    st.subheader("📊 Historial de evaluaciones")
    st.dataframe(df_hist, use_container_width=True)

# ==========================
# ======= HTS_TST ==========
# ==========================
if menu == "HTS_TST":
    st.title("📋 Evaluación de Calidad de Datos - HTS_TST")

    st.header("💼 Datos generales")
    col1, col2, col3 = st.columns(3)
    with col1:
        pais = st.selectbox("País", ["Honduras", "Guatemala", "El Salvador", "Nicaragua", "Panamá"])
        mes_reporte = st.selectbox(
            "Mes de reporte",
            ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        )
    with col2:
        unidad = st.text_input("Nombre de la unidad")
        fecha_recepcion = st.date_input("Fecha de recepción")
    with col3:
        registros_revisados = st.number_input("Número de registros revisados", min_value=1, step=1)
        asesor = st.text_input("Nombre del asesor (revisor)")

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
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            cumple = st.radio("Cumple", ["Sí", "No"], key=f"cumple_{i}", horizontal=True)
        with c2:
            accion = st.radio("Acción correctiva realizada", ["Sí", "No"], key=f"accion_{i}", horizontal=True)
        with c3:
            observacion = st.text_input("Observaciones", key=f"obs_{i}")

        respuestas.append({
            "criterio": criterio,
            "cumple": cumple,
            "accion_correctiva": accion,
            "observacion": observacion
        })

    # === Resumen visual de cumplimiento ===
    st.subheader("📈 Resumen de cumplimiento")
    df_chk = pd.DataFrame(respuestas)

    # Asegurar orden "Sí", "No" aunque falte alguno
    conteo_global = df_chk['cumple'].value_counts().reindex(['Sí', 'No'], fill_value=0)
    df_global = conteo_global.rename_axis('Estado').to_frame('Cantidad')

    colg1, colg2 = st.columns([1,2])
    with colg1:
        st.metric("Total criterios", int(df_chk.shape[0]))
        st.metric("Cumplen (Sí)", int(conteo_global.get('Sí', 0)))
        st.metric("No cumplen (No)", int(conteo_global.get('No', 0)))

    with colg2:
        st.caption("Total de criterios que cumplen vs no cumplen")
        st.bar_chart(df_global, use_container_width=True)

    # --- Barras por criterio (apiladas Sí/No) ---
    st.subheader("🧩 Cumplimiento por criterio")
    pivot_criterio = (
        df_chk
        .pivot_table(index='criterio', columns='cumple', values='accion_correctiva', aggfunc='count', fill_value=0)
        .reindex(columns=['Sí', 'No'], fill_value=0)
    )
    st.caption("Cada barra muestra, por criterio, cuántas veces se marcó 'Sí' y 'No'")
    st.bar_chart(pivot_criterio, use_container_width=True)

    with st.expander("Ver detalle de criterios"):
        st.dataframe(pivot_criterio.reset_index(), use_container_width=True)

    # --- Envío a Google Sheets ---
    if st.button("📤 Enviar evaluación", key="submit_hts"):
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(hts_sheet_name)
        for fila in respuestas:
            sheet.append_row([
                pais, mes_reporte, unidad, str(fecha_recepcion), registros_revisados, asesor,
                fila["criterio"], fila["cumple"], fila["accion_correctiva"], fila["observacion"]
            ])
        st.success("✅ Evaluación enviada y guardada")
        df_resumen = pd.DataFrame(respuestas)
        st.dataframe(df_resumen, use_container_width=True)
        st.download_button(
            "⬇️ Descargar Excel",
            data=df_resumen.to_csv(index=False).encode("utf-8"),
            file_name="HTS_TST_resultados.csv"
        )

# ==========================
# ====== TX_ML / RTT =======
# ==========================
elif menu == "TX_ML y TX_RTT":
    st.title("📋 Evaluación TX_ML y TX_RTT")

    # ---------- Utilidades seguras ----------
    def _es_fecha(x):
        return isinstance(x, date)

    def _anio_base(fecha_esperada, fecha_registro):
        if _es_fecha(fecha_esperada):
            return fecha_esperada.year
        if _es_fecha(fecha_registro):
            return fecha_registro.year
        return date.today().year

    def _fin_trimestre(tri, anio):
        limites = {
            "Q1": date(anio, 12, 31),
            "Q2": date(anio, 3, 31),
            "Q3": date(anio, 6, 30),
            "Q4": date(anio, 9, 30)
        }
        return limites[tri]

    def _fmt_fecha(x):
        return x.strftime("%Y-%m-%d") if _es_fecha(x) else ""

    # ---------- Datos generales ----------
    st.header("💼 Datos generales")
    col1, col2 = st.columns(2)
    with col1:
        pais_tx = st.selectbox("País", ["Honduras", "Guatemala", "El Salvador", "Nicaragua", "Panamá"], key="pais_tx")
        unidad_tx = st.text_input("Unidad de salud", key="unidad_tx")
    with col2:
        asesor_tx = st.text_input("Asesor responsable", key="asesor_tx")
        fecha_registro = st.date_input("Fecha de evaluación", key="fecha_eval")

    # ---------- Datos del paciente ----------
    st.header("🧑 Datos del paciente")
    c1, c2 = st.columns(2)
    with c1:
        fecha_ultima_visita = st.date_input("Fecha última visita", value=None, key="f_ult_visita")
        fecha_esperada = st.date_input("Fecha esperada de visita", value=None, key="f_esperada")
        st.caption("Requerido para calcular días perdidos y TX_ML/TX_CURR")
        fecha_recuperacion = st.date_input("Fecha de recuperación", value=None, key="f_recuperacion")
    with c2:
        trimestre = st.selectbox("Trimestre", ["Q1", "Q2", "Q3", "Q4"])

    # Año de referencia robusto
    anio_ref = _anio_base(fecha_esperada, fecha_registro)
    fin_trimestre = _fin_trimestre(trimestre, anio_ref)

    # Cálculo de días perdidos sólo si existe fecha_esperada
    if _es_fecha(fecha_esperada):
        ref = fecha_recuperacion if _es_fecha(fecha_recuperacion) else date.today()
        dias_perdido = (ref - fecha_esperada).days
    else:
        dias_perdido = None  # No se puede calcular sin fecha_esperada

    cuenta_tx_ml = "NO"
    accion_tx_curr = "NINGUNA"
    estado_usuario = ""
    mensaje_recuperacion = ""
    alerta_logica = ""

    # Reglas con tolerancia a nulos
    if _es_fecha(fecha_recuperacion) and _es_fecha(fecha_esperada) and (fecha_recuperacion < fecha_esperada):
        cuenta_tx_ml = "ERROR"
        accion_tx_curr = "Fecha de recuperación < esperada"
        alerta_logica = "⚠️ Fecha de recuperación es anterior a la esperada."
    elif dias_perdido is None:
        estado_usuario = "Información insuficiente"
        mensaje_recuperacion = "No se puede calcular sin 'Fecha esperada de visita'."
        cuenta_tx_ml = "N/A"
        accion_tx_curr = "N/A"
    else:
        if dias_perdido < 28:
            estado_usuario = "Activo en la cohorte"
            mensaje_recuperacion = "---"
            cuenta_tx_ml = "NO"
            accion_tx_curr = "NINGUNA"
        elif 28 <= dias_perdido < 90:
            estado_usuario = "Perdido en seguimiento"
            if _es_fecha(fecha_recuperacion):
                if fecha_recuperacion <= fin_trimestre:
                    mensaje_recuperacion = "Se recuperó en el trimestre"
                    cuenta_tx_ml = "NO"
                    accion_tx_curr = "NINGUNA"
                else:
                    mensaje_recuperacion = "Se recuperó en otro trimestre"
                    cuenta_tx_ml = "SÍ"
                    accion_tx_curr = "RESTAR"
            else:
                mensaje_recuperacion = "No se recuperó en el trimestre"
                cuenta_tx_ml = "SÍ"
                accion_tx_curr = "RESTAR"
        else:
            estado_usuario = "En abandono"
            if _es_fecha(fecha_recuperacion):
                if fecha_recuperacion <= fin_trimestre:
                    mensaje_recuperacion = "Se recuperó en el trimestre"
                    cuenta_tx_ml = "NO"
                    accion_tx_curr = "NINGUNA"
                else:
                    mensaje_recuperacion = "Se recuperó en otro trimestre"
                    cuenta_tx_ml = "SÍ"
                    accion_tx_curr = "RESTAR"
            else:
                mensaje_recuperacion = "No se recuperó en el trimestre"
                cuenta_tx_ml = "SÍ"
                accion_tx_curr = "RESTAR"

    # Mensajes
    if alerta_logica:
        st.warning(alerta_logica)

    estado_txt = f"🔹 Estado: {estado_usuario} | {mensaje_recuperacion}"
    st.success(estado_txt)

    if dias_perdido is None:
        st.info("🗓 Días perdidos: N/D (falta 'Fecha esperada de visita')")
    else:
        st.info(f"🗓 Días perdidos: {dias_perdido}")

    st.info(f"📉 TX_ML: {cuenta_tx_ml} | TX_CURR: {accion_tx_curr}")

    # ---------- Reglas de habilitación de guardado ----------
    puede_guardar = _es_fecha(fecha_esperada) and not (
        _es_fecha(fecha_recuperacion) and _es_fecha(fecha_esperada) and (fecha_recuperacion < fecha_esperada)
    )

    # Mensajes de validación
    if not _es_fecha(fecha_esperada):
        st.error("❗ Falta 'Fecha esperada de visita'. No se puede guardar hasta ingresarla.")
    elif _es_fecha(fecha_recuperacion) and _es_fecha(fecha_esperada) and (fecha_recuperacion < fecha_esperada):
        st.error("❗ La 'Fecha de recuperación' no puede ser anterior a la 'Fecha esperada de visita'.")

    # ---------- Guardar ----------
    if st.button("📤 Guardar evaluación", key="guardar_tx", disabled=not puede_guardar):
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet(txml_sheet_name)
        sheet.append_row([
            _fmt_fecha(fecha_ultima_visita), _fmt_fecha(fecha_esperada), _fmt_fecha(fecha_recuperacion), trimestre,
            estado_usuario, mensaje_recuperacion, cuenta_tx_ml, accion_tx_curr,
            pais_tx, unidad_tx, asesor_tx, _fmt_fecha(fecha_registro)
        ])
        st.success("✅ Evaluación guardada")

        registros = sheet.get_all_records()
        df_reg = pd.DataFrame(registros)
        st.subheader("🗂 Registros recientes")
        st.dataframe(df_reg.tail(5), use_container_width=True)





