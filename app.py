import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px
from sqlalchemy import create_engine

# Configuração do banco
usuario = "data_iesb"
senha = "wjDfqcUxfjtYXp04tr0S"
host = "rds-prod.cmt2mu288c4s.us-east-1.rds.amazonaws.com"
porta = "5432"
banco = "iesb"

engine = create_engine(f"postgresql+psycopg2://{usuario}:{senha}@{host}:{porta}/{banco}")
nome_view = "educacao_basica_ride_df"
data_ride = pd.read_sql(f"SELECT * FROM {nome_view}", con=engine)
DATA_URL = "https://raw.githubusercontent.com/usuario/repositorio/main/educacao_basica_ride_df.csv"

# Colunas de interesse
COLS = [
    "QT_MAT_BAS", "CO_ENTIDADE", "QT_DOC_BAS", "CO_MUNICIPIO", "TP_DEPENDENCIA",
    "QT_MAT_INF", "QT_MAT_FUND", "QT_MAT_MED", "QT_MAT_EJA", "NU_ANO_CENSO",
    "QT_MAT_BAS_BRANCA", "QT_MAT_BAS_PRETA", "QT_MAT_BAS_PARDA", "QT_MAT_BAS_AMARELA",
    "QT_MAT_BAS_INDIGENA", "QT_TUR_BAS", "IN_INTERNET", "IN_BIBLIOTECA",
    "IN_LABORATORIO_INFORMATICA", "IN_QUADRA_ESPORTES", "IN_LABORATORIO_CIENCIAS",
    "IN_ACESSIBILIDADE_RAMPAS", "TP_LOCALIZACAO", "IN_ALIMENTACAO",
    "QT_DESKTOP_ALUNO", "QT_COMP_PORTATIL_ALUNO", "QT_TABLET_ALUNO",
    "QT_PROF_BIBLIOTECARIO", "QT_PROF_PSICOLOGO", "QT_PROF_ASSIST_SOCIAL",
    "QT_MAT_INF_INT", "QT_MAT_FUND_INT", "QT_MAT_MED_INT", "NO_DISTRITO"
]

STAGE_COLUMN = {
    "Básico": "QT_MAT_BAS",
    "Infantil": "QT_MAT_INF",
    "Fundamental": "QT_MAT_FUND",
    "Médio": "QT_MAT_MED",
    "EJA": "QT_MAT_EJA",
}

st.set_page_config(
    page_title="Educação Básica – RIDE/DF",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data(show_spinner=True)
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, usecols=COLS, low_memory=False)
    df["media_alunos_turma"] = df["QT_MAT_BAS"] / df["QT_TUR_BAS"].replace(0, pd.NA)
    return df

def sidebar_data_source():
    return st.sidebar.radio(
        "Fonte de dados",
        ("GitHub CSV", "Banco de Dados (PostgreSQL)"),
        horizontal=True,
    )

def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("🔎 Filtros")
    stage = st.sidebar.radio(
        "Fase de ensino",
        list(STAGE_COLUMN.keys()),
        horizontal=True,
    )
    years = sorted(df["NU_ANO_CENSO"].unique())
    year = st.sidebar.select_slider(
        "Ano do censo", options=years, value=max(years)
    )
    return stage, year

def main():
    data_source = sidebar_data_source()

    if data_source == "GitHub CSV":
        data = load_data(DATA_URL)
    else:
        data = data_ride.copy()
        data = data[COLS]
        data["media_alunos_turma"] = data["QT_MAT_BAS"] / data["QT_TUR_BAS"].replace(0, pd.NA)

    stage, year = sidebar_filters(data)
    df_year = data.query("NU_ANO_CENSO == @year")
    stage_col = STAGE_COLUMN[stage]

    st.title("Relatório Educação Básica – RIDE/DF")
    st.subheader(f"Ano: {year} · Fase: {stage}")

    col1, col2, col3 = st.columns(3)
    col1.metric("🏫 Escolas", f"{df_year['CO_ENTIDADE'].nunique():,}")
    col2.metric("👨‍🎓 Matrículas", f"{df_year[stage_col].sum():,}")
    col3.metric("👨‍🏫 Docentes", f"{df_year['QT_DOC_BAS'].sum():,}")

    top_muni = (
        df_year.groupby("NO_DISTRITO")[stage_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    st.subheader("Top 10 municípios por matrículas")
    st.bar_chart(top_muni, x="NO_DISTRITO", y=stage_col)

    dep = df_year.groupby("TP_DEPENDENCIA")[stage_col].sum().reset_index()
    fig_dep, ax_dep = plt.subplots()
    ax_dep.pie(
        dep[stage_col],
        labels=dep["TP_DEPENDENCIA"],
        autopct="%1.1f%%",
        startangle=90,
    )
    ax_dep.axis("equal")
    st.subheader("Distribuição de matrículas por dependência administrativa")
    st.pyplot(fig_dep)

    serie_historica = (
        data.groupby("NU_ANO_CENSO")[stage_col].sum().reset_index()
    )
    fig_hist = px.bar(
        serie_historica,
        x="NU_ANO_CENSO",
        y=stage_col,
        text=stage_col,
        labels={"NU_ANO_CENSO": "Ano", stage_col: "Matrículas"},
        title="Matrículas ao longo dos anos (RIDE/DF)",
    )
    fig_hist.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_hist.update_layout(yaxis_title="Matrículas", xaxis_title="Ano")
    st.plotly_chart(fig_hist, use_container_width=True)

    media_turma = (
        df_year.groupby("NO_DISTRITO")["media_alunos_turma"]
        .mean()
        .dropna()
        .sort_values()
        .head(10)
        .reset_index()
    )
    st.subheader("Menor média de alunos por turma (Top 10 municípios)")
    st.bar_chart(media_turma, x="NO_DISTRITO", y="media_alunos_turma")


if __name__ == "__main__":
    main()
