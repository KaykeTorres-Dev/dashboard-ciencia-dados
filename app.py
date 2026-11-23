import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de vendas da Amazon", layout="wide")

# Estilo visual
st.markdown("""
    <style>
        .main { background-color: #F8F9FA; }
        h1 { color: #1B2B5E; }
    </style>
""", unsafe_allow_html=True)

# Taxa de conversão: 1 INR (Rupia) ≈ R$ 0.06
TAXA_INR_PARA_BRL = 0.06

# Carregamento e tratamento dos dados
@st.cache_data
def load_data():
    df = pd.read_csv("Base de dados - Amazon Sales Bruto.csv")
    
    # Tratamento dos preços originais em INR
    df['discounted_price_num'] = df['discounted_price'].astype(str).str.replace('₹','', regex=True).str.replace(',','', regex=True).str.strip().astype(float)
    df['rating_count_num'] = pd.to_numeric(df['rating_count'].astype(str).str.replace(',','', regex=True).str.strip(), errors='coerce').fillna(0)
    df['rating_num'] = pd.to_numeric(df['rating'], errors='coerce')
    
    # Extração da categoria principal
    df['categoria_principal'] = (
        df['category'].astype(str)
        .apply(lambda x: x.split('|')[0] if '|' in x else x)
        .str.replace('&', ' & ', regex=False)
        .str.replace('  ', ' ', regex=False)
        .str.strip()
    )
    
    # Conversão para Real Brasileiro (R$)
    df['preco_brl'] = df['discounted_price_num'] * TAXA_INR_PARA_BRL
    df['faturamento_estimado_brl'] = df['preco_brl'] * df['rating_count_num']
    
    return df

df = load_data()

# Título do Dashboard
st.title("🛒 Dashboard de vendas da Amazon (Valores em R$)")
st.markdown("Análise interativa de faturamento, volume de avaliações e satisfação dos clientes (convertidos para o Real Brasileiro).")

# Filtros na barra lateral (Sidebar)
st.sidebar.header("Filtros do dashboard")
cat_selecionada = st.sidebar.selectbox("Selecione a categoria principal", ["Todas"] + list(df['categoria_principal'].unique()))

if cat_selecionada != "Todas":
    df_filtrado = df[df['categoria_principal'] == cat_selecionada]
else:
    df_filtrado = df

