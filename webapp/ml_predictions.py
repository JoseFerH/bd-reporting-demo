"""
ML_PREDICTIONS.PY
=================
Módulo de Machine Learning para predicciones avanzadas
Sistema de Business Intelligence - Ferretería Petapa

Funcionalidades:
- Predicción de demanda con algoritmos ML
- Detección de anomalías en ventas
- Análisis de estacionalidad
- Recomendaciones automáticas de compra
- Clustering de productos
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

class InventoryMLAnalyzer:
    """
    Clase principal para análisis de Machine Learning del inventario
    """
    
    def __init__(self, data):
        """
        Inicializar el analizador ML
        
        Args:
            data (pd.DataFrame): DataFrame con datos del inventario
        """
        self.data = data.copy()
        self.scaler = StandardScaler()
        self.demand_model = None
        self.anomaly_model = None
        self.cluster_model = None
        
    def prepare_features(self):
        """
        Preparar características para modelos ML
        
        Returns:
            pd.DataFrame: DataFrame con características preparadas
        """
        df = self.data.copy()
        
        # Calcular características adicionales
        df['precio_ratio'] = df['precio_venta'] / df['costo_unitario']
        df['margen_absoluto'] = df['precio_venta'] - df['costo_unitario']
        df['rotacion_anual'] = np.where(
            df['stock_actual'] > 0,
            12 * df['ventas_mes_actual'] / df['stock_actual'],
            0
        )
        
        # Tendencia de ventas
        df['tendencia_ventas'] = np.where(
            df['ventas_mes_anterior'] > 0,
            (df['ventas_mes_actual'] - df['ventas_mes_anterior']) / df['ventas_mes_anterior'],
            0
        )
        
        # Ratio stock/ventas
        df['ratio_stock_ventas'] = np.where(
            df['ventas_mes_actual'] > 0,
            df['stock_actual'] / df['ventas_mes_actual'],
            999  # Valor alto para productos sin ventas
        )
        
        # Variables categóricas numéricas
        df['categoria_encoded'] = pd.Categorical(df['categoria_id']).codes
        df['proveedor_encoded'] = pd.Categorical(df['proveedor_id']).codes
        
        # Características temporales (simuladas)
        df['dias_desde_ultima_venta'] = np.random.randint(1, 90, len(df))
        df['estacionalidad'] = np.sin(2 * np.pi * pd.to_datetime('today').month / 12)
        
        return df
    
    def predict_demand(self, horizon_days=30):
        """
        Predecir demanda futura usando Random Forest
        
        Args:
            horizon_days (int): Días hacia el futuro para predecir
            
        Returns:
            pd.DataFrame: Predicciones de demanda
        """
        df = self.prepare_features()
        
        # Seleccionar características para el modelo
        feature_cols = [
            'ventas_mes_actual', 'ventas_mes_anterior', 'ventas_trimestre',
            'stock_actual', 'precio_ratio', 'margen_absoluto', 'rotacion_anual',
            'tendencia_ventas', 'ratio_stock_ventas', 'categoria_encoded',
            'proveedor_encoded', 'dias_desde_ultima_venta', 'estacionalidad'
        ]
        
        # Filtrar productos con suficiente historial
        df_model = df[df['ventas_trimestre'] > 0].copy()
        
        if len(df_model) < 10:
            # Si no hay suficientes datos, usar predicción simple
            return self._simple_demand_prediction(df, horizon_days)
        
        X = df_model[feature_cols].fillna(0)
        y = df_model['ventas_mes_actual']
        
        # Entrenar modelo
        self.demand_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        # Dividir datos para validación
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        self.demand_model.fit(X_train, y_train)
        
        # Hacer predicciones
        y_pred_test = self.demand_model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        
        # Predecir para todo el dataset
        predictions = self.demand_model.predict(X)
        
        # Ajustar predicciones por horizon_days
        factor_tiempo = horizon_days / 30  # Normalizar a mes
        predictions_adjusted = predictions * factor_tiempo
        
        # Crear DataFrame de resultados
        results = df_model[['producto_id', 'nombre', 'ventas_mes_actual', 'stock_actual']].copy()
        results['prediccion_demanda'] = np.maximum(0, predictions_adjusted.round(0).astype(int))
        results['confianza_prediccion'] = np.minimum(100, 100 - (mae / y_train.mean() * 100))
        
        # Calcular métricas de riesgo
        results['riesgo_desabasto'] = np.where(
            results['stock_actual'] < results['prediccion_demanda'],
            'ALTO',
            np.where(
                results['stock_actual'] < results['prediccion_demanda'] * 1.5,
                'MEDIO',
                'BAJO'
            )
        )
        
        results['cantidad_sugerida_compra'] = np.maximum(
            0, 
            results['prediccion_demanda'] * 1.2 - results['stock_actual']  # 20% buffer
        ).round(0).astype(int)
        
        # Métricas del modelo
        model_metrics = {
            'mae': mae,
            'rmse': rmse,
            'productos_analizados': len(df_model),
            'precision_promedio': results['confianza_prediccion'].mean()
        }
        
        return results.sort_values('riesgo_desabasto', key=lambda x: x.map({'ALTO': 1, 'MEDIO': 2, 'BAJO': 3})), model_metrics
    
    def _simple_demand_prediction(self, df, horizon_days):
        """
        Predicción simple cuando no hay suficientes datos para ML
        """
        results = df[['producto_id', 'nombre', 'ventas_mes_actual', 'stock_actual']].copy()
        
        # Predicción basada en tendencia simple
        factor_tiempo = horizon_days / 30
        results['prediccion_demanda'] = np.where(
            df['ventas_mes_anterior'] > 0,
            ((df['ventas_mes_actual'] + df['ventas_mes_anterior']) / 2 * factor_tiempo).round(0),
            (df['ventas_mes_actual'] * factor_tiempo).round(0)
        ).astype(int)
        
        results['confianza_prediccion'] = 50  # Confianza baja
        results['riesgo_desabasto'] = 'MEDIO'  # Asumir riesgo medio
        results['cantidad_sugerida_compra'] = np.maximum(
            0, results['prediccion_demanda'] - results['stock_actual']
        ).astype(int)
        
        model_metrics = {
            'mae': 0,
            'rmse': 0,
            'productos_analizados': len(df),
            'precision_promedio': 50
        }
        
        return results, model_metrics
    
    def detect_anomalies(self):
        """
        Detectar anomalías en patrones de ventas
        
        Returns:
            pd.DataFrame: Productos con anomalías detectadas
        """
        df = self.prepare_features()
        
        # Seleccionar características para detección de anomalías
        anomaly_features = [
            'ventas_mes_actual', 'ventas_mes_anterior', 'ventas_trimestre',
            'rotacion_anual', 'tendencia_ventas', 'ratio_stock_ventas'
        ]
        
        df_anomaly = df[anomaly_features].fillna(0)
        
        # Normalizar datos
        df_scaled = self.scaler.fit_transform(df_anomaly)
        
        # Entrenar modelo de detección de anomalías
        self.anomaly_model = IsolationForest(
            contamination=0.1,  # 10% de datos como anomalías
            random_state=42,
            n_jobs=-1
        )
        
        anomaly_labels = self.anomaly_model.fit_predict(df_scaled)
        anomaly_scores = self.anomaly_model.score_samples(df_scaled)
        
        # Preparar resultados
        results = df[['producto_id', 'nombre', 'ventas_mes_actual', 'stock_actual']].copy()
        results['es_anomalia'] = anomaly_labels == -1
        results['score_anomalia'] = anomaly_scores
        results['percentil_anomalia'] = pd.qcut(
            anomaly_scores, 
            q=5, 
            labels=['Muy Anómalo', 'Anómalo', 'Normal', 'Típico', 'Muy Típico']
        )
        
        # Clasificar tipo de anomalía
        def clasificar_anomalia(row):
            if not row['es_anomalia']:
                return 'Normal'
            elif row['ventas_mes_actual'] > row['ventas_mes_anterior'] * 3:
                return 'Pico de Ventas'
            elif row['ventas_mes_actual'] < row['ventas_mes_anterior'] * 0.3 and row['ventas_mes_anterior'] > 0:
                return 'Caída Drástica'
            elif row['stock_actual'] > row['ventas_mes_actual'] * 6:
                return 'Sobrestock'
            else:
                return 'Patrón Irregular'
        
        results['tipo_anomalia'] = df.apply(clasificar_anomalia, axis=1)
        
        # Filtrar solo anomalías
        anomalies = results[results['es_anomalia']].sort_values('score_anomalia')
        
        return anomalies
    
    def cluster_products(self, n_clusters=5):
        """
        Agrupar productos por comportamiento similar
        
        Args:
            n_clusters (int): Número de clusters
            
        Returns:
            pd.DataFrame: Productos con clusters asignados
        """
        df = self.prepare_features()
        
        # Características para clustering
        cluster_features = [
            'ventas_mes_actual', 'rotacion_anual', 'margen_absoluto',
            'precio_ratio', 'tendencia_ventas', 'ratio_stock_ventas'
        ]
        
        df_cluster = df[cluster_features].fillna(0)
        
        # Normalizar datos
        df_scaled = self.scaler.fit_transform(df_cluster)
        
        # Aplicar K-Means
        self.cluster_model = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10
        )
        
        cluster_labels = self.cluster_model.fit_predict(df_scaled)
        
        # Preparar resultados
        results = df[['producto_id', 'nombre', 'nombre_categoria', 'ventas_mes_actual', 'margen_porcentaje']].copy()
        results['cluster'] = cluster_labels
        
        # Caracterizar clusters
        cluster_stats = df.groupby(cluster_labels).agg({
            'ventas_mes_actual': 'mean',
            'margen_porcentaje': 'mean',
            'rotacion_anual': 'mean',
            'precio_venta': 'mean'
        }).round(2)
        
        # Asignar nombres descriptivos a clusters
        cluster_names = {}
        for i in range(n_clusters):
            stats = cluster_stats.iloc[i]
            if stats['ventas_mes_actual'] > df['ventas_mes_actual'].quantile(0.8):
                if stats['margen_porcentaje'] > df['margen_porcentaje'].quantile(0.7):
                    cluster_names[i] = 'Estrellas (Alta Venta, Alto Margen)'
                else:
                    cluster_names[i] = 'Volumen (Alta Venta, Bajo Margen)'
            elif stats['margen_porcentaje'] > df['margen_porcentaje'].quantile(0.8):
                cluster_names[i] = 'Premium (Baja Venta, Alto Margen)'
            elif stats['rotacion_anual'] < df['rotacion_anual'].quantile(0.3):
                cluster_names[i] = 'Lento Movimiento'
            else:
                cluster_names[i] = 'Estándar'
        
        results['nombre_cluster'] = results['cluster'].map(cluster_names)
        
        return results, cluster_stats, cluster_names
    
    def generate_recommendations(self):
        """
        Generar recomendaciones automáticas basadas en ML
        
        Returns:
            dict: Diccionario con diferentes tipos de recomendaciones
        """
        recommendations = {}
        
        # 1. Predicciones de demanda
        demand_pred, demand_metrics = self.predict_demand()
        recommendations['demand_predictions'] = {
            'data': demand_pred,
            'metrics': demand_metrics
        }
        
        # 2. Anomalías detectadas
        anomalies = self.detect_anomalies()
        recommendations['anomalies'] = anomalies
        
        # 3. Clustering de productos
        clusters, cluster_stats, cluster_names = self.cluster_products()
        recommendations['clusters'] = {
            'data': clusters,
            'stats': cluster_stats,
            'names': cluster_names
        }
        
        # 4. Productos críticos para acción inmediata
        critical_actions = self._generate_critical_actions(demand_pred)
        recommendations['critical_actions'] = critical_actions
        
        # 5. Oportunidades de negocio
        opportunities = self._identify_opportunities(clusters)
        recommendations['opportunities'] = opportunities
        
        return recommendations
    
    def _generate_critical_actions(self, demand_pred):
        """
        Generar acciones críticas basadas en predicciones
        """
        critical = demand_pred[demand_pred['riesgo_desabasto'] == 'ALTO'].copy()
        
        if critical.empty:
            return pd.DataFrame()
        
        critical['accion_recomendada'] = 'Compra Urgente'
        critical['prioridad'] = 'ALTA'
        critical['tiempo_limite'] = '7 días'
        
        return critical[['nombre', 'stock_actual', 'prediccion_demanda', 
                        'cantidad_sugerida_compra', 'accion_recomendada', 'prioridad']]
    
    def _identify_opportunities(self, clusters):
        """
        Identificar oportunidades de negocio basadas en clusters
        """
        opportunities = []
        
        # Analizar cada cluster
        for cluster_id, cluster_name in clusters.groupby('cluster')['nombre_cluster'].first().items():
            cluster_data = clusters[clusters['cluster'] == cluster_id]
            
            if 'Estrellas' in cluster_name:
                opportunities.append({
                    'tipo': 'Potenciar Éxitos',
                    'descripcion': f'Incrementar stock de productos estrella (Cluster: {cluster_name})',
                    'productos_afectados': len(cluster_data),
                    'accion': 'Aumentar inventario y promoción'
                })
            
            elif 'Lento Movimiento' in cluster_name:
                opportunities.append({
                    'tipo': 'Optimizar Inventario',
                    'descripcion': f'Reducir stock de productos de lento movimiento (Cluster: {cluster_name})',
                    'productos_afectados': len(cluster_data),
                    'accion': 'Liquidación o descuentos'
                })
            
            elif 'Premium' in cluster_name:
                opportunities.append({
                    'tipo': 'Maximizar Margen',
                    'descripcion': f'Promocionar productos premium (Cluster: {cluster_name})',
                    'productos_afectados': len(cluster_data),
                    'accion': 'Marketing dirigido'
                })
        
        return pd.DataFrame(opportunities)

# ================================
# FUNCIONES AUXILIARES
# ================================

def get_feature_importance(analyzer):
    """
    Obtener importancia de características del modelo de demanda
    
    Args:
        analyzer (InventoryMLAnalyzer): Analizador entrenado
        
    Returns:
        pd.DataFrame: Importancia de características
    """
    if analyzer.demand_model is None:
        return pd.DataFrame()
    
    feature_names = [
        'ventas_mes_actual', 'ventas_mes_anterior', 'ventas_trimestre',
        'stock_actual', 'precio_ratio', 'margen_absoluto', 'rotacion_anual',
        'tendencia_ventas', 'ratio_stock_ventas', 'categoria_encoded',
        'proveedor_encoded', 'dias_desde_ultima_venta', 'estacionalidad'
    ]
    
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': analyzer.demand_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return importance_df

def simulate_scenarios(analyzer, scenarios):
    """
    Simular diferentes escenarios de demanda
    
    Args:
        analyzer (InventoryMLAnalyzer): Analizador ML
        scenarios (dict): Diccionario con escenarios a simular
        
    Returns:
        dict: Resultados de simulación
    """
    results = {}
    
    for scenario_name, scenario_params in scenarios.items():
        # Modificar datos según escenario
        modified_data = analyzer.data.copy()
        
        if 'demand_multiplier' in scenario_params:
            modified_data['ventas_mes_actual'] *= scenario_params['demand_multiplier']
        
        if 'price_change' in scenario_params:
            modified_data['precio_venta'] *= (1 + scenario_params['price_change'])
        
        # Crear nuevo analizador con datos modificados
        scenario_analyzer = InventoryMLAnalyzer(modified_data)
        predictions, metrics = scenario_analyzer.predict_demand()
        
        results[scenario_name] = {
            'predictions': predictions,
            'metrics': metrics,
            'scenario_params': scenario_params
        }
    
    return results

# ================================
# EJEMPLO DE USO
# ================================

if __name__ == "__main__":
    # Cargar datos de ejemplo
    try:
        df = pd.read_csv('data/inventario_expandido.csv')
        
        # Crear analizador ML
        analyzer = InventoryMLAnalyzer(df)
        
        # Generar recomendaciones completas
        recommendations = analyzer.generate_recommendations()
        
        print("🤖 Análisis ML Completado!")
        print(f"📊 Productos analizados: {len(df)}")
        print(f"⚠️ Productos con riesgo alto: {len(recommendations['demand_predictions']['data'][recommendations['demand_predictions']['data']['riesgo_desabasto'] == 'ALTO'])}")
        print(f"🔍 Anomalías detectadas: {len(recommendations['anomalies'])}")
        print(f"📈 Clusters identificados: {len(recommendations['clusters']['names'])}")
        
    except FileNotFoundError:
        print("❌ Archivo de datos no encontrado. Ejecutar desde el directorio del proyecto.")
    except Exception as e:
        print(f"❌ Error en análisis ML: {e}")
