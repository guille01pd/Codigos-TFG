"""
Mostrar dijkstra.py — Dijkstra animado sobre el Metro de Madrid.

Teclas:
  ESPACIO          pausa / reanuda
  +  /  -          aumenta / reduce velocidad
  R                nueva ruta (modal en pantalla, sin terminal)
  ENTER            reiniciar animación (misma ruta)
  ESC              salir / cerrar modal
Ratón:
  Rueda            zoom in / out  (niveles 10 _ 15)
  Botón izquierdo  arrastrar para desplazar el mapa
"""
import sys
import math
import heapq
import importlib.machinery, importlib.util
from pathlib import Path
from io import BytesIO

import pygame
import requests

# ── rutas ────────────────────────────────────────────────────────────────────
CODIGOS    = Path(__file__).parent
TILE_CACHE = CODIGOS / '__tile_cache__'
TILE_CACHE.mkdir(exist_ok=True)

# ── módulos propios ──────────────────────────────────────────────────────────
def _cargar_modulo(nombre, archivo):
    ruta   = str(CODIGOS / archivo)
    loader = importlib.machinery.SourceFileLoader(nombre, ruta)
    spec   = importlib.util.spec_from_loader(nombre, loader)
    mod    = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

metro_mod = _cargar_modulo('metro', 'Metro_mad.py')

# ── ventana y render ─────────────────────────────────────────────────────────
WIN_W, WIN_H    = 1720, 920
FPS             = 60
STEPS_PER_FRAME = 4

# ── tiles de mapa ────────────────────────────────────────────────────────────
ZOOM_MIN  = 10
ZOOM_MAX  = 15
TILE_SIZE = 256
TILE_URL  = "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
HEADERS   = {'User-Agent': 'TFG-Metro-Madrid/1.0 (educational)'}

_tile_mem: dict = {}   # caché en memoria de tiles ya decodificados

# ── colores de línea del Metro de Madrid ─────────────────────────────────────
COLORES_LINEA_HEX = {
    '1' : '#00AAFF', '2' : '#E52320', '3' : '#FFD700',
    '4' : '#924B35', '5' : '#96BE0C', '6' : '#9B9EA1',
    '7' : '#F89A1B', '8' : '#F368A5', '9' : '#8B37A5',
    '10': '#174FA2', '11': '#00A650', '12': '#A39830',
    'R' : '#0066CC',
}

