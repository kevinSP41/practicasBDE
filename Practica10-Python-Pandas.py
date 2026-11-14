from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError
import pandas as pd

URI = "mongodb://localhost:27017/"


# ==============================================================================
# EJERCICIO 1: Comprobar conexión mediante ping e imprimir conteos
# ==============================================================================
def explorar(db):
    print("\n--- EJERCICIO 1: Colecciones y cantidades ---")
    for nombre in ["productos", "clientes", "proveedores", "ventas"]:
        print(f"Colección '{nombre}': {db[nombre].count_documents({})} documentos")


def consultar(db):
    # ==========================================================================
    # EJERCICIO 2: Consultar 5 productos con precio > 5000 (mayor a menor)
    # ==========================================================================
    print("\n--- EJERCICIO 2: Top 5 productos con precio mayor a 5,000 ---")
    campos_prod = {"_id": 0, "sku": 1, "nombre": 1, "precio": 1}
    cursor_prod = (
        db.productos.find({"precio": {"$gt": 5000}}, campos_prod)
        .sort("precio", DESCENDING)
        .limit(5)
    )
    for doc in cursor_prod:
        print(doc)

    # ==========================================================================
    # EJERCICIO 3: Buscar ventas de C001 y proyectar venta_id, fecha, estado y total
    # ==========================================================================
    print("\n--- EJERCICIO 3: Ventas del cliente C001 ---")
    campos_ventas = {"_id": 0, "venta_id": 1, "fecha": 1, "estado": 1, "total": 1}
    ventas_c001 = list(db.ventas.find({"cliente_id": "C001"}, campos_ventas))
    print(f"Total de ventas encontradas para C001: {len(ventas_c001)}")
    for venta in ventas_c001:
        print(venta)


# ==============================================================================
# EJERCICIO 4: CRUD en practica10_temporal mostrando contadores de cada operación
# ==============================================================================
def crud_temporal(db):
    print("\n--- EJERCICIO 4: CRUD en 'practica10_temporal' ---")
    col = db["practica10_temporal"]
    clave = {"origen": "practica10", "codigo": "LAB10"}
    col.delete_many(clave)  # Limpieza previa para evitar duplicados de pruebas anteriores

    try:
        # 1. Insertar
        insertado = col.insert_one(
            {**clave, "nombre": "Prueba Python", "stock": 5, "precio": 100}
        )
        conteo_insertados = 1 if insertado.acknowledged else 0
        print(f"[CREATE] Documentos insertados: {conteo_insertados} (ID: {insertado.inserted_id})")

        # 2. Consultar
        doc_consultado = col.find_one(clave, {"_id": 0})
        conteo_consultados = col.count_documents(clave)
        print(f"[READ]   Documentos encontrados: {conteo_consultados} -> {doc_consultado}")

        # 3. Modificar
        actualizado = col.update_one(
            clave, {"$set": {"precio": 150}, "$inc": {"stock": 10}}
        )
        print(
            f"[UPDATE] Coincidentes: {actualizado.matched_count} | "
            f"Modificados: {actualizado.modified_count}"
        )
        print(f"         Documento después del cambio: {col.find_one(clave, {'_id': 0})}")

    finally:
        # 4. Eliminar
        eliminado = col.delete_one(clave)
        restantes = col.count_documents(clave)
        print(
            f"[DELETE] Documentos eliminados: {eliminado.deleted_count} | "
            f"Restantes con esa clave: {restantes}"
        )


def agregar(db):
    # ==========================================================================
    # EJERCICIO 5: Calcular con aggregate() número e importe de ventas por estado
    # ==========================================================================
    print("\n--- EJERCICIO 5: Número e importe de ventas por estado (MongoDB) ---")
    pipeline_estado = [
        {
            "$group": {
                "_id": "$estado",
                "ventas": {"$sum": 1},
                "importe_registrado": {"$sum": "$total"},
            }
        },
        {"$sort": {"importe_registrado": -1}},
    ]
    for fila in db.ventas.aggregate(pipeline_estado):
        print(fila)

    # ==========================================================================
    # EJERCICIO 6: Relacionar ventas y clientes con $lookup y mostrar 10 resultados
    # ==========================================================================
    print("\n--- EJERCICIO 6: Ventas y clientes con $lookup (10 resultados) ---")
    pipeline_clientes = [
        {
            "$lookup": {
                "from": "clientes",
                "localField": "cliente_id",
                "foreignField": "cliente_id",
                "as": "datos_cliente",
            }
        },
        {"$unwind": {"path": "$datos_cliente", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "_id": 0,
                "venta_id": 1,
                "fecha": 1,
                "nombre_cliente": "$datos_cliente.nombre",
                "total": 1,
            }
        },
        {"$limit": 10},
    ]
    for fila in db.ventas.aggregate(pipeline_clientes):
        print(fila)


