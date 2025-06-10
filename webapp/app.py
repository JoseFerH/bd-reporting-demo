"""
APP.PY
======
Aplicación Principal - Dashboard BI Ferretería Petapa
Sistema Integrado de Business Intelligence

Autor: José Fernando Hurtarte
Email: jhurtarte1@gmail.com
Fecha: Diciembre 2024

Funcionalidades:
- Dashboard interactivo con KPIs en tiempo real
- Análisis predictivo con Machine Learning
- Gestión de alertas automáticas
- Reportes financieros avanzados
- Integración con PostgreSQL
- Deploy en Heroku
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Agregar directorio actual al path para imports locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports locales
try:
    from database_config import DatabaseManager
    from ml_predictions import InventoryMLAnalyzer
    DATABASE_AVAILABLE = True
except ImportError as e:
    st.warning(f"⚠️ Módulos de base de datos no disponibles: {e}")
    DATABASE_AVAILABLE = False

import warnings
warnings.filterwarnings('ignore')

# ================================
# CONFIGURACIÓN INICIAL
# ================================

st.set_page_config(
    page_title="🔧 Ferretería Petapa - Dashboard BI",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/tu-usuario/bd-reporting-demo',
        'Report a bug': 'mailto:jhurtarte1@gmail.com',
        'About': """
        # Ferretería Petapa - Dashboard BI
        
        Sistema de Business Intelligence desarrollado por **José Fernando Hurtarte**.
        
        **Funcionalidades principales:**
        - Control de inventarios en tiempo real
        - Análisis predictivo con ML
        - Gestión de alertas automáticas
        - Reportes financieros avanzados
        
        **Tecnologías utilizadas:**
        - Python + Streamlit
        - PostgreSQL
        - Plotly + Pandas
        - Scikit-learn
        - Heroku (Deploy)
        
        📧 **Contacto:** jhurtarte1@gmail.com
        """
    }
)

# CSS personalizado mejorado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #60a5fa 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.3);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .main-header h3 {
        color: #e0e7ff;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
        font-size: 1.2rem;
    }
    
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 5px solid #3b82f6;
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    .metric-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .alert-critical { border-left-color: #ef4444; }
    .alert-high { border-left-color: #f97316; }
    .alert-medium { border-left-color: #eab308; }
    .alert-low { border-left-color: #22c55e; }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-green { background-color: #22c55e; }
    .status-yellow { background-color: #eab308; }
    .status-orange { background-color: #f97316; }
    .status-red { background-color: #ef4444; }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    .info-box {
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        border: 1px solid #0ea5e9;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .success-box {
        background: linear-gradient(135deg, #f0fdf4, #dcfce7);
        border: 1px solid #22c55e;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fffbeb, #fef3c7);
        border: 1px solid #f59e0b;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ================================
# FUNCIONES DE DATOS
# ================================

@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_data_source():
    """
    Cargar datos desde la fuente disponible (CSV o Base de Datos)
    
    Returns:
        tuple: (DataFrame principal, alertas, movimientos, es_db)
    """
    if DATABASE_AVAILABLE and os.getenv('DATABASE_URL'):
        # Intentar cargar desde base de datos
        try:
            db = DatabaseManager()
            if db.connect():
                st.sidebar.success("🔗 Conectado a PostgreSQL")
                
                # Cargar datos principales con JOIN
                query = """
                SELECT 
                    i.*,
                    c.nombre_categoria,
                    c.margen_promedio as categoria_margen,
                    p.nombre_proveedor,
                    p.calificacion as proveedor_calificacion,
                    p.tiempo_entrega_dias,
                    u.seccion || '-' || u.pasillo || '-' || u.estante as ubicacion_codigo,
                    u.descripcion as ubicacion_descripcion
                FROM inventario i
                LEFT JOIN categorias c ON i.categoria_id = c.categoria_id
                LEFT JOIN proveedores p ON i.proveedor_id = p.proveedor_id
                LEFT JOIN ubicaciones u ON i.ubicacion_id = u.ubicacion_id
                WHERE i.activo = true
                ORDER BY i.producto_id;
                """
                
                df = db.execute_query(query)
                
                # Cargar alertas y movimientos
                try:
                    alertas = db.execute_query("SELECT * FROM alertas WHERE estado = 'ACTIVA' ORDER BY fecha_generacion DESC;")
                    movimientos = db.execute_query("SELECT * FROM movimientos_inventario ORDER BY fecha_movimiento DESC LIMIT 100;")
                except:
                    alertas = pd.DataFrame()
                    movimientos = pd.DataFrame()
                
                db.disconnect()
                
                if not df.empty:
                    return df, alertas, movimientos, True
                
        except Exception as e:
            st.sidebar.error(f"❌ Error BD: {e}")
    
    # Fallback a archivos CSV
    st.sidebar.info("📁 Cargando desde archivos CSV")
    return load_csv_data()

def load_csv_data():
    """
    Cargar datos desde archivos CSV
    
    Returns:
        tuple: (DataFrame principal, alertas, movimientos, es_db)
    """
    try:
        # Cargar datos principales
        inventario = pd.read_csv('data/inventario_expandido.csv')
        categorias = pd.read_csv('data/categorias.csv')
        proveedores = pd.read_csv('data/proveedores.csv')
        ubicaciones = pd.read_csv('data/ubicaciones.csv')
        
        # Combinar datos
        df = inventario.merge(categorias, on='categoria_id', how='left')
        df = df.merge(proveedores, on='proveedor_id', how='left')
        df = df.merge(ubicaciones, on='ubicacion_id', how='left')
        
        # Datos opcionales
        try:
            alertas = pd.read_csv('data/alertas_sample.csv')
            movimientos = pd.read_csv('data/movimientos_inventario_sample.csv')
        except:
            alertas = pd.DataFrame()
            movimientos = pd.DataFrame()
        
        return df, alertas, movimientos, False
        
    except FileNotFoundError as e:
        st.error(f"❌ Archivos de datos no encontrados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False

@st.cache_data
def process_data(df):
    """
    Procesar y enriquecer datos
    
    Args:
        df (pd.DataFrame): DataFrame base
        
    Returns:
        pd.DataFrame: DataFrame procesado
    """
    if df.empty:
        return df
    
    # Conversiones de tipos
    date_columns = ['fecha_ultima_compra', 'fecha_ultima_venta', 'fecha_creacion']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Calcular métricas adicionales
    df['utilidad_unitaria'] = df['precio_venta'] - df['costo_unitario']
    df['margen_porcentaje'] = (df['utilidad_unitaria'] / df['precio_venta'] * 100).round(2)
    df['utilidad_mes'] = df['utilidad_unitaria'] * df['ventas_mes_actual']
    df['valor_inventario'] = df['stock_actual'] * df['costo_unitario']
    
    # Rotación de inventario
    df['rotacion_mensual'] = np.where(
        df['stock_actual'] > 0, 
        df['ventas_mes_actual'] / df['stock_actual'], 
        0
    )
    df['meses_inventario'] = np.where(
        df['ventas_mes_actual'] > 0,
        df['stock_actual'] / df['ventas_mes_actual'],
        999
    )
    
    # Estado del stock
    def clasificar_stock(row):
        if row['stock_actual'] == 0:
            return '🔴 SIN STOCK'
        elif row['stock_actual'] <= row['stock_minimo']:
            return '🟠 CRÍTICO'
        elif row['stock_actual'] <= row['punto_reorden']:
            return '🟡 BAJO'
        else:
            return '🟢 NORMAL'
    
    df['estado_stock'] = df.apply(clasificar_stock, axis=1)
    
    # Crecimiento de ventas
    df['crecimiento_pct'] = np.where(
        df['ventas_mes_anterior'] > 0,
        ((df['ventas_mes_actual'] - df['ventas_mes_anterior']) / df['ventas_mes_anterior'] * 100),
        0
    )
    
    return df

# ================================
# FUNCIONES DE ANÁLISIS
# ================================

def calculate_kpis(df):
    """Calcular KPIs principales del negocio"""
    if df.empty:
        return {}
    
    total_productos = len(df)
    productos_activos = len(df[df.get('activo', True) == True])
    productos_criticos = len(df[df['estado_stock'].isin(['🔴 SIN STOCK', '🟠 CRÍTICO'])])
    
    valor_total_inventario = df['valor_inventario'].sum()
    ingresos_mes = (df['ventas_mes_actual'] * df['precio_venta']).sum()
    costos_mes = (df['ventas_mes_actual'] * df['costo_unitario']).sum()
    utilidad_mes = ingresos_mes - costos_mes
    margen_promedio = df['margen_porcentaje'].mean()
    
    # Métricas de eficiencia
    rotacion_promedio = df[df['rotacion_mensual'] > 0]['rotacion_mensual'].mean()
    productos_sin_movimiento = len(df[df['ventas_mes_actual'] == 0])
    
    return {
        'total_productos': total_productos,
        'productos_activos': productos_activos,
        'productos_criticos': productos_criticos,
        'pct_productos_criticos': (productos_criticos / total_productos * 100) if total_productos > 0 else 0,
        'valor_inventario': valor_total_inventario,
        'ingresos_mes': ingresos_mes,
        'costos_mes': costos_mes,
        'utilidad_mes': utilidad_mes,
        'margen_promedio': margen_promedio,
        'margen_neto': (utilidad_mes / ingresos_mes * 100) if ingresos_mes > 0 else 0,
        'rotacion_promedio': rotacion_promedio if not pd.isna(rotacion_promedio) else 0,
        'productos_sin_movimiento': productos_sin_movimiento
    }

def generate_insights(df, kpis):
    """
    Generar insights automáticos del negocio
    
    Args:
        df (pd.DataFrame): Datos procesados
        kpis (dict): KPIs calculados
        
    Returns:
        list: Lista de insights
    """
    insights = []
    
    # Análisis de stock crítico
    if kpis['pct_productos_criticos'] > 15:
        insights.append({
            'tipo': 'warning',
            'titulo': '⚠️ Alto Porcentaje de Productos Críticos',
            'mensaje': f'{kpis["pct_productos_criticos"]:.1f}% de productos en estado crítico. Revisar proceso de reabastecimiento.',
            'prioridad': 'alta'
        })
    
    # Análisis de rentabilidad
    if kpis['margen_neto'] < 20:
        insights.append({
            'tipo': 'warning',
            'titulo': '📉 Margen Neto Bajo',
            'mensaje': f'Margen neto actual: {kpis["margen_neto"]:.1f}%. Considerar optimización de precios o costos.',
            'prioridad': 'media'
        })
    elif kpis['margen_neto'] > 35:
        insights.append({
            'tipo': 'success',
            'titulo': '💰 Excelente Rentabilidad',
            'mensaje': f'Margen neto de {kpis["margen_neto"]:.1f}% indica operación muy rentable.',
            'prioridad': 'info'
        })
    
    # Análisis de rotación
    if kpis['rotacion_promedio'] < 0.5:
        insights.append({
            'tipo': 'warning',
            'titulo': '🔄 Baja Rotación de Inventario',
            'mensaje': 'Rotación promedio baja indica posible sobrestock. Considerar estrategias de liquidación.',
            'prioridad': 'media'
        })
    
    # Productos sin movimiento
    if kpis['productos_sin_movimiento'] > kpis['total_productos'] * 0.2:
        insights.append({
            'tipo': 'info',
            'titulo': '📦 Productos Sin Movimiento',
            'mensaje': f'{kpis["productos_sin_movimiento"]} productos sin ventas este mes. Revisar estrategia comercial.',
            'prioridad': 'baja'
        })
    
    # Oportunidades de crecimiento
    if not df.empty:
        top_growth = df[df['crecimiento_pct'] > 50]
        if len(top_growth) > 0:
            insights.append({
                'tipo': 'success',
                'titulo': '🚀 Productos con Alto Crecimiento',
                'mensaje': f'{len(top_growth)} productos con crecimiento >50%. Oportunidad de incrementar stock.',
                'prioridad': 'info'
            })
    
    return insights

# ================================
# COMPONENTES DE UI
# ================================

def render_header():
    """Renderizar header principal"""
    st.markdown("""
    <div class="main-header">
        <h1>🔧 Ferretería Petapa - Dashboard BI</h1>
        <h3>Sistema Inteligente de Control de Inventarios y Business Intelligence</h3>
    </div>
    """, unsafe_allow_html=True)

def render_kpi_cards(kpis):
    """Renderizar tarjetas de KPIs principales"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_productos = f"+{kpis['productos_activos']} activos" if kpis.get('productos_activos') else None
        st.metric(
            label="📦 Total Productos",
            value=f"{kpis.get('total_productos', 0):,}",
            delta=delta_productos
        )
    
    with col2:
        st.metric(
            label="💰 Valor Inventario",
            value=f"Q{kpis.get('valor_inventario', 0):,.2f}",
            delta="Capital invertido"
        )
    
    with col3:
        utilidad = kpis.get('utilidad_mes', 0)
        margen = kpis.get('margen_neto', 0)
        delta_utilidad = f"{margen:.1f}% margen" if margen else None
        st.metric(
            label="📊 Utilidad Mes",
            value=f"Q{utilidad:,.2f}",
            delta=delta_utilidad,
            delta_color="normal" if margen >= 20 else "inverse"
        )
    
    with col4:
        criticos = kpis.get('productos_criticos', 0)
        pct_criticos = kpis.get('pct_productos_criticos', 0)
        delta_criticos = f"{pct_criticos:.1f}% del total"
        st.metric(
            label="⚠️ Productos Críticos",
            value=criticos,
            delta=delta_criticos,
            delta_color="inverse" if pct_criticos > 10 else "normal"
        )

