import numpy as np
import pandas as pd


def calcular_distancia_haversine(p1, p2):
    """
    Calcula la distancia real en metros entre dos coordenadas (lat, lon)
    utilizando la fórmula del Haversine (geometría esférica).
    """
    R = 6371000
    lat1, lon1 = np.radians(p1[0]), np.radians(p1[1])
    lat2, lon2 = np.radians(p2[0]), np.radians(p2[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    return float(np.round(R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)), 2))


def _haversine_vec(lat1, lon1, lat2, lon2):
    """Versión vectorizada de Haversine para arrays numpy."""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    return np.round(R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)), 2)


def generar_grafo_metro_madrid():
    # -------------------------------------------------------------------------
    # 1. LEER ARCHIVOS GTFS
    # -------------------------------------------------------------------------
    try:
        DATA = r'C:\Users\Guillermo\Desktop\universidad\5º curso\TFG\datos_metro'
        routes     = pd.read_csv(f'{DATA}/routes.txt',     encoding='utf-8-sig', usecols=['route_id', 'route_short_name'])
        trips      = pd.read_csv(f'{DATA}/trips.txt',      encoding='utf-8-sig', usecols=['trip_id', 'route_id'])
        stops      = pd.read_csv(f'{DATA}/stops.txt',      encoding='utf-8-sig', usecols=['stop_id', 'stop_name', 'stop_lat', 'stop_lon'])
        stop_times = pd.read_csv(f'{DATA}/stop_times.txt', encoding='utf-8-sig', usecols=['trip_id', 'stop_id', 'stop_sequence'])
    except FileNotFoundError as e:
        print(f"Error: No se encontró '{e.filename}'.")
        return None

    # -------------------------------------------------------------------------
    # 2. CONSTRUIR MAPEO trip -> línea
    # -------------------------------------------------------------------------
    trip_line = (trips.merge(routes, on='route_id')
                      .rename(columns={'route_short_name': 'linea'})
                      [['trip_id', 'linea']])

    # -------------------------------------------------------------------------
    # 3. FILTRAR ANDENES VÁLIDOS (stops.txt)
    # -------------------------------------------------------------------------
    stops = stops[
        stops['stop_id'].str.startswith('par_') &
        stops['stop_lat'].notna() &
        stops['stop_lon'].notna()
    ].copy()
    stops['stop_name'] = stops['stop_name'].str.strip().str.upper()

    # -------------------------------------------------------------------------
    # 4. COMBINAR stop_times CON LÍNEA Y ORDENAR SECUENCIAS
    # -------------------------------------------------------------------------
    st = (stop_times[stop_times['stop_id'].isin(stops['stop_id'])]
                    .merge(trip_line, on='trip_id')
                    .sort_values(['trip_id', 'stop_sequence']))

    # Conexiones entre andenes consecutivos usando shift dentro de cada viaje
    st = st.assign(stop_id_next=st.groupby('trip_id')['stop_id'].shift(-1))
    conexiones = (st.dropna(subset=['stop_id_next'])
                    [['stop_id', 'stop_id_next']]
                    .drop_duplicates())

    # -------------------------------------------------------------------------
    # 5. CREAR MAPEO AL NUEVO ID: linea_indice (ej: '1_1')
    # -------------------------------------------------------------------------
    min_seq = (st.groupby(['linea', 'stop_id'])['stop_sequence']
                 .min()
                 .reset_index()
                 .sort_values(['linea', 'stop_sequence']))
    min_seq['idx']    = min_seq.groupby('linea').cumcount() + 1
    min_seq['new_id'] = min_seq['linea'] + '_' + min_seq['idx'].astype(str)
    id_map = min_seq.set_index('stop_id')['new_id']

    # -------------------------------------------------------------------------
    # 6. ARISTAS DE TRAYECTO CON HAVERSINE VECTORIZADO
    # -------------------------------------------------------------------------
    coords = stops.set_index('stop_id')[['stop_lat', 'stop_lon']]

    aristas = (conexiones[conexiones['stop_id'].isin(id_map.index) &
                           conexiones['stop_id_next'].isin(id_map.index)]
               .copy()
               .assign(new_orig=lambda df: df['stop_id'].map(id_map),
                       new_dest=lambda df: df['stop_id_next'].map(id_map))
               .merge(coords.add_suffix('_orig'), left_on='stop_id',      right_index=True)
               .merge(coords.add_suffix('_dest'), left_on='stop_id_next', right_index=True))

    aristas['dist'] = _haversine_vec(
        aristas['stop_lat_orig'].values, aristas['stop_lon_orig'].values,
        aristas['stop_lat_dest'].values, aristas['stop_lon_dest'].values,
    )

    grafo = {
        orig: list(zip(g['new_dest'], g['dist']))
        for orig, g in aristas.groupby('new_orig')[['new_dest', 'dist']]
    }

    # -------------------------------------------------------------------------
    # 7. ARISTAS DE TRANSBORDO (misma estación física, peso = 0.0)
    # Se usa proximidad geográfica (< UMBRAL metros) en lugar de nombre exacto,
    # porque en el GTFS los andenes de distintas líneas pueden tener nombres distintos.
    # -------------------------------------------------------------------------
    UMBRAL_TRANSBORDO = 200  # metros

    andenes_validos_trans = (stops[stops['stop_id'].isin(id_map.index)]
                             .assign(new_id=lambda df: df['stop_id'].map(id_map))
                             [['new_id', 'stop_lat', 'stop_lon']]
                             .reset_index(drop=True))

    ids   = andenes_validos_trans['new_id'].values
    lats  = andenes_validos_trans['stop_lat'].values
    lons  = andenes_validos_trans['stop_lon'].values

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            linea_i = ids[i].split('_')[0]
            linea_j = ids[j].split('_')[0]
            if linea_i == linea_j:
                continue  # mismo andén o misma línea, no es transbordo
            dist = calcular_distancia_haversine(
                (lats[i], lons[i]), (lats[j], lons[j])
            )
            if dist < UMBRAL_TRANSBORDO:
                grafo.setdefault(ids[i], []).append((ids[j], 0.0))
                grafo.setdefault(ids[j], []).append((ids[i], 0.0))

    # Mapeos nombre <-> id para consultas por nombre de estación
    andenes_validos = stops[stops['stop_id'].isin(id_map.index)].copy()
    andenes_validos['new_id'] = andenes_validos['stop_id'].map(id_map)

    id_to_name  = andenes_validos.set_index('new_id')['stop_name'].to_dict()
    name_to_ids = (andenes_validos.groupby('stop_name')['new_id']
                                  .apply(list)
                                  .to_dict())

    node_coords = {nid: (float(lat), float(lon))
                   for nid, lat, lon in zip(ids, lats, lons)}

    return grafo, id_to_name, name_to_ids, node_coords

#A partir de aquí se muestra el resultado de la función anterior, no es necesario
# EJECUCIÓN Y MUESTRA DEL RESULTADO
# -------------------------------------------------------------------------
if __name__ == "__main__":
    resultado = generar_grafo_metro_madrid()
    if resultado is None:
        exit(1)

    grafo_metro, id_to_name, name_to_ids, node_coords = resultado
    print("=" * 60)
    print(f"Grafo generado exitosamente con {len(grafo_metro)} nodos.")
    print("=" * 60)

    nodos_ejemplo = sorted(grafo_metro.keys())[:4]
    print("\nMuestra de la estructura del diccionario de tuplas:")
    for nodo in nodos_ejemplo:
        print(f"\nClave: '{nodo}'  [{id_to_name.get(nodo, '?')}]")
        print("Lista de destinos y pesos (en metros):")
        for destino, peso in grafo_metro[nodo]:
            tipo = "Transbordo" if peso == 0.0 else "Trayecto"
            print(f"  └─> '{destino}' [{id_to_name.get(destino, '?')}] | {peso} m ({tipo})")


