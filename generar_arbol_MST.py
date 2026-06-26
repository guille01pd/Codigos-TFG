"""
arbol_MST.py — Prim animado sobre un grafo precargado de NetworkX.

Grafo: random_geometric_graph (NetworkX) — vértices con posición 2D,
       pesos = distancia euclídea entre vértices vecinos.

Teclas:
  ESPACIO          pausa / reanuda
  +  /  -          aumenta / reduce velocidad
  R                nuevo origen (modal en pantalla)
  ENTER            reiniciar animación (mismo origen)
  ESC              salir
Ratón:
  Rueda            zoom in / out
  Botón izquierdo  arrastrar para desplazar
"""
import sys
import math
import heapq

import random

import pygame
import networkx as nx

# ── ventana ───────────────────────────────────────────────────────────────────
WIN_W, WIN_H    = 1720, 920
FPS             = 60
STEPS_PER_FRAME = 2

# ── paleta ────────────────────────────────────────────────────────────────────
C_BG        = (255, 255, 255)
C_EDGE_BASE = (170, 175, 200)       # aristas del grafo base
C_CANDIDATE = ( 20,  80, 200)       # aristas candidatas en la frontera de Prim
C_MST_EDGE  = (200,  90,   0)       # aristas del MST construido
C_NODE_BASE = ( 70,  80, 130)       # vértice aún no incorporado
C_NODE_MST  = ( 20, 160,  70)       # vértice incorporado al MST
C_CURRENT   = (200,  90,   0)       # vértice recién incorporado (animación)
C_ORIGIN    = (  0, 160, 140)       # vértice origen
C_WHITE     = ( 20,  25,  45)       # texto sobre fondo claro
C_GRAY      = ( 90,  95, 115)
C_HUD_BG    = ( 12,  15,  30)
C_MODAL_BG  = ( 14,  18,  38)

# ── área de dibujo (respeta HUD arriba y panel lateral izquierdo) ─────────────
HUD_H   = 64
PANEL_W = 340
MARGIN  = 55
DRAW_X0 = PANEL_W + MARGIN          # borde izquierdo del área de vértices
DRAW_Y0 = HUD_H   + MARGIN          # borde superior del área de vértices
DRAW_W  = WIN_W   - DRAW_X0 - MARGIN
DRAW_H  = WIN_H   - DRAW_Y0 - MARGIN


# ── cargar grafo de NetworkX ──────────────────────────────────────────────────
def cargar_grafo_nx():
    """
    Carga un random_geometric_graph de NetworkX.
    Toma el componente conexo más grande, asigna como peso un entero
    positivo aleatorio y devuelve (grafo_dict, id_to_name, node_pos_base).
    node_pos_base: {nid: (px, py)} en coordenadas de pantalla.
    """
    G_raw = nx.random_geometric_graph(55, 0.28, seed=42)

    # componente conexo más grande
    componente = max(nx.connected_components(G_raw), key=len)
    G = nx.convert_node_labels_to_integers(G_raw.subgraph(componente).copy())

    # peso = entero positivo aleatorio entre 1 y 99
    rng = random.Random(42)
    for u, v in G.edges():
        G[u][v]['weight'] = rng.randint(1, 99)

    # convertir al formato { vertice: [(vecino, peso), ...] }
    grafo = {n: [(v, G[n][v]['weight']) for v in G.neighbors(n)] for n in G.nodes()}

    # escalar posiciones [0,1]² → coordenadas de pantalla dentro del área de dibujo
    node_pos_base = {}
    for n in G.nodes():
        nx_, ny_ = G.nodes[n]['pos']
        node_pos_base[n] = (int(DRAW_X0 + nx_ * DRAW_W),
                            int(DRAW_Y0 + ny_ * DRAW_H))

    id_to_name = {n: f"Vértice {n:>2}" for n in G.nodes()}
    return grafo, id_to_name, node_pos_base


