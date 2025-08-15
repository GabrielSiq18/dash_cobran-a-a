import pandas as pd
import streamlit as st
import plotly.express as px
import json
import requests

# -----------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------
st.set_page_config(
    page_title="Dashboard de Cobrança", 
    page_icon=":money_with_wings:", 
    layout="wide"
)

# -----------------------------
# LOGIN SIMPLES
# -----------------------------
usuarios = {
    "Disk": "Disk321",
    "admin": "senhaadmin"
}

def login():
    st.title("🔐 Login do Dashboard")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    entrar = st.button("Entrar")

    if entrar:
        if usuario in usuarios and usuarios[usuario] == senha:
            st.session_state["logado"] = True
            st.session_state["usuario"] = usuario
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# Se não estiver logado, mostra tela de login e encerra o script
if "logado" not in st.session_state or not st.session_state["logado"]:
    login()
    st.stop()

# -----------------------------
# CARREGA DADOS
# -----------------------------
caminho_planilha = r'C:\Users\gabriel.silva\Documents\dados\COBRANÇA DISK.xlsx'
df_atualizado = pd.read_excel(caminho_planilha)

df_atualizado.columns = df_atualizado.columns.str.strip()  # Remove espaços extras

# Converte datas
df_atualizado["Data_Venc"] = pd.to_datetime(df_atualizado["Data_Venc"], errors='coerce')

# Cria colunas de ano e mês numérico
df_atualizado['Ano'] = df_atualizado['Data_Venc'].dt.year.astype('Int64')
df_atualizado['Mes'] = df_atualizado['Data_Venc'].dt.month.astype('Int64')
df_atualizado['Vendedor'] = df_atualizado['Vendedor'].str.upper()

# -----------------------------
# FILTROS NA SIDEBAR
# -----------------------------
st.sidebar.success(f"Logado como {st.session_state['usuario']}")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.experimental_rerun()

st.sidebar.header("🔍 Filtros")

vendedores_disponiveis = sorted(df_atualizado['Vendedor'].dropna().unique())
# Adiciona um checkbox para "Selecionar Todos"
selecionar_todos_vendedores = st.sidebar.checkbox("Selecionar Todos os Vendedores", value=True)

if selecionar_todos_vendedores:
    vendedores_selecionados = vendedores_disponiveis
else:
    vendedores_selecionados = st.sidebar.multiselect("Vendedores", vendedores_disponiveis)

# --- Filtro de Estados ---
estados_disponiveis = sorted(df_atualizado['Estado'].dropna().unique())
selecionar_todos_estados = st.sidebar.checkbox("Selecionar Todos os Estados", value=True)

if selecionar_todos_estados:
    estados_selecionados = estados_disponiveis
else:
    estados_selecionados = st.sidebar.multiselect("Estado", estados_disponiveis)

anos_disponiveis = sorted(df_atualizado['Ano'].dropna().unique()) 
selecionar_todos_anos = st.sidebar.checkbox("Selecionar Todos os Anos", value=True)

if selecionar_todos_anos:
    anos_selecionados = anos_disponiveis
else:
    anos_selecionados = st.sidebar.multiselect("Ano", anos_disponiveis, default=anos_disponiveis)

meses_disponiveis = sorted(df_atualizado['Mes'].dropna().unique())
selecionar_todos_meses = st.sidebar.checkbox("Selecionar Todos os Meses", value=True)

if selecionar_todos_meses:
    meses_selecionados = meses_disponiveis
else:
    meses_selecionados = st.sidebar.multiselect("Mês", meses_disponiveis, default=meses_disponiveis)

# -----------------------------
# FILTRAGEM
# -----------------------------
df_filtrado = df_atualizado[
    (df_atualizado['Ano'].isin(anos_selecionados)) &
    (df_atualizado['Mes'].isin(meses_selecionados)) &
    (df_atualizado['Estado'].isin(estados_selecionados)) &
    (df_atualizado['Vendedor'].isin(vendedores_selecionados))
]

# -----------------------------
# TÍTULO E KPIs
# -----------------------------
st.title("📊 Monitoramento de Cobranças Automáticas")
st.markdown("Acompanhamento dos status de cobrança e inadimplência")

