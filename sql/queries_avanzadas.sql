-- =====================================================
-- CONSULTAS AVANZADAS PARA BUSINESS INTELLIGENCE
-- Sistema de Inventarios - Ferretería Petapa
-- =====================================================

-- =====================================================
-- 1. ANÁLISIS DE PRODUCTOS TOP Y CRÍTICOS
-- =====================================================

-- Top 10 productos por ventas mensuales
SELECT 
    i.producto_id,
    i.nombre,
    c.nombre_categoria,
    p.nombre_proveedor,
    i.ventas_mes_actual,
    i.stock_actual,
    ROUND((i.precio_venta - i.costo_unitario) * i.ventas_mes_actual, 2) as utilidad_mes,
    CASE 
        WHEN i.stock_actual <= i.stock_minimo THEN '🔴 CRÍTICO'
        WHEN i.stock_actual <= i.punto_reorden THEN '🟡 BAJO' 
        ELSE '🟢 NORMAL'
    END as estado_stock
FROM inventario i
JOIN categorias c ON i.categoria_id = c.categoria_id
JOIN proveedores p ON i.proveedor_id = p.proveedor_id
WHERE i.activo = TRUE
ORDER BY i.ventas_mes_actual DESC
LIMIT 10;

-- Productos con stock crítico que requieren reorden urgente
SELECT 
    i.producto_id,
    i.nombre,
    c.nombre_categoria,
    i.stock_actual,
    i.stock_minimo,
    i.punto_reorden,
    i.ventas_mes_actual,
    p.nombre_proveedor,
    p.tiempo_entrega_dias,
    ROUND(i.stock_actual::DECIMAL / NULLIF(i.ventas_mes_actual, 0) * 30, 1) as dias_inventario,
    (i.punto_reorden - i.stock_actual) as cantidad_sugerida_compra,
    ROUND((i.punto_reorden - i.stock_actual) * i.costo_unitario, 2) as inversion_requerida
FROM inventario i
JOIN categorias c ON i.categoria_id = c.categoria_id
JOIN proveedores p ON i.proveedor_id = p.proveedor_id
WHERE i.stock_actual <= i.stock_minimo 
    AND i.activo = TRUE
ORDER BY 
    CASE WHEN i.stock_actual = 0 THEN 0 ELSE 1 END,
    i.ventas_mes_actual DESC;

-- =====================================================
-- 2. ANÁLISIS DE RENTABILIDAD
-- =====================================================

-- Análisis de rentabilidad por categoría
SELECT 
    c.categoria_id,
    c.nombre_categoria,
    COUNT(*) as total_productos,
    SUM(i.stock_actual) as stock_total,
    ROUND(AVG(((i.precio_venta - i.costo_unitario) / i.precio_venta) * 100), 2) as margen_promedio_pct,
    ROUND(SUM(i.stock_actual * i.costo_unitario), 2) as valor_inventario,
    ROUND(SUM((i.precio_venta - i.costo_unitario) * i.ventas_mes_actual), 2) as utilidad_mes,
    ROUND(SUM(i.ventas_mes_actual * i.precio_venta), 2) as ingresos_mes,
    ROUND(SUM(i.ventas_mes_actual), 0) as unidades_vendidas_mes
FROM inventario i
JOIN categorias c ON i.categoria_id = c.categoria_id
WHERE i.activo = TRUE
GROUP BY c.categoria_id, c.nombre_categoria
ORDER BY utilidad_mes DESC;

-- Productos más rentables (Top 15)
SELECT 
    i.producto_id,
    i.nombre,
    c.nombre_categoria,
    i.costo_unitario,
    i.precio_venta,
    ROUND(i.precio_venta - i.costo_unitario, 2) as utilidad_unitaria,
    ROUND(((i.precio_venta - i.costo_unitario) / i.precio_venta) * 100, 2) as margen_pct,
    i.ventas_mes_actual,
    ROUND((i.precio_venta - i.costo_unitario) * i.ventas_mes_actual, 2) as utilidad_total_mes,
    ROUND(i.ventas_mes_actual * i.precio_venta, 2) as ingresos_mes