# ── Prim generador (para animación) ──────────────────────────────────────────
# Produce eventos para animar paso a paso:
#   ('visit', vertice, peso_arista, padre)  — vértice incorporado al MST
#   ('edge',  u, v)                         — arista añadida como candidata
#   ('done',  mst_aristas, peso_total)      — MST completo
def prim_gen(grafo, inicio):
    Conjunto_explorado = set()
    mst_aristas = []
    peso_total  = 0.0

    heap = []
    for adyacente, peso in grafo[inicio]:
        heapq.heappush(heap, (peso, inicio, adyacente))
        yield ('edge', inicio, adyacente)   # aristas candidatas iniciales

    Conjunto_explorado.add(inicio)
    yield ('visit', inicio, 0.0, None)      # origen incorporado (coste 0)

    while heap:
        peso, origen, vertice = heapq.heappop(heap)

        if vertice in Conjunto_explorado:
            continue

        Conjunto_explorado.add(vertice)
        mst_aristas.append((peso, origen, vertice))
        peso_total += peso
        yield ('visit', vertice, peso, origen)  # vértice incorporado al MST

        for adyacente, p in grafo[vertice]:
            if adyacente not in Conjunto_explorado:
                heapq.heappush(heap, (p, vertice, adyacente))
                yield ('edge', vertice, adyacente)

    yield ('done', mst_aristas, peso_total)


# ── modal de selección de vértice ─────────────────────────────────────────────
MAX_VISIBLE = 15
ITEM_H      = 38