def analizar_pandas(db):
    campos = {
        "_id": 0,
        "venta_id": 1,
        "cliente_id": 1,
        "estado": 1,
        "canal": 1,
        "total": 1,
        "fecha": 1,
    }
    df = pd.DataFrame(list(db.ventas.find({}, campos)))
    if df.empty:
        print("No hay ventas para analizar.")
        return

    # Limpieza y conversión de tipos
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce", utc=True)
    df["mes"] = df["fecha"].dt.strftime("%Y-%m")

    # ==========================================================================
    # EJERCICIO 7: DataFrame de ventas con head(), info(), nulos y descriptivos
    # ==========================================================================
    print("\n--- EJERCICIO 7: Exploración del DataFrame de ventas ---")
    print("Primeras 5 filas (head):")
    print(df.head())

    print("\nInformación estructural (info):")
    df.info()

    print("\nConteo de valores nulos por columna:")
    print(df.isna().sum())

    print("\nEstadísticos descriptivos (describe):")
    print(df.describe())

    # ==========================================================================
    # EJERCICIO 8: Número e importe de ventas completadas por canal con Pandas
    # ==========================================================================
    print("\n--- EJERCICIO 8: Ventas completadas por canal (Pandas) ---")
    completadas = df.loc[df["estado"] == "completada"]
    resumen_canal_pd = (
        completadas.groupby("canal", dropna=False)["total"]
        .agg(numero_ventas="count", importe_total="sum", ticket_promedio="mean")
        .reset_index()
        .sort_values(by="importe_total", ascending=False)
    )
    print(resumen_canal_pd.to_string(index=False))

    # ==========================================================================
    # EJERCICIO 9: Obtener importe registrado por mes y exportar un CSV
    # ==========================================================================
    print("\n--- EJERCICIO 9: Importe registrado por mes y exportación CSV ---")
    resumen_mes = (
        df.groupby("mes", dropna=False)["total"]
        .agg(ventas="count", importe_registrado="sum")
        .reset_index()
        .sort_values(by="mes")
    )
    print(resumen_mes.to_string(index=False))
    archivo_mes = "Practica10-importe-mensual.csv"
    resumen_mes.to_csv(archivo_mes, index=False, encoding="utf-8-sig")
    print(f"CSV mensual generado: {archivo_mes}")

    # ==========================================================================
    # EJERCICIO 10: Comparar resultados por canal (MongoDB vs Pandas)
    # ==========================================================================
    print("\n--- EJERCICIO 10: Comparación por canal (MongoDB vs Pandas) ---")
    pipeline_canal_mongo = [
        {"$match": {"estado": "completada"}},
        {
            "$group": {
                "_id": "$canal",
                "numero_ventas": {"$sum": 1},
                "importe_total": {"$sum": "$total"},
                "ticket_promedio": {"$avg": "$total"},
            }
        },
        {"$sort": {"importe_total": -1}},
    ]
    resumen_canal_mongo = pd.DataFrame(list(db.ventas.aggregate(pipeline_canal_mongo)))
    resumen_canal_mongo.rename(columns={"_id": "canal"}, inplace=True)

    print("Resultados desde MongoDB (aggregate):")
    print(resumen_canal_mongo.to_string(index=False))

    comparacion = pd.merge(
        resumen_canal_mongo,
        resumen_canal_pd,
        on="canal",
        how="outer",
        suffixes=("_mongo", "_pandas"),
    )
    comparacion["diferencia_importe"] = (
        comparacion["importe_total_mongo"] - comparacion["importe_total_pandas"]
    ).round(4)
    print("\nTabla comparativa directa:")
    print(comparacion.to_string(index=False))
    print(
        "\nExplicación: Si los datos en MongoDB están limpios (sin nulos ni textos en 'total'), "
        "los resultados coinciden exactamente (diferencia = 0). Pueden surgir ligeras diferencias si:\n"
        "  1) Existen documentos con 'total' no numérico o nulo: MongoDB ignora no numéricos en $sum, "
        "mientras que Pandas con errors='coerce' los convierte a NaN.\n"
        "  2) Existen documentos sin el campo 'canal' (null vs NaN al agrupar).\n"
        "  3) Precisión de punto flotante (Decimal128/int en BSON frente a float64 en Pandas)."
    )

    # ==========================================================================
    # EJERCICIO 11: Análisis adicional (Filtro + Agrupación + Exportación)
    # ==========================================================================
    print("\n--- EJERCICIO 11: Análisis adicional (Ranking VIP de clientes) ---")
    # Filtro: ventas completadas con importe >= 1,000
    filtro_vip = df.loc[(df["estado"] == "completada") & (df["total"] >= 1000)]
    # Agrupación: por cliente_id calculando frecuencia, gasto total y ticket promedio
    ranking_vip = (
        filtro_vip.groupby("cliente_id", dropna=False)["total"]
        .agg(
            compras_calificadas="count",
            gasto_acumulado="sum",
            ticket_promedio="mean",
        )
        .reset_index()
        .sort_values(by="gasto_acumulado", ascending=False)
    )
    print("Top 10 clientes con compras completadas >= $1,000:")
    print(ranking_vip.head(10).to_string(index=False))

    archivo_vip = "Practica10-analisis-clientes-vip.csv"
    ranking_vip.to_csv(archivo_vip, index=False, encoding="utf-8-sig")
    print(f"CSV adicional generado: {archivo_vip}")


def main():
    client = MongoClient(URI, serverSelectionTimeoutMS=5000)
    try:
        # Parte del Ejercicio 1: Verificación de conexión mediante ping
        respuesta_ping = client.admin.command("ping")
        db = client["ventas_online"]
        print(f"Ping exitoso: {respuesta_ping} | Conectado a '{db.name}'")

        explorar(db)
        consultar(db)
        crud_temporal(db)
        agregar(db)
        analizar_pandas(db)
    except PyMongoError as exc:
        print("Error al comunicarse con MongoDB:", exc)
    finally:
        client.close()
        print("\nConexión cerrada.")


if __name__ == "__main__":
    main()