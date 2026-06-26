#librerías 
import math
import heapq 


# definimso el algoritmo de Dijkstra como una función que toma un grafo, un vertice fuente y un vertice destino como argumentos. 
# el grafo se representa como un diccionario  de listas de tuplas donde los argumentos son vertice inicio y destino 

#La función devuelve la distancia más corta desde el vertice inicio al vertice destino.
def dijkstra(grafo, inicio, fin):
    distancia = {}
    padres = {}  
    # condiciones inicales
    for key, d in grafo.items():
        distancia[key] = math.inf
        padres[key] = None

    distancia[inicio] = 0
    Conjunto_explorado = set()

    # generar el heap con el vertice inicio y su distancia inicial (0)
    heap = []
    heapq.heappush(heap, (0, inicio)) #Introducimos la distancia y el vertice en el heap, con funcion PUSH


    # parte iterativa
    # mientras el heap no esté vacío, se extrae el vertice con la distancia más corta utilizando la función POP
    while heap :
        d, vertice = heapq.heappop(heap)
        if vertice in Conjunto_explorado:
            continue
        
        
        Conjunto_explorado.add(vertice)
        #Añadimos un break, para terminar el bucle while cuando se llegaa destino, 
        if vertice == fin:
            break

        # comprobamos distancia con vertices adyacentes al vertice actual 
        for adyacente, peso in grafo[vertice]:
            if adyacente in Conjunto_explorado:
                continue

            #actualizamos su distancia si se encuentra una ruta más corta a través del vertice actual.    
            if distancia[vertice] + peso < distancia[adyacente]:
                distancia[adyacente] = distancia[vertice] + peso
                padres[adyacente] = vertice
                heapq.heappush(heap, (distancia[adyacente],adyacente))

    
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