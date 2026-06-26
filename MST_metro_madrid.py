"""
MST_metro_madrid.py — Prim animado sobre el Metro de Madrid.

Muestra el Árbol de Expansión Mínima construido paso a paso con el
algoritmo de Prim sobre la red real del Metro de Madrid (datos GTFS).

Teclas:
  ESPACIO          pausa / reanuda
  +  /  -          aumenta / reduce velocidad
  R                nuevo origen (modal en pantalla)
  ENTER            reiniciar animación (mismo origen)
  ESC              salir
Ratón:
  Rueda            zoom in / out  (niveles 10 − 15)
  Botón izquierdo  arrastrar para desplazar el mapa
  Rueda sobre panel  desplazar lista de aristas MST
"""
import sys
import math
import heapq
import importlib.machinery, importlib.util
from pathlib import Path
from io import BytesIO

import pygame
import requests

# ── rutas ─────────────────────────────────────────────────────────────────────
CODIGOS    = Path(__file__).parent
TILE_CACHE = CODIGOS / '__tile_cache__'
TILE_CACHE.mkdir(exist_ok=True)

# ── módulos propios ────────────────────────────────────────────────────────────
def _cargar_modulo(nombre, archivo):
    ruta   = str(CODIGOS / archivo)
    loader = importlib.machinery.SourceFileLoader(nombre, ruta)
    spec   = importlib.util.spec_from_loader(nombre, loader)
    mod    = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

metro_mod = _cargar_modulo('metro', 'Metro_mad.py')

# ── ventana ────────────────────────────────────────────────────────────────────
WIN_W, WIN_H    = 1720, 920
FPS             = 60
STEPS_PER_FRAME = 4

# ── tiles ──────────────────────────────────────────────────────────────────────
ZOOM_MIN  = 10
ZOOM_MAX  = 15
TILE_SIZE = 256
TILE_URL  = "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
HEADERS   = {'User-Agent': 'TFG-Metro-Madrid/1.0 (educational)'}
_tile_mem: dict = {}

# ── colores de línea ───────────────────────────────────────────────────────────
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

# ── paleta ─────────────────────────────────────────────────────────────────────
C_BG        = (10,  12,  22)
C_MST_EDGE  = (255, 195,  50)
C_CANDIDATE = (30,  100, 220)
C_NODE_BASE = (55,   60,  90)
C_NODE_MST  = (50,  200, 120)
C_CURRENT   = (255, 210,  40)
C_ORIGIN    = (0,   230, 200)
C_WHITE     = (230, 235, 245)
C_GRAY      = (110, 115, 135)
C_HUD_BG    = (12,   15,  30)
C_MODAL_BG  = (14,   18,  38)

HUD_H   = 64
PANEL_W = 340


# ── tiles ──────────────────────────────────────────────────────────────────────
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
    tx0 = int(origin_tx);           ty0 = int(origin_ty)
    tx1 = int(origin_tx + WIN_W / TILE_SIZE) + 1
    ty1 = int(origin_ty + WIN_H / TILE_SIZE) + 1
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            tile = fetch_tile(zoom, tx, ty)
            surf.blit(tile, (int((tx - origin_tx) * TILE_SIZE),
                             int((ty - origin_ty) * TILE_SIZE)))
    return surf


def build_net_surf(grafo, screen_pos):
    """Aristas del metro coloreadas por línea (semi-transparentes)."""
    surf  = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    drawn = set()
    for u, vecinos in grafo.items():
        if u not in screen_pos:
            continue
        linea_u = u.split('_')[0]
        for v, w in vecinos:
            if v not in screen_pos:
                continue
            key = (min(u, v), max(u, v))
            if key in drawn:
                continue
            drawn.add(key)
            if w == 0.0:
                pygame.draw.line(surf, (80, 85, 110, 80),
                                 screen_pos[u], screen_pos[v], 1)
            else:
                col = COLORES_LINEA.get(linea_u, (100, 100, 100))
                pygame.draw.line(surf, (*col, 70),
                                 screen_pos[u], screen_pos[v], 2)
    return surf