def modal_elegir_vertice(screen, clock, fonts, grafo, id_to_name,
                          etiqueta, acento_rgb, cancelable=True):
    font_big, font_med, font_sm = fonts

    todos = sorted(
        [(nid, id_to_name.get(nid, str(nid)), len(grafo.get(nid, [])))
         for nid in grafo],
        key=lambda x: x[0]
    )

    query      = ""
    sel_idx    = 0
    scroll_off = 0

    BOX_W   = 560
    BOX_H   = WIN_H - 100
    BOX_X   = (WIN_W - BOX_W) // 2
    BOX_Y   = 50
    LIST_Y0 = BOX_Y + 120

    while True:
        q = query.upper()
        filtered = [(nid, n, g) for nid, n, g in todos
                    if not q or q in n.upper() or q in str(nid)]

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
                    if cancelable:
                        return None
                    else:
                        pygame.quit(); sys.exit()
                elif event.key == pygame.K_RETURN:
                    if filtered:
                        return filtered[sel_idx][0]
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
                if BOX_X <= mx <= BOX_X + BOX_W:
                    for i in range(min(MAX_VISIBLE, len(filtered))):
                        iy = LIST_Y0 + i * ITEM_H
                        if iy <= my < iy + ITEM_H:
                            clicked = scroll_off + i
                            if clicked == sel_idx:
                                return filtered[clicked][0]
                            sel_idx = clicked

        # ── dibujar modal ────────────────────────────────────────────────────
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
            (query + ("▌" if cursor_blink else " ")) if query else "Buscar vértice...",
            True, C_WHITE if query else C_GRAY)
        screen.blit(stxt, (srect.x + 12, srect.y + 8))

        esc_hint = "ESC cancelar  · " if cancelable else ""
        screen.blit(font_sm.render(
            f"↑↓ navegar  ·  Enter / clic×2 seleccionar  ·  {esc_hint}Rueda desplazar",
            True, C_GRAY), (BOX_X + 16, BOX_Y + 108))

        pygame.draw.line(screen, (35, 40, 70),
                         (BOX_X + 10, LIST_Y0 - 4), (BOX_X + BOX_W - 10, LIST_Y0 - 4), 1)

        for i, (nid, nombre, grado) in enumerate(filtered[scroll_off: scroll_off + MAX_VISIBLE]):
            actual_i = scroll_off + i
            iy       = LIST_Y0 + i * ITEM_H
            is_sel   = (actual_i == sel_idx)

            row = pygame.Surface((BOX_W - 32, ITEM_H - 2), pygame.SRCALPHA)
            row.fill((38, 58, 110, 220) if is_sel else (22, 26, 50, 180))
            screen.blit(row, (BOX_X + 16, iy))
            if is_sel:
                pygame.draw.rect(screen, acento_rgb,
                                 (BOX_X + 16, iy, BOX_W - 32, ITEM_H - 2), 1)

            # badge con ID del vértice
            badge = pygame.Rect(BOX_X + 22, iy + 7, 52, 22)
            pygame.draw.rect(screen, (60, 90, 150) if is_sel else (35, 45, 80),
                             badge, border_radius=4)
            bid = font_sm.render(str(nid), True, C_WHITE)
            screen.blit(bid, (badge.x + badge.w // 2 - bid.get_width() // 2, badge.y + 3))

            screen.blit(font_med.render(nombre, True, C_WHITE if is_sel else (175, 180, 210)),
                        (BOX_X + 84, iy + 8))
            screen.blit(font_sm.render(f"grado {grado}", True, C_GRAY),
                        (BOX_X + BOX_W - 110, iy + 11))

        if len(filtered) > MAX_VISIBLE:
            sb_h    = MAX_VISIBLE * ITEM_H
            sb_x    = BOX_X + BOX_W - 10
            pygame.draw.rect(screen, (35, 40, 68), (sb_x, LIST_Y0, 6, sb_h))
            ratio   = MAX_VISIBLE / len(filtered)
            thumb_h = max(18, int(sb_h * ratio))
            thumb_y = LIST_Y0 + int((sb_h - thumb_h) * scroll_off /
                                    max(1, len(filtered) - MAX_VISIBLE))
            pygame.draw.rect(screen, acento_rgb, (sb_x, thumb_y, 6, thumb_h), border_radius=3)

        pygame.display.flip()
        clock.tick(FPS)


# ── HUD ───────────────────────────────────────────────────────────────────────
def dibujar_hud(screen, fonts, en_mst, peso_total, n_total, speed, paused, done,
                orig_name, zoom_pct, hide_non_mst=False):
    font_big, font_med, font_sm = fonts

    hud = pygame.Surface((WIN_W, HUD_H))
    hud.fill(C_HUD_BG)
    screen.blit(hud, (0, 0))
    pygame.draw.line(screen, (40, 45, 70), (0, HUD_H), (WIN_W, HUD_H), 1)

    for x in (300, 440, 580):
        pygame.draw.line(screen, (45, 50, 80), (x, 8), (x, 56), 1)

    screen.blit(font_big.render("PRIM  MST", True, C_MST_EDGE), (16, 14))

    screen.blit(font_sm.render("EN MST / TOTAL",  True, C_GRAY),            (310, 10))
    screen.blit(font_med.render(f"{en_mst} / {n_total}", True, C_NODE_MST), (310, 28))

    screen.blit(font_sm.render("PESO MST",  True, C_GRAY),                         (450, 10))
    val_peso = f"{int(peso_total)}" if peso_total > 0 else "—"
    screen.blit(font_med.render(val_peso, True, C_MST_EDGE),                       (450, 28))

    screen.blit(font_sm.render("ARISTAS MST",  True, C_GRAY),                      (590, 10))
    screen.blit(font_med.render(str(max(0, en_mst - 1)), True, C_MST_EDGE),        (590, 28))

    btn_rect = None
    if done:
        btn_rect = pygame.Rect(730, 13, 170, 38)
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
    screen.blit(font_med.render(estado, True, col_est), (WIN_W - 220, 14))

    hint = (f"vel ×{speed} [+/-]  [SPC] pausa  [ENTER] reiniciar  [R] nuevo origen  [ESC] salir"
            f"    zoom:{zoom_pct:.0f}% [rueda]  pan:[btn izq]")
    screen.blit(font_sm.render(hint, True, C_GRAY), (WIN_W - 810, 42))
    screen.blit(font_sm.render(f"  Origen: {orig_name}", True, (170, 175, 200)), (16, 44))
    return btn_rect


# ── panel lateral: lista de aristas del MST ───────────────────────────────────
def dibujar_panel_mst(screen, fonts, mst_aristas, id_to_name, peso_total):
    _, font_med, font_sm = fonts
    n = len(mst_aristas)
    if n == 0:
        return

    PX      = 16
    PY      = HUD_H + 10
    PW      = PANEL_W - 22
    TITLE_H = 34
    MAX_H   = WIN_H - PY - 16
    ROW_H   = min(26, max(14, (MAX_H - TITLE_H - 16) // max(n, 1)))
    PH      = min(MAX_H, TITLE_H + ROW_H * n + 16)

    panel = pygame.Surface((PW, PH), pygame.SRCALPHA)
    panel.fill((14, 18, 38, 225))
    pygame.draw.rect(panel, (100, 150, 90), panel.get_rect(), 1, border_radius=6)

    panel.blit(font_med.render(f"MST · {n} aristas · {int(peso_total)}", True, C_WHITE),
               (12, 10))
    pygame.draw.line(panel, (45, 50, 80), (12, TITLE_H), (PW - 12, TITLE_H), 1)

    for i, (peso, origen, destino) in enumerate(mst_aristas):
        y     = TITLE_H + 8 + i * ROW_H
        linea = f"{id_to_name.get(origen, origen)} → {id_to_name.get(destino, destino)}"
        if len(linea) > 30:
            linea = linea[:29] + '…'
        panel.blit(font_sm.render(linea,         True, (175, 210, 175)), (12,      y))
        panel.blit(font_sm.render(str(int(peso)), True, C_GRAY),           (PW - 72, y))

    screen.blit(panel, (PX, PY))


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("Cargando grafo de NetworkX (random_geometric_graph, seed=42)...")
    grafo, id_to_name, node_pos_base = cargar_grafo_nx()
    n_total = len(grafo)
    n_aristas = sum(len(v) for v in grafo.values()) // 2
    print(f"Grafo: {n_total} vértices, {n_aristas} aristas.\n")

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Prim MST — NetworkX random_geometric_graph")
    clock  = pygame.time.Clock()

    font_big = pygame.font.SysFont('Consolas', 26, bold=True)
    font_med = pygame.font.SysFont('Consolas', 17, bold=True)
    font_sm  = pygame.font.SysFont('Consolas', 13)
    fonts    = (font_big, font_med, font_sm)

    # ── cámara ───────────────────────────────────────────────────────────────
    zoom   = 1.0
    pan_x  = 0.0
    pan_y  = 0.0
    panning  = False
    pan_last = (0, 0)

    # centro del área de dibujo (pivote del zoom)
    cx_draw = DRAW_X0 + DRAW_W / 2
    cy_draw = DRAW_Y0 + DRAW_H / 2

    def spos():
        """Aplica zoom y pan a las posiciones base; devuelve dict {nid: (px,py)}."""
        result = {}
        for nid, (bx, by) in node_pos_base.items():
            result[nid] = (int(cx_draw + (bx - cx_draw) * zoom + pan_x),
                           int(cy_draw + (by - cy_draw) * zoom + pan_y))
        return result

    # ── selección inicial ────────────────────────────────────────────────────
    screen.fill(C_BG)
    pygame.display.flip()
    origen = modal_elegir_vertice(screen, clock, fonts, grafo, id_to_name,
                                  "ORIGEN", C_ORIGIN, cancelable=False)
    if origen is None:
        pygame.quit(); sys.exit()

    def reset_sim(orig):
        return {
            'gen'        : prim_gen(grafo, orig),
            'en_mst'     : 0,
            'peso_total' : 0.0,
            'current'    : None,
            'mst_nodes'  : set(),
            'mst_edges'  : [],      # [(origen, destino), ...]
            'cand_edges' : [],      # [(u, v), ...]
            'mst_aristas'  : [],      # [(peso, origen, destino), ...]
            'done'         : False,
            'hide_non_mst' : False,
        }

    sim       = reset_sim(origen)
    speed     = STEPS_PER_FRAME
    paused    = False
    orig_name = id_to_name.get(origen, str(origen))

    btn_rect = None
    running = True
    while running:
        sp = spos()

        # ── eventos ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    speed = min(speed + 1, 30)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed = max(speed - 1, 1)
                elif event.key == pygame.K_RETURN:
                    if sim['done']:
                        sim    = reset_sim(origen)
                        paused = False
                elif event.key == pygame.K_r:
                    nuevo = modal_elegir_vertice(
                        screen, clock, fonts, grafo, id_to_name,
                        "ORIGEN", C_ORIGIN, cancelable=True)
                    if nuevo is None:
                        continue
                    origen    = nuevo
                    orig_name = id_to_name.get(origen, str(origen))
                    sim       = reset_sim(origen)
                    paused    = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if btn_rect is not None and btn_rect.collidepoint(event.pos):
                        sim['hide_non_mst'] = not sim['hide_non_mst']
                    else:
                        panning = True; pan_last = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    panning = False

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    pan_x += event.pos[0] - pan_last[0]
                    pan_y += event.pos[1] - pan_last[1]
                    pan_last = event.pos

            elif event.type == pygame.MOUSEWHEEL:
                factor = 1.12 if event.y > 0 else (1 / 1.12)
                zoom   = max(0.3, min(5.0, zoom * factor))

        # ── avanzar Prim ─────────────────────────────────────────────────────
        if not sim['done'] and not paused:
            for _ in range(speed):
                try:
                    step = next(sim['gen'])
                    kind = step[0]

                    if kind == 'visit':
                        _, v, peso_arista, padre = step
                        sim['en_mst']    += 1
                        sim['current']    = v
                        sim['peso_total'] += peso_arista
                        sim['mst_nodes'].add(v)
                        if padre is not None:
                            sim['mst_edges'].append((padre, v))

                    elif kind == 'edge':
                        _, u, v = step
                        sim['cand_edges'].append((u, v))

                    elif kind == 'done':
                        sim['mst_aristas'] = step[1]
                        sim['peso_total']  = step[2]
                        sim['done']        = True
                        break

                except StopIteration:
                    sim['done'] = True
                    break

        # ── dibujar ──────────────────────────────────────────────────────────
        screen.fill(C_BG)

        # aristas base del grafo (se ocultan cuando el MST está completo y se activó el filtro)
        hide = sim['done'] and sim['hide_non_mst']
        if not hide:
            drawn = set()
            for u, vecinos in grafo.items():
                pu = sp.get(u)
                if pu is None:
                    continue
                for v, _ in vecinos:
                    key = (min(u, v), max(u, v))
                    if key in drawn:
                        continue
                    drawn.add(key)
                    pv = sp.get(v)
                    if pv:
                        pygame.draw.line(screen, C_EDGE_BASE, pu, pv, 1)

        # aristas candidatas (frontera de Prim)
        if not hide:
            for u, v in sim['cand_edges']:
                pu, pv = sp.get(u), sp.get(v)
                if pu and pv:
                    pygame.draw.line(screen, (*C_CANDIDATE, 60), pu, pv, 1)

        # aristas del MST
        for u, v in sim['mst_edges']:
            pu, pv = sp.get(u), sp.get(v)
            if pu and pv:
                pygame.draw.line(screen, C_MST_EDGE, pu, pv, 3)

        # vértices base
        for nid, p in sp.items():
            pygame.draw.circle(screen, C_NODE_BASE, p, 5)

        # vértices incorporados al MST
        for nid in sim['mst_nodes']:
            p = sp.get(nid)
            if p:
                pygame.draw.circle(screen, C_NODE_MST, p, 7)

        # vértice origen
        p_orig = sp.get(origen)
        if p_orig:
            pygame.draw.circle(screen, C_ORIGIN, p_orig, 10)
            pygame.draw.circle(screen, C_WHITE,  p_orig, 10, 2)
            screen.blit(font_sm.render(orig_name, True, C_ORIGIN),
                        (p_orig[0] + 13, p_orig[1] - 8))

        # vértice recién incorporado (pulso animado)
        cur = sim['current']
        if cur and cur != origen and not sim['done']:
            p = sp.get(cur)
            if p:
                t = pygame.time.get_ticks()
                r = 7 + int(3 * abs(math.sin(t / 180)))
                pygame.draw.circle(screen, C_CURRENT, p, r)
                pygame.draw.circle(screen, C_WHITE,   p, r, 1)

        # HUD
        btn_rect = dibujar_hud(screen, fonts,
                               sim['en_mst'], sim['peso_total'], n_total,
                               speed, paused, sim['done'],
                               orig_name, zoom * 100, sim['hide_non_mst'])

        # panel y banner de finalización
        if sim['done'] and sim['mst_aristas']:
            dibujar_panel_mst(screen, fonts, sim['mst_aristas'], id_to_name, sim['peso_total'])

            banner = font_med.render(
                f"  MST completado — {len(sim['mst_aristas'])} aristas · "
                f"peso {int(sim['peso_total'])}  ·  ENTER reiniciar  ",
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
