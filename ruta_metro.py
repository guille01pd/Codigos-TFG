import importlib.machinery
import importlib.util
from pathlib import Path

CODIGOS = Path(__file__).parent


def _cargar_modulo(nombre, archivo):
    ruta = str(CODIGOS / archivo)
    loader = importlib.machinery.SourceFileLoader(nombre, ruta)
    spec = importlib.util.spec_from_loader(nombre, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


metro_mod    = _cargar_modulo('metro',    'Metro_mad.py')
dijkstra_mod = _cargar_modulo('dijkstra', 'Algoritmo de Dijkstra heap.py')


def estaciones_de_linea(linea, grafo, id_to_name):
    nodos = [(k, id_to_name.get(k, '?')) for k in grafo if k.startswith(f'{linea}_')]
    return sorted(nodos, key=lambda x: int(x[0].split('_')[1]))


def seleccionar_estacion(etiqueta, grafo, id_to_name):
    while True:
        linea = input(f"\nLínea de {etiqueta}: ").strip()
        estaciones = estaciones_de_linea(linea, grafo, id_to_name)
        if not estaciones:
            print(f"  No se encontró la línea '{linea}'. Inténtalo de nuevo.")
            continue

        print(f"  Estaciones de la línea {linea}:")
        for i, (id_, nombre) in enumerate(estaciones):
            print(f"    [{i}] {nombre} ")

        try:
            sel = int(input("  Selecciona el número: "))
            if 0 <= sel < len(estaciones):
                return estaciones[sel][0]
        except ValueError:
            pass
        print("  Selección no válida.")


if __name__ == '__main__':
    print("Cargando grafo del Metro de Madrid...")
    resultado = metro_mod.generar_grafo_metro_madrid()
    if resultado is None:
        exit(1)

    grafo, id_to_name, name_to_ids, *_ = resultado
    print(f"Grafo listo: {len(grafo)} nodos.\n")

    origen  = seleccionar_estacion('ORIGEN',  grafo, id_to_name)
    destino = seleccionar_estacion('DESTINO', grafo, id_to_name)

    nombre_orig = id_to_name.get(origen,  origen)
    nombre_dest = id_to_name.get(destino, destino)
    print(f"\nCalculando ruta: {nombre_orig} → {nombre_dest} ...")

    distancia, camino = dijkstra_mod.dijkstra(grafo, origen, destino)

    print()
    if distancia == float('inf'):
        print("No existe ruta entre las estaciones seleccionadas.")
    else:
        print(f"Distancia total: {distancia:.0f} m  ({distancia / 1000:.2f} km)")
        print(f"\nRuta ({len(camino)} paradas):")
        for i, nodo in enumerate(camino):
            nombre = id_to_name.get(nodo, nodo)
            linea  = nodo.split('_')[0]
            prefijo = "  └─>" if i > 0 else "  ●  "
            print(f"{prefijo} [{linea}] {nombre} ")


