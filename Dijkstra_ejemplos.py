##Dijkstra con ejemplos


#librerías 
import math
import heapq 
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



dijkstra_mod = _cargar_modulo('dijkstra', 'Algoritmo de Dijkstra heap.py')
# definimso el algoritmo de Dijkstra como una función que toma un grafo, un vertice fuente y un vertice destino como argumentos. 
# el grafo se representa como un diccionario  de listas de tuplas donde los argumentos son vertice inicio y destino 

# ejemplo con grafo dirigido

# grafo
grafo_dirigido = {
    'A': [('B', 4), ('C', 2)],   
    'B': [('D', 5)],             
    'C': [('B', 1), ('E', 6)],   
    'D': [('F', 3), ('G', 7)],   
    'E': [('D', 2), ('H', 4)],   
    'F': [('I', 2)],             
    'G': [('F', 1), ('J', 5)],   
    'H': [('G', 1), ('I', 6)],   
    'I': [('J', 3)],             
    'J': []                      
}


dis_min_dir, camino = dijkstra(grafo_dirigido, 'A', 'J')
print("Distancia mínima en grafo dirigido de A a J:", dis_min_dir)
print(f"Ruta exacta a seguir: {' -> '.join(camino)}")

# ejemplo con grafo no dirigido

# grafo NO dirigido con 10 vértices
grafo_no_dirigido = {
    'A': [('B', 4), ('C', 2)],
    'B': [('A', 4), ('D', 5), ('C', 1)], 
    'C': [('A', 2), ('B', 1), ('E', 6)], 
    'D': [('B', 5), ('F', 3), ('G', 7), ('E', 2)], 
    'E': [('C', 6), ('D', 2), ('H', 4)],
    'F': [('D', 3), ('I', 2), ('G', 1)], 
    'G': [('D', 7), ('F', 1), ('J', 5), ('H', 1)], 
    'H': [('E', 4), ('G', 1), ('I', 6)], 
    'I': [('F', 2), ('J', 3), ('H', 6)],
    'J': [('G', 5), ('I', 3)] 
}

dis_min_no_dir, camino = dijkstra(grafo_no_dirigido, 'A', 'J')
print("Distancia mínima en grafo no dirigido de A a J:", dis_min_no_dir)
print(f"Ruta exacta a seguir: {' -> '.join(camino)}")




# parte aleartoria
import random
random.seed(123) 


def generar_grafo_dirigido(num_vertices, min_aristas, max_aristas):
    V = [f'V{i}' for i in range(num_vertices)]
    W = {nodo: [] for nodo in V}

    for nodo in V:
        num_aristas = random.randint(min_aristas, max_aristas)
        posibles_destinos = [n for n in V if n != nodo]
        destinos_elegidos = random.sample(posibles_destinos, min(num_aristas, len(posibles_destinos)))
        
        for destino in destinos_elegidos:
            peso = random.randint(2, 20)
            W[nodo].append((destino, peso))
    
    return V, W

def generar_grafo_no_dirigido(num_vertices, min_aristas, max_aristas):
    V = [f'V{i}' for i in range(num_vertices)]
    W = {nodo: [] for nodo in V}

    for nodo in V:
        actuales = len(W[nodo])
        if actuales >= max_aristas:
            continue
            
        num_aristas = random.randint(min_aristas, max_aristas) - actuales
        if num_aristas <= 0:
            continue

        posibles_destinos = [n for n in V if n != nodo and not any(d == n for d, _ in W[nodo])]
        destinos_elegidos = random.sample(posibles_destinos, min(num_aristas, len(posibles_destinos)))
        
        for destino in destinos_elegidos:
            if len(W[destino]) < max_aristas:
                peso = random.randint(1, 10)
                W[nodo].append((destino, peso))
                W[destino].append((nodo, peso))
    
    return V, W


#ejemplos

V, W = generar_grafo_dirigido(100, 4, 10)
origen, destino = random.sample(V, 2)

dis_min_dir, camino = dijkstra(W, origen, destino)
print("Distancia mínima en grafo dirigido de {} a {}: {}".format(origen, destino, dis_min_dir))
print(f"Ruta exacta a seguir: {' -> '.join(camino)}")



V, W = generar_grafo_no_dirigido(100, 4, 10)
origen, destino = random.sample(V, 2)

dis_min_no_dir, camino = dijkstra(W, origen, destino)
print("Distancia mínima en grafo no dirigido de {} a {}: {}".format(origen, destino, dis_min_no_dir))