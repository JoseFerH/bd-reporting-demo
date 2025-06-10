-- =====================================================
-- SCHEMA COMPLETO PARA SISTEMA DE INVENTARIOS
-- Ferretería Petapa - Business Intelligence Demo
-- =====================================================

-- Tabla de Categorías
CREATE TABLE categorias (
    categoria_id INT PRIMARY KEY,
    nombre_categoria VARCHAR(50) NOT NULL,
    descripcion TEXT,
    margen_promedio DECIMAL(5,2) DEFAULT 0.30,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Proveedores
CREATE TABLE proveedores (
    proveedor_id INT PRIMARY KEY,
    nombre_proveedor VARCHAR(100) NOT NULL,
    contacto VARCHAR(100),
    telefono VARCHAR(20),
    email VARCHAR(100),
    direccion TEXT,
    ciudad VARCHAR(50),
    pais VARCHAR(50) DEFAULT 'Guatemala',
    tiempo_entrega_dias INT DEFAULT 7,
    calificacion DECIMAL(3,2) DEFAULT 4.0,
    activo BOOLEAN DEFAULT TRUE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Ubicaciones en Almacén
CREATE TABLE ubicaciones (
    ubicacion_id INT PRIMARY KEY,
    seccion VARCHAR(20) NOT NULL,
    pasillo VARCHAR(10),
    estante VARCHAR(10),
    nivel VARCHAR(10),
    capacidad_maxima INT DEFAULT 100,
    descripcion TEXT
);

-- Tabla Principal de Inventario (EXPANDIDA)
CREATE TABLE inventario (
    producto_id INT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    categoria_id INT,
    proveedor_id INT,
    ubicacion_id INT,
    
    -- Stock y Control
    stock_actual INT NOT NULL DEFAULT 0,
    stock_minimo INT NOT NULL DEFAULT 5,
    stock_maximo INT NOT NULL DEFAULT 100,
    punto_reorden INT NOT NULL DEFAULT 10,
    
    -- Financiero
    costo_unitario DECIMAL(10,2) NOT NULL,
    precio_venta DECIMAL(10,2) NOT NULL,
    precio_venta_mayoreo DECIMAL(10,2),
    moneda VARCHAR(3) DEFAULT 'GTQ',
    
    -- Ventas y Movimiento
    ventas_mes_actual INT DEFAULT 0,
    ventas_mes_anterior INT DEFAULT 0,
    ventas_trimestre INT DEFAULT 0,
    ventas_año INT DEFAULT 0,
    
    -- Fechas
    fecha_ultima_compra DATE,
    fecha_ultima_venta DATE,
    fecha_vencimiento DATE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Información Adicional
    codigo_barras VARCHAR(50),
    unidad_medida VARCHAR(20) DEFAULT 'pieza',
    peso_kg DECIMAL(8,3),
    dimensiones VARCHAR(50),
    marca VARCHAR(50),
    modelo VARCHAR(50),
    garantia_meses INT DEFAULT 0,
    
    -- Flags de Control
    requiere_refrigeracion BOOLEAN DEFAULT FALSE,
    es_peligroso BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE,
    
    -- Claves Foráneas
    FOREIGN KEY (categoria_id) REFERENCES categorias(categoria_id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(proveedor_id),
    FOREIGN KEY (ubicacion_id) REFERENCES ubicaciones(ubicacion_id)
);

-- Tabla de Historial de Movimientos
CREATE TABLE movimientos_inventario (
    movimiento_id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL,
    tipo_movimiento VARCHAR(20) NOT NULL, -- 'ENTRADA', 'SALIDA', 'AJUSTE', 'MERMA'
    cantidad INT NOT NULL,
    costo_unitario DECIMAL(10,2),
    precio_venta DECIMAL(10,2),
    motivo VARCHAR(100),
    usuario VARCHAR(50),
    fecha_movimiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stock_anterior INT,
    stock_nuevo INT,
    documento_referencia VARCHAR(50),
    
    FOREIGN KEY (producto_id) REFERENCES inventario(producto_id)
);

-- Tabla de Alertas
CREATE TABLE alertas (
    alerta_id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL,
    tipo_alerta VARCHAR(30) NOT NULL, -- 'STOCK_BAJO', 'VENCIMIENTO', 'SIN_MOVIMIENTO'
    mensaje TEXT NOT NULL,
    prioridad VARCHAR(10) DEFAULT 'MEDIA', -- 'ALTA', 'MEDIA', 'BAJA'
    estado VARCHAR(20) DEFAULT 'ACTIVA', -- 'ACTIVA', 'RESUELTA', 'IGNORADA'
    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP,
    usuario_asignado VARCHAR(50),
    
    FOREIGN KEY (producto_id) REFERENCES inventario(producto_id)
);

-- Tabla de Órdenes de Compra
CREATE TABLE ordenes_compra (
    orden_id SERIAL PRIMARY KEY,
    proveedor_id INT NOT NULL,
    fecha_orden DATE NOT NULL,
    fecha_esperada_entrega DATE,
    fecha_entrega_real DATE,
    estado VARCHAR(20) DEFAULT 'PENDIENTE', -- 'PENDIENTE', 'ENVIADA', 'RECIBIDA', 'CANCELADA'
    total_orden DECIMAL(12,2),
    impuestos DECIMAL(10,2),
    descuento DECIMAL(10,2) DEFAULT 0.00,
    usuario_creador VARCHAR(50),
    notas TEXT,
    
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(proveedor_id)
);

-- Tabla de Detalles de Órdenes de Compra
CREATE TABLE detalle_ordenes_compra (
    detalle_id SERIAL PRIMARY KEY,
    orden_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad_ordenada INT NOT NULL,
    cantidad_recibida INT DEFAULT 0,
    precio_unitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    
    FOREIGN KEY (orden_id) REFERENCES ordenes_compra(orden_id),
    FOREIGN KEY (producto_id) REFERENCES inventario(producto_id)
);

-- =====================================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- =====================================================

-- Índices para consultas frecuentes
CREATE INDEX idx_inventario_categoria ON inventario(categoria_id);
CREATE INDEX idx_inventario_proveedor ON inventario(proveedor_id);
CREATE INDEX idx_inventario_stock_bajo ON inventario(stock_actual, stock_minimo) WHERE stock_actual <= stock_minimo;
CREATE INDEX idx_inventario_ventas_mes ON inventario(ventas_mes_actual DESC);
CREATE INDEX idx_movimientos_fecha ON movimientos_inventario(fecha_movimiento DESC);
CREATE INDEX idx_movimientos_producto ON movimientos_inventario(producto_id);
CREATE INDEX idx_alertas_activas ON alertas(estado, fecha_generacion) WHERE estado = 'ACTIVA';

-- =====================================================
-- VISTAS PARA REPORTES COMUNES
-- =====================================================

-- Vista de Productos con Stock Crítico
CREATE VIEW vista_stock_critico AS
SELECT 
    i.producto_id,
    i.nombre,
    c.nombre_categoria,
    i.stock_actual,
    i.stock_minimo,
    i.punto_reorden,
    p.nombre_proveedor,
    p.tiempo_entrega_dias,
    i.ventas_mes_actual,
    CASE 
        WHEN i.stock_actual = 0 THEN 'SIN_STOCK'
        WHEN i.stock_actual <= i.stock_minimo THEN 'CRITICO'
        WHEN i.stock_actual <= i.punto_reorden THEN 'BAJO'
        ELSE 'NORMAL'
    END as estado_stock
FROM inventario i
LEFT JOIN categorias c ON i.categoria_id = c.categoria_id
LEFT JOIN proveedores p ON i.proveedor_id = p.proveedor_id
WHERE i.activo = TRUE
ORDER BY i.stock_actual ASC, i.ventas_mes_actual DESC;

-- Vista de Análisis de Rentabilidad
CREATE VIEW vista_rentabilidad AS
SELECT 
    i.producto_id,
    i.nombre,
    c.nombre_categoria,
    i.costo_unitario,
    i.precio_venta,
    (i.precio_venta - i.costo_unitario) as utilidad_unitaria,
    ROUND(((i.precio_venta - i.costo_unitario) / i.precio_venta * 100), 2) as margen_porcentaje,
    i.ventas_mes_actual,
    (i.precio_venta - i.costo_unitario) * i.ventas_mes_actual as utilidad_mes,
    i.stock_actual * i.costo_unitario as valor_inventario,
    CASE 
        WHEN i.ventas_mes_actual > 0 THEN ROUND(i.stock_actual::DECIMAL / i.ventas_mes_actual, 2)
        ELSE NULL
    END as meses_inventario
FROM inventario i
LEFT JOIN categorias c ON i.categoria_id = c.categoria_id
WHERE i.activo = TRUE
ORDER BY utilidad_mes DESC NULLS LAST;

-- Vista de Top Productos
CREATE VIEW vista_top_productos AS
SELECT 
    i.producto_id,
    i.nombre,
    c.nombre_categoria,
    i.ventas_mes_actual,
    i.ventas_trimestre,
    i.ventas_año,
    (i.precio_venta - i.costo_unitario) * i.ventas_mes_actual as utilidad_mes,
    i.stock_actual,
    RANK() OVER (ORDER BY i.ventas_mes_actual DESC) as ranking_ventas,
    RANK() OVER (ORDER BY (i.precio_venta - i.costo_unitario) * i.ventas_mes_actual DESC) as ranking_utilidad
FROM inventario i
LEFT JOIN categorias c ON i.categoria_id = c.categoria_id
WHERE i.activo = TRUE AND i.ventas_mes_actual > 0
ORDER BY i.ventas_mes_actual DESC;

-- =====================================================
-- TRIGGERS PARA AUTOMATIZACIÓN
-- =====================================================

-- Función para actualizar fecha de modificación
CREATE OR REPLACE FUNCTION actualizar_fecha_modificacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para inventario
CREATE TRIGGER trigger_actualizar_inventario
    BEFORE UPDATE ON inventario
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_modificacion();

-- Función para generar alertas automáticas
CREATE OR REPLACE FUNCTION generar_alertas_stock()
RETURNS TRIGGER AS $$
BEGIN
    -- Alert for low stock
    IF NEW.stock_actual <= NEW.stock_minimo AND OLD.stock_actual > OLD.stock_minimo THEN
        INSERT INTO alertas (producto_id, tipo_alerta, mensaje, prioridad)
        VALUES (NEW.producto_id, 'STOCK_BAJO', 
                'Stock crítico: ' || NEW.nombre || ' tiene solo ' || NEW.stock_actual || ' unidades',
                CASE WHEN NEW.stock_actual = 0 THEN 'ALTA' ELSE 'MEDIA' END);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para alertas de stock
CREATE TRIGGER trigger_alertas_stock
    AFTER UPDATE OF stock_actual ON inventario
    FOR EACH ROW
    EXECUTE FUNCTION generar_alertas_stock();
