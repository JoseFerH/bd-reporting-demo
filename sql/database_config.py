"""
DATABASE_CONFIG.PY
==================
Configuración y manejo de base de datos PostgreSQL
Sistema de Business Intelligence - Ferretería Petapa

Funcionalidades:
- Conexión a PostgreSQL local y en la nube
- Carga de datos desde CSV a la base de datos
- Ejecutor de consultas SQL avanzadas
- Sincronización de datos
- Backup y restore automatizado
"""

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
import os
from datetime import datetime
import logging
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gestor principal de la base de datos PostgreSQL
    """
    
    def __init__(self, config=None):
        """
        Inicializar el gestor de base de datos
        
        Args:
            config (dict): Configuración de conexión personalizada
        """
        self.config = config or self._get_default_config()
        self.engine = None
        self.connection = None
        
    def _get_default_config(self):
        """
        Obtener configuración por defecto desde variables de entorno
        """
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'ferreteria_petapa'),
            'username': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'sslmode': os.getenv('DB_SSLMODE', 'prefer')
        }
    
    def connect(self):
        """
        Establecer conexión con la base de datos
        
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            # Crear string de conexión
            connection_string = (
                f"postgresql://{self.config['username']}:{self.config['password']}"
                f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
                f"?sslmode={self.config['sslmode']}"
            )
            
            # Crear engine de SQLAlchemy
            self.engine = create_engine(connection_string, echo=False)
            
            # Probar conexión
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("✅ Conexión a PostgreSQL establecida exitosamente")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return False
    
    def disconnect(self):
        """
        Cerrar conexión con la base de datos
        """
        if self.engine:
            self.engine.dispose()
            logger.info("🔌 Conexión cerrada")
    
    def create_tables(self):
        """
        Crear todas las tablas del schema si no existen
        
        Returns:
            bool: True si las tablas fueron creadas exitosamente
        """
        try:
            # Leer schema SQL
            with open('sql/schema_completo.sql', 'r', encoding='utf-8') as file:
                schema_sql = file.read()
            
            # Ejecutar schema
            with self.engine.connect() as conn:
                # Dividir por comandos individuales
                commands = schema_sql.split(';')
                
                for command in commands:
                    command = command.strip()
                    if command and not command.startswith('--'):
                        try:
                            conn.execute(text(command))
                            conn.commit()
                        except Exception as cmd_error:
                            # Log error pero continuar (puede ser que la tabla ya exista)
                            logger.warning(f"⚠️ Comando SQL: {cmd_error}")
                
                logger.info("✅ Schema de base de datos creado/actualizado")
                return True
                
        except FileNotFoundError:
            logger.error("❌ Archivo schema_completo.sql no encontrado")
            return False
        except Exception as e:
            logger.error(f"❌ Error creando tablas: {e}")
            return False
    
    def load_csv_data(self, force_reload=False):
        """
        Cargar datos desde archivos CSV a la base de datos
        
        Args:
            force_reload (bool): Forzar recarga de datos
            
        Returns:
            bool: True si los datos fueron cargados exitosamente
        """
        try:
            csv_files = {
                'categorias': 'data/categorias.csv',
                'proveedores': 'data/proveedores.csv',
                'ubicaciones': 'data/ubicaciones.csv',
                'inventario': 'data/inventario_expandido.csv'
            }
            
            # Archivos opcionales
            optional_files = {
                'alertas': 'data/alertas_sample.csv',
                'movimientos_inventario': 'data/movimientos_inventario_sample.csv'
            }
            
            for table_name, file_path in csv_files.items():
                if os.path.exists(file_path):
                    self._load_table_from_csv(table_name, file_path, force_reload)
                else:
                    logger.warning(f"⚠️ Archivo no encontrado: {file_path}")
            
            # Cargar archivos opcionales
            for table_name, file_path in optional_files.items():
                if os.path.exists(file_path):
                    self._load_table_from_csv(table_name, file_path, force_reload)
            
            logger.info("✅ Datos CSV cargados exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando datos CSV: {e}")
            return False
    
    def _load_table_from_csv(self, table_name, file_path, force_reload=False):
        """
        Cargar una tabla específica desde CSV
        
        Args:
            table_name (str): Nombre de la tabla
            file_path (str): Ruta del archivo CSV
            force_reload (bool): Forzar recarga
        """
        try:
            # Verificar si la tabla ya tiene datos
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                
                if count > 0 and not force_reload:
                    logger.info(f"📊 Tabla {table_name} ya tiene datos ({count} registros)")
                    return
            
            # Leer CSV
            df = pd.read_csv(file_path)
            
            # Convertir tipos de datos según la tabla
            df = self._convert_data_types(df, table_name)
            
            # Cargar a la base de datos
            df.to_sql(
                table_name, 
                self.engine, 
                if_exists='replace',
                index=False,
                method='multi',
                chunksize=1000
            )
            
            logger.info(f"✅ {table_name}: {len(df)} registros cargados desde {file_path}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando {table_name}: {e}")
    
    def _convert_data_types(self, df, table_name):
        """
        Convertir tipos de datos según la tabla
        
        Args:
            df (pd.DataFrame): DataFrame a convertir
            table_name (str): Nombre de la tabla
            
        Returns:
            pd.DataFrame: DataFrame con tipos corregidos
        """
        # Conversiones específicas por tabla
        if table_name == 'inventario':
            date_columns = ['fecha_ultima_compra', 'fecha_ultima_venta', 'fecha_creacion']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Convertir booleanos
            bool_columns = ['requiere_refrigeracion', 'es_peligroso', 'activo']
            for col in bool_columns:
                if col in df.columns:
                    df[col] = df[col].astype(bool)
        
        elif table_name == 'movimientos_inventario':
            if 'fecha_movimiento' in df.columns:
                df['fecha_movimiento'] = pd.to_datetime(df['fecha_movimiento'], errors='coerce')
        
        elif table_name == 'alertas':
            if 'fecha_generacion' in df.columns:
                df['fecha_generacion'] = pd.to_datetime(df['fecha_generacion'], errors='coerce')
            if 'fecha_resolucion' in df.columns:
                df['fecha_resolucion'] = pd.to_datetime(df['fecha_resolucion'], errors='coerce')
        
        return df
    
    def execute_query(self, query, params=None):
        """
        Ejecutar consulta SQL y retornar resultados
        
        Args:
            query (str): Consulta SQL
            params (dict): Parámetros para la consulta
            
        Returns:
            pd.DataFrame: Resultados de la consulta
        """
        try:
            with self.engine.connect() as conn:
                result = pd.read_sql(query, conn, params=params)
                return result
        except Exception as e:
            logger.error(f"❌ Error ejecutando consulta: {e}")
            return pd.DataFrame()
    
    def execute_advanced_queries(self):
        """
        Ejecutar consultas avanzadas del archivo SQL
        
        Returns:
            dict: Diccionario con resultados de consultas importantes
        """
        try:
            results = {}
            
            # Consultas específicas importantes
            queries = {
                'productos_criticos': """
                    SELECT 
                        i.producto_id,
                        i.nombre,
                        c.nombre_categoria,
                        i.stock_actual,
                        i.stock_minimo,
                        i.ventas_mes_actual,
                        p.nombre_proveedor,
                        CASE 
                            WHEN i.stock_actual = 0 THEN 'SIN_STOCK'
                            WHEN i.stock_actual <= i.stock_minimo THEN 'CRITICO'
                            WHEN i.stock_actual <= i.punto_reorden THEN 'BAJO'
                            ELSE 'NORMAL'
                        END as estado_stock
                    FROM inventario i
                    LEFT JOIN categorias c ON i.categoria_id = c.categoria_id
                    LEFT JOIN proveedores p ON i.proveedor_id = p.proveedor_id
                    WHERE i.activo = true
                        AND i.stock_actual <= i.stock_minimo
                    ORDER BY i.stock_actual ASC, i.ventas_mes_actual DESC;
                """,
                
                'top_productos_ventas': """
                    SELECT 
                        i.producto_id,
                        i.nombre,
                        c.nombre_categoria,
                        i.ventas_mes_actual,
                        i.stock_actual,
                        ROUND((i.precio_venta - i.costo_unitario) * i.ventas_mes_actual, 2) as utilidad_mes,
                        CASE 
                            WHEN i.stock_actual <= i.stock_minimo THEN 'CRÍTICO'
                            WHEN i.stock_actual <= i.punto_reorden THEN 'BAJO' 
                            ELSE 'NORMAL'
                        END as estado_stock
                    FROM inventario i
                    JOIN categorias c ON i.categoria_id = c.categoria_id
                    WHERE i.activo = true
                    ORDER BY i.ventas_mes_actual DESC
                    LIMIT 15;
                """,
                
                'rentabilidad_categoria': """
                    SELECT 
                        c.categoria_id,
                        c.nombre_categoria,
                        COUNT(*) as total_productos,
                        SUM(i.stock_actual) as stock_total,
                        ROUND(AVG(((i.precio_venta - i.costo_unitario) / i.precio_venta) * 100), 2) as margen_promedio_pct,
                        ROUND(SUM(i.stock_actual * i.costo_unitario), 2) as valor_inventario,
                        ROUND(SUM((i.precio_venta - i.costo_unitario) * i.ventas_mes_actual), 2) as utilidad_mes,
                        ROUND(SUM(i.ventas_mes_actual * i.precio_venta), 2) as ingresos_mes
                    FROM inventario i
                    JOIN categorias c ON i.categoria_id = c.categoria_id
                    WHERE i.activo = true
                    GROUP BY c.categoria_id, c.nombre_categoria
                    ORDER BY utilidad_mes DESC;
                """,
                
                'kpis_principales': """
                    SELECT 
                        'RESUMEN EJECUTIVO' as seccion,
                        COUNT(*) as total_productos,
                        COUNT(*) FILTER (WHERE stock_actual > 0) as productos_en_stock,
                        COUNT(*) FILTER (WHERE stock_actual <= stock_minimo) as productos_stock_critico,
                        ROUND(SUM(stock_actual * costo_unitario), 2) as valor_total_inventario,
                        ROUND(SUM(ventas_mes_actual * precio_venta), 2) as ingresos_mes_actual,
                        ROUND(SUM((precio_venta - costo_unitario) * ventas_mes_actual), 2) as utilidad_bruta_mes,
                        ROUND(AVG(((precio_venta - costo_unitario) / precio_venta) * 100), 2) as margen_promedio_pct,
                        SUM(ventas_mes_actual) as unidades_vendidas_mes
                    FROM inventario 
                    WHERE activo = true;
                """
            }
            
            for query_name, query_sql in queries.items():
                try:
                    result = self.execute_query(query_sql)
                    results[query_name] = result
                    logger.info(f"✅ Consulta {query_name}: {len(result)} registros")
                except Exception as e:
                    logger.error(f"❌ Error en consulta {query_name}: {e}")
                    results[query_name] = pd.DataFrame()
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando consultas avanzadas: {e}")
            return {}
    
    def backup_database(self, backup_path=None):
        """
        Crear backup de la base de datos
        
        Args:
            backup_path (str): Ruta donde guardar el backup
            
        Returns:
            str: Ruta del archivo de backup creado
        """
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backups/ferreteria_petapa_backup_{timestamp}.sql"
            
            # Crear directorio de backups si no existe
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Comando pg_dump
            cmd = (
                f"pg_dump -h {self.config['host']} -p {self.config['port']} "
                f"-U {self.config['username']} -d {self.config['database']} "
                f"-f {backup_path} --verbose"
            )
            
            # Ejecutar comando (requiere que pg_dump esté en PATH)
            result = os.system(cmd)
            
            if result == 0:
                logger.info(f"✅ Backup creado exitosamente: {backup_path}")
                return backup_path
            else:
                logger.error("❌ Error creando backup")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error en backup: {e}")
            return None
    
    def get_table_stats(self):
        """
        Obtener estadísticas de todas las tablas
        
        Returns:
            pd.DataFrame: Estadísticas de tablas
        """
        query = """
        SELECT 
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes,
            n_live_tup as live_rows,
            n_dead_tup as dead_rows,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        ORDER BY live_rows DESC;
        """
        
        return self.execute_query(query)
    
    def optimize_database(self):
        """
        Optimizar la base de datos (VACUUM, ANALYZE)
        
        Returns:
            bool: True si la optimización fue exitosa
        """
        try:
            with self.engine.connect() as conn:
                # VACUUM para limpiar datos muertos
                conn.execute(text("VACUUM"))
                
                # ANALYZE para actualizar estadísticas
                conn.execute(text("ANALYZE"))
                
                logger.info("✅ Base de datos optimizada (VACUUM + ANALYZE)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error optimizando base de datos: {e}")
            return False