FROM inventario i
JOIN categorias c ON i.categoria_id = c.categoria_id
WHERE i.activo = TRUE AND i.ventas_mes_actual > 0
ORDER BY (i.precio_venta - i.costo_unitario) * i.ventas_mes_actual DESC
LIMIT 15;

-- =====================================================
-- 3. ANÁLISIS DE PROVEEDORES
-- =====================================================

-- Performance de proveedores
SELECT 
    p.proveedor_id,
    p.nombre_proveedor,
    p.calificacion,
    p.tiempo_entrega_dias,
    COUNT(i.producto_id) as total_productos,
    SUM(i.stock_actual) as stock_total,
    ROUND(SUM(i.stock_actual * i.costo_unitario), 2) as valor_inventario,
    ROUND(SUM(i.ventas_mes_actual * i.precio_venta), 2) as ingresos_generados,
    ROUND(AVG(((i.precio_venta - i.costo_unitario) / i.precio_venta) * 100), 2) as margen_promedio_pct,
    SUM(CASE WHEN i.stock_actual <= i.stock_minimo THEN 1 ELSE 0 END) as productos_stock_critico
FROM proveedores p
JOIN inventario i ON p.proveedor_id = i.proveedor_id
WHERE i.activo = TRUE
GROUP BY p.proveedor_id, p.nombre_proveedor, p.calificacion, p.tiempo_entrega_dias
ORDER BY ingresos_generados DESC;

-- =====================================================
-- 4. ANÁLISIS DE ROTACIÓN DE INVENTARIO
-- =====================================================

-- Análisis de rotación por producto
WITH rotacion_inventario AS (
    SELECT 
        i.producto_id,
        i.nombre,
        c.nombre_categoria,
        i.stock_actual,
        i.ventas_mes_actual,
        i.costo_unitario,
        CASE 
            WHEN i.stock_actual > 0 AND i.ventas_mes_actual > 0 
            THEN ROUND(i.stock_actual::DECIMAL / i.ventas_mes_actual, 2)
            ELSE NULL 
        END as meses_inventario,
        CASE 
            WHEN i.stock_actual > 0 AND i.ventas_mes_actual > 0 
            THEN ROUND(12.0 / (i.stock_actual::DECIMAL / i.ventas_mes_actual), 2)
            ELSE 0 
        END as rotacion_anual,
        i.stock_actual * i.costo_unitario as valor_inventario
    FROM inventario i
    JOIN categorias c ON i.categoria_id = c.categoria_id
    WHERE i.activo = TRUE
)
SELECT 
    *,
    CASE 
        WHEN rotacion_anual >= 12 THEN '🟢 EXCELENTE (>12x/año)'
        WHEN rotacion_anual >= 6 THEN '🟡 BUENA (6-12x/año)'
        WHEN rotacion_anual >= 3 THEN '🟠 REGULAR (3-6x/año)'
        WHEN rotacion_anual > 0 THEN '🔴 LENTA (<3x/año)'
        ELSE '⚫ SIN MOVIMIENTO'
    END as clasificacion_rotacion
FROM rotacion_inventario
ORDER BY rotacion_anual DESC;

-- Productos de lento movimiento (candidatos para liquidación)
SELECT 
    i.producto_id,
    i.nombre,
    c.nombre_categoria,
    i.stock_actual,
    i.ventas_mes_actual,
    i.ventas_trimestre,
    i.fecha_ultima_venta,
    EXTRACT(DAY FROM CURRENT_DATE - i.fecha_ultima_venta) as dias_sin_venta,
    i.stock_actual * i.costo_unitario as valor_inventario_inmovilizado,
    ROUND(i.precio_venta * 0.7, 2) as precio_liquidacion_sugerido
