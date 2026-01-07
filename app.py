import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from huggingface_hub import HfApi, hf_hub_download

st.set_page_config(page_title="Bolsa de Valores de Ecuador – Dashboard",layout="wide", initial_sidebar_state="expanded")
st.title("Bolsa de Valores de Ecuador (ACCIONES) – Dashboard")
st.write("Este panel carga un dataset desde Hugging Face (HF) y permite visualizar la serie temporal de monto y volumen de acciones, por Emisor.")

DATASET_REPO = "beta3/Historical_Data_of_Ecuador_Stock_Exchange"  # cámbialo si usas otro

def find_a_file(repo_id: str, pattern: str = ".csv"):
    api = HfApi()
    files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    # prioriza CSV
    for f in files:
        if pattern in f:
            return f
    # si no hay CSV, intenta Parquet
    for f in files:
        if f.endswith(".parquet"):
            return f
    raise FileNotFoundError("No se encontró un CSV/Parquet en el dataset de HF.")

@st.cache_data(show_spinner=True)
def load_from_hub(repo_id: str) -> pd.DataFrame:
    filename = find_a_file(repo_id, ".csv")
    local_path = hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset")
    if filename.endswith(".csv"):
        df = pd.read_csv(local_path)
    else:
        df = pd.read_parquet(local_path)
    return df

with st.spinner("Cargando dataset desde HF Hub..."):
    raw = load_from_hub(DATASET_REPO)

# ====== Normalización automática para ACCIONES ======
import numpy as np

ACCIONES_MAP = {
    "date": ["FECHA NEGOCIACIÓN", "FECHA_NEGOCIACION", "FECHA"],
    "issuer": ["EMISOR"],
    "instrument_type": ["TÍTULO", "TITULO"],   # será "ACCIONES"
    "exchange": ["BOLSA"],                     # BVQ / BVG
    "traded_volume": ["NÚMERO DE ACCIONES", "NUMERO DE ACCIONES", "CANTIDAD"],
    "traded_value": ["VALOR EFECTO", "VALOR_EFECTO", "MONTO"],   # monto total
    "price": ["PRECIO"]
}

def _norm(s: str) -> str:
    return (s.strip().lower()
            .replace(" ", "").replace("ó","o").replace("í","i")
            .replace("é","e").replace("á","a").replace("ú","u")
            .replace("ñ","n"))