def render_insights(insights):
    """Renderizar insights automáticos"""
    if not insights:
        return
    
    st.subheader("🧠 Insights Automáticos del Negocio")
    
    for insight in insights:
        if insight['tipo'] == 'warning':
            st.warning(f"**{insight['titulo']}**\n\n{insight['mensaje']}")
        elif insight['tipo'] == 'success':
            st.success(f"**{insight['titulo']}**\n\n{insight['mensaje']}")
        else:
            st.info(f"**{insight['titulo']}**\n\n{insight['mensaje']}")

def render_sidebar_info(df, es_db):
    """Renderizar información en sidebar"""
    st.sidebar.markdown("---")
    
    # Estado de conexión
    if es_db:
        st.sidebar.success("🗄️ Datos desde PostgreSQL")
    else:
        st.sidebar.info("📁 Datos desde archivos CSV")
    
    # Estadísticas rápidas
    st.sidebar.markdown("### 📊 Estadísticas Rápidas")
    
    if not df.empty:
        total_valor = df['valor_inventario'].sum()
        productos_activos = len(df[df.get('activo', True) == True])
        
        st.sidebar.metric("💰 Valor Total", f"Q{total_valor:,.2f}")
        st.sidebar.metric("📦 Productos Activos", productos_activos)
        
        # Distribución por estado
        estado_counts = df['estado_stock'].value_counts()
        st.sidebar.markdown("**Estado del Stock:**")
        for estado, count in estado_counts.items():
            st.sidebar.write(f"{estado}: {count}")
    
    # Información del desarrollador
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👨‍💻 Desarrollador")
    st.sidebar.info("""
    **José Fernando Hurtarte**
    
    📧 jhurtarte1@gmail.com
    
    💼 Estudiante de Ingeniería en Sistemas - USAC
    
    🚀 Especialista en:
    - Business Intelligence
    - Desarrollo Full Stack
    - Análisis de Datos
    - Machine Learning
    """)
    
    # Footer con timestamp
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
    <div style='text-align: center; color: #6b7280; font-size: 0.8rem;'>
        <p>🚀 Powered by Streamlit & Plotly</p>
        <p>📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <p>⭐ bd-reporting-demo v2.0</p>
    </div>
    """, unsafe_allow_html=True)

# ================================
# FUNCIÓN PRINCIPAL
# ================================

def main():
    """Función principal de la aplicación"""
    
    # Renderizar header
    render_header()
    
    # Cargar datos
    with st.spinner("🔄 Cargando datos..."):
        df, alertas, movimientos, es_db = load_data_source()
    
    if df.empty:
        st.error("❌ No se pudieron cargar los datos. Verifique la configuración.")
        st.info("📋 **Pasos para solucionar:**\n1. Verificar archivos CSV en carpeta 'data/'\n2. Configurar variables de entorno para PostgreSQL\n3. Ejecutar `python database_config.py --setup`")
        return
    
    # Procesar datos
    df = process_data(df)
    
    # Configurar sidebar
    st.sidebar.header("🎛️ Configuración del Dashboard")
    
    # Filtros
    categorias_disponibles = ['Todas'] + sorted(df['nombre_categoria'].dropna().unique().tolist())
    categoria_filtro = st.sidebar.selectbox("📂 Filtrar por Categoría", categorias_disponibles)
    
    proveedores_disponibles = ['Todos'] + sorted(df['nombre_proveedor'].dropna().unique().tolist())
    proveedor_filtro = st.sidebar.selectbox("🏢 Filtrar por Proveedor", proveedores_disponibles)
    
    # Aplicar filtros
    df_filtered = df.copy()
    if categoria_filtro != 'Todas':
        df_filtered = df_filtered[df_filtered['nombre_categoria'] == categoria_filtro]
    if proveedor_filtro != 'Todos':
        df_filtered = df_filtered[df_filtered['nombre_proveedor'] == proveedor_filtro]
    
    # Calcular KPIs
    kpis = calculate_kpis(df_filtered)
    
    # Renderizar KPIs principales
    render_kpi_cards(kpis)
    
    st.markdown("---")
    
    # Generar y mostrar insights
    insights = generate_insights(df_filtered, kpis)
    if insights:
        render_insights(insights)
        st.markdown("---")
    
    # Pestañas principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Dashboard Principal", 
        "⚠️ Alertas y Control", 
        "🤖 ML y Predicciones",
        "💰 Análisis Financiero",
        "📋 Reportes y Datos"
    ])
    
    # TAB 1: Dashboard Principal
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top 10 Productos por Ventas")
            if not df_filtered.empty:
                top_ventas = df_filtered.nlargest(10, 'ventas_mes_actual')
                
                fig_top = px.bar(
                    top_ventas, 
                    x='ventas_mes_actual', 
                    y='nombre',
                    orientation='h',
                    color='margen_porcentaje',
                    color_continuous_scale='RdYlGn',
                    title="Unidades vendidas este mes",
                    labels={'ventas_mes_actual': 'Ventas', 'nombre': 'Producto'}
                )
                fig_top.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            st.subheader("📊 Estado del Inventario")
            if not df_filtered.empty:
                stock_dist = df_filtered['estado_stock'].value_counts()
                
                colors = {
                    '🟢 NORMAL': '#22c55e',
                    '🟡 BAJO': '#eab308', 
                    '🟠 CRÍTICO': '#f97316',
                    '🔴 SIN STOCK': '#ef4444'
                }
                
                fig_pie = px.pie(
                    values=stock_dist.values,
                    names=stock_dist.index,
                    color=stock_dist.index,
                    color_discrete_map=colors,
                    title="Distribución por estado"
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
        
        # Análisis por categoría
        st.subheader("📂 Performance por Categoría")
        if not df_filtered.empty:
            categoria_analysis = df_filtered.groupby('nombre_categoria').agg({
                'ventas_mes_actual': 'sum',
                'utilidad_mes': 'sum',
                'valor_inventario': 'sum',
                'producto_id': 'count',
                'margen_porcentaje': 'mean'
            }).round(2)
            
            categoria_analysis.columns = ['Ventas (Un)', 'Utilidad (Q)', 'Valor Inv (Q)', 'Productos', 'Margen %']
            categoria_analysis = categoria_analysis.sort_values('Utilidad (Q)', ascending=False)
            
            st.dataframe(categoria_analysis, use_container_width=True)
    
    # TAB 2: Alertas y Control
    with tab2:
        st.subheader("🚨 Control y Alertas del Sistema")
        
        # Productos críticos
        productos_criticos = df_filtered[df_filtered['estado_stock'].isin(['🔴 SIN STOCK', '🟠 CRÍTICO'])]
        
        if not productos_criticos.empty:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown("#### 📋 Productos que Requieren Atención")
                
                alertas_display = productos_criticos[[
                    'nombre', 'nombre_categoria', 'stock_actual', 'stock_minimo', 
                    'ventas_mes_actual', 'nombre_proveedor', 'estado_stock'
                ]].sort_values('stock_actual')
                
                st.dataframe(alertas_display, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### 📊 Resumen Crítico")
                
                sin_stock = len(productos_criticos[productos_criticos['estado_stock'] == '🔴 SIN STOCK'])
                criticos = len(productos_criticos[productos_criticos['estado_stock'] == '🟠 CRÍTICO'])
                valor_critico = productos_criticos['valor_inventario'].sum()
                
                st.metric("🔴 Sin Stock", sin_stock)
                st.metric("🟠 Stock Crítico", criticos)
                st.metric("💰 Valor en Riesgo", f"Q{valor_critico:,.2f}")
        else:
            st.success("🎉 ¡Excelente! No hay productos en estado crítico.")
        
        # Alertas de base de datos
        if not alertas.empty:
            st.markdown("---")
            st.subheader("🔔 Alertas del
