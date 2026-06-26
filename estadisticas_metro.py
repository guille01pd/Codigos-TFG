import importlib.machinery, importlib.util
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams

CODIGOS = Path(__file__).parent
SALIDA  = Path(r'C:\Users\Guillermo\Desktop\universidad\5º curso\TFG\imagenes')

COLORES_LINEA = {
    '1' : '#00AAFF', '2' : '#E52320', '3' : '#FFD700',
    '4' : '#924B35', '5' : '#96BE0C', '6' : '#9B9EA1',
    '7' : '#F89A1B', '8' : '#F368A5', '9' : '#8B37A5',
    '10': '#174FA2', '11': '#00A650', '12': '#A39830',
    'R' : '#0066CC',
}
BG   = '#F4F6F9'
BG_AX = '#FAFBFC'
FG   = '#1A1A2E'


def _cargar_modulo(nombre, archivo):
    ruta = str(CODIGOS / archivo)
    loader = importlib.machinery.SourceFileLoader(nombre, ruta)
    spec = importlib.util.spec_from_loader(nombre, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


metro_mod = _cargar_modulo('metro', 'Metro_mad.py')


# =============================================================================
# CÁLCULO
# =============================================================================

def calcular_estadisticas(grafo, id_to_name):
    linea_nodos     = defaultdict(set)
    linea_dists     = defaultdict(list)
    linea_trans_ids = defaultdict(set)
    linea_trans_con = defaultdict(set)
    nodo_trans_cnt  = defaultdict(int)

    for nodo, vecinos in grafo.items():
        linea = nodo.split('_')[0]
        linea_nodos[linea].add(nodo)
        for dest, peso in vecinos:
            if peso > 0.0:
                linea_dists[linea].append(float(peso))
            else:
                linea_trans_ids[linea].add(nodo)
                linea_trans_con[linea].add(dest.split('_')[0])
                nodo_trans_cnt[nodo] += 1

    filas = []
    for linea in sorted(linea_nodos.keys(), key=lambda x: (len(x), x)):
        dists = linea_dists[linea]
        filas.append({
            'Línea'            : linea,
            'Paradas'          : len(linea_nodos[linea]),
            'Longitud (km)'    : round(sum(dists) / 2 / 1000, 2),
            'Media (m)'        : round(float(np.mean(dists)) if dists else 0, 1),
            'Std (m)'          : round(float(np.std(dists))  if dists else 0, 1),
            'Mín (m)'          : round(float(min(dists))     if dists else 0, 1),
            'Máx (m)'          : round(float(max(dists))     if dists else 0, 1),
            'Est. transbordo'  : len(linea_trans_ids[linea]),
            'Líneas conectadas': len(linea_trans_con[linea]),
        })

    df = pd.DataFrame(filas)
    todas_dists = np.array([p for vs in grafo.values() for _, p in vs if p > 0]) / 2
    return df, nodo_trans_cnt, todas_dists


# =============================================================================
# UTILIDADES DE DIBUJO
# =============================================================================

def _estilo_base():
    rcParams['font.family'] = 'DejaVu Sans'


def _guardar(fig, nombre):
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / nombre
    fig.savefig(ruta, dpi=200, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"  Guardada: {ruta.name}")


def _hbar_fig(valores, etiq, colores, titulo, xlabel, nombre_archivo):
    """Figura independiente de barras horizontales."""
    alto = max(4, len(etiq) * 0.5 + 1.2)
    fig, ax = plt.subplots(figsize=(9, alto), facecolor=BG)
    y_pos = range(len(etiq))
    bars = ax.barh(y_pos, valores, color=colores, edgecolor='white',
                   linewidth=0.6, height=0.65)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(etiq, fontsize=10)
    ax.set_title(titulo, fontweight='bold', fontsize=13, pad=8, color=FG)
    ax.set_xlabel(xlabel, fontsize=10, color='#444')
    ax.invert_yaxis()
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_facecolor(BG_AX)
    ax.tick_params(axis='x', labelsize=9)
    margen = max(valores) * 0.13 if max(valores) > 0 else 1
    for bar, val in zip(bars, valores):
        ax.text(bar.get_width() + margen * 0.1,
                bar.get_y() + bar.get_height() / 2,
                str(val), va='center', fontsize=9, color='#333')
    ax.set_xlim(0, max(valores) + margen)
    fig.tight_layout()
    _guardar(fig, nombre_archivo)


# =============================================================================
# 7 GRÁFICAS INDIVIDUALES
# =============================================================================

def guardar_informe(grafo, id_to_name):
    _estilo_base()
    df, nodo_trans_cnt, todas_dists = calcular_estadisticas(grafo, id_to_name)

    lineas  = df['Línea'].tolist()
    colores = [COLORES_LINEA.get(l, '#888888') for l in lineas]
    etiq    = [f"L{l}" for l in lineas]

    # ------------------------------------------------------------------
    # 1. Paradas por línea
    # ------------------------------------------------------------------
    _hbar_fig(df['Paradas'].tolist(), etiq, colores,
              'Número de paradas por línea', 'Paradas',
              '01_paradas_por_linea.png')

    # ------------------------------------------------------------------
    # 2. Longitud total por línea
    # ------------------------------------------------------------------
    _hbar_fig(df['Longitud (km)'].tolist(), etiq, colores,
              'Longitud total por línea', 'km',
              '02_longitud_por_linea.png')

    # ------------------------------------------------------------------
    # 3. Distancia media entre paradas
    # ------------------------------------------------------------------
    _hbar_fig(df['Media (m)'].tolist(), etiq, colores,
              'Distancia media entre paradas consecutivas', 'm',
              '03_distancia_media.png')

    # ------------------------------------------------------------------
    # 4. Estaciones con transbordo por línea
    # ------------------------------------------------------------------
    _hbar_fig(df['Est. transbordo'].tolist(), etiq, colores,
              'Estaciones con transbordo por línea', 'Número',
              '04_estaciones_transbordo.png')

    # ------------------------------------------------------------------
    # 5. Líneas distintas a las que conecta cada línea
    # ------------------------------------------------------------------
    _hbar_fig(df['Líneas conectadas'].tolist(), etiq, colores,
              'Líneas distintas conectadas vía transbordo', 'Líneas',
              '05_lineas_conectadas.png')

    # ------------------------------------------------------------------
    # 6. Histograma de distancias entre paradas consecutivas
    # ------------------------------------------------------------------
    fig6, ax6 = plt.subplots(figsize=(9, 5), facecolor=BG)
    if len(todas_dists) > 0:
        _, bins, patches = ax6.hist(todas_dists, bins=25,
                                    edgecolor='white', linewidth=0.5)
        for patch, left in zip(patches, bins[:-1]):
            patch.set_facecolor(plt.cm.Blues(0.3 + 0.7 * (left / bins[-1])))
        media = np.mean(todas_dists)
        ax6.axvline(media, color='#E52320', linestyle='--', linewidth=1.5,
                    label=f'Media: {media:.0f} m')
        ax6.axvline(np.median(todas_dists), color='#F89A1B', linestyle=':',
                    linewidth=1.5, label=f'Mediana: {np.median(todas_dists):.0f} m')
        ax6.legend(fontsize=10)
        ax6.set_xlabel('Distancia entre paradas consecutivas (m)', fontsize=10, color='#444')
        ax6.set_ylabel('Frecuencia', fontsize=10, color='#444')
    ax6.set_title('Distribución de distancias entre paradas', fontweight='bold',
                  fontsize=13, pad=8, color=FG)
    ax6.spines[['top', 'right']].set_visible(False)
    ax6.set_facecolor(BG_AX)
    ax6.tick_params(labelsize=9)
    fig6.tight_layout()
    _guardar(fig6, '06_histograma_distancias.png')

    # ------------------------------------------------------------------
    # 7. Top 10 andenes con más transbordos
    # ------------------------------------------------------------------
    top10 = sorted(nodo_trans_cnt.items(), key=lambda x: -x[1])[:10]
    fig7, ax7 = plt.subplots(figsize=(10, 5), facecolor=BG)
    if top10:
        nombres_t = [id_to_name.get(n, n)[:30] for n, _ in top10]
        cnts_t    = [c for _, c in top10]
        cols_t    = [COLORES_LINEA.get(n.split('_')[0], '#888') for n, _ in top10]
        bars7 = ax7.barh(range(len(nombres_t)), cnts_t, color=cols_t,
                         edgecolor='white', linewidth=0.5, height=0.65)
        ax7.set_yticks(range(len(nombres_t)))
        ax7.set_yticklabels(nombres_t, fontsize=10)
        ax7.invert_yaxis()
        ax7.set_xlabel('Número de conexiones de transbordo', fontsize=10, color='#444')
        for bar, val in zip(bars7, cnts_t):
            ax7.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                     str(val), va='center', fontsize=9)
        ax7.set_xlim(0, max(cnts_t) * 1.18)
    ax7.set_title('Top 10: andenes con más conexiones de transbordo',
                  fontweight='bold', fontsize=13, pad=8, color=FG)
    ax7.spines[['top', 'right']].set_visible(False)
    ax7.set_facecolor(BG_AX)
    ax7.tick_params(axis='x', labelsize=9)
    fig7.tight_layout()
    _guardar(fig7, '07_top_transbordos.png')

    # ------------------------------------------------------------------
    # 8. Tabla resumen por línea (sin desviación estándar)
    # ------------------------------------------------------------------
    cols_tabla = ['Línea', 'Paradas', 'Longitud (km)', 'Media (m)',
                  'Mín (m)', 'Máx (m)', 'Est. transbordo', 'Líneas conectadas']
    cell_data  = df[cols_tabla].values.tolist()

    cell_colors = []
    for row_linea in df['Línea']:
        fila = ['#ECECEC'] * len(cols_tabla)
        fila[0] = COLORES_LINEA.get(row_linea, '#CCCCCC')
        cell_colors.append(fila)

    fig8, ax8 = plt.subplots(figsize=(13, 5), facecolor=BG)
    ax8.axis('off')

    tabla = ax8.table(
        cellText=cell_data,
        colLabels=cols_tabla,
        cellLoc='center',
        loc='center',
        cellColours=cell_colors,
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 1.7)

    for j in range(len(cols_tabla)):
        tabla[0, j].set_facecolor('#1A1A2E')
        tabla[0, j].set_text_props(color='white', fontweight='bold', fontsize=10)

    for i in range(1, len(cell_data) + 1):
        tabla[i, 0].set_text_props(color='white', fontweight='bold')

    ax8.set_title('Resumen estadístico por línea', fontweight='bold',
                  fontsize=13, pad=12, color=FG)
    fig8.tight_layout()
    _guardar(fig8, '08_tabla_resumen.png')

    print(f"\nTotal: 8 imágenes guardadas en {SALIDA}")


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================
if __name__ == '__main__':
    print("Cargando grafo del Metro de Madrid...")
    resultado = metro_mod.generar_grafo_metro_madrid()
    if resultado is None:
        exit(1)
    grafo, id_to_name, name_to_ids, *_ = resultado
    guardar_informe(grafo, id_to_name)