if not df_filtrado.empty:
    total_clientes = df_filtrado['Razão'].nunique()
    total_inad = df_filtrado['Saldo'].sum()
    total_regiao = df_filtrado.groupby('Cidade')['Saldo'].sum().reset_index()
    top_10_devedores = df_filtrado.groupby('Razão')['Saldo'].sum().nlargest(10).reset_index()
    regiao_mais_inadimplente = df_filtrado.groupby('Estado')['Saldo'].sum().idxmax()
    Inad_por_vendedor = df_filtrado.groupby('Vendedor')['Saldo'].sum().reset_index()
else:
    total_clientes, total_inad, total_regiao, top_10_devedores, regiao_mais_inadimplente = 0, 0, pd.DataFrame(columns=['Cidade', 'Saldo']), pd.DataFrame(columns=['Razão', 'Saldo']), ""

col1, col2, col3 = st.columns(3)
col1.metric("Total de Clientes", f"{total_clientes:,}")
col2.metric("Total Inadimplente", f"R$ {total_inad:,.2f}")
col3.metric("Região Mais Inadimplente", regiao_mais_inadimplente)

st.markdown("---")

# -----------------------------
# GRÁFICOS
# -----------------------------
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    if not df_filtrado.empty:
        st.subheader("🏆 Top 10 Clientes Devedores")
        st.dataframe(top_10_devedores)


with col_graf2:
   if not df_filtrado.empty:
        st.subheader("📍 Inadimplência por Vendedor")

        # 1. Agrupe os dados para o gráfico
        Inad_por_vendedor = df_filtrado.groupby('Vendedor')['Saldo'].sum().sort_values(ascending=True).reset_index()
        
        # 2. Crie o gráfico de barras lateral
        fig_vendedor = px.bar(
            Inad_por_vendedor, 
            x='Saldo',  # O valor do saldo no eixo horizontal
            y='Vendedor', # O nome do vendedor no eixo vertical
            orientation='h', # Define a orientação como horizontal
            labels={'Saldo': 'Saldo Inadimplente', 'Vendedor': 'Vendedor'},
            title='Inadimplência por Vendedor'
        )

        # 3. Exiba o gráfico
        st.plotly_chart(fig_vendedor, use_container_width=True)

if not df_filtrado.empty:
    inad_mes_a_mes = (
        df_filtrado.groupby(['Ano', 'Mes'])['Saldo']
        .sum()
        .reset_index()
    )

    ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    meses_nomes = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                   7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    inad_mes_a_mes['Mes_Nome'] = inad_mes_a_mes['Mes'].map(meses_nomes)
    
    inad_mes_a_mes['Mes_Nome'] = pd.Categorical(
        inad_mes_a_mes['Mes_Nome'],
        categories=['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
        ordered=True
    )
    
    inad_mes_a_mes = inad_mes_a_mes.sort_values(['Ano', 'Mes'])
    
st.subheader("📈 Inadimplência Mês a Mês")
fig_inad_mes = px.line(
    inad_mes_a_mes, 
    x='Mes_Nome',       
    y='Saldo',  
    color='Ano',
    range_y=[0, inad_mes_a_mes['Saldo'].max() * 1.1] 
)
st.plotly_chart(fig_inad_mes, use_container_width=True)


if not df_filtrado.empty:
        st.subheader("📍 Inadimplência por Estado")

        total_regiao = df_filtrado.groupby('Estado')['Saldo'].sum().reset_index()

        url_geojson = 'https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson'
        geojson_estados = requests.get(url_geojson).json()

        fig_regiao = px.choropleth_mapbox(
            total_regiao,
            geojson=geojson_estados,
            locations='Estado',
            color='Saldo',
            featureidkey="properties.sigla",
            mapbox_style="carto-positron",
            zoom=2.8,
            center={"lat": -14.2350, "lon": -51.9253},
            opacity=0.6,
            labels={'Saldo': 'Inadimplência'},
            color_continuous_scale=["#ffff00", "#ffa500","#ff0000"],
        )
        fig_regiao.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

        st.plotly_chart(fig_regiao, use_container_width=True)

st.subheader("📊 Relação dos Clientes")
st.dataframe(df_filtrado, use_container_width=True)


