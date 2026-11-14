from datetime import datetime, timedelta, timezone
from time import perf_counter
import random
from faker import Faker
from pymongo import MongoClient
from pymongo.errors import PyMongoError

URI = 'mongodb://localhost:27017/'
BD = 'ventas_online'
COLECCION = 'ventas_escalabilidad'
LOTE = 2000
META = 500000  # 10000, 100000, 250000, 500000 o 1000000
fake = Faker('es_MX')


def crear_venta(numero):
    semilla = 2026 + numero
    rng = random.Random(semilla)
    fake.seed_instance(semilla)
    cantidad = rng.randint(1, 5)
    precio = round(rng.uniform(80, 9000), 2)
    return {
        'venta_id': f'SIM{numero:08d}',
        'cliente_id': f'C{rng.randint(1, 50):03d}',
        'fecha': datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=rng.randint(0, 1000)),
        'estado': rng.choice(['completada', 'pendiente', 'cancelada']),
        'canal': rng.choice(['online', 'tienda', 'app']),
        'total': round(cantidad * precio, 2),
        'items': [{'sku': f'P{rng.randint(1, 50):03d}', 'cantidad': cantidad, 'precio': precio}],
        'region': rng.choice(['Norte', 'Centro', 'Sur']),
        'referencia': fake.bothify(text='REF-####-????'),
        'origen': 'practica11',
    }


def cargar_hasta(coleccion, meta):
    if coleccion.count_documents({'origen': {'$ne': 'practica11'}}, limit=1):
        raise ValueError('Hay documentos ajenos a la practica en la coleccion.')
    actual = coleccion.count_documents({})
    ultimo = coleccion.find_one({}, {'venta_id': 1, '_id': 0}, sort=[('venta_id', -1)])
    ultimo_numero = int(ultimo['venta_id'][3:]) if ultimo else 0
    if actual != ultimo_numero:
        raise ValueError('La secuencia no es continua; revise los datos antes de continuar.')
    if actual > meta:
        raise ValueError('La coleccion ya supera la meta solicitada.')
    inicio = perf_counter()
    for primero in range(actual + 1, meta + 1, LOTE):
        ultimo_lote = min(primero + LOTE - 1, meta)
        documentos = [crear_venta(i) for i in range(primero, ultimo_lote + 1)]
        coleccion.insert_many(documentos, ordered=True)
        print(f'Cargados: {ultimo_lote:,} / {meta:,}')
    return perf_counter() - inicio


def comparar_inserciones(db):
    col = db['ventas_prueba_insercion']
    if col.count_documents({}) > 0:
        raise ValueError('La coleccion auxiliar no esta vacia; revise antes de continuar.')
    cantidad = 2000
    documentos = [crear_venta(i) for i in range(1, cantidad + 1)]
    try:
        inicio = perf_counter()
        for documento in documentos:
            col.insert_one(documento.copy())
        individual = perf_counter() - inicio
        col.delete_many({})
        inicio = perf_counter()
        col.insert_many([{k: v for k, v in d.items() if k != '_id'} for d in documentos], ordered=True)
        lotes = perf_counter() - inicio
        print(f'Individual: {individual:.3f} s | insert_many: {lotes:.3f} s')
        print('Documentos comparados:', col.count_documents({}))
    finally:
        col.delete_many({})


def main():
    with MongoClient(URI, serverSelectionTimeoutMS=5000) as cliente:
        cliente.admin.command('ping')
        col = cliente[BD][COLECCION]
        print('Registros iniciales:', col.count_documents({}))
        segundos = cargar_hasta(col, META)
        print('Registros finales:', col.count_documents({}))
        print('Tiempo de carga:', round(segundos, 3), 's')
        # Comparacion opcional, ejecutar solo cuando se indique:
        # comparar_inserciones(cliente[BD])


if __name__ == '__main__':
    try:
        main()
    except (PyMongoError, ValueError) as exc:
        print('Error:', exc)
        raise SystemExit(1)
