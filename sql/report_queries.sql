-- 1. Top 5 productos con más ventas
SELECT
    producto_id,
    nombre,
    ventas_mes
FROM
    inventario
ORDER BY
    ventas_mes DESC
LIMIT 5;

-- 2. Productos con stock bajo umbral (<10 unidades)
SELECT
    producto_id,
    nombre,
    stock
FROM
    inventario
WHERE
    stock < 10
ORDER BY
    stock ASC;

-- 3. Ratio ventas/stock (ventas por unidad disponible)
SELECT
    producto_id,
    nombre,
    ventas_mes,
    stock,
    CASE
        WHEN stock = 0 THEN NULL
        ELSE ROUND(ventas_mes::numeric / stock, 2)
    END AS ratio_ventas_por_stock
FROM
    inventario
ORDER BY
    ratio_ventas_por_stock DESC;
