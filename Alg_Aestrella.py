#librerías
import math
import heapq


# definimos el algoritmo A* como una función que toma un grafo, un vértice fuente, un vértice destino
# y las coordenadas de los vértices como argumentos.
# el grafo se representa como un diccionario de listas de tuplas donde los argumentos son vértice inicio y destino.

# La función devuelve la distancia más corta desde el vértice inicio al vértice destino.
def Aestrella(grafo, inicio, fin, coordenadas):
    distancia = {}
    padres = {}
    # condiciones iniciales
    for key, d in grafo.items():
        distancia[key] = math.inf
        padres[key] = None

    distancia[inicio] = 0
    Conjunto_explorado = set()

    # heurística: distancia euclídea entre el vértice n y el vértice destino
    def heuristica(n):
        x1, y1 = coordenadas[n]
        x2, y2 = coordenadas[fin]
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    # generar el heap con el vértice inicio y su f(inicio) = g(inicio) + h(inicio)
    heap = []
    heapq.heappush(heap, (heuristica(inicio), inicio))  # Introducimos f y el vértice en el heap


    # parte iterativa
    # mientras el heap no esté vacío, se extrae el vértice con menor f = g + h utilizando la función POP
    while heap:
        f, vertice = heapq.heappop(heap)
        if vertice in Conjunto_explorado:
            continue

        Conjunto_explorado.add(vertice)
        # Añadimos un break, para terminar el bucle while cuando se llega a destino,
        if vertice == fin:
            break

        # comprobamos distancia con vértices adyacentes al vértice actual
        for adyacente, peso in grafo[vertice]:
            if adyacente in Conjunto_explorado:
                continue

            # actualizamos su distancia si se encuentra una ruta más corta a través del vértice actual.
            nueva_g = distancia[vertice] + peso
            if nueva_g < distancia[adyacente]:
                distancia[adyacente] = nueva_g
                padres[adyacente] = vertice
                f_nuevo = nueva_g + heuristica(adyacente)  # f = g + h(distancia euclídea al destino)
                heapq.heappush(heap, (f_nuevo, adyacente))


    # reconstruimos el camino desde el final
    camino = []
    nodo_actual = fin

    # si la distancia sigue siendo infinito, no existe camino
    if distancia[fin] == math.inf:
        return math.inf, ["No existe camino entre {} y {}".format(inicio, fin)]

    # camino
    while nodo_actual is not None:
        camino.append(nodo_actual)
        nodo_actual = padres[nodo_actual]

    camino.reverse()  # Le damos la vuelta para que vaya de 'inicio' a 'fin'

    return distancia[fin], camino
