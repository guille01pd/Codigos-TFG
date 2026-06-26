#Codigo para etraer datos de metro madrid, y expresarlos mediante un grafo

#primero importy datos

#librerias
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import heapq as hq
import math


#cargar datos de metro madrid, solo los que voy a usar,

vertices = pd.read_csv(r"C:\Users\Guillermo\Desktop\universidad\5º curso\TFG\Claude\metro_madrid_nodes.csv")
aristas = pd.read_csv(r"C:\Users\Guillermo\Desktop\universidad\5º curso\TFG\Claude\metro_madrid_edges.csv")

#Genero los cruces entre las tablas, para quedarme sol con los datos que me interesan.




#Genero el grafo, siguiendo un diccionario de listas de tuplas, donde cada tupla contiene el vertice ady, y el peso de la arista


#Printeo ciertas variables para comprobar que el grafo se ha generado correctamente, y que los datos se han cargado bien.
print("Número de nodos:", G.number_of_nodes())
print("Número de aristas:", G.number_of_edges())


#Aplico el script que he creado para la función de Dijkstra con heapq
dijkstra_heap = lambda grafo, inicio, fin: dijkstra(grafo, inicio, fin)