# ================================
# FUNCIONES DE UTILIDAD
# ================================

def create_sample_config():
    """
    Crear archivo de configuración de ejemplo
    """
    config_content = """
# CONFIGURACIÓN DE BASE DE DATOS
# ==============================
# Copiar este archivo como .env y configurar las variables

# PostgreSQL Local
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ferreteria_petapa
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_SSLMODE=prefer

# PostgreSQL en la Nube (Heroku, AWS RDS, etc.)
# DATABASE_URL=postgresql://user:password@host:port/database

# Configuración de aplicación
STREAMLIT_PORT=8501
DEBUG_MODE=false
"""
    
    with open('.env.example', 'w') as f:
        f.write(config_content)
    
    print("✅ Archivo .env.example creado")

def test_connection(config=None):
    """
    Probar conexión a la base de datos
    
    Args:
        config (dict): Configuración personalizada
        
    Returns:
        bool: True si la conexión es exitosa
    """
    db = DatabaseManager(config)
    
    if db.connect():
        # Ejecutar consulta de prueba
        result = db.execute_query("SELECT version();")
        if not result.empty:
            print(f"✅ PostgreSQL Version: {result.iloc[0, 0]}")
            
        # Mostrar estadísticas básicas
        stats = db.get_table_stats()
        if not stats.empty:
            print(f"📊 Tablas en la base de datos: {len(stats)}")
            
        db.disconnect()
        return True
    else:
        print("❌ No se pudo conectar a la base de datos")
        return False