FROM inventario i
JOIN categorias c ON i.categoria_id = c.categoria_id
WHERE i.activo = TRUE 
    AND (i.ventas_mes_actual <= 2 OR i.fecha_ultima_venta < CURRENT_DATE - INTERVAL '60 days')
    AND i.stock_actual > 5
ORDER BY valor_inventario_inmovilizado DESC;

-- =====================================================
-- 5. ANÁLISIS DE UBICACIONES Y CAPACIDAD
-- =====================================================

-- Utilización de ubicaciones en almacén
SELECT 
    u.ubicacion_id,
    CONCAT(u.seccion, '-', u.pasillo, '-', u.estante, '-', u.nivel) as ubicacion_codigo,
    u.capacidad_maxima,
    COUNT(i.producto_id) as productos_almacenados,
    SUM(i.stock_actual) as unidades_almacenadas,
    ROUND((SUM(i.stock_actual)::DECIMAL / u.capacidad_maxima) * 100, 2) as porcentaje_ocupacion,
    ROUND(SUM(i.stock_actual * i.costo_unitario), 2) as valor_almacenado,
    u.descripcion
FROM ubicaciones u
LEFT JOIN inventario i ON u.ubicacion_id = i.ubicacion_id AND i.activo = TRUE
GROUP BY u.ubicacion_id, u.seccion, u.pasillo, u.estante, u.nivel, u.capacidad_maxima, u.descripcion
ORDER BY porcentaje_ocupacion DESC;

-- =====================================================
-- 6. PROYECCIONES Y PREDICCIONES
-- =====================================================

-- Proyección de ventas próximo mes basada en tendencia
WITH tendencia_ventas AS (
    SELECT 
        i.producto_id,
        i.nombre,
        c.nombre_categoria,
        i.ventas_mes_actual,
        i.ventas_mes_anterior,
        CASE 
            WHEN i.ventas_mes_anterior > 0 
            THEN ROUND(((i.ventas_mes_actual::DECIMAL - i.ventas_mes_anterior) / i.ventas_mes_anterior) * 100, 2)
            ELSE 0 
        END as crecimiento_pct,
        CASE 
            WHEN i.ventas_mes_anterior > 0 
            THEN ROUND(i.ventas_mes_actual * (1 + ((i.ventas_mes_actual::DECIMAL - i.ventas_mes_anterior) / i.ventas_mes_anterior)), 0)
            ELSE i.ventas_mes_actual 
        END as proyeccion_siguiente_mes,
        i.stock_actual,
        i.punto_reorden
    FROM inventario i
    JOIN categorias c ON i.categoria_id = c.categoria_id
    WHERE i.activo = TRUE
)
SELECT 
    *,
    CASE 
        WHEN stock_actual < proyeccion_siguiente_mes THEN '⚠️ RIESGO DESABASTO'
        WHEN stock_actual < proyeccion_siguiente_mes * 1.5 THEN '🟡 STOCK AJUSTADO'
        ELSE '🟢 STOCK SUFICIENTE'
    END as evaluacion_stock_futuro,
    GREATEST(0, proyeccion_siguiente_mes - stock_actual) as compra_sugerida
FROM tendencia_ventas
ORDER BY crecimiento_pct DESC;

-- =====================================================
-- 7. ANÁLISIS FINANCIERO INTEGRAL
-- =====================================================

-- Dashboard ejecutivo - KPIs principales
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
WHERE activo = TRUE;

