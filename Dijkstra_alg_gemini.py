
"""
Algoritmo de Dijkstra.

Parámetros:
V : conjunto de nodos
W : diccionario de diccionarios representando el valor y dirección de las aristas que unen los vértices en V. 
s : vértice de origen.
"""

def dijkstra(V, W, s):
 
    
    # Definimos los diccionarios y el conjunto de vértices no visitados
    distancias = {}      # Diccionario de distancia 
    predecesores = {}     # Diccionario de predecesores 
    Q = set(V)  # Conjunto Q de vértices no visitados
    infinito = float('inf') 

    #Damos valor infinito a todos los nodos y 0 al nodo origen
    for v in V: 
        distancias[v] = infinito
        predecesores[v] = None
        
    distancias[s] = 0
    predecesores[s] = s

    # Iniciamos el bucle principal del algoritmo
    while len(Q) > 0:
        #Extraemos el nodo u en el conjunto de nodos no visitados Q que se encuentre a la mínima distancia del conjunto de nodos visitados
        u = min(Q, key= lambda nodo: distancias[nodo])
        
        # Si la distancia mínima es infinito, los nodos restantes son inalcanzables, y por tanto podemos terminar el algoritmo
        if distancias[u] == infinito:
            break 
            
        # Eliminamos u del conjunto de nodos no visitados
        Q.remove(u)
        
        # Proceso de relajación: actualizamos las distancias de los nodos vecinos
        # Iteramos sobre los nodos v vecinos del nodo u
        if u in W:
            for v, arista_uv in W[u].items():
                if v in Q: # Solo consideramos aristas hacia nodos no visitados
                    alt = distancias[u] + arista_uv
                    if alt < distancias[v]: # Si la distancia alternativa es menor que la distancia actual, actualizamos la distancia y el predecesor
                        distancias[v] = alt
                        predecesores[v] = u # Actualizamos el predecesor de v
                        
    return distancias, predecesores 


# Función para reconstruir el camino mínimo desde el nodo origen hasta el nodo destino
def reconstruir_camino(predecesores, origen, destino):
    if origen == destino:
        return [origen]

    camino = []
    actual = destino
    while actual is not None:
        camino.append(actual)
        actual = predecesores.get(actual)

    if camino[-1] != origen:
        return []

    camino.reverse()
    return camino

#Funcion para calcular el valor del camino mínimo desde el nodo origen hasta el nodo destino
def calcular_valor_camino(camino):
    valor = 0
    for i in range(len(camino) - 1):
        valor += W[camino[i]][camino[i + 1]]
    return valor



# Ejemplo
# Grafo con 5 nodos y 5 aristas
# Definición del conjunto de nodos V
V = {'A', 'B', 'C', 'D', 'E'}

# Definición de las aristas y sus pesos w(u, v)
W = {
    'A': {'B': 10, 'C': 3},
    'B': {'C': 1, 'D': 2},
    'C': {'B': 4, 'D': 8, 'E': 2},
    'D': {'E': 7},
    'E': {'D': 9}
}

origen = 'A' 
destino = 'E'   

distancias, predecesores = dijkstra(V, W, origen)
camino = reconstruir_camino(predecesores, origen, destino)
valor = calcular_valor_camino(camino)

print(f"Camino mínimo desde {origen} a {destino}: {' -> '.join(camino)} con valor {valor}")



#Ejemplo 2, mayor complejidad;
# Grafo con 50 nodos y 100 aristas

import random
def generar_grafo(num_vertices,min_aristas,max_aristas):
    # Generamos una lista de nodos 
    V = [f'V{i}' for i in range(num_vertices)]

    # Grafo vacío
    W = {nodo: {} for nodo in V}

    for nodo in V:
        
        num_aristas = random.randint(min_aristas, max_aristas)
        
        # Filtrar los posibles destinos (no puede tener bucles)
        posibles_destinos = [n for n in V if n != nodo]
        
        # Elegir los destinos al azar sin que se repitan
        destinos_elegidos = random.sample(posibles_destinos, num_aristas)
        
        # Asignar las aristas con un peso aleatorio entre 1 y 10
        for destino in destinos_elegidos:
            peso = random.randint(1, 10)
            W[nodo][destino] = peso
    
    return V, W


#Generamos un grafo aleatorio con 100 nodos y elegimos dos nodos al azar como origen y destino
V, W = generar_grafo(100, 4, 10)
origen, destino = random.sample(V, 2)

        

distancias, predecesores = dijkstra(V, W, origen)
camino = reconstruir_camino(predecesores, origen, destino)


print(f"Camino mínimo desde {origen} a {destino}: {' -> '.join(camino)} con valor {distancias[destino]}")