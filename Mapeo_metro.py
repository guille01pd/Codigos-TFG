import heapq
import math
from typing import Dict, Hashable, Tuple, List, Optional

Nodo = Hashable
Grafo = Dict[Nodo, Dict[Nodo, float]]

def dijkstra(grafo: Grafo, origen: Nodo) -> Tuple[Dict[Nodo, float], Dict[Nodo, Optional[Nodo]]]:
    """
    grafo: {u: {v: peso, ...}, ...}  (pesos no negativos)
    retorna:
      - dist: distancia mínima desde 'origen' a cada nodo
      - prev: predecesor para reconstruir el camino
    """
    dist: Dict[Nodo, float] = {n: math.inf for n in grafo}
    prev: Dict[Nodo, Optional[Nodo]] = {n: None for n in grafo}
    dist[origen] = 0.0

    pq: List[Tuple[float, Nodo]] = [(0.0, origen)]  # (distancia, nodo)

    while pq:
        d_u, u = heapq.heappop(pq)
        if d_u != dist[u]:
            continue  # entrada vieja en la cola

        for v, w in grafo[u].items():
            if w < 0:
                raise ValueError("Dijkstra requiere pesos no negativos.")
            nd = d_u + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    return dist, prev

def reconstruir_camino(prev: Dict[Nodo, Optional[Nodo]], origen: Nodo, destino: Nodo) -> List[Nodo]:
    if origen == destino:
        return [origen]
    camino: List[Nodo] = []
    cur: Optional[Nodo] = destino
    while cur is not None:
        camino.append(cur)
        if cur == origen:
            break
        cur = prev.get(cur)
    if camino[-1] != origen:
        return []  # no hay camino
    camino.reverse()
    return camino


if __name__ == "__main__":
    grafo = {
        "A": {"B": 1, "C": 4},
        "B": {"C": 2, "D": 5},
        "C": {"D": 1},
        "D": {},
    }

    dist, prev = dijkstra(grafo, "A")
    print("Distancias:", dist)
    print("Camino A->D:", reconstruir_camino(prev, "A", "D"))


#Ejemplo de uso:#

grafo = {
"A": {"B": 7, "C": 9, "F": 14},
"B": {"A": 7, "C": 10, "D": 15},
"C": {"A": 9, "B": 10, "D": 11, "F": 2},
"D": {"B": 15, "C": 11, "E": 6},
"E": {"D": 6, "F": 9},
"F": {"A": 14, "C": 2, "E": 9},
}

dist, prev = dijkstra(grafo, "A")
print(dist)
print(reconstruir_camino(prev, "A", "E"))