# ── Prim generador ─────────────────────────────────────────────────────────────
def prim_gen(grafo, inicio):
    explorado   = set()
    mst_aristas = []
    peso_total  = 0.0

    heap = []
    for vecino, peso in grafo.get(inicio, []):
        heapq.heappush(heap, (peso, inicio, vecino))
        yield ('edge', inicio, vecino)

    explorado.add(inicio)
    yield ('visit', inicio, 0.0, None)

    while heap:
        peso, origen, vertice = heapq.heappop(heap)
        if vertice in explorado:
            continue

        explorado.add(vertice)
        mst_aristas.append((peso, origen, vertice))
        peso_total += peso
        yield ('visit', vertice, peso, origen)

        for vecino, p in grafo.get(vertice, []):
            if vecino not in explorado:
                heapq.heappush(heap, (p, vertice, vecino))
                yield ('edge', vertice, vecino)

    yield ('done', mst_aristas, peso_total)


# ── modal de selección de estación ────────────────────────────────────────────
MAX_VISIBLE = 15
ITEM_H      = 38
LINEAS_BTN  = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'R']

def modal_elegir_estacion(screen, clock, fonts, grafo, id_to_name,
                           etiqueta, acento_rgb, cancelable=True):
    font_big, font_med, font_sm = fonts

    todas = sorted(
        [(nid, id_to_name.get(nid, nid), nid.split('_')[0]) for nid in grafo],
        key=lambda x: (x[1], x[2])
    )

    query        = ""
    sel_idx      = 0
    scroll_off   = 0
    linea_filter = None

    BOX_W = 740;  BOX_H = WIN_H - 80
    BOX_X = (WIN_W - BOX_W) // 2;  BOX_Y = 40

    BTN_W, BTN_H, BTN_GAP = 42, 26, 4
    btn_rects = {ln: pygame.Rect(BOX_X + 16 + i * (BTN_W + BTN_GAP),
                                 BOX_Y + 102, BTN_W, BTN_H)
                 for i, ln in enumerate(LINEAS_BTN)}
    LIST_Y0 = BOX_Y + 164

    while True:
        q        = query.upper()
        filtered = [(nid, n, l) for nid, n, l in todas
                    if (not q or q in n.upper())
                    and (linea_filter is None or l == linea_filter)]

        if sel_idx >= len(filtered):
            sel_idx = max(0, len(filtered) - 1)
        if sel_idx < scroll_off:
            scroll_off = sel_idx
        if sel_idx >= scroll_off + MAX_VISIBLE:
            scroll_off = sel_idx - MAX_VISIBLE + 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if cancelable: return None
                    else:          pygame.quit(); sys.exit()
                elif event.key == pygame.K_RETURN:
                    if filtered: return filtered[sel_idx][0]
                elif event.key == pygame.K_BACKSPACE:
                    query = query[:-1]; sel_idx = 0; scroll_off = 0
                elif event.key == pygame.K_UP:
                    sel_idx = max(0, sel_idx - 1)
                elif event.key == pygame.K_DOWN:
                    sel_idx = min(len(filtered) - 1, sel_idx + 1)
                elif event.key == pygame.K_PAGEUP:
                    sel_idx = max(0, sel_idx - MAX_VISIBLE)
                elif event.key == pygame.K_PAGEDOWN:
                    sel_idx = min(len(filtered) - 1, sel_idx + MAX_VISIBLE)
                elif event.unicode and event.unicode.isprintable():
                    query += event.unicode; sel_idx = 0; scroll_off = 0
            elif event.type == pygame.MOUSEWHEEL:
                scroll_off = max(0, min(max(0, len(filtered) - MAX_VISIBLE),
                                        scroll_off - event.y))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                hit_btn = False
                for ln, rect in btn_rects.items():
                    if rect.collidepoint(mx, my):
                        linea_filter = None if linea_filter == ln else ln
                        sel_idx = 0; scroll_off = 0
                        hit_btn = True; break
                if not hit_btn and BOX_X <= mx <= BOX_X + BOX_W:
                    for i in range(min(MAX_VISIBLE, len(filtered))):
                        iy = LIST_Y0 + i * ITEM_H
                        if iy <= my < iy + ITEM_H:
                            clicked = scroll_off + i
                            if clicked == sel_idx: return filtered[clicked][0]
                            sel_idx = clicked

        # ── dibujar modal ─────────────────────────────────────────────────────
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((4, 6, 16, 210))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, C_MODAL_BG, (BOX_X, BOX_Y, BOX_W, BOX_H), border_radius=10)
        pygame.draw.rect(screen, acento_rgb, (BOX_X, BOX_Y, BOX_W, BOX_H), 2, border_radius=10)

        screen.blit(font_big.render(f"Seleccionar  {etiqueta}", True, acento_rgb),
                    (BOX_X + 20, BOX_Y + 16))
        cnt = font_sm.render(f"{len(filtered)} resultado(s)", True, C_GRAY)
        screen.blit(cnt, (BOX_X + BOX_W - cnt.get_width() - 16, BOX_Y + 22))

        srect = pygame.Rect(BOX_X + 16, BOX_Y + 58, BOX_W - 32, 40)
        pygame.draw.rect(screen, (24, 28, 52), srect, border_radius=6)
        pygame.draw.rect(screen, acento_rgb,   srect, 1, border_radius=6)
        cursor_blink = (pygame.time.get_ticks() // 500) % 2 == 0
        stxt = font_med.render(
            (query + ("▌" if cursor_blink else " ")) if query else "Buscar estación...",
            True, C_WHITE if query else C_GRAY)
        screen.blit(stxt, (srect.x + 12, srect.y + 8))

        for ln, rect in btn_rects.items():
            col = COLORES_LINEA.get(ln, (120, 120, 120))
            if linea_filter == ln:
                pygame.draw.rect(screen, col, rect, border_radius=4)
            else:
                pygame.draw.rect(screen, (25, 30, 55), rect, border_radius=4)
                pygame.draw.rect(screen, col, rect, 1, border_radius=4)
            btxt = font_sm.render(f"L{ln}", True, C_WHITE)
            screen.blit(btxt, (rect.x + rect.w // 2 - btxt.get_width() // 2,
                               rect.y + rect.h // 2 - btxt.get_height() // 2))

        esc_hint = "ESC cancelar  · " if cancelable else ""
        screen.blit(font_sm.render(
            f"↑↓ navegar  ·  Enter / clic×2 seleccionar  ·  {esc_hint}"
            f"Clic en línea filtrar  ·  Rueda desplazar",
            True, C_GRAY), (BOX_X + 16, BOX_Y + 136))

        pygame.draw.line(screen, (35, 40, 70),
                         (BOX_X + 10, LIST_Y0 - 4), (BOX_X + BOX_W - 10, LIST_Y0 - 4), 1)

        for i, (nid, nombre, linea) in enumerate(filtered[scroll_off: scroll_off + MAX_VISIBLE]):
            actual_i = scroll_off + i
            iy       = LIST_Y0 + i * ITEM_H
            is_sel   = (actual_i == sel_idx)

            row = pygame.Surface((BOX_W - 32, ITEM_H - 2), pygame.SRCALPHA)
            row.fill((38, 58, 110, 220) if is_sel else (22, 26, 50, 180))
            screen.blit(row, (BOX_X + 16, iy))
            if is_sel:
                pygame.draw.rect(screen, acento_rgb,
                                 (BOX_X + 16, iy, BOX_W - 32, ITEM_H - 2), 1)

            badge_col  = COLORES_LINEA.get(linea, (120, 120, 120))
            badge_rect = pygame.Rect(BOX_X + 22, iy + 7, 44, 22)
            pygame.draw.rect(screen, badge_col, badge_rect, border_radius=4)
            btxt = font_sm.render(f"L{linea}", True, C_WHITE)
            screen.blit(btxt, (badge_rect.x + badge_rect.w // 2 - btxt.get_width() // 2,
                               badge_rect.y + 3))
            screen.blit(font_med.render(nombre[:48], True, C_WHITE if is_sel else (175, 180, 210)),
                        (BOX_X + 76, iy + 8))

        if len(filtered) > MAX_VISIBLE:
            sb_h = MAX_VISIBLE * ITEM_H
            sb_x = BOX_X + BOX_W - 10
            pygame.draw.rect(screen, (35, 40, 68), (sb_x, LIST_Y0, 6, sb_h))
            ratio   = MAX_VISIBLE / len(filtered)
            thumb_h = max(18, int(sb_h * ratio))
            thumb_y = LIST_Y0 + int((sb_h - thumb_h) * scroll_off /
                                    max(1, len(filtered) - MAX_VISIBLE))
            pygame.draw.rect(screen, acento_rgb, (sb_x, thumb_y, 6, thumb_h), border_radius=3)

        pygame.display.flip()
        clock.tick(FPS)


# ── HUD ────────────────────────────────────────────────────────────────────────
def dibujar_hud(screen, fonts, en_mst, n_total, peso_km, n_aristas_mst,
                speed, paused, done, orig_name, zoom, hide_non_mst=False):
    font_big, font_med, font_sm = fonts

    hud = pygame.Surface((WIN_W, HUD_H))
    hud.fill(C_HUD_BG)
    screen.blit(hud, (0, 0))
    pygame.draw.line(screen, (40, 45, 70), (0, HUD_H), (WIN_W, HUD_H), 1)

    for x in (300, 440, 580, 730):
        pygame.draw.line(screen, (45, 50, 80), (x, 8), (x, 56), 1)

    screen.blit(font_big.render("PRIM  MST", True, C_MST_EDGE), (16, 14))

    screen.blit(font_sm.render("EN MST / TOTAL",  True, C_GRAY),              (310, 10))
    screen.blit(font_med.render(f"{en_mst} / {n_total}", True, C_NODE_MST),   (310, 28))

    screen.blit(font_sm.render("PESO MST",  True, C_GRAY),                    (450, 10))
    val_peso = f"{peso_km:.2f} km" if peso_km > 0 else "—"
    screen.blit(font_med.render(val_peso, True, C_MST_EDGE),                  (450, 28))

    screen.blit(font_sm.render("ARISTAS MST",  True, C_GRAY),                 (590, 10))
    screen.blit(font_med.render(str(n_aristas_mst), True, C_MST_EDGE),        (590, 28))

    btn_rect = None
    if done:
        btn_rect   = pygame.Rect(740, 13, 170, 38)
        btn_col    = (35, 110, 60)  if hide_non_mst else (20, 55, 40)
        btn_border = (80, 210, 120) if hide_non_mst else (50, 110, 70)
        pygame.draw.rect(screen, btn_col,    btn_rect, border_radius=6)
        pygame.draw.rect(screen, btn_border, btn_rect, 1, border_radius=6)
        lbl      = "○ Mostrar no-MST" if hide_non_mst else "● Ocultar no-MST"
        lbl_surf = font_sm.render(lbl, True, C_WHITE)
        screen.blit(lbl_surf, (btn_rect.x + btn_rect.w // 2 - lbl_surf.get_width()  // 2,
                               btn_rect.y + btn_rect.h // 2 - lbl_surf.get_height() // 2))

    estado  = "LISTO ✓" if done else ("PAUSA" if paused else "CONSTRUYENDO")
    col_est = (70, 220, 110) if done else (255, 195, 50) if paused else (160, 165, 185)
    screen.blit(font_med.render(estado, True, col_est), (WIN_W - 210, 14))

    hint = (f"vel ×{speed} [+/-]  [SPC] pausa  [ENTER] reiniciar  "
            f"[R] nuevo origen  [ESC] salir    zoom:{zoom} [rueda]  pan:[btn izq]")
    screen.blit(font_sm.render(hint, True, C_GRAY), (WIN_W - 820, 42))
    screen.blit(font_sm.render(f"  Origen: {orig_name}", True, (170, 175, 200)), (16, 44))

    return btn_rect


# ── panel lateral: lista de aristas MST ───────────────────────────────────────
def dibujar_panel_mst(screen, fonts, mst_aristas, id_to_name, peso_total, scroll):
    _, font_med, font_sm = fonts
    n = len(mst_aristas)
    if n == 0:
        return

    PX      = 16;  PY = HUD_H + 10
    PW      = PANEL_W - 22
    TITLE_H = 34;  ROW_H = 22
    MAX_H   = WIN_H - PY - 16
    vis     = (MAX_H - TITLE_H - 16) // ROW_H
    PH      = min(MAX_H, TITLE_H + vis * ROW_H + 16)

    panel = pygame.Surface((PW, PH), pygame.SRCALPHA)
    panel.fill((14, 18, 38, 225))
    pygame.draw.rect(panel, (100, 150, 90), panel.get_rect(), 1, border_radius=6)

    panel.blit(font_med.render(
        f"MST · {n} aristas · {peso_total/1000:.1f} km", True, C_WHITE), (12, 10))
    pygame.draw.line(panel, (45, 50, 80), (12, TITLE_H), (PW - 12, TITLE_H), 1)

    scroll = max(0, min(scroll, max(0, n - vis)))
    for i in range(vis):
        idx = scroll + i
        if idx >= n:
            break
        peso, origen, destino = mst_aristas[idx]
        y = TITLE_H + 8 + i * ROW_H

        linea     = destino.split('_')[0]
        badge_col = COLORES_LINEA.get(linea, (80, 85, 110))
        badge     = pygame.Rect(8, y + 2, 28, 16)
        pygame.draw.rect(panel, badge_col, badge, border_radius=3)
        btxt = font_sm.render(f"L{linea}", True, C_WHITE)
        panel.blit(btxt, (badge.x + badge.w // 2 - btxt.get_width() // 2, badge.y + 1))

        nombre = id_to_name.get(destino, destino)
        if len(nombre) > 22:
            nombre = nombre[:21] + '…'
        panel.blit(font_sm.render(nombre, True, (175, 210, 175)), (42, y + 2))

        peso_txt = "T" if peso == 0.0 else f"{int(peso)}m"
        panel.blit(font_sm.render(peso_txt, True, C_GRAY), (PW - 50, y + 2))

    if n > vis:
        sb_h = vis * ROW_H;  sb_x = PW - 8
        pygame.draw.rect(panel, (35, 40, 68), (sb_x, TITLE_H, 5, sb_h))
        ratio   = vis / n
        thumb_h = max(14, int(sb_h * ratio))
        thumb_y = TITLE_H + int((sb_h - thumb_h) * scroll / max(1, n - vis))
        pygame.draw.rect(panel, (80, 200, 110), (sb_x, thumb_y, 5, thumb_h), border_radius=2)

    screen.blit(panel, (PX, PY))


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("Cargando grafo Metro de Madrid...")
    resultado = metro_mod.generar_grafo_metro_madrid()
    if resultado is None:
        sys.exit(1)
    grafo, id_to_name, _, node_coords = resultado
    n_total = len(grafo)
    print(f"Grafo: {n_total} vértices · MST tendrá {n_total - 1} aristas.\n")

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Prim MST — Metro de Madrid")
    clock  = pygame.time.Clock()

    font_big = pygame.font.SysFont('Consolas', 26, bold=True)
    font_med = pygame.font.SysFont('Consolas', 17, bold=True)
    font_sm  = pygame.font.SysFont('Consolas', 13)
    fonts    = (font_big, font_med, font_sm)

    # ── cámara ───────────────────────────────────────────────────────────────
    lats = [c[0] for c in node_coords.values()]
    lons = [c[1] for c in node_coords.values()]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2

    cam_zoom  = 12
    origin_tx, origin_ty = compute_origin(center_lat, center_lon, cam_zoom)

    map_surf  = None
    net_surf  = None
    screen_pos: dict = {}

    # superficies de animación (se pintan incrementalmente)
    cand_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    mst_surf  = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    node_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)

    sim: dict = {}   # se rellena en reset_sim

    def rebuild_camera():
        nonlocal map_surf, net_surf, screen_pos
        map_surf   = build_map_surf(origin_tx, origin_ty, cam_zoom)
        screen_pos = build_screen_pos(node_coords, origin_tx, origin_ty, cam_zoom)
        net_surf   = build_net_surf(grafo, screen_pos)
        cand_surf.fill((0, 0, 0, 0))
        mst_surf .fill((0, 0, 0, 0))
        node_surf.fill((0, 0, 0, 0))
        # redibujar MST ya construido con las nuevas posiciones
        for _, u, v in sim.get('mst_edges', []):
            if u in screen_pos and v in screen_pos:
                pygame.draw.line(mst_surf, (*C_MST_EDGE, 220),
                                 screen_pos[u], screen_pos[v], 4)
        for nid in sim.get('mst_nodes', set()):
            if nid in screen_pos:
                pygame.draw.circle(node_surf, (*C_NODE_MST, 200), screen_pos[nid], 3)

    # ── selección inicial del origen ─────────────────────────────────────────
    screen.fill(C_BG)
    pygame.display.flip()
    origen = modal_elegir_estacion(screen, clock, fonts, grafo, id_to_name,
                                   "ORIGEN", C_ORIGIN, cancelable=False)
    if origen is None:
        pygame.quit(); sys.exit()

    def reset_sim(orig):
        cand_surf.fill((0, 0, 0, 0))
        mst_surf .fill((0, 0, 0, 0))
        node_surf.fill((0, 0, 0, 0))
        return {
            'gen'          : prim_gen(grafo, orig),
            'en_mst'       : 0,
            'peso_total'   : 0.0,
            'current'      : None,
            'mst_nodes'    : set(),
            'mst_edges'    : [],     # [(peso, u, v)] usada para rebuild_camera
            'mst_aristas'  : [],     # [(peso, u, v)] copia final al terminar
            'done'         : False,
            'hide_non_mst' : False,
            'panel_scroll' : 0,
        }

    sim = reset_sim(origen)

    print("Descargando mapa...")
    rebuild_camera()
    print("  Mapa listo.\n")

    speed     = STEPS_PER_FRAME
    paused    = False
    orig_name = id_to_name.get(origen, origen)
    panning   = False
    pan_last  = (0, 0)
    btn_rect  = None

    PANEL_AREA = pygame.Rect(16, HUD_H + 10, PANEL_W - 22, WIN_H - HUD_H - 26)

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
                        sim    = reset_sim(origen)
                        paused = False
                elif event.key == pygame.K_r:
                    nuevo = modal_elegir_estacion(
                        screen, clock, fonts, grafo, id_to_name,
                        "ORIGEN", C_ORIGIN, cancelable=True)
                    if nuevo is None:
                        continue
                    origen    = nuevo
                    orig_name = id_to_name.get(origen, origen)
                    sim       = reset_sim(origen)
                    paused    = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if btn_rect is not None and btn_rect.collidepoint(event.pos):
                        sim['hide_non_mst'] = not sim['hide_non_mst']
                    else:
                        panning  = True
                        pan_last = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    panning = False

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    dx = event.pos[0] - pan_last[0]
                    dy = event.pos[1] - pan_last[1]
                    pan_last   = event.pos
                    origin_tx -= dx / TILE_SIZE
                    origin_ty -= dy / TILE_SIZE
                    rebuild_camera()

            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if PANEL_AREA.collidepoint(mx, my) and sim['done']:
                    sim['panel_scroll'] = max(0, sim['panel_scroll'] - event.y)
                else:
                    new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, cam_zoom + event.y))
                    if new_zoom != cam_zoom:
                        mid_tx = origin_tx + WIN_W / 2 / TILE_SIZE
                        mid_ty = origin_ty + WIN_H / 2 / TILE_SIZE
                        scale  = 2 ** (new_zoom - cam_zoom)
                        cam_zoom  = new_zoom
                        origin_tx = mid_tx * scale - WIN_W / 2 / TILE_SIZE
                        origin_ty = mid_ty * scale - WIN_H / 2 / TILE_SIZE
                        rebuild_camera()

        # ── avanzar Prim ─────────────────────────────────────────────────────
        if not sim['done'] and not paused:
            for _ in range(speed):
                try:
                    step = next(sim['gen'])
                    kind = step[0]

                    if kind == 'visit':
                        _, v, peso, padre = step
                        sim['en_mst']    += 1
                        sim['current']    = v
                        sim['peso_total'] += peso
                        sim['mst_nodes'].add(v)
                        if padre is not None:
                            sim['mst_edges'].append((peso, padre, v))
                            if padre in screen_pos and v in screen_pos:
                                pygame.draw.line(mst_surf, (*C_MST_EDGE, 220),
                                                 screen_pos[padre], screen_pos[v], 4)
                        if v in screen_pos:
                            pygame.draw.circle(node_surf, (*C_NODE_MST, 200),
                                               screen_pos[v], 3)

                    elif kind == 'edge':
                        _, u, v = step
                        if u in screen_pos and v in screen_pos:
                            pygame.draw.line(cand_surf, (*C_CANDIDATE, 35),
                                             screen_pos[u], screen_pos[v], 1)

                    elif kind == 'done':
                        sim['mst_aristas'] = step[1]
                        sim['peso_total']  = step[2]
                        sim['done']        = True
                        cand_surf.fill((0, 0, 0, 0))
                        break

                except StopIteration:
                    sim['done'] = True
                    break

        # ── dibujar ──────────────────────────────────────────────────────────
        hide = sim['done'] and sim['hide_non_mst']

        screen.blit(map_surf, (0, 0))
        if not hide:
            screen.blit(net_surf,  (0, 0))
            screen.blit(cand_surf, (0, 0))
        screen.blit(mst_surf,  (0, 0))

        # vértices base no incorporados
        if not hide:
            for nid, p in screen_pos.items():
                if nid not in sim['mst_nodes']:
                    pygame.draw.circle(screen, C_NODE_BASE, p, 2)

        screen.blit(node_surf, (0, 0))

        # vértice origen
        p_orig = screen_pos.get(origen)
        if p_orig:
            pygame.draw.circle(screen, C_ORIGIN, p_orig, 5)
            pygame.draw.circle(screen, C_WHITE,  p_orig, 5, 2)
            screen.blit(font_sm.render(orig_name[:28], True, C_ORIGIN),
                        (p_orig[0] + 13, p_orig[1] - 8))

        # vértice recién incorporado (pulso animado)
        cur = sim['current']
        if cur and cur != origen and not sim['done']:
            p = screen_pos.get(cur)
            if p:
                t = pygame.time.get_ticks()
                r = 4 + int(2 * abs(math.sin(t / 180)))
                pygame.draw.circle(screen, C_CURRENT, p, r)
                pygame.draw.circle(screen, C_WHITE,   p, r, 1)

        # HUD
        btn_rect = dibujar_hud(
            screen, fonts,
            sim['en_mst'], n_total,
            sim['peso_total'] / 1000,
            max(0, sim['en_mst'] - 1),
            speed, paused, sim['done'],
            orig_name, cam_zoom, sim['hide_non_mst'])

        # panel y banner de finalización
        if sim['done'] and sim['mst_aristas']:
            dibujar_panel_mst(screen, fonts, sim['mst_aristas'],
                              id_to_name, sim['peso_total'], sim['panel_scroll'])

            banner = font_med.render(
                f"  MST completado — {len(sim['mst_aristas'])} aristas · "
                f"{sim['peso_total']/1000:.2f} km  ·  ENTER reiniciar  ",
                True, C_MST_EDGE)
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
