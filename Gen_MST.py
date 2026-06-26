#librerías
import math
import heapq

# Algoritmo de Prim 
# Grafo conexxo y no dirigido
# Construye el MST creciendo desde un vértice inicial.

def Alg_prim(grafo, inicio):
    Conjunto_explorado = set()
    mst_aristas = []     
    peso_total  = 0.0

    
    heap = []
    for adyacente, peso in grafo[inicio]:
        # añadimos aristas del vértice inicial
        heapq.heappush(heap, (peso, inicio, adyacente))  

    Conjunto_explorado.add(inicio)

    # parte iterativa
    # poppear la arista de menor peso
    while heap:
        peso, origen, vertice = heapq.heappop(heap)

        # asegurarse de no formar ciclos
        if vertice in Conjunto_explorado:
            continue

        # append el vértice nuevo al árbol
        Conjunto_explorado.add(vertice)
        mst_aristas.append((peso, origen, vertice))
        peso_total += peso

        # exploramos las aristas del nuevo vértice incorporado
        for adyacente, p in grafo[vertice]:
            if adyacente not in Conjunto_explorado:
                heapq.heappush(heap, (p, vertice, adyacente))

    return peso_total, mst_aristas


# Construir árbol mst

def construir_arbol(mst_aristas):
    arbol = {}

    for peso, origen, destino in mst_aristas:
        # inicializamos la lista de adyacencia si el vértice no existe aún
        if origen not in arbol:
            arbol[origen] = []
        if destino not in arbol:
            arbol[destino] = []

        # añadimos la arista en ambas direcciones (árbol no dirigido)
        arbol[origen].append((destino, peso))
        arbol[destino].append((origen, peso))

    return arbol