-- Análisis ABC de productos (80/20 rule)
WITH ranking_productos AS (
    SELECT 
        i.producto_id,
        i.nombre,
        c.nombre_categoria,
        i.ventas_mes_actual * i.precio_venta as ingresos_mes,
        SUM(i.ventas_mes_actual * i.precio_venta) OVER() as ingresos_totales,
        ROW_NUMBER() OVER(ORDER BY i.ventas_mes_actual * i.precio_venta DESC) as ranking,
        COUNT(*) OVER() as total_productos
    FROM inventario i
    JOIN categorias c ON i.categoria_id = c.categoria_id
    WHERE i.activo = TRUE AND i.ventas_mes_actual > 0
),
productos_con_acumulado AS (
    SELECT 
        *,
        SUM(ingresos_mes) OVER(ORDER BY ranking) as ingresos_acumulados,
        ROUND((SUM(ingresos_mes) OVER(ORDER BY ranking) / ingresos_totales) * 100, 2) as porcentaje_acumulado
    FROM ranking_productos
)
SELECT 
    producto_id,
    nombre,
    nombre_categoria,
    ranking,
    ROUND(ingresos_mes, 2) as ingresos_mes,
    porcentaje_acumulado,
    CASE 
        WHEN porcentaje_acumulado <= 80 THEN 'A - VITAL (80% ingresos)'
        WHEN porcentaje_acumulado <= 95 THEN 'B - IMPORTANTE (15% ingresos)'
        ELSE 'C - NORMAL (5% ingresos)'
    END as clasificacion_abc
FROM productos_con_acumulado
ORDER BY ranking;

-- =====================================================
-- 8. ALERTAS AUTOMÁTICAS Y REPORTES
-- =====================================================

-- Generación automática de alertas de reorden
SELECT 
    'ALERTA_REORDEN' as tipo_alerta,
    i.producto_id,
    i.nombre,
    'Stock bajo: ' || i.stock_actual || ' unidades (mínimo: ' || i.stock_minimo || ')' as mensaje,
    CASE 
        WHEN i.stock_actual = 0 THEN 'CRÍTICA'
        WHEN i.stock_actual <= ROUND(i.stock_minimo * 0.5) THEN 'ALTA'
        ELSE 'MEDIA'
    END as prioridad,
    p.nombre_proveedor,
    p.tiempo_entrega_dias,
    ROUND((i.punto_reorden - i.stock_actual) * i.costo_unitario, 2) as inversion_sugerida,
    CURRENT_DATE as fecha_generacion
FROM inventario i
JOIN proveedores p ON i.proveedor_id = p.proveedor_id
WHERE i.stock_actual <= i.stock_minimo AND i.activo = TRUE

UNION ALL

-- Alertas de productos sin movimiento
SELECT 
    'ALERTA_SIN_MOVIMIENTO' as tipo_alerta,
    i.producto_id,
    i.nombre,
    'Producto sin ventas por ' || EXTRACT(DAY FROM CURRENT_DATE - i.fecha_ultima_venta) || ' días' as mensaje,
    CASE 
        WHEN EXTRACT(DAY FROM CURRENT_DATE - i.fecha_ultima_venta) > 90 THEN 'ALTA'
        WHEN EXTRACT(DAY FROM CURRENT_DATE - i.fecha_ultima_venta) > 60 THEN 'MEDIA'
        ELSE 'BAJA'
    END as prioridad,
    p.nombre_proveedor,
    NULL as tiempo_entrega_dias,
    ROUND(i.stock_actual * i.costo_unitario, 2) as inversion_inmovilizada,
    CURRENT_DATE as fecha_generacion
FROM inventario i
JOIN proveedores p ON i.proveedor_id = p.proveedor_id
WHERE i.fecha_ultima_venta < CURRENT_DATE - INTERVAL '45 days' 
    AND i.stock_actual > 0 
    AND i.activo = TRUE

ORDER BY 
    CASE tipo_alerta 
        WHEN 'ALERTA_REORDEN' THEN 1 
        ELSE 2 
    END,
    CASE prioridad 
        WHEN 'CRÍTICA' THEN 1 
        WHEN 'ALTA' THEN 2 
        WHEN 'MEDIA' THEN 3 
        ELSE 4 
    END;

-- =====================================================
-- 9. ANÁLISIS DE TENDENCIAS TEMPORALES
-- =====================================================