def pick_col(df, candidates):
    # busca coincidencia exacta o “normalizada” (sin acentos/espacios)
    cols_norm = {_norm(c): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        cn = _norm(c)
        if cn in cols_norm:
            return cols_norm[cn]
    return None

def standardize_acciones(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    rename_map = {}
    for std, cand in ACCIONES_MAP.items():
        found = pick_col(df, cand)
        if found:
            rename_map[found] = std
    df = df.rename(columns=rename_map)

    # tipos
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for num in ["traded_volume", "traded_value", "price"]:
        if num in df.columns:
            df[num] = (df[num].astype(str)
                       .str.replace(r"[\\s,]", "", regex=True)
                       .str.replace("\xa0", "", regex=False))
            df[num] = pd.to_numeric(df[num], errors="coerce")

    # si falta traded_value, lo calculamos
    if "traded_value" not in df.columns and {"price","traded_volume"}.issubset(df.columns):
        df["traded_value"] = df["price"] * df["traded_volume"]

    # si falta traded_volume, lo aproximamos
    if "traded_volume" not in df.columns and {"price","traded_value"}.issubset(df.columns):
        df["traded_volume"] = np.where(df["price"]>0, df["traded_value"]/df["price"], np.nan)

    # limpieza mínima
    key_cols = [c for c in ["date","issuer","traded_value","traded_volume"] if c in df.columns]
    if key_cols:
        df = df.dropna(subset=key_cols, how="all")

    if "instrument_type" in df.columns:
        df["instrument_type"] = df["instrument_type"].astype(str)
    if "exchange" in df.columns:
        df["exchange"] = df["exchange"].astype(str)
    return df

# === aplicar a lo cargado en 'raw' ===
df = standardize_acciones(raw)

# validación mínima
has_date   = "date" in df.columns and df["date"].notna().any()
has_value  = "traded_value" in df.columns
has_volume = "traded_volume" in df.columns
has_issuer = "issuer" in df.columns

if not (has_date and (has_value or has_volume)):
    st.error("Faltan columnas mínimas: 'date' + ('traded_value' o 'traded_volume'). Revisa mapeo ACCIONES_MAP.")
    st.stop()

# =====================  ESTILOS Y HELPERS  =====================
CARD_CSS = """
<style>
/* tarjetas limpias y responsivas */
.block-container { padding-top: 2.2rem; padding-bottom: 2rem; }
.card {
  background: var(--secondary-background-color, #151B2B);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 4px 16px;
}
.card h4 { margin: 0 0 0.2rem 0; font-weight: 700;border-bottom: none; }
.card .muted { color: #9aa4b2; font-size: .9rem; }
.kpi {
  display:flex; align-items:baseline; gap:.6rem;padding:1px 0.7rem;
  font-weight:700; font-size:1.6rem; line-height:1; text-align:left;
  margin-top: -3rem;
}
.kpi small { font-weight:500; font-size:.85rem; color:#9aa4b2; }
.hr { height:1px; background:rgba(255,255,255,.06); margin:.6rem 0 1rem; }
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

def card(title, subtitle=None):
    """Context manager para dibujar una tarjeta."""
    from contextlib import contextmanager
    @contextmanager
    def _card():
        st.markdown(f'<div class="card"><h4>{title}</h4>' + (f'<div class="muted">{subtitle}</div>' if subtitle else "") + '<div class="hr"></div>', unsafe_allow_html=True)
        yield
        st.markdown("</div>", unsafe_allow_html=True)
    return _card()

# =====================  SIDEBAR (FILTROS)  =====================
with st.sidebar:
    st.header("Filtros")
    # Frecuencia temporal
    freq = st.radio("Frecuencia", ["Día","Semana","Mes"], horizontal=True)
    freq_map = {"Día":"D", "Semana":"W", "Mes":"M"}

    # Fechas
    min_date, max_date = df["date"].min().date(), df["date"].max().date()
    cA, cB = st.columns(2)
    with cA: start_date = st.date_input("Desde", min_value=min_date, max_value=max_date, value=min_date)
    with cB: end_date   = st.date_input("Hasta",  min_value=min_date, max_value=max_date, value=max_date)

    # Emisor
    issuer_sel = "Todos"
    if "issuer" in df.columns:
        issuers = ["Todos"] + sorted(df["issuer"].dropna().astype(str).unique().tolist())
        issuer_sel = st.selectbox("Emisor", options=issuers, index=0)

    # Bolsa (BVQ/BVG)
    exchange_sel = "Todas"
    if "exchange" in df.columns:
        exchanges = ["Todas"] + sorted(df["exchange"].dropna().astype(str).unique().tolist())
        exchange_sel = st.selectbox("Bolsa", options=exchanges, index=0)

    # Parámetros de gráficos
    metric_choice = st.radio("Métrica de participación", ["Monto negociado","Volumen negociado"], horizontal=True)
    top_n = st.slider("Top N en la torta", 5, 25, 10, 1)

# =====================  APLICAR FILTROS  =====================
dff = df.loc[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))].copy()
if "issuer" in dff.columns and issuer_sel != "Todos":
    dff = dff[dff["issuer"].astype(str) == issuer_sel]
if "exchange" in dff.columns and exchange_sel != "Todas":
    dff = dff[dff["exchange"].astype(str) == exchange_sel]

has_value  = "traded_value"  in dff.columns
has_volume = "traded_volume" in dff.columns
metric_col = "traded_value" if (metric_choice == "Monto negociado" and has_value) else ("traded_volume" if has_volume else None)

# Serie temporal reamostrada
agg = {}
if has_value:  agg["traded_value"]  = "sum"
if has_volume: agg["traded_volume"] = "sum"
ts = (dff.set_index("date")
         .sort_index()
         .resample({"Día":"D","Semana":"W","Mes":"M"}[freq])
         .agg(agg)
         .reset_index()
         .rename(columns={"index":"date"}))

# =====================  FILA 1: KPIs  =====================
k1, k2, k3, k4 = st.columns([1,1,1,1])
with k1:
    with card("Monto negociado"):
        st.markdown(f'<div class="kpi">{(dff["traded_value"].sum() if has_value else 0):,.2f}<small>USD</small></div>', unsafe_allow_html=True)
with k2:
    with card("Volumen negociado"):
        st.markdown(f'<div class="kpi">{(dff["traded_volume"].sum() if has_volume else 0):,.0f}<small>unid.</small></div>', unsafe_allow_html=True)
with k3:
    with card("Registros"):
        st.markdown(f'<div class="kpi">{len(dff):,}</div>', unsafe_allow_html=True)
with k4:
    with card("Rango de fechas"):
        st.markdown(f'<div class="kpi">"**{start_date} → {end_date}**"</div>', unsafe_allow_html=True)


# =====================  FILA 2: Serie temporal + controles  =====================
c1, c2 = st.columns([2,1])
with c1:
    with card("Evolución temporal", f"Frecuencia: {freq}"):
        fig = go.Figure()
        if has_value:
            fig.add_trace(go.Scatter(x=ts["date"], y=ts["traded_value"], name="Monto", mode="lines"))
        if has_volume:
            fig.add_trace(go.Bar(x=ts["date"], y=ts["traded_volume"], name="Volumen", opacity=0.55, yaxis="y2"))
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Monto",
            yaxis2=dict(title="Volumen", overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

with c2:
    with card("Participación por bolsa", "Distribución del monto"):
        if "exchange" in dff.columns and has_value:
            share_ex = dff.groupby("exchange", as_index=False)["traded_value"].sum()
            st.plotly_chart(px.pie(share_ex, names="exchange", values="traded_value", hole=0.45), use_container_width=True)
        else:
            st.caption("No disponible para este archivo.")

# =====================  FILA 3: Torta por emisor + ranking mini  =====================
p1, p2 = st.columns([1.5, 1])
with p1:
    with card("Participación por emisor", f"Métrica: {metric_choice} — Top {top_n} + Otros"):
        if metric_col:
            share = (dff.groupby("issuer", as_index=False)[metric_col]
                       .sum()
                       .sort_values(metric_col, ascending=False))
            share_top = share.head(top_n).copy()
            resto = share[metric_col].iloc[top_n:].sum()
            if resto > 0:
                share_top.loc[len(share_top)] = ["Otros", resto]
            total = share_top[metric_col].sum()
            if pd.isna(total) or total == 0:
                st.info("No hay datos suficientes para mostrar participación. Ajusta filtros.")
            else:
                st.plotly_chart(px.pie(share_top, names="issuer", values=metric_col, hole=0.35), use_container_width=True)
                st.download_button("Descargar participación (CSV)",
                                   data=share_top.to_csv(index=False).encode("utf-8"),
                                   file_name="participacion_emisor.csv",
                                   mime="text/csv")
        else:
            st.info("Selecciona una métrica válida en la barra lateral.")

with p2:
    with card("Top emisores (mini)", "Top 10 por valor absoluto"):
        if metric_col:
            mini = (dff.groupby("issuer", as_index=False)[metric_col]
                      .sum()
                      .sort_values(metric_col, ascending=False)
                      .head(10))
            st.dataframe(mini, use_container_width=True, height=340)
        else:
            st.caption("Sin métrica para ordenar.")

# =====================  FILA 4: Tabla detalle + descarga  =====================
t1, = st.columns([1])
with t1:
    with card("Detalle de operaciones filtradas"):
        st.dataframe(dff, use_container_width=True, height=380)
        st.download_button("Descargar CSV filtrado",
                           data=dff.to_csv(index=False).encode("utf-8"),
                           file_name="bolsa_ec_filtrado.csv",
                           mime="text/csv")

# =====================  PESTAÑA METODOLÓGICA  =====================
with st.expander("Metodología y ficha técnica"):
    st.markdown(
        "- **Fuente**: Hugging Face Hub (HF Hub), dataset `beta3/Historical_Data_of_Ecuador_Stock_Exchange`.\n"
        "- **Cobertura**: Acciones (BVQ/BVG); filtros por fecha, emisor y bolsa.\n"
        "- **Definiciones**: *Monto negociado (traded_value)*, *Volumen negociado (traded_volume)*, *Precio (price)*.\n"
        "- **Frecuencia**: Día/Semana/Mes con reamostrado agregando sumas.\n"
        "- **Limitaciones**: outliers; variaciones de esquema entre archivos del dataset.\n"
        "- **Siglas**: HF = Hugging Face; **KPI = Indicador Clave de Desempeño**; **API = Interfaz de Programación de Aplicaciones**.\n"
    )
