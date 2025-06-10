import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ================================
# CONFIGURACIÓN INICIAL
# ================================

st.set_page_config(
    page_title="📊 Ferretería Petapa - Dashboard BI",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 50%, #60a5fa 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header h3 {
        color: #e0e7ff;
        margin: 0;
        font-weight: 300;
    }
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
    }
    .alert-critical { border-left-color: #ef4444; }
    .alert-high { border-left-color: #f97316; }
    .alert-medium { border-left-color: #eab308; }
    .alert-low { border-left-color: #22c55e; }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    }
</style>
""", unsafe_allow_html=True)

# ================================
# FUNCIONES DE CARGA DE DATOS
# ================================

@st.cache_data
def load_data():
    """Carga todos los datasets necesarios"""
    try:
        # Cargar datos principales
        inventario = pd.read_csv('data/inventario_expandido.csv')
        categorias = pd.read_csv('data/categorias.csv')
        proveedores = pd.read_csv('data/proveedores.csv')
        ubicaciones = pd.read_csv('data/ubicaciones.csv')
        
        # Datos opcionales
        try:
            alertas = pd.read_csv('data/alertas_sample.csv')
            movimientos = pd.read_csv('data/movimientos_inventario_sample.csv')
        except:
            alertas = pd.DataFrame()
            movimientos = pd.DataFrame()
        
        # Combinar datos
        df = inventario.merge(categorias, on='categoria_id', how='left')
        df = df.merge(proveedores, on='proveedor_id', how='left')
        df = df.merge(ubicaciones, on='ubicacion_id', how='left')
        
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
        df['rotacion_mensual'] = np.where(df['stock_actual'] > 0, 
                                        df['ventas_mes_actual'] / df['stock_actual'], 
                                        0)
        
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
        
        return df, alertas, movimientos
        
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ================================
# FUNCIONES DE ANÁLISIS
# ================================

def calculate_kpis(df):
    """Calcula KPIs principales"""
    total_productos = len(df)
    productos_activos = len(df[df['activo'] == True])
    productos_criticos = len(df[df['estado_stock'].isin(['🔴 SIN STOCK', '🟠 CRÍTICO'])])
    
    valor_total_inventario = df['valor_inventario'].sum()
    ingresos_mes = (df['ventas_mes_actual'] * df['precio_venta']).sum()
    utilidad_mes = df['utilidad_mes'].sum()
    margen_promedio = df['margen_porcentaje'].mean()
    
    return {
        'total_productos': total_productos,
        'productos_activos': productos_activos,
        'productos_criticos': productos_criticos,
        'valor_inventario': valor_total_inventario,
        'ingresos_mes': ingresos_mes,
        'utilidad_mes': utilidad_mes,
        'margen_promedio': margen_promedio,
        'pct_productos_criticos': (productos_criticos / total_productos * 100) if total_productos > 0 else 0
    }

def predict_demand(df):
    """Predicción simple de demanda basada en tendencia"""
    df_pred = df.copy()
    
    # Calcular crecimiento mensual
    df_pred['crecimiento_pct'] = np.where(
        df_pred['ventas_mes_anterior'] > 0,
        ((df_pred['ventas_mes_actual'] - df_pred['ventas_mes_anterior']) / df_pred['ventas_mes_anterior'] * 100),
        0
    )
    
    # Proyección próximo mes
    df_pred['proyeccion_siguiente_mes'] = np.where(
        df_pred['ventas_mes_anterior'] > 0,
        df_pred['ventas_mes_actual'] * (1 + df_pred['crecimiento_pct'] / 100),
        df_pred['ventas_mes_actual']
    ).round(0).astype(int)
    
    # Evaluación de riesgo
    def evaluar_riesgo(row):
        if row['stock_actual'] < row['proyeccion_siguiente_mes']:
            return '⚠️ RIESGO DESABASTO'
        elif row['stock_actual'] < row['proyeccion_siguiente_mes'] * 1.5:
            return '🟡 STOCK AJUSTADO'
        else:
            return '🟢 STOCK SUFICIENTE'
    
    df_pred['riesgo_futuro'] = df_pred.apply(evaluar_riesgo, axis=1)
    df_pred['compra_sugerida'] = np.maximum(0, df_pred['proyeccion_siguiente_mes'] - df_pred['stock_actual'])
    
    return df_pred

# ================================
# INTERFAZ PRINCIPAL
# ================================

def main():
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🔧 Ferretería Petapa - Dashboard BI</h1>
        <h3>Sistema Inteligente de Control de Inventarios</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Cargar datos
    df, alertas, movimientos = load_data()
    
    if df.empty:
        st.error("❌ No se pudieron cargar los datos. Verifique que los archivos CSV estén en la carpeta 'data/'")
        return
    
    # Sidebar para filtros
    st.sidebar.header("🎛️ Filtros y Configuración")
    
    # Filtros
    categorias_disponibles = ['Todas'] + sorted(df['nombre_categoria'].dropna().unique().tolist())
    categoria_filtro = st.sidebar.selectbox("📂 Categoría", categorias_disponibles)
    
    proveedores_disponibles = ['Todos'] + sorted(df['nombre_proveedor'].dropna().unique().tolist())
    proveedor_filtro = st.sidebar.selectbox("🏢 Proveedor", proveedores_disponibles)
    
    estado_stock_filtro = st.sidebar.multiselect(
        "📊 Estado del Stock",
        ['🟢 NORMAL', '🟡 BAJO', '🟠 CRÍTICO', '🔴 SIN STOCK'],
        default=['🟢 NORMAL', '🟡 BAJO', '🟠 CRÍTICO', '🔴 SIN STOCK']
    )
    
    # Aplicar filtros
    df_filtered = df.copy()
    if categoria_filtro != 'Todas':
        df_filtered = df_filtered[df_filtered['nombre_categoria'] == categoria_filtro]
    if proveedor_filtro != 'Todos':
        df_filtered = df_filtered[df_filtered['nombre_proveedor'] == proveedor_filtro]
    if estado_stock_filtro:
        df_filtered = df_filtered[df_filtered['estado_stock'].isin(estado_stock_filtro)]
    
    # Pestañas principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Dashboard Principal", 
        "⚠️ Alertas y Stock Crítico", 
        "🎯 Análisis Predictivo",
        "💰 Análisis Financiero",
        "📋 Reportes Detallados"
    ])
    
    # ================================
    # TAB 1: DASHBOARD PRINCIPAL
    # ================================
    with tab1:
        # KPIs principales
        kpis = calculate_kpis(df_filtered)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📦 Total Productos",
                value=f"{kpis['total_productos']:,}",
                delta=f"{kpis['productos_activos']} activos"
            )
        
        with col2:
            st.metric(
                label="💰 Valor Inventario",
                value=f"Q{kpis['valor_inventario']:,.2f}",
                delta="Total invertido"
            )
        
        with col3:
            st.metric(
                label="📊 Ingresos Mes",
                value=f"Q{kpis['ingresos_mes']:,.2f}",
                delta=f"Utilidad: Q{kpis['utilidad_mes']:,.2f}"
            )
        
        with col4:
            st.metric(
                label="⚠️ Productos Críticos",
                value=kpis['productos_criticos'],
                delta=f"{kpis['pct_productos_criticos']:.1f}% del total",
                delta_color="inverse"
            )
        
        st.markdown("---")
        
        # Gráficos principales
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top 10 Productos por Ventas")
            top_ventas = df_filtered.nlargest(10, 'ventas_mes_actual')
            
            fig_top = px.bar(
                top_ventas, 
                x='ventas_mes_actual', 
                y='nombre',
                orientation='h',
                color='margen_porcentaje',
                color_continuous_scale='RdYlGn',
                title="Unidades vendidas este mes"
            )
            fig_top.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            st.subheader("📊 Distribución por Estado de Stock")
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
                title="Estado actual del inventario"
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Análisis por categoría
        st.subheader("📂 Análisis por Categoría")
        
        categoria_analysis = df_filtered.groupby('nombre_categoria').agg({
            'ventas_mes_actual': 'sum',
            'utilidad_mes': 'sum',
            'valor_inventario': 'sum',
            'producto_id': 'count'
        }).round(2)
        categoria_analysis.columns = ['Ventas (Unidades)', 'Utilidad (Q)', 'Valor Inventario (Q)', 'Productos']
        categoria_analysis = categoria_analysis.sort_values('Utilidad (Q)', ascending=False)
        
        st.dataframe(categoria_analysis, use_container_width=True)
    
    # ================================
    # TAB 2: ALERTAS Y STOCK CRÍTICO
    # ================================
    with tab2:
        st.subheader("🚨 Productos que Requieren Atención Inmediata")
        
        # Productos críticos
        productos_criticos = df_filtered[df_filtered['estado_stock'].isin(['🔴 SIN STOCK', '🟠 CRÍTICO'])]
        
        if not productos_criticos.empty:
            # Mostrar alertas por prioridad
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### 📋 Lista de Productos Críticos")
                
                alertas_display = productos_criticos[[
                    'nombre', 'nombre_categoria', 'stock_actual', 'stock_minimo', 
                    'ventas_mes_actual', 'nombre_proveedor', 'estado_stock'
                ]].copy()
                
                alertas_display['Días de inventario'] = np.where(
                    alertas_display['ventas_mes_actual'] > 0,
                    (alertas_display['stock_actual'] / alertas_display['ventas_mes_actual'] * 30).round(1),
                    'Sin ventas'
                )
                
                alertas_display = alertas_display.sort_values('stock_actual')
                
                # Aplicar estilos
                def highlight_critical(row):
                    if row['estado_stock'] == '🔴 SIN STOCK':
                        return ['background-color: #fee2e2'] * len(row)
                    elif row['estado_stock'] == '🟠 CRÍTICO':
                        return ['background-color: #fed7aa'] * len(row)
                    else:
                        return [''] * len(row)
                
                st.dataframe(
                    alertas_display.style.apply(highlight_critical, axis=1),
                    use_container_width=True,
                    hide_index=True
                )
            
            with col2:
                st.markdown("### 📊 Resumen de Alertas")
                
                # Contadores de alertas
                sin_stock = len(productos_criticos[productos_criticos['estado_stock'] == '🔴 SIN STOCK'])
                criticos = len(productos_criticos[productos_criticos['estado_stock'] == '🟠 CRÍTICO'])
                
                st.markdown(f"""
                <div class="metric-container alert-critical">
                    <h3>🔴 Sin Stock</h3>
                    <h2>{sin_stock}</h2>
                    <p>Productos agotados</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-container alert-high">
                    <h3>🟠 Stock Crítico</h3>
                    <h2>{criticos}</h2>
                    <p>Requieren reorden urgente</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Valor inmovilizado
                valor_critico = productos_criticos['valor_inventario'].sum()
                st.markdown(f"""
                <div class="metric-container alert-medium">
                    <h3>💰 Valor en Riesgo</h3>
                    <h2>Q{valor_critico:,.2f}</h2>
                    <p>Capital en productos críticos</p>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            st.success("🎉 ¡Excelente! No hay productos en estado crítico.")
        
        # Recomendaciones de compra
        st.markdown("---")
        st.subheader("🛒 Recomendaciones de Compra")
        
        if not productos_criticos.empty:
            compras_recomendadas = productos_criticos.copy()
            compras_recomendadas['Cantidad Sugerida'] = compras_recomendadas['punto_reorden'] - compras_recomendadas['stock_actual']
            compras_recomendadas['Inversión Requerida'] = compras_recomendadas['Cantidad Sugerida'] * compras_recomendadas['costo_unitario']
            
            compras_display = compras_recomendadas[[
                'nombre', 'nombre_proveedor', 'Cantidad Sugerida', 'costo_unitario', 'Inversión Requerida'
            ]].sort_values('Inversión Requerida', ascending=False)
            
            st.dataframe(compras_display, use_container_width=True, hide_index=True)
            
            total_inversion = compras_display['Inversión Requerida'].sum()
            st.info(f"💡 **Inversión total requerida para normalizar stock:** Q{total_inversion:,.2f}")
    
    # ================================
    # TAB 3: ANÁLISIS PREDICTIVO
    # ================================
    with tab3:
        st.subheader("🔮 Predicciones de Demanda y Stock")
        
        # Generar predicciones
        df_pred = predict_demand(df_filtered)
        
        # Métricas de predicción
        col1, col2, col3 = st.columns(3)
        
        with col1:
            riesgo_desabasto = len(df_pred[df_pred['riesgo_futuro'] == '⚠️ RIESGO DESABASTO'])
            st.metric("⚠️ Riesgo Desabasto", riesgo_desabasto, "productos próximo mes")
        
        with col2:
            crecimiento_promedio = df_pred['crecimiento_pct'].mean()
            st.metric("📈 Crecimiento Promedio", f"{crecimiento_promedio:.1f}%", "vs mes anterior")
        
        with col3:
            total_compra_sugerida = df_pred['compra_sugerida'].sum()
            st.metric("🛒 Compra Sugerida", f"{total_compra_sugerida:,.0f}", "unidades totales")
        
        # Tabla de predicciones
        st.markdown("### 📊 Análisis Predictivo por Producto")
        
        pred_display = df_pred[df_pred['ventas_mes_actual'] > 0][[
            'nombre', 'ventas_mes_actual', 'ventas_mes_anterior', 'crecimiento_pct',
            'proyeccion_siguiente_mes', 'stock_actual', 'riesgo_futuro', 'compra_sugerida'
        ]].sort_values('crecimiento_pct', ascending=False)
        
        # Filtrar solo productos con proyecciones interesantes
        pred_display = pred_display[
            (pred_display['compra_sugerida'] > 0) | 
            (abs(pred_display['crecimiento_pct']) > 10)
        ]
        
        if not pred_display.empty:
            st.dataframe(pred_display, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No se detectaron patrones significativos de crecimiento o riesgo en los productos filtrados.")
        
        # Gráfico de tendencias
        st.markdown("### 📈 Tendencias de Ventas por Categoría")
        
        tendencias_cat = df_pred.groupby('nombre_categoria').agg({
            'ventas_mes_actual': 'sum',
            'ventas_mes_anterior': 'sum',
            'crecimiento_pct': 'mean'
        }).reset_index()
        
        fig_tendencias = px.scatter(
            tendencias_cat,
            x='ventas_mes_anterior',
            y='ventas_mes_actual',
            size='crecimiento_pct',
            color='crecimiento_pct',
            hover_name='nombre_categoria',
            color_continuous_scale='RdYlGn',
            title="Evolución de ventas por categoría (tamaño = % crecimiento)"
        )
        fig_tendencias.add_line(x=[0, tendencias_cat['ventas_mes_anterior'].max()], 
                              y=[0, tendencias_cat['ventas_mes_anterior'].max()], 
                              name="Sin cambio")
        st.plotly_chart(fig_tendencias, use_container_width=True)
    
    # ================================
    # TAB 4: ANÁLISIS FINANCIERO
    # ================================
    with tab4:
        st.subheader("💰 Análisis de Rentabilidad y Performance Financiero")
        
        # KPIs financieros
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ingresos_totales = (df_filtered['ventas_mes_actual'] * df_filtered['precio_venta']).sum()
            st.metric("💵 Ingresos Mes", f"Q{ingresos_totales:,.2f}")
        
        with col2:
            costos_totales = (df_filtered['ventas_mes_actual'] * df_filtered['costo_unitario']).sum()
            st.metric("💸 Costos Mes", f"Q{costos_totales:,.2f}")
        
        with col3:
            utilidad_neta = ingresos_totales - costos_totales
            st.metric("💰 Utilidad Neta", f"Q{utilidad_neta:,.2f}")
        
        with col4:
            margen_neto = (utilidad_neta / ingresos_totales * 100) if ingresos_totales > 0 else 0
            st.metric("📊 Margen Neto", f"{margen_neto:.1f}%")
        
        # Análisis ABC
        st.markdown("### 🎯 Análisis ABC de Productos")
        
        df_abc = df_filtered[df_filtered['ventas_mes_actual'] > 0].copy()
        df_abc['ingresos_producto'] = df_abc['ventas_mes_actual'] * df_abc['precio_venta']
        df_abc = df_abc.sort_values('ingresos_producto', ascending=False)
        df_abc['ingresos_acumulados'] = df_abc['ingresos_producto'].cumsum()
        df_abc['porcentaje_acumulado'] = df_abc['ingresos_acumulados'] / df_abc['ingresos_producto'].sum() * 100
        
        # Clasificación ABC
        def clasificar_abc(pct):
            if pct <= 80:
                return 'A - Vital (80% ingresos)'
            elif pct <= 95:
                return 'B - Importante (15% ingresos)'
            else:
                return 'C - Normal (5% ingresos)'
        
        df_abc['clasificacion_abc'] = df_abc['porcentaje_acumulado'].apply(clasificar_abc)
        
        # Mostrar distribución ABC
        abc_counts = df_abc['clasificacion_abc'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_abc = px.pie(
                values=abc_counts.values,
                names=abc_counts.index,
                title="Distribución ABC de Productos",
                color_discrete_sequence=['#ef4444', '#f97316', '#22c55e']
            )
            st.plotly_chart(fig_abc, use_container_width=True)
        
        with col2:
            # Top productos clase A
            productos_a = df_abc[df_abc['clasificacion_abc'] == 'A - Vital (80% ingresos)'].head(10)
            st.markdown("**🏆 Top 10 Productos Clase A**")
            
            productos_display = productos_a[['nombre', 'ingresos_producto', 'margen_porcentaje']].copy()
            productos_display['ingresos_producto'] = productos_display['ingresos_producto'].round(2)
            st.dataframe(productos_display, hide_index=True, use_container_width=True)
        
        # Análisis de rentabilidad por proveedor
        st.markdown("### 🏢 Performance por Proveedor")
        
        proveedor_analysis = df_filtered.groupby('nombre_proveedor').agg({
            'ventas_mes_actual': 'sum',
            'utilidad_mes': 'sum',
            'valor_inventario': 'sum',
            'margen_porcentaje': 'mean',
            'producto_id': 'count'
        }).round(2)
        
        proveedor_analysis.columns = ['Ventas (Un.)', 'Utilidad (Q)', 'Valor Inv. (Q)', 'Margen %', 'Productos']
        proveedor_analysis = proveedor_analysis.sort_values('Utilidad (Q)', ascending=False)
        
        st.dataframe(proveedor_analysis, use_container_width=True)
    
    # ================================
    # TAB 5: REPORTES DETALLADOS
    # ================================
    with tab5:
        st.subheader("📋 Reportes Detallados del Inventario")
        
        # Selector de tipo de reporte
        tipo_reporte = st.selectbox(
            "📊 Seleccionar Tipo de Reporte",
            [
                "Inventario Completo",
                "Productos Más Vendidos",
                "Análisis de Rotación",
                "Productos Sin Movimiento",
                "Reporte de Márgenes"
            ]
        )
        
        if tipo_reporte == "Inventario Completo":
            st.markdown("### 📦 Inventario Completo")
            
            inventario_completo = df_filtered[[
                'nombre', 'nombre_categoria', 'stock_actual', 'stock_minimo', 
                'precio_venta', 'costo_unitario', 'margen_porcentaje',
                'ventas_mes_actual', 'valor_inventario', 'estado_stock',
                'nombre_proveedor'
            ]].sort_values('valor_inventario', ascending=False)
            
            st.dataframe(inventario_completo, use_container_width=True, hide_index=True)
        
        elif tipo_reporte == "Productos Más Vendidos":
            st.markdown("### 🏆 Top Productos por Ventas")
            
            top_products = df_filtered.nlargest(20, 'ventas_mes_actual')[[
                'nombre', 'ventas_mes_actual', 'ventas_mes_anterior',
                'utilidad_mes', 'stock_actual', 'rotacion_mensual'
            ]]
            
            st.dataframe(top_products, use_container_width=True, hide_index=True)
        
        elif tipo_reporte == "Análisis de Rotación":
            st.markdown("### 🔄 Análisis de Rotación de Inventario")
            
            rotacion_analysis = df_filtered[df_filtered['ventas_mes_actual'] > 0].copy()
            rotacion_analysis['meses_inventario'] = np.where(
                rotacion_analysis['ventas_mes_actual'] > 0,
                rotacion_analysis['stock_actual'] / rotacion_analysis['ventas_mes_actual'],
                999
            )
            
            # Clasificar rotación
            def clasificar_rotacion(meses):
                if meses < 1:
                    return '🟢 Excelente (<1 mes)'
                elif meses < 2:
                    return '🟡 Buena (1-2 meses)'
                elif meses < 3:
                    return '🟠 Regular (2-3 meses)'
                else:
                    return '🔴 Lenta (>3 meses)'
            
            rotacion_analysis['clasificacion_rotacion'] = rotacion_analysis['meses_inventario'].apply(clasificar_rotacion)
            
            rotacion_display = rotacion_analysis[[
                'nombre', 'ventas_mes_actual', 'stock_actual', 'meses_inventario',
                'clasificacion_rotacion', 'valor_inventario'
            ]].sort_values('meses_inventario', ascending=False)
            
            st.dataframe(rotacion_display, use_container_width=True, hide_index=True)
        
        elif tipo_reporte == "Productos Sin Movimiento":
            st.markdown("### 📉 Productos con Poco o Sin Movimiento")
            
            sin_movimiento = df_filtered[
                (df_filtered['ventas_mes_actual'] <= 2) | 
                (df_filtered['ventas_mes_actual'] == 0)
            ].copy()
            
            sin_movimiento['valor_inmovilizado'] = sin_movimiento['stock_actual'] * sin_movimiento['costo_unitario']
            
            if not sin_movimiento.empty:
                sin_mov_display = sin_movimiento[[
                    'nombre', 'nombre_categoria', 'stock_actual', 'ventas_mes_actual',
                    'ventas_trimestre', 'valor_inmovilizado', 'fecha_ultima_venta'
                ]].sort_values('valor_inmovilizado', ascending=False)
                
                st.dataframe(sin_mov_display, use_container_width=True, hide_index=True)
                
                total_inmovilizado = sin_movimiento['valor_inmovilizado'].sum()
                st.warning(f"💰 **Capital inmovilizado total:** Q{total_inmovilizado:,.2f}")
            else:
                st.success("🎉 ¡Todos los productos tienen movimiento activo!")
        
        elif tipo_reporte == "Reporte de Márgenes":
            st.markdown("### 💹 Análisis de Márgenes de Utilidad")
            
            margenes_analysis = df_filtered.copy()
            margenes_analysis = margenes_analysis.sort_values('margen_porcentaje', ascending=False)
            
            margenes_display = margenes_analysis[[
                'nombre', 'costo_unitario', 'precio_venta', 'utilidad_unitaria',
                'margen_porcentaje', 'ventas_mes_actual', 'utilidad_mes'
            ]]
            
            st.dataframe(margenes_display, use_container_width=True, hide_index=True)
            
            # Estadísticas de márgenes
            col1, col2, col3 = st.columns(3)
            
            with col1:
                margen_promedio = margenes_analysis['margen_porcentaje'].mean()
                st.metric("📊 Margen Promedio", f"{margen_promedio:.1f}%")
            
            with col2:
                margen_maximo = margenes_analysis['margen_porcentaje'].max()
                st.metric("📈 Margen Máximo", f"{margen_maximo:.1f}%")
            
            with col3:
                margen_minimo = margenes_analysis['margen_porcentaje'].min()
                st.metric("📉 Margen Mínimo", f"{margen_minimo:.1f}%")
        
        # Botones de descarga
        st.markdown("---")
        st.markdown("### 📥 Descargar Reportes")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Preparar datos para descarga
            if st.button("📊 Descargar Inventario Completo"):
                csv_data = df_filtered.to_csv(index=False)
                st.download_button(
                    label="💾 Descargar CSV",
                    data=csv_data,
                    file_name=f"inventario_completo_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("⚠️ Descargar Productos Críticos"):
                productos_criticos_download = df_filtered[df_filtered['estado_stock'].isin(['🔴 SIN STOCK', '🟠 CRÍTICO'])]
                if not productos_criticos_download.empty:
                    csv_criticos = productos_criticos_download.to_csv(index=False)
                    st.download_button(
                        label="💾 Descargar CSV",
                        data=csv_criticos,
                        file_name=f"productos_criticos_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No hay productos críticos para descargar")
        
        with col3:
            if st.button("📈 Descargar Análisis ABC"):
                if 'df_abc' in locals():
                    csv_abc = df_abc.to_csv(index=False)
                    st.download_button(
                        label="💾 Descargar CSV",
                        data=csv_abc,
                        file_name=f"analisis_abc_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
    
    # ================================
    # SIDEBAR: INFORMACIÓN ADICIONAL
    # ================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Estadísticas Rápidas")
    
    # Stats del dataset filtrado
    total_valor = df_filtered['valor_inventario'].sum()
    productos_activos = len(df_filtered[df_filtered['activo'] == True])
    
    st.sidebar.metric("💰 Valor Total Filtrado", f"Q{total_valor:,.2f}")
    st.sidebar.metric("📦 Productos Filtrados", productos_activos)
    
    # Distribución por estado
    estado_counts = df_filtered['estado_stock'].value_counts()
    st.sidebar.markdown("**📊 Estado del Stock:**")
    for estado, count in estado_counts.items():
        st.sidebar.write(f"{estado}: {count}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Información del Sistema")
    st.sidebar.info("""
    **🔧 Ferretería Petapa - Dashboard BI**
    
    ✅ **Funcionalidades:**
    - Control de inventarios en tiempo real
    - Alertas automáticas de stock crítico
    - Análisis predictivo de demanda
    - Reportes financieros detallados
    - Análisis ABC de productos
    
    📊 **Métricas Clave:**
    - KPIs de inventario y ventas
    - Análisis de rentabilidad
    - Rotación de productos
    - Proyecciones de stock
    
    🎯 **Desarrollado por:** José Fernando Hurtarte
    
    📧 **Contacto:** jhurtarte1@gmail.com
    """)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; color: #6b7280; font-size: 0.8rem;'>
        <p>🚀 Powered by Streamlit & Plotly</p>
        <p>📅 Actualizado: {}</p>
    </div>
    """.format(datetime.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