-- Comparación de performance mensual
SELECT 
    'COMPARACIÓN MENSUAL' as periodo,
    SUM(ventas_mes_actual) as ventas_mes_actual,
    SUM(ventas_mes_anterior) as ventas_mes_anterior,
    ROUND(((SUM(ventas_mes_actual) - SUM(ventas_mes_anterior))::DECIMAL / NULLIF(SUM(ventas_mes_anterior), 0)) * 100, 2) as crecimiento_unidades_pct,
    ROUND(SUM(ventas_mes_actual * precio_venta), 2) as ingresos_mes_actual,
    ROUND(SUM(ventas_mes_anterior * precio_venta), 2) as ingresos_mes_anterior,
    ROUND(((SUM(ventas_mes_actual * precio_venta) - SUM(ventas_mes_anterior * precio_venta))::DECIMAL / NULLIF(SUM(ventas_mes_anterior * precio_venta), 0)) * 100, 2) as crecimiento_ingresos_pct
FROM inventario 
WHERE activo = TRUE;

-- =====================================================
-- 10. FUNCIONES DE ANÁLISIS PREDICTIVO
-- =====================================================

-- Identificación de productos estacionales o con patrones
WITH patron_ventas AS (
    SELECT 
        i.producto_id,
        i.nombre,
        c.nombre_categoria,
        i.ventas_mes_actual,
        i.ventas_mes_anterior,
        i.ventas_trimestre,
        i.ventas_año,
        ROUND(i.ventas_trimestre::DECIMAL / 3, 2) as promedio_trimestral,
        ROUND(i.ventas_año::DECIMAL / 12, 2) as promedio_anual,
        CASE 
            WHEN i.ventas_mes_actual > (i.ventas_año::DECIMAL / 12) * 1.5 THEN 'PICO_ALTA'
            WHEN i.ventas_mes_actual < (i.ventas_año::DECIMAL / 12) * 0.5 THEN 'VALLE_BAJA'
            ELSE 'NORMAL'
        END as patron_estacional
    FROM inventario i
    JOIN categorias c ON i.categoria_id = c.categoria_id
    WHERE i.activo = TRUE AND i.ventas_año > 0
)
SELECT 
    *,
    CASE 
        WHEN patron_estacional = 'PICO_ALTA' THEN 'Considerar aumentar stock'
        WHEN patron_estacional = 'VALLE_BAJA' THEN 'Considerar reducir pedidos'
        ELSE 'Mantener estrategia actual'
    END as recomendacion_compra
FROM patron_ventas
ORDER BY 
    CASE patron_estacional 
        WHEN 'PICO_ALTA' THEN 1 
        WHEN 'VALLE_BAJA' THEN 2 
        ELSE 3 
    END,
    ventas_mes_actual DESC;

-- =====================================================
-- 11. MÉTRICAS DE RENDIMIENTO OPERATIVO
-- =====================================================

-- Eficiencia por categoría y proveedor
SELECT 
    c.nombre_categoria,
    p.nombre_proveedor,
    COUNT(i.producto_id) as productos_gestionados,
    ROUND(AVG(i.ventas_mes_actual), 2) as promedio_ventas_mes,
    ROUND(AVG(((i.precio_venta - i.costo_unitario) / i.precio_venta) * 100), 2) as margen_promedio,
    ROUND(SUM(i.stock_actual * i.costo_unitario), 2) as capital_inmovilizado,
    COUNT(*) FILTER (WHERE i.stock_actual <= i.stock_minimo) as productos_criticos,
    ROUND(COUNT(*) FILTER (WHERE i.stock_actual <= i.stock_minimo)::DECIMAL / COUNT(*) * 100, 2) as pct_productos_criticos,
    p.calificacion as calificacion_proveedor,
    p.tiempo_entrega_dias
FROM inventario i
JOIN categorias c ON i.categoria_id = c.categoria_id
JOIN proveedores p ON i.proveedor_id = p.proveedor_id
WHERE i.activo = TRUE
GROUP BY c.nombre_categoria, p.nombre_proveedor, p.calificacion, p.tiempo_entrega_dias
ORDER BY margen_promedio DESC, pct_productos_criticos ASC;