def setup_database(force_reload=False):
    """
    Configurar completamente la base de datos
    
    Args:
        force_reload (bool): Forzar recarga de datos
        
    Returns:
        bool: True si la configuración fue exitosa
    """
    print("🚀 Iniciando configuración de base de datos...")
    
    db = DatabaseManager()
    
    if not db.connect():
        return False
    
    # Crear tablas
    if not db.create_tables():
        return False
    
    # Cargar datos
    if not db.load_csv_data(force_reload):
        return False
    
    # Optimizar base de datos
    db.optimize_database()
    
    # Ejecutar consultas de prueba
    results = db.execute_advanced_queries()
    
    if results and 'kpis_principales' in results:
        kpis = results['kpis_principales'].iloc[0]
        print(f"📊 Productos cargados: {kpis['total_productos']}")
        print(f"💰 Valor inventario: Q{kpis['valor_total_inventario']:,.2f}")
        print(f"⚠️ Productos críticos: {kpis['productos_stock_critico']}")
    
    db.disconnect()
    
    print("✅ Base de datos configurada exitosamente!")
    return True

# ================================
# SCRIPT PRINCIPAL
# ================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestor de Base de Datos - Ferretería Petapa")
    parser.add_argument('--setup', action='store_true', help='Configurar base de datos completa')
    parser.add_argument('--test', action='store_true', help='Probar conexión')
    parser.add_argument('--backup', action='store_true', help='Crear backup')
    parser.add_argument('--reload', action='store_true', help='Forzar recarga de datos')
    parser.add_argument('--optimize', action='store_true', help='Optimizar base de datos')
    parser.add_argument('--create-config', action='store_true', help='Crear archivo de configuración')
    
    args = parser.parse_args()
    
    if args.create_config:
        create_sample_config()
    elif args.test:
        test_connection()
    elif args.setup:
        setup_database(force_reload=args.reload)
    elif args.backup:
        db = DatabaseManager()
        if db.connect():
            backup_path = db.backup_database()
            if backup_path:
                print(f"✅ Backup creado: {backup_path}")
            db.disconnect()
    elif args.optimize:
        db = DatabaseManager()
        if db.connect():
            db.optimize_database()
            db.disconnect()
    else:
        print("🔧 Gestor de Base de Datos - Ferretería Petapa")
        print("Uso: python database_config.py [--setup|--test|--backup|--reload|--optimize|--create-config]")
        print("\nOpciones:")
        print("  --setup         Configurar base de datos completa")
        print("  --test          Probar conexión a la base de datos")
        print("  --backup        Crear backup de la base de datos")
        print("  --reload        Forzar recarga de datos CSV")
        print("  --optimize      Optimizar base de datos (VACUUM + ANALYZE)")
        print("  --create-config Crear archivo de configuración de ejemplo")