def hex_to_rgb(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

COLORES_LINEA = {k: hex_to_rgb(v) for k, v in COLORES_LINEA_HEX.items()}

# ── paleta general ────────────────────────────────────────────────────────────
C_BG       = (10,  12,  22)
C_EXPLORED = (30, 120, 255)
C_NODE     = (50, 140, 255)
C_CURRENT  = (255, 210,  40)
C_PATH     = (60,  230, 110)
C_ORIGIN   = (0,  230, 200)
C_DEST     = (210,  50,  50)
C_WHITE    = (230, 235, 245)
C_GRAY     = (110, 115, 135)
C_HUD_BG   = (12,  15,  30)
C_MODAL_BG = (14,  18,  38)


# ── tile math ─────────────────────────────────────────────────────────────────
def ll_to_tile_float(lat, lon, zoom):
    n  = 2 ** zoom
    x  = (lon + 180) / 360 * n
    lr = math.radians(lat)
    y  = (1 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2 * n
    return x, y


def fetch_tile(z, x, y):
    key = (z, x, y)
    if key in _tile_mem:
        return _tile_mem[key]
    cached = TILE_CACHE / f"{z}_{x}_{y}.png"
    if cached.exists():
        surf = pygame.image.load(str(cached))
        _tile_mem[key] = surf
        return surf
    try:
        r = requests.get(TILE_URL.format(z=z, x=x, y=y),
                         headers=HEADERS, timeout=10)
        r.raise_for_status()
        cached.write_bytes(r.content)
        surf = pygame.image.load(BytesIO(r.content))
        _tile_mem[key] = surf
        return surf
    except Exception as exc:
        print(f"  Tile {z}/{x}/{y} no disponible: {exc}")
        s = pygame.Surface((TILE_SIZE, TILE_SIZE))
        s.fill(C_BG)
        _tile_mem[key] = s
        return s


# ── funciones de cámara ───────────────────────────────────────────────────────
def compute_origin(center_lat, center_lon, zoom):
    cx, cy = ll_to_tile_float(center_lat, center_lon, zoom)
    return cx - WIN_W / 2 / TILE_SIZE, cy - WIN_H / 2 / TILE_SIZE


def build_screen_pos(node_coords, origin_tx, origin_ty, zoom):
    def _ll(lat, lon):
        tx, ty = ll_to_tile_float(lat, lon, zoom)
        return int((tx - origin_tx) * TILE_SIZE), int((ty - origin_ty) * TILE_SIZE)
    return {nid: _ll(lat, lon) for nid, (lat, lon) in node_coords.items()}


def build_map_surf(origin_tx, origin_ty, zoom):
    surf = pygame.Surface((WIN_W, WIN_H))
    surf.fill(C_BG)
    tx0 = int(origin_tx)
    ty0 = int(origin_ty)
    tx1 = int(origin_tx + WIN_W / TILE_SIZE) + 1
    ty1 = int(origin_ty + WIN_H / TILE_SIZE) + 1
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            tile = fetch_tile(zoom, tx, ty)
            px = int((tx - origin_tx) * TILE_SIZE)
            py = int((ty - origin_ty) * TILE_SIZE)
            surf.blit(tile, (px, py))
    return surf


def build_net_surf(grafo, screen_pos):
    surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    drawn = set()
    for u, vecinos in grafo.items():
        if u not in screen_pos:
            continue
        for v, w in vecinos:
            if v not in screen_pos:
                continue
            key = (min(u, v), max(u, v))
            if key in drawn or w == 0.0:
                continue
            drawn.add(key)
            pygame.draw.line(surf, (55, 60, 80, 80), screen_pos[u], screen_pos[v], 1)
    return surf


def rebuild_exploration_surfs(explored_nodes_list, explored_edges_list, screen_pos):
    edge_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    node_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    for u, v in explored_edges_list:
        if u in screen_pos and v in screen_pos:
            pygame.draw.line(edge_surf, (*C_EXPLORED, 130),
                             screen_pos[u], screen_pos[v], 2)
    for nid in explored_nodes_list:
        if nid in screen_pos:
            pygame.draw.circle(node_surf, (*C_NODE, 190), screen_pos[nid], 4)
    return edge_surf, node_surf


# ── modal de selección de estación ───────────────────────────────────────────
MAX_VISIBLE = 15   # filas visibles en el modal
ITEM_H      = 38
LINEAS_BTN  = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'R']

def modal_elegir_estacion(screen, clock, fonts, grafo, id_to_name,
                           etiqueta, acento_rgb, cancelable=True):
    """
    Modal de búsqueda/selección de estación dentro de pygame.
    Devuelve el node_id seleccionado, o None si el usuario cancela.
    """
    font_big, font_med, font_sm = fonts

    # lista completa ordenada por nombre
    todas = sorted(
        [(nid, id_to_name.get(nid, nid), nid.split('_')[0])
         for nid in grafo],
        key=lambda x: (x[1], x[2])
    )

    query        = ""
    sel_idx      = 0
    scroll_off   = 0
    linea_filter = None   # None = todas las líneas

    BOX_W = 740
    BOX_H = WIN_H - 80
    BOX_X = (WIN_W - BOX_W) // 2
    BOX_Y = 40

    # botones de filtro por línea (calculados una vez, fuera del bucle)
    BTN_W     = 42
    BTN_H     = 26
    BTN_GAP   = 4
    BTN_ROW_Y = BOX_Y + 102
    btn_rects = {}
    for i, ln in enumerate(LINEAS_BTN):
        btn_rects[ln] = pygame.Rect(BOX_X + 16 + i * (BTN_W + BTN_GAP),
                                    BTN_ROW_Y, BTN_W, BTN_H)

    LIST_Y0 = BOX_Y + 164   # y donde empieza la lista dentro de la pantalla

    while True:
        # ── filtrar ─────────────────────────────────────────────────────────
        q = query.upper()
        if q or linea_filter:
            filtered = [(nid, n, l) for nid, n, l in todas
                        if (not q or q in n.upper())
                        and (linea_filter is None or l == linea_filter)]
        else:
            filtered = todas

        if sel_idx >= len(filtered):
            sel_idx = max(0, len(filtered) - 1)
        # mantener sel_idx visible
        if sel_idx < scroll_off:
            scroll_off = sel_idx
        if sel_idx >= scroll_off + MAX_VISIBLE:
            scroll_off = sel_idx - MAX_VISIBLE + 1

        # ── eventos ─────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if cancelable:
                        return None
                    else:
                        pygame.quit(); sys.exit()
                elif event.key == pygame.K_RETURN:
                    if filtered:
                        return filtered[sel_idx][0]
                elif event.key == pygame.K_BACKSPACE:
                    query = query[:-1]
                    sel_idx = 0; scroll_off = 0
                elif event.key == pygame.K_UP:
                    sel_idx = max(0, sel_idx - 1)
                elif event.key == pygame.K_DOWN:
                    sel_idx = min(len(filtered) - 1, sel_idx + 1)
                elif event.key == pygame.K_PAGEUP:
                    sel_idx = max(0, sel_idx - MAX_VISIBLE)
                elif event.key == pygame.K_PAGEDOWN:
                    sel_idx = min(len(filtered) - 1, sel_idx + MAX_VISIBLE)
                elif event.unicode and event.unicode.isprintable():
                    query += event.unicode
                    sel_idx = 0; scroll_off = 0

            elif event.type == pygame.MOUSEWHEEL:
                scroll_off = max(0, min(
                    max(0, len(filtered) - MAX_VISIBLE),
                    scroll_off - event.y))

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                hit_btn = False
                for ln, rect in btn_rects.items():
                    if rect.collidepoint(mx, my):
                        linea_filter = None if linea_filter == ln else ln
                        sel_idx = 0; scroll_off = 0
                        hit_btn = True
                        break
                if not hit_btn and BOX_X <= mx <= BOX_X + BOX_W:
                    for i in range(min(MAX_VISIBLE, len(filtered))):
                        iy = LIST_Y0 + i * ITEM_H
                        if iy <= my < iy + ITEM_H:
                            clicked = scroll_off + i
                            if clicked == sel_idx:
                                return filtered[clicked][0]   # doble click = confirmar
                            sel_idx = clicked

        # ── dibujar overlay ──────────────────────────────────────────────────
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((4, 6, 16, 210))
        screen.blit(overlay, (0, 0))

        # caja modal
        pygame.draw.rect(screen, C_MODAL_BG,
                         (BOX_X, BOX_Y, BOX_W, BOX_H), border_radius=10)
        pygame.draw.rect(screen, acento_rgb,
                         (BOX_X, BOX_Y, BOX_W, BOX_H), 2, border_radius=10)

        # título
        titulo = font_big.render(f"Seleccionar  {etiqueta}", True, acento_rgb)
        screen.blit(titulo, (BOX_X + 20, BOX_Y + 16))

        cnt_txt = font_sm.render(f"{len(filtered)} resultado(s)", True, C_GRAY)
        screen.blit(cnt_txt, (BOX_X + BOX_W - cnt_txt.get_width() - 16, BOX_Y + 22))

        # barra de búsqueda
        srect = pygame.Rect(BOX_X + 16, BOX_Y + 58, BOX_W - 32, 40)
        pygame.draw.rect(screen, (24, 28, 52), srect, border_radius=6)
        pygame.draw.rect(screen, acento_rgb,   srect, 1,  border_radius=6)
        cursor_blink = (pygame.time.get_ticks() // 500) % 2 == 0
        display_query = query + ("▌" if cursor_blink else " ")
        stxt = font_med.render(display_query if query else "Buscar estación...", True,
                               C_WHITE if query else C_GRAY)
        screen.blit(stxt, (srect.x + 12, srect.y + 8))

        # botones de filtro por línea
        for ln, rect in btn_rects.items():
            col = COLORES_LINEA.get(ln, (120, 120, 120))
            if linea_filter == ln:
                pygame.draw.rect(screen, col, rect, border_radius=4)
            else:
                pygame.draw.rect(screen, (25, 30, 55), rect, border_radius=4)
                pygame.draw.rect(screen, col, rect, 1, border_radius=4)
            btxt_l = font_sm.render(f"L{ln}", True, C_WHITE)
            screen.blit(btxt_l, (rect.x + rect.w // 2 - btxt_l.get_width() // 2,
                                 rect.y + rect.h // 2 - btxt_l.get_height() // 2))

        # ayuda
        esc_hint = "ESC cancelar  · " if cancelable else ""
        hint = font_sm.render(
            f"↑↓ navegar  ·  Enter / clic×2 seleccionar  ·  {esc_hint}Clic en línea filtrar  ·  Rueda desplazar",
            True, C_GRAY)
        screen.blit(hint, (BOX_X + 16, BOX_Y + 136))

        # separador
        pygame.draw.line(screen, (35, 40, 70),
                         (BOX_X + 10, LIST_Y0 - 4), (BOX_X + BOX_W - 10, LIST_Y0 - 4), 1)

        # lista de estaciones
        visible = filtered[scroll_off: scroll_off + MAX_VISIBLE]
        for i, (_, nombre, linea) in enumerate(visible):
            actual_i = scroll_off + i
            iy = LIST_Y0 + i * ITEM_H
            is_sel = (actual_i == sel_idx)

            # fondo de fila
            row_col = (38, 58, 110, 220) if is_sel else (22, 26, 50, 180)
            row = pygame.Surface((BOX_W - 32, ITEM_H - 2), pygame.SRCALPHA)
            row.fill(row_col)
            screen.blit(row, (BOX_X + 16, iy))

            if is_sel:
                pygame.draw.rect(screen, acento_rgb,
                                 (BOX_X + 16, iy, BOX_W - 32, ITEM_H - 2), 1)

            # badge de línea
            badge_col = COLORES_LINEA.get(linea, (120, 120, 120))
            badge_rect = pygame.Rect(BOX_X + 22, iy + 7, 44, 22)
            pygame.draw.rect(screen, badge_col, badge_rect, border_radius=4)
            btxt = font_sm.render(f"L{linea}", True, C_WHITE)
            screen.blit(btxt, (badge_rect.x + badge_rect.w // 2 - btxt.get_width() // 2,
                               badge_rect.y + 3))

            # nombre
            col_n = C_WHITE if is_sel else (175, 180, 210)
            ntxt = font_med.render(nombre[:48], True, col_n)
            screen.blit(ntxt, (BOX_X + 76, iy + 8))

        # scrollbar
        if len(filtered) > MAX_VISIBLE:
            sb_total_h = MAX_VISIBLE * ITEM_H
            sb_x = BOX_X + BOX_W - 10
            sb_y = LIST_Y0
            pygame.draw.rect(screen, (35, 40, 68), (sb_x, sb_y, 6, sb_total_h))
            ratio     = MAX_VISIBLE / len(filtered)
            thumb_h   = max(18, int(sb_total_h * ratio))
            thumb_y   = sb_y + int((sb_total_h - thumb_h) *
                                   scroll_off / max(1, len(filtered) - MAX_VISIBLE))
            pygame.draw.rect(screen, acento_rgb, (sb_x, thumb_y, 6, thumb_h), border_radius=3)

        pygame.display.flip()
        clock.tick(FPS)


# ── Dijkstra generador ────────────────────────────────────────────────────────
#mirar diferencia con el mio
def dijkstra_gen(grafo, inicio, fin):
    todos = set(grafo.keys())
    for vs in grafo.values():
        for n, _ in vs:
            todos.add(n)

    dist = {n: math.inf for n in todos}
    prev = {n: None     for n in todos}
    dist[inicio] = 0

    heap    = [(0.0, inicio)]
    visited = set()

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        yield ('visit', u, d)

        #Un break, para terminar el bucle while cuando se llegaa destino, 
        #para no explorar vértices innecesarios.
        if u == fin:
            break

        for v, w in grafo.get(u, []):
            if v not in visited:
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))
                    yield ('edge', u, v)

    path, cur = [], fin
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    yield ('done', path, dist.get(fin, math.inf))


# ── HUD ───────────────────────────────────────────────────────────────────────
def contar_transbordos(path):
    if not path:
        return 0
    return sum(1 for i in range(len(path) - 1)
               if path[i].split('_')[0] != path[i + 1].split('_')[0])


def dibujar_hud(screen, fonts, explored, dist_m, transbordos, speed, paused, done,
                orig_name, dest_name, zoom):
    font_big, font_med, font_sm = fonts
    HUD_H = 64

    hud = pygame.Surface((WIN_W, HUD_H))
    hud.fill(C_HUD_BG)
    screen.blit(hud, (0, 0))
    pygame.draw.line(screen, (40, 45, 70), (0, HUD_H), (WIN_W, HUD_H), 1)

    pygame.draw.line(screen, (45, 50, 80), (340, 8), (340, 56), 1)
    pygame.draw.line(screen, (45, 50, 80), (465, 8), (465, 56), 1)
    pygame.draw.line(screen, (45, 50, 80), (590, 8), (590, 56), 1)

    screen.blit(font_big.render("DIJKSTRA", True, (90, 150, 255)), (16, 14))

    screen.blit(font_sm.render("EXPLORADOS",  True, C_GRAY), (350, 10))
    screen.blit(font_med.render(str(explored), True, (80, 170, 255)), (350, 28))

    screen.blit(font_sm.render("DISTANCIA", True, C_GRAY), (475, 10))
    val_dist = "—" if math.isinf(dist_m) else f"{dist_m/1000:.2f} km"
    col_dist = C_GRAY if math.isinf(dist_m) else (70, 220, 110)
    screen.blit(font_med.render(val_dist, True, col_dist), (475, 28))

    screen.blit(font_sm.render("TRANSBORDOS", True, C_GRAY), (600, 10))
    val_trans = "—" if math.isinf(dist_m) else str(transbordos)
    col_trans = C_GRAY if math.isinf(dist_m) else (255, 195, 50)
    screen.blit(font_med.render(val_trans, True, col_trans), (600, 28))

    estado = "LISTO ✓" if done else ("PAUSA" if paused else "EXPLORANDO")
    col_st = (70, 220, 110) if done else (255, 195, 50) if paused else (160, 165, 185)
    screen.blit(font_med.render(estado, True, col_st), (WIN_W - 210, 14))

    hint = (f"vel ×{speed} [+/-]  [SPC] pausa  [ENTER] reiniciar  [R] nueva ruta  [ESC] salir"
            f"    zoom:{zoom} [rueda]  pan:[btn izq]")
    screen.blit(font_sm.render(hint, True, C_GRAY), (WIN_W - 800, 42))

    ruta_txt = font_sm.render(f"  {orig_name}  →  {dest_name}", True, (170, 175, 200))
    screen.blit(ruta_txt, (16, 44))


# ── panel de ruta (columna izquierda) ────────────────────────────────────────
def peso_arista(grafo, origen, destino):
    for dest, peso in grafo.get(origen, []):
        if dest == destino:
            return peso
    return None


def dibujar_panel_ruta(screen, fonts, final_path, id_to_name, dist_m, grafo):
    _, font_med, font_sm = fonts
    n = len(final_path)
    if n == 0:
        return

    PANEL_X    = 16
    PANEL_Y    = 80
    PANEL_W    = 340
    TITLE_H    = 34
    COL_DIST_X = PANEL_W - 80
    MAX_H      = WIN_H - PANEL_Y - 16
    ROW_H      = min(30, max(16, (MAX_H - TITLE_H - 16) // n))
    PANEL_H    = min(MAX_H, TITLE_H + ROW_H * n + 16)

    panel = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    panel.fill((*C_MODAL_BG, 225))
    pygame.draw.rect(panel, (60, 90, 140), panel.get_rect(), 1, border_radius=6)

    titulo = font_med.render(f"RUTA · {n} paradas · {dist_m/1000:.2f} km", True, C_WHITE)
    panel.blit(titulo, (12, 10))
    pygame.draw.line(panel, (45, 50, 80), (12, TITLE_H), (PANEL_W - 12, TITLE_H), 1)

    cx = 22
    for i, nid in enumerate(final_path):
        cy = TITLE_H + 8 + i * ROW_H + ROW_H // 2
        if i < n - 1:
            siguiente     = final_path[i + 1]
            peso          = peso_arista(grafo, nid, siguiente)
            es_transbordo = (peso == 0.0 and nid.split('_')[0] != siguiente.split('_')[0])
            cy_seg        = cy + ROW_H // 2

            if es_transbordo:
                col_linea = COLORES_LINEA.get(siguiente.split('_')[0], C_NODE)
                alto_barra = ROW_H - 10
                pygame.draw.rect(panel, col_linea,
                                 (COL_DIST_X + 8, cy_seg - alto_barra // 2, 5, alto_barra),
                                 border_radius=2)
            elif peso is not None:
                etiqueta = font_sm.render(f"{peso:.0f} m", True, C_GRAY)
                panel.blit(etiqueta, (COL_DIST_X, cy_seg - etiqueta.get_height() // 2))

            pygame.draw.line(panel, C_GRAY, (cx, cy), (cx, cy + ROW_H), 2)

        if i == 0:
            col, r, txt_col = C_ORIGIN, 7, C_ORIGIN
        elif i == n - 1:
            col, r, txt_col = C_DEST, 7, C_DEST
        else:
            col, r, txt_col = COLORES_LINEA.get(nid.split('_')[0], C_NODE), 4, C_WHITE
        pygame.draw.circle(panel, col, (cx, cy), r)
        if r >= 6:
            pygame.draw.circle(panel, C_WHITE, (cx, cy), r, 1)

        nombre = id_to_name.get(nid, nid)
        if len(nombre) > 22:
            nombre = nombre[:21] + '…'
        txt = font_sm.render(nombre, True, txt_col)
        panel.blit(txt, (cx + 16, cy - txt.get_height() // 2))

    screen.blit(panel, (PANEL_X, PANEL_Y))


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("Generando grafo...")
    resultado = metro_mod.generar_grafo_metro_madrid()
    if resultado is None:
        sys.exit(1)
    grafo, id_to_name, _, node_coords = resultado
    print(f"Grafo metro Madrid: {len(grafo)} vértices.")
    print(f"Complejidad O(n log n): {len(grafo) * math.log(len(grafo)) } operaciones\n")

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Dijkstra — Metro de Madrid")
    clock  = pygame.time.Clock()

    font_big = pygame.font.SysFont('Consolas', 26, bold=True)
    font_med = pygame.font.SysFont('Consolas', 17, bold=True)
    font_sm  = pygame.font.SysFont('Consolas', 13)
    fonts    = (font_big, font_med, font_sm)

    # ── estado de cámara ────────────────────────────────────────────────────
    lats = [c[0] for c in node_coords.values()]
    lons = [c[1] for c in node_coords.values()]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2

    cam_zoom  = 12
    origin_tx, origin_ty = compute_origin(center_lat, center_lon, cam_zoom)

    explored_nodes_list: list = []
    explored_edges_list: list = []

    map_surf = net_surf = edge_surf = node_surf = None
    screen_pos: dict = {}

    def rebuild_camera():
        nonlocal map_surf, net_surf, edge_surf, node_surf, screen_pos
        map_surf   = build_map_surf(origin_tx, origin_ty, cam_zoom)
        screen_pos = build_screen_pos(node_coords, origin_tx, origin_ty, cam_zoom)
        net_surf   = build_net_surf(grafo, screen_pos)
        edge_surf, node_surf = rebuild_exploration_surfs(
            explored_nodes_list, explored_edges_list, screen_pos)

    print("Descargando mapa...")
    rebuild_camera()
    print("  Mapa listo.\n")

    # ── selección inicial directamente en pygame ─────────────────────────────
    origen = modal_elegir_estacion(screen, clock, fonts, grafo, id_to_name,
                                   "ORIGEN", C_ORIGIN, cancelable=False)
    if origen is None:
        pygame.quit(); sys.exit()

    destino = modal_elegir_estacion(screen, clock, fonts, grafo, id_to_name,
                                    "DESTINO", C_DEST, cancelable=False)
    if destino is None:
        pygame.quit(); sys.exit()

    # ── pan ──────────────────────────────────────────────────────────────────
    panning  = False
    pan_last = (0, 0)

    def reset_sim(orig, dest):
        explored_nodes_list.clear()
        explored_edges_list.clear()
        edge_surf.fill((0, 0, 0, 0))
        node_surf.fill((0, 0, 0, 0))
        return {
            'gen'         : dijkstra_gen(grafo, orig, dest),
            'explored'    : 0,
            'current'     : None,
            'current_dist': 0.0,
            'final_path'  : None,
            'done'        : False,
        }

    sim    = reset_sim(origen, destino)
    speed  = STEPS_PER_FRAME
    paused = False

    orig_name = id_to_name.get(origen,  origen)
    dest_name = id_to_name.get(destino, destino)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    speed = min(speed + 2, 60)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed = max(speed - 2, 1)
                elif event.key == pygame.K_RETURN:
                    if sim['done']:
                        sim    = reset_sim(origen, destino)
                        paused = False
                elif event.key == pygame.K_r:
                    # nueva ruta con modal en pantalla
                    nuevo_orig = modal_elegir_estacion(
                        screen, clock, fonts, grafo, id_to_name,
                        "ORIGEN", C_ORIGIN, cancelable=True)
                    if nuevo_orig is None:
                        continue   # cancelado → mantener ruta actual
                    nuevo_dest = modal_elegir_estacion(
                        screen, clock, fonts, grafo, id_to_name,
                        "DESTINO", C_DEST, cancelable=True)
                    if nuevo_dest is None:
                        continue
                    origen    = nuevo_orig
                    destino   = nuevo_dest
                    orig_name = id_to_name.get(origen,  origen)
                    dest_name = id_to_name.get(destino, destino)
                    sim    = reset_sim(origen, destino)
                    paused = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    panning  = True
                    pan_last = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    panning = False

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    dx = event.pos[0] - pan_last[0]
                    dy = event.pos[1] - pan_last[1]
                    pan_last = event.pos
                    origin_tx -= dx / TILE_SIZE
                    origin_ty -= dy / TILE_SIZE
                    rebuild_camera()

            elif event.type == pygame.MOUSEWHEEL:
                new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, cam_zoom + event.y))
                if new_zoom != cam_zoom:
                    mid_tx = origin_tx + WIN_W / 2 / TILE_SIZE
                    mid_ty = origin_ty + WIN_H / 2 / TILE_SIZE
                    scale  = 2 ** (new_zoom - cam_zoom)
                    mid_tx *= scale
                    mid_ty *= scale
                    cam_zoom  = new_zoom
                    origin_tx = mid_tx - WIN_W / 2 / TILE_SIZE
                    origin_ty = mid_ty - WIN_H / 2 / TILE_SIZE
                    rebuild_camera()

        # ── avanzar Dijkstra ─────────────────────────────────────────────────
        if not sim['done'] and not paused:
            for _ in range(speed):
                try:
                    step = next(sim['gen'])
                    kind = step[0]
                    if kind == 'visit':
                        _, u, d = step
                        sim['current']      = u
                        sim['current_dist'] = d
                        sim['explored']    += 1
                        explored_nodes_list.append(u)
                        if u in screen_pos:
                            pygame.draw.circle(node_surf, (*C_NODE, 190),
                                               screen_pos[u], 4)
                    elif kind == 'edge':
                        _, u, v = step
                        explored_edges_list.append((u, v))
                        if u in screen_pos and v in screen_pos:
                            pygame.draw.line(edge_surf, (*C_EXPLORED, 130),
                                             screen_pos[u], screen_pos[v], 2)
                    elif kind == 'done':
                        sim['final_path']   = step[1]
                        sim['current_dist'] = step[2]
                        sim['done']         = True
                        break
                except StopIteration:
                    sim['done'] = True
                    break

        # ── dibujar mapa + capas ─────────────────────────────────────────────
        screen.blit(map_surf,  (0, 0))
        screen.blit(net_surf,  (0, 0))
        screen.blit(edge_surf, (0, 0))
        screen.blit(node_surf, (0, 0))

        if sim['final_path']:
            pts = [screen_pos[n] for n in sim['final_path'] if n in screen_pos]
            if len(pts) > 1:
                pygame.draw.lines(screen, C_PATH, False, pts, 5)
            for p in pts:
                pygame.draw.circle(screen, C_PATH, p, 5)

        cur = sim['current']
        if cur and cur in screen_pos and not sim['done']:
            p = screen_pos[cur]
            t = pygame.time.get_ticks()
            r = 7 + int(3 * abs(math.sin(t / 180)))
            pygame.draw.circle(screen, C_CURRENT, p, r)
            pygame.draw.circle(screen, C_WHITE,   p, r, 1)

        orig_pos = screen_pos.get(origen)
        dest_pos = screen_pos.get(destino)
        if orig_pos:
            pygame.draw.circle(screen, C_ORIGIN, orig_pos, 11)
            pygame.draw.circle(screen, C_WHITE,  orig_pos, 11, 2)
            screen.blit(font_sm.render(orig_name[:28], True, C_ORIGIN),
                        (orig_pos[0] + 14, orig_pos[1] - 8))
        if dest_pos:
            pygame.draw.circle(screen, C_DEST, dest_pos, 11)
            pygame.draw.circle(screen, C_WHITE, dest_pos, 11, 2)
            screen.blit(font_sm.render(dest_name[:28], True, C_DEST),
                        (dest_pos[0] + 14, dest_pos[1] - 8))

        dibujar_hud(screen, fonts,
                    sim['explored'], sim['current_dist'],
                    contar_transbordos(sim['final_path']),
                    speed, paused, sim['done'],
                    orig_name, dest_name, cam_zoom)

        if sim['done'] and sim['final_path']:
            dibujar_panel_ruta(screen, fonts, sim['final_path'], id_to_name, sim['current_dist'], grafo)

            n_paradas = len(sim['final_path'])
            km        = sim['current_dist'] / 1000
            banner    = font_med.render(
                f"  Ruta encontrada — {n_paradas} paradas · {km:.2f} km  ·  ENTER reiniciar  ",
                True, C_PATH)
            bw = banner.get_width() + 20
            bg = pygame.Surface((bw, 34), pygame.SRCALPHA)
            bg.fill((12, 15, 30, 200))
            bx = WIN_W // 2 - bw // 2
            screen.blit(bg,     (bx, WIN_H - 44))
            screen.blit(banner, (bx + 10, WIN_H - 40))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == '__main__':
    main()