# Função para formatar valores monetários grandes com a escala (Milhões, Bilhões, Trilhões) no padrão pt-BR
def formatar_moeda_amigavel(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    if valor >= 1e12:
        val_fmt = f"{valor / 1e12:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {val_fmt} Trilhões"
    elif valor >= 1e9:
        val_fmt = f"{valor / 1e9:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {val_fmt} Bilhões"
    elif valor >= 1e6:
        val_fmt = f"{valor / 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {val_fmt} Milhões"
    else:
        val_fmt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {val_fmt}"

# Função para formatar quantidades grandes com a escala (Mil, Milhões, Bilhões) no padrão pt-BR
def formatar_qtd_amigavel(valor):
    if pd.isna(valor):
        return "0"
    if valor >= 1e9:
        val_fmt = f"{valor / 1e9:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{val_fmt} Bilhões"
    elif valor >= 1e6:
        val_fmt = f"{valor / 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{val_fmt} Milhões"
    elif valor >= 1e3:
        val_fmt = f"{valor / 1e3:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{val_fmt} Mil"
    else:
        return f"{valor:,.0f}".replace(",", ".")

# Bloco de KPIs (Cartões em R$)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

faturamento_total = df_filtrado['faturamento_estimado_brl'].sum()
quantidade_total = df_filtrado['rating_count_num'].sum()
avaliacao_media = df_filtrado['rating_num'].mean()
ticket_medio = faturamento_total / quantidade_total if quantidade_total > 0 else 0

kpi1.metric("Faturamento estimado", formatar_moeda_amigavel(faturamento_total))
kpi2.metric("Qtd. vendida (Est.)", formatar_qtd_amigavel(quantidade_total))
kpi3.metric("Avaliação média", f"{avaliacao_media:.2f} ⭐")
kpi4.metric("Ticket médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# Linha 1 de Gráficos (2 colunas)
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Top 10 produtos por nº de avaliações")
    top10 = df_filtrado.nlargest(10, 'rating_count_num')
    
    fig_top10 = px.bar(
        top10, 
        x='rating_count_num', 
        y='product_name', 
        orientation='h',
        labels={'rating_count_num': 'Nº de avaliações', 'product_name': 'Produto'},
        color='rating_count_num', 
        color_continuous_scale='Blues'
    )
    
    fig_top10.update_traces(
        hovertemplate="<b>%{y}</b><br>Nº de avaliações: %{x:,.0f}<extra></extra>"
    )
    
    fig_top10.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_top10, use_container_width=True)

with col_g2:
    st.subheader("Faturamento estimado por Categoria (Top 3)")
    cat_fat = df_filtrado.groupby('categoria_principal')['faturamento_estimado_brl'].sum().reset_index()
    cat_fat = cat_fat.sort_values(by='faturamento_estimado_brl', ascending=False)
    
    if len(cat_fat) > 5:
        top5 = cat_fat.head(5)
        outros = pd.DataFrame({'categoria_principal': ['Outros'], 'faturamento_estimado_brl': [cat_fat.tail(len(cat_fat)-5)['faturamento_estimado_brl'].sum()]})
        cat_fat_final = pd.concat([top5, outros], ignore_index=True)
    else:
        cat_fat_final = cat_fat

    cat_fat_final['fat_formatado'] = cat_fat_final['faturamento_estimado_brl'].apply(formatar_moeda_amigavel)
    
    fig_pie = px.pie(
        cat_fat_final, 
        names='categoria_principal', 
        values='faturamento_estimado_brl', 
        hole=0.4,
        custom_data=['fat_formatado']
    )
    
    fig_pie.update_traces(
        hovertemplate="<b>%{label}</b><br>Faturamento est.: %{customdata[0]}<br>Porcentagem: %{percent}<extra></extra>"
    )
    
    st.plotly_chart(fig_pie, use_container_width=True)

# Linha 2 de Gráficos (Dispersão e Tabela)
col_g3, col_g4 = st.columns(2)

with col_g3:
    st.subheader("Relação: preço (R$) x Nota dos produtos")
    
    fig_scatter = px.scatter(
        df_filtrado.head(200), 
        x='preco_brl', 
        y='rating_num',
        size='rating_count_num', 
        hover_name='product_name', 
        labels={
            'preco_brl': 'Preço com desconto (R$)', 
            'rating_num': 'Nota média',
            'rating_count_num': 'Nº de avaliações'
        },
        color='rating_num', 
        color_continuous_scale='Viridis'
    )
    
    fig_scatter.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Preço: R$ %{x:,.2f}<br>Nota média: %{y:.2f} ⭐<extra></extra>",
        customdata=df_filtrado.head(200)[['product_name']].values
    )
    
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_g4:
    st.subheader("Resumo analítico por categoria (Tabela condicional)")
    tabela_resumo = df_filtrado.groupby('categoria_principal').agg(
        Produtos=('product_id', 'count'),
        Faturamento_Est_BRL=('faturamento_estimado_brl', 'sum'),
        Nota_Media=('rating_num', 'mean')
    ).reset_index().sort_values(by='Faturamento_Est_BRL', ascending=False)
    
    tabela_resumo['Faturamento estimado (R$)'] = tabela_resumo['Faturamento_Est_BRL'].apply(formatar_moeda_amigavel)
    
    tabela_exibicao = tabela_resumo[['categoria_principal', 'Produtos', 'Faturamento estimado (R$)', 'Nota_Media']].rename(columns={
        'categoria_principal': 'Categoria principal',
        'Produtos': 'Produtos',
        'Nota_Media': 'Nota média'
    })
    
    st.dataframe(
        tabela_exibicao.style.background_gradient(subset=['Faturamento estimado (R$)'], gmap=tabela_resumo['Faturamento_Est_BRL'], cmap='Blues')
                             .background_gradient(subset=['Nota média'], cmap='Blues')
                             .format({'Nota média': '{:.2f}', 'Produtos': '{:,}'.format}),
        use_container_width=True,
        hide_index=True
    )

# Rodapé
st.markdown("---")
st.caption("Fonte: Amazon Sales Dataset (Kaggle). Valores convertidos de INR para BRL (1 INR = R$ 0,06).")