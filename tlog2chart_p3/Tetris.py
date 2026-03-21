"""
Tetris.py

Single-file Tetris implementation using pygame.
Features:
 - Play manually (keyboard) or let the AI play
 - 7-bag randomizer, hold, next queue, scoring, levels
 - AI evaluates all legal placements using Tetris heuristics

Controls (User mode):
 - Left/Right: arrow keys
 - Rotate clockwise: Up
 - Soft drop: Down
 - Hard drop: Space
 - Hold: Left Shift
 - Pause: P
 - Restart: R

Run: python Tetris.py
"""

import pygame
import random
import copy
import json
import os
import sys
import subprocess
from collections import deque

# --- Configuration ---
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
BLOCK = 30  # pixel size of a block
SIDE_PANEL = 200
WINDOW_WIDTH = BOARD_WIDTH * BLOCK + SIDE_PANEL
WINDOW_HEIGHT = BOARD_HEIGHT * BLOCK
FPS = 60
DEBUG_HITBOX = False  # set True to visualize side-panel clickable areas

# Colors
BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
WHITE = (255, 255, 255)
COLORS = {
    'I': (0, 240, 240),
    'O': (240, 240, 0),
    'T': (160, 0, 240),
    'S': (0, 240, 0),
    'Z': (240, 0, 0),
    'J': (0, 0, 240),
    'L': (240, 160, 0),
}

# Tetromino definitions: rotation states as lists of (x,y) coordinates
TETROMINOES = {
    'I': [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
    ],
    'O': [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    'T': [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'S': [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
    ],
    'Z': [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
    ],
    'J': [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    'L': [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}

# Heuristic weights for AI (reasonable defaults)
AI_WEIGHTS = {
    'lines': 0.760666,
    'aggregate_height': -0.510066,
    'holes': -0.35663,
    'bumpiness': -0.184483,
}

# Maximum delay per AI action in seconds when slider is at max (slider maps 0..1 -> 0..MAX_AI_DELAY)
MAX_AI_DELAY = 0.25
HIGH_SCORES_FILE = 'highscores.json'
MAX_HIGH_SCORES = 10

# Music defaults
def _module_resource_path(fname: str) -> str:
    """Return a path to a resource located next to this module file.

    This ensures music and other assets are found when launched from a different
    current working directory or when packaged as a module.
    """
    return os.path.join(os.path.dirname(__file__), fname)

MUSIC_FILE_CANDIDATES = [_module_resource_path('music.ogg'), _module_resource_path('music.mp3')]
MUSIC_ENABLED = True
MUSIC_LOADED = False
MUSIC_VOLUME = 0.5


class Piece:
    def __init__(self, shape):
        self.shape = shape
        self.rot = 0
        self.x = BOARD_WIDTH // 2 - 2
        self.y = 0

    @property
    def states(self):
        return TETROMINOES[self.shape]

    def cells(self, rot=None, x=None, y=None):
        if rot is None:
            rot = self.rot
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        state = self.states[rot % len(self.states)]
        return [(x + cx, y + cy) for (cx, cy) in state]

    def rotate(self, direction=1):
        self.rot = (self.rot + direction) % len(self.states)


def create_board():
    return [[None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]


def valid_position(board, piece, dx=0, dy=0, rot=None):
    x = piece.x + dx
    y = piece.y + dy
    rot = piece.rot if rot is None else rot
    for (cx, cy) in piece.states[rot % len(piece.states)]:
        bx = x + cx
        by = y + cy
        if bx < 0 or bx >= BOARD_WIDTH or by < 0 or by >= BOARD_HEIGHT:
            return False
        if board[by][bx] is not None:
            return False
    return True


def lock_piece(board, piece):
    for (x, y) in piece.cells():
        if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH:
            board[y][x] = piece.shape


def clear_lines(board):
    new_board = [row for row in board if any(cell is None for cell in row)]
    lines_cleared = BOARD_HEIGHT - len(new_board)
    for _ in range(lines_cleared):
        new_board.insert(0, [None for _ in range(BOARD_WIDTH)])
    return new_board, lines_cleared


def draw_text(surface, text, size, x, y, color=WHITE):
    font = pygame.font.SysFont('Consolas', size)
    surf = font.render(text, True, color)
    surface.blit(surf, (x, y))


def draw_board(surface, board, offset_x=0, offset_y=0):
    # background
    for r in range(BOARD_HEIGHT):
        for c in range(BOARD_WIDTH):
            rect = pygame.Rect(offset_x + c * BLOCK, offset_y + r * BLOCK, BLOCK, BLOCK)
            pygame.draw.rect(surface, GRAY, rect, 1)
            val = board[r][c]
            if val is not None:
                pygame.draw.rect(surface, COLORS[val], rect.inflate(-2, -2))


def draw_piece(surface, piece, offset_x=0, offset_y=0, ghost=False):
    color = COLORS[piece.shape]
    if ghost:
        color = tuple(min(255, int(c * 0.35)) for c in color)
    for (x, y) in piece.cells():
        if y >= 0:
            rect = pygame.Rect(offset_x + x * BLOCK, offset_y + y * BLOCK, BLOCK, BLOCK)
            pygame.draw.rect(surface, color, rect.inflate(-2, -2))


def draw_next(surface, queue, offset_x, offset_y):
    # Show only 2 next pieces in a larger preview area
    draw_text(surface, 'Next', 20, offset_x, offset_y)
    # scale the preview relative to BLOCK
    preview_block = int(BLOCK * 0.7)
    oy = offset_y + 30
    # vertical spacing between previews
    step_y = preview_block * 4 + 8
    for i, shape in enumerate(queue[:2]):
        states = TETROMINOES[shape][0]
        for (x, y) in states:
            rect = pygame.Rect(offset_x + x * preview_block + 10, oy + y * preview_block + i * step_y, preview_block, preview_block)
            pygame.draw.rect(surface, COLORS[shape], rect.inflate(-1, -1))


def draw_hold(surface, hold, offset_x, offset_y):
    draw_text(surface, 'Hold', 20, offset_x, offset_y)
    if hold is None:
        return
    # use same preview scale as draw_next for visual consistency
    preview_block = int(BLOCK * 0.7)
    states = TETROMINOES[hold][0]
    oy = offset_y + 30
    for (x, y) in states:
        rect = pygame.Rect(offset_x + x * preview_block + 10, oy + y * preview_block, preview_block, preview_block)
        pygame.draw.rect(surface, COLORS[hold], rect.inflate(-1, -1))


def draw_volume_slider(surface, value, offset_x, offset_y):
    # value: 0.0..1.0
    w = 150
    h = 10
    rect = pygame.Rect(offset_x, offset_y, w, h)
    # background bar
    pygame.draw.rect(surface, GRAY, rect)
    # filled portion
    fill_rect = pygame.Rect(offset_x, offset_y, int(w * value), h)
    pygame.draw.rect(surface, WHITE, fill_rect)
    # knob
    knob_x = offset_x + int(w * value)
    knob_rect = pygame.Rect(knob_x - 4, offset_y - 6, 8, h + 12)
    pygame.draw.rect(surface, COLORS['I'], knob_rect)
    # label
    draw_text(surface, f'Volume', 18, offset_x, offset_y - 24)
    draw_text(surface, f'{int(value*100)}%', 14, offset_x + w + 10, offset_y - 4)


def draw_ai_slider(surface, value, offset_x, offset_y):
    # value: 0.0..1.0
    w = 150
    h = 10
    rect = pygame.Rect(offset_x, offset_y, w, h)
    # background bar
    pygame.draw.rect(surface, GRAY, rect)
    # filled portion
    fill_rect = pygame.Rect(offset_x, offset_y, int(w * value), h)
    pygame.draw.rect(surface, WHITE, fill_rect)
    # knob
    knob_x = offset_x + int(w * value)
    knob_rect = pygame.Rect(knob_x - 4, offset_y - 6, 8, h + 12)
    pygame.draw.rect(surface, COLORS['T'], knob_rect)
    # label
    draw_text(surface, f'AI Speed', 18, offset_x, offset_y - 24)
    ms = int(value * MAX_AI_DELAY * 1000)
    draw_text(surface, f'{ms} ms/action', 14, offset_x + w + 10, offset_y - 4)


def draw_music_status(surface, offset_x, offset_y):
    # small music indicator (clickable in-game)
    status = 'On' if MUSIC_ENABLED and MUSIC_LOADED else 'Off'
    draw_text(surface, f'Music: {status} (M)', 16, offset_x, offset_y)


def get_heights(board):
    heights = [0] * BOARD_WIDTH
    for c in range(BOARD_WIDTH):
        for r in range(BOARD_HEIGHT):
            if board[r][c] is not None:
                heights[c] = BOARD_HEIGHT - r
                break
    return heights


def count_holes(board):
    holes = 0
    for c in range(BOARD_WIDTH):
        block_seen = False
        for r in range(BOARD_HEIGHT):
            if board[r][c] is not None:
                block_seen = True
            elif block_seen and board[r][c] is None:
                holes += 1
    return holes


def aggregate_height(heights):
    return sum(heights)


def bumpiness(heights):
    b = 0
    for i in range(len(heights) - 1):
        b += abs(heights[i] - heights[i + 1])
    return b


def ai_best_move(board, piece, next_queue):
    # Simulate all rotations and x positions, choose best by heuristics
    best_score = -float('inf')
    best = None
    for rot in range(len(piece.states)):
        # compute min and max x for placement by checking piece width
        xs = [cx for (cx, cy) in piece.states[rot]]
        min_c = min(xs)
        max_c = max(xs)
        for x in range(-min_c, BOARD_WIDTH - max_c):
            # copy piece for simulation
            sim_piece = Piece(piece.shape)
            sim_piece.x = x
            sim_piece.rot = rot
            sim_piece.y = 0
            # drop until collision
            while valid_position(board, sim_piece, dy=1):
                sim_piece.y += 1
            # if initial position invalid, skip
            if not valid_position(board, sim_piece):
                continue
            # simulate board
            board_copy = copy.deepcopy(board)
            lock_piece(board_copy, sim_piece)
            board_copy, lines = clear_lines(board_copy)
            heights = get_heights(board_copy)
            agg = aggregate_height(heights)
            holes = count_holes(board_copy)
            bump = bumpiness(heights)
            score = (
                AI_WEIGHTS['lines'] * lines
                + AI_WEIGHTS['aggregate_height'] * agg
                + AI_WEIGHTS['holes'] * holes
                + AI_WEIGHTS['bumpiness'] * bump
            )
            if score > best_score:
                best_score = score
                best = (rot, x)
    return best


def ai_tetris_move(board, piece, next_queue):
    # Prioritize placements that clear the most lines (prefer 4-line clears),
    # then break ties using the same heuristic as ai_best_move.
    best_score = -float('inf')
    best = None
    for rot in range(len(piece.states)):
        xs = [cx for (cx, cy) in piece.states[rot]]
        min_c = min(xs)
        max_c = max(xs)
        for x in range(-min_c, BOARD_WIDTH - max_c):
            sim_piece = Piece(piece.shape)
            sim_piece.x = x
            sim_piece.rot = rot
            sim_piece.y = 0
            while valid_position(board, sim_piece, dy=1):
                sim_piece.y += 1
            if not valid_position(board, sim_piece):
                continue
            board_copy = copy.deepcopy(board)
            lock_piece(board_copy, sim_piece)
            board_copy, lines = clear_lines(board_copy)
            # Primary objective: maximize immediate cleared lines
            # Secondary: use heuristic score to prefer better configurations
            heights = get_heights(board_copy)
            agg = aggregate_height(heights)
            holes = count_holes(board_copy)
            bump = bumpiness(heights)
            heuristic_score = (
                AI_WEIGHTS['lines'] * lines
                + AI_WEIGHTS['aggregate_height'] * agg
                + AI_WEIGHTS['holes'] * holes
                + AI_WEIGHTS['bumpiness'] * bump
            )
            # Give very large bonus for 4-line clears (Tetrises) so they are preferred
            tetris_bonus = 1000 if lines == 4 else 0
            score = (lines * 10000) + tetris_bonus + heuristic_score
            if score > best_score:
                best_score = score
                best = (rot, x)
    return best


def load_high_scores():
    if not os.path.exists(HIGH_SCORES_FILE):
        return []
    try:
        with open(HIGH_SCORES_FILE, 'r', encoding='utf-8') as f:
            scores = json.load(f)
            if not isinstance(scores, list):
                return []
            # normalize older formats (e.g., list of numbers or missing fields)
            normalized = []
            for entry in scores:
                if isinstance(entry, dict):
                    # ensure keys exist
                    normalized.append({
                        'name': entry.get('name', '---'),
                        'mode': entry.get('mode', entry.get('mode', '')),
                        'score': int(entry.get('score', 0)),
                        'lines': int(entry.get('lines', 0)),
                        'level': int(entry.get('level', 0)),
                    })
                elif isinstance(entry, (int, float)):
                    # legacy number only
                    normalized.append({'name': '---', 'mode': '', 'score': int(entry), 'lines': 0, 'level': 0})
                else:
                    # unknown format, skip
                    continue
            # sort to ensure order
            normalized.sort(key=lambda e: (e.get('score', 0), e.get('lines', 0)), reverse=True)
            return normalized
    except Exception:
        return []


def save_high_scores(scores):
    try:
        with open(HIGH_SCORES_FILE, 'w', encoding='utf-8') as f:
            json.dump(scores, f, indent=2)
    except Exception:
        pass


def add_high_score(entry):
    # entry: dict with keys 'score','lines','mode','name','level'
    scores = load_high_scores()
    # map mode to friendly name
    m = entry.get('mode', '')
    if m == 'ai_greedy':
        entry['mode'] = 'AI Greedy'
    elif m == 'ai_tetris':
        entry['mode'] = 'AI Tetris'
    elif m == 'user':
        entry['mode'] = 'User'
    # ensure fields
    entry['name'] = entry.get('name', '---')
    entry['score'] = int(entry.get('score', 0))
    entry['lines'] = int(entry.get('lines', 0))
    entry['level'] = int(entry.get('level', 0))
    scores.append(entry)
    # sort by score desc, then lines desc
    scores.sort(key=lambda e: (e.get('score', 0), e.get('lines', 0)), reverse=True)
    # keep top N
    scores = scores[:MAX_HIGH_SCORES]
    save_high_scores(scores)
    return scores


def show_high_scores(screen, clock):
    # display highscores and wait for key to return
    scores = load_high_scores()
    running = True
    # fonts for title, headers and entries
    title_size = 36
    header_size = 16
    entry_size = 16
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                return
        screen.fill(BLACK)
        # Title
        draw_text(screen, 'HIGH SCORES', title_size, 20, 8)
        # Column headers (compact layout so we can fit top 10)
        header_y = 56
        col_rank = 20
        col_name = 60
        col_mode = 180
        col_score = 300
        col_lines = 380
        col_level = 440
        # draw headers in red to stand out
        draw_text(screen, 'Rank', header_size, col_rank, header_y, color=(200, 30, 30))
        draw_text(screen, 'Name', header_size, col_name, header_y, color=(200, 30, 30))
        draw_text(screen, 'Mode', header_size, col_mode, header_y, color=(200, 30, 30))
        draw_text(screen, 'Score', header_size, col_score, header_y, color=(200, 30, 30))
        draw_text(screen, 'Lines', header_size, col_lines, header_y, color=(200, 30, 30))
        draw_text(screen, 'Level', header_size, col_level, header_y, color=(200, 30, 30))
        # entries
        start_y = header_y + 26
        line_h = 24
        if not scores:
            draw_text(screen, 'No high scores yet.', entry_size, 20, start_y)
        else:
            for i, s in enumerate(scores):
                y = start_y + i * line_h
                # columns: rank, name, mode, score (formatted), lines, level
                draw_text(screen, f"{i+1}.", entry_size, col_rank, y)
                draw_text(screen, f"{s.get('name','')}", entry_size, col_name, y)
                draw_text(screen, f"{s.get('mode','')}", entry_size, col_mode, y)
                # formatted score with thousands separator
                draw_text(screen, f"{s.get('score',0):,}", entry_size, col_score, y)
                draw_text(screen, f"{s.get('lines',0)}", entry_size, col_lines, y)
                draw_text(screen, f"{s.get('level',0)}", entry_size, col_level, y)
        draw_text(screen, 'Press any key to return', 14, 20, WINDOW_HEIGHT - 40)
        pygame.display.flip()
        clock.tick(10)


def new_bag():
    bag = list(TETROMINOES.keys())
    random.shuffle(bag)
    return deque(bag)


def spawn_piece(queue):
    if len(queue) < 7:
        queue.extend(new_bag())
    shape = queue.popleft()
    return Piece(shape)


def init_music():
    global MUSIC_LOADED, MUSIC_ENABLED
    # try to initialize mixer and load a music file if present
    try:
        pygame.mixer.init()
        for fname in MUSIC_FILE_CANDIDATES:
            if os.path.exists(fname):
                pygame.mixer.music.load(fname)
                MUSIC_LOADED = True
                if MUSIC_ENABLED:
                    try:
                        pygame.mixer.music.play(-1)
                        try:
                            pygame.mixer.music.set_volume(MUSIC_VOLUME)
                        except Exception:
                            pass
                    except Exception:
                        pass
                break
    except Exception:
        MUSIC_LOADED = False


def toggle_music():
    global MUSIC_ENABLED, MUSIC_LOADED
    MUSIC_ENABLED = not MUSIC_ENABLED
    if not MUSIC_LOADED:
        return
    if MUSIC_ENABLED:
        try:
            pygame.mixer.music.play(-1)
            try:
                pygame.mixer.music.set_volume(MUSIC_VOLUME)
            except Exception:
                pass
        except Exception:
            pass
    else:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


def prompt_for_name(screen, clock, prompt='Enter name (max 12 chars):', maxlen=12, default='PLAYER'):
    # Simple text input with backspace/enter
    name = ''
    active = True
    while active:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return default
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    active = False
                    break
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    return default
                else:
                    # use event.unicode to get actual character
                    ch = event.unicode
                    if ch and len(name) < maxlen and (32 <= ord(ch) <= 126):
                        name += ch
        screen.fill(BLACK)
        draw_text(screen, prompt, 24, 20, 120)
        # draw input box
        pygame.draw.rect(screen, GRAY, pygame.Rect(20, 160, 360, 40))
        draw_text(screen, name + ('|' if int(pygame.time.get_ticks() / 300) % 2 == 0 else ''), 28, 26, 164, color=WHITE)
        draw_text(screen, 'Enter=OK Esc=Cancel', 16, 20, 220)
        pygame.display.flip()
        clock.tick(30)
    if name.strip() == '':
        return default
    return name.strip()


def main():
    pygame.init()
    # initialize mixer and load music if available
    try:
        init_music()
    except Exception:
        pass
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption('Tetris - User / AI')
    clock = pygame.time.Clock()

    running = True
    while running:
        mode = menu(screen, clock)
        if mode == 'exit':
            break
        if mode == 'highscores':
            show_high_scores(screen, clock)
            continue
        result = game(screen, clock, mode)
        if result == 'exit':
            running = False

    pygame.quit()


def launch_subprocess():
    """Launch this module in a separate Python process using -m.

    Returns True if the subprocess was started, False on failure.
    """
    try:
        python = sys.executable or 'python'
        cmd = [python, '-m', 'tlog2chart_p3.Tetris']
        # package parent (project root) ensures the tlog2chart_p3 package is importable
        pkg_parent = os.path.dirname(os.path.dirname(__file__))
        subprocess.Popen(cmd, cwd=pkg_parent)
        return True
    except Exception:
        return False


def run(blocking: bool = True, as_process: bool = True):
    """Run the Tetris application.

    Parameters:
      blocking: if True and as_process is False, this call blocks until the game exits.
      as_process: if True, attempt to run the game as a separate process (recommended).

    When called from a Tkinter GUI, use run(blocking=False, as_process=True) so the
    game runs in its own process and does not interfere with the Tk event loop.
    """
    if as_process:
        ok = launch_subprocess()
        if ok:
            return
        # fallback to in-process call
    if blocking:
        main()
    else:
        # run in background thread (best-effort; pygame may require main thread on some platforms)
        import threading

        t = threading.Thread(target=main, daemon=True)
        t.start()


def menu(screen, clock):
    font = pygame.font.SysFont('Consolas', 30)
    selected = 0
    options = ['Play (User)', 'Play (AI - Greedy)', 'Play (AI - Tetris)', 'High Scores', 'Exit']
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'exit'
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if selected == 0:
                        return 'user'
                    elif selected == 1:
                        return 'ai_greedy'
                    elif selected == 2:
                        return 'ai_tetris'
                    elif selected == 3:
                        return 'highscores'
                    else:
                        return 'exit'

        screen.fill(BLACK)
        draw_text(screen, 'TETRIS', 60, 20, 20)
        for i, opt in enumerate(options):
            color = WHITE if i == selected else GRAY
            surf = font.render(opt, True, color)
            screen.blit(surf, (50, 120 + i * 40))
        # brief controls shown at the bottom of the main menu (manual) - split into 2 lines
        draw_text(screen, 'Controls: ←/→ Move  Up=Rotate  Down=Soft  Space=Hard', 16, 20, WINDOW_HEIGHT - 56)
        draw_text(screen, 'Shift=Hold  P=Pause  R=Restart  M=Music', 16, 20, WINDOW_HEIGHT - 32)
        pygame.display.flip()
        clock.tick(FPS)


def game(screen, clock, mode='user'):
    global MUSIC_VOLUME
    board = create_board()
    queue = new_bag()
    # ensure queue has a few pieces
    queue.extend(new_bag())
    current = spawn_piece(queue)
    next_queue = list(queue)
    hold = None
    hold_locked = False
    score = 0
    level = 1
    total_lines = 0
    drop_timer = 0.0
    drop_interval = max(0.05, 1.0 - (level - 1) * 0.1)
    fall_speed = drop_interval
    running = True
    paused = False
    ai_state = None  # will hold {'rot':int,'target_x':int,'stage': 'rotate'|'move'|'drop'}
    ai_action_timer = 0.0
    ai_slider_value = 0.5  # 0.0..1.0, default mid = noticeable slowdown
    ai_dragging = False
    vol_dragging = False

    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'exit'
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_r:
                    return 'restart'
                if event.key == pygame.K_m:
                    # toggle music
                    toggle_music()
                if paused:
                    continue
                if mode == 'user':
                    if event.key == pygame.K_LEFT:
                        if valid_position(board, current, dx=-1):
                            current.x -= 1
                    elif event.key == pygame.K_RIGHT:
                        if valid_position(board, current, dx=1):
                            current.x += 1
                    elif event.key == pygame.K_UP:
                        new_rot = (current.rot + 1) % len(current.states)
                        if valid_position(board, current, rot=new_rot):
                            current.rotate(1)
                    elif event.key == pygame.K_DOWN:
                        if valid_position(board, current, dy=1):
                            current.y += 1
                    elif event.key == pygame.K_SPACE:
                        # hard drop
                        while valid_position(board, current, dy=1):
                            current.y += 1
                        lock_piece(board, current)
                        board, lines = clear_lines(board)
                        if lines:
                            score += score_from_lines(lines, level)
                            total_lines += lines
                        hold_locked = False
                        current = spawn_piece(queue)
                    elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                        if not hold_locked:
                            if hold is None:
                                hold = current.shape
                                current = spawn_piece(queue)
                            else:
                                cur_shape = current.shape
                                current = Piece(hold)
                                hold = cur_shape
                            hold_locked = True
            # Mouse handling for AI slider and music/volume controls
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                side_x = BOARD_WIDTH * BLOCK + 10
                # updated hitboxes to match rendering positions: music, ai slider, volume slider
                # rendering uses: music at y=440, ai slider at y=500, volume slider at y=540
                music_rect = pygame.Rect(side_x, 440, 150, 20)
                slider_rect = pygame.Rect(side_x, 500, 150, 10)
                vol_rect = pygame.Rect(side_x, 540, 150, 10)
                if slider_rect.collidepoint(mx, my):
                    ai_dragging = True
                    # update slider value immediately
                    rel = (mx - slider_rect.x) / slider_rect.w
                    ai_slider_value = max(0.0, min(1.0, rel))
                if music_rect.collidepoint(mx, my):
                    # toggle music on click
                    toggle_music()
                if vol_rect.collidepoint(mx, my):
                    vol_dragging = True
                    rel = (mx - vol_rect.x) / vol_rect.w
                    MUSIC_VOLUME = max(0.0, min(1.0, rel))
                    # apply volume immediately if loaded
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
            if event.type == pygame.MOUSEBUTTONUP:
                ai_dragging = False
                vol_dragging = False
            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                side_x = BOARD_WIDTH * BLOCK + 10
                if ai_dragging:
                    slider_rect = pygame.Rect(side_x, 500, 150, 10)
                    rel = (mx - slider_rect.x) / slider_rect.w
                    ai_slider_value = max(0.0, min(1.0, rel))
                if vol_dragging:
                    vol_rect = pygame.Rect(side_x, 540, 150, 10)
                    rel = (mx - vol_rect.x) / vol_rect.w
                    MUSIC_VOLUME = max(0.0, min(1.0, rel))
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass

        if paused:
            # draw paused screen
            screen.fill(BLACK)
            draw_text(screen, 'PAUSED', 60, 50, 80)
            draw_text(screen, 'Press P to resume', 24, 50, 160)
            pygame.display.flip()
            continue

        # AI planning on spawn (set up ai_state)
        if mode in ('ai_greedy', 'ai_tetris') and ai_state is None:
            if mode == 'ai_greedy':
                plan = ai_best_move(board, current, next_queue)
            else:
                plan = ai_tetris_move(board, current, next_queue)
            if plan is not None:
                rot, tx = plan
                ai_state = {'rot': rot, 'target_x': tx, 'stage': 'rotate'}
                ai_action_timer = 0.0

        # compute action delay from slider
        ai_action_delay = ai_slider_value * MAX_AI_DELAY

        # Apply AI state if present: step rotate -> move -> drop
        if mode in ('ai_greedy', 'ai_tetris') and ai_state is not None:
            # if delay is zero, perform actions without waiting
            if ai_action_delay == 0:
                # perform all instantly (old behavior)
                rot = ai_state['rot']
                target_x = ai_state['target_x']
                # rotate until rot matches
                while current.rot != rot:
                    new_rot = (current.rot + 1) % len(current.states)
                    if valid_position(board, current, rot=new_rot):
                        current.rotate(1)
                    else:
                        if valid_position(board, current, dx=-1, rot=new_rot):
                            current.x -= 1
                            current.rotate(1)
                        elif valid_position(board, current, dx=1, rot=new_rot):
                            current.x += 1
                            current.rotate(1)
                        else:
                            break
                # move horizontally
                while current.x < target_x and valid_position(board, current, dx=1):
                    current.x += 1
                while current.x > target_x and valid_position(board, current, dx=-1):
                    current.x -= 1
                # hard drop
                while valid_position(board, current, dy=1):
                    current.y += 1
                lock_piece(board, current)
                board, lines = clear_lines(board)
                if lines:
                    score += score_from_lines(lines, level)
                    total_lines += lines
                hold_locked = False
                current = spawn_piece(queue)
                ai_state = None
            else:
                # throttled step-by-step approach
                ai_action_timer += dt
                if ai_action_timer >= ai_action_delay:
                    ai_action_timer = 0.0
                    stage = ai_state['stage']
                    rot = ai_state['rot']
                    target_x = ai_state['target_x']
                    if stage == 'rotate':
                        if current.rot != rot:
                            new_rot = (current.rot + 1) % len(current.states)
                            if valid_position(board, current, rot=new_rot):
                                current.rotate(1)
                            else:
                                # try simple wall kicks
                                if valid_position(board, current, dx=-1, rot=new_rot):
                                    current.x -= 1
                                    current.rotate(1)
                                elif valid_position(board, current, dx=1, rot=new_rot):
                                    current.x += 1
                                    current.rotate(1)
                                else:
                                    # cannot rotate; skip to move stage
                                    ai_state['stage'] = 'move'
                        else:
                            ai_state['stage'] = 'move'
                    elif stage == 'move':
                        if current.x < target_x and valid_position(board, current, dx=1):
                            current.x += 1
                        elif current.x > target_x and valid_position(board, current, dx=-1):
                            current.x -= 1
                        else:
                            ai_state['stage'] = 'drop'
                    elif stage == 'drop':
                        # perform hard drop
                        while valid_position(board, current, dy=1):
                            current.y += 1
                        lock_piece(board, current)
                        board, lines = clear_lines(board)
                        if lines:
                            score += score_from_lines(lines, level)
                            total_lines += lines
                        hold_locked = False
                        current = spawn_piece(queue)
                        ai_state = None

        # gravity (user mode auto fall)
        drop_timer += dt
        if drop_timer >= fall_speed:
            drop_timer = 0
            if valid_position(board, current, dy=1):
                current.y += 1
            else:
                # lock
                lock_piece(board, current)
                board, lines = clear_lines(board)
                if lines:
                    score += score_from_lines(lines, level)
                    total_lines += lines
                hold_locked = False
                current = spawn_piece(queue)

        # level update
        level = 1 + total_lines // 10
        fall_speed = max(0.02, 1.0 - (level - 1) * 0.08)

        # check spawn collision -> game over
        if not valid_position(board, current):
            # game over
            # ask for name if score qualifies for top list
            scores_before = load_high_scores()
            qualify = False
            if len(scores_before) < MAX_HIGH_SCORES:
                qualify = True
            else:
                # list is sorted desc
                if scores_before and score > scores_before[-1].get('score', 0):
                    qualify = True
            if qualify:
                player_name = prompt_for_name(screen, clock, default='PLAYER')
            else:
                player_name = '---'
            # record to high scores (include level and name)
            add_high_score({'name': player_name, 'score': score, 'lines': total_lines, 'level': level, 'mode': mode})
            screen.fill(BLACK)
            draw_text(screen, 'GAME OVER', 60, 20, 120)
            draw_text(screen, f'Score: {score:,}  Lines: {total_lines}  Level: {level}', 24, 20, 200)
            draw_text(screen, 'Press R to restart, M for menu, or close window', 18, 20, 260)
            pygame.display.flip()
            # wait for player choice
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return 'exit'
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            return 'restart'
                        if event.key == pygame.K_m:
                            return 'menu'
                        # any other key also returns to menu
                        return 'menu'
                clock.tick(10)

        # render
        screen.fill(BLACK)
        # draw playfield
        draw_board(screen, board, 0, 0)
        # ghost piece
        ghost = Piece(current.shape)
        ghost.x, ghost.y, ghost.rot = current.x, current.y, current.rot
        while valid_position(board, ghost, dy=1):
            ghost.y += 1
        draw_piece(screen, ghost, 0, 0, ghost=True)
        draw_piece(screen, current, 0, 0)

        # side panel
        side_x = BOARD_WIDTH * BLOCK + 10
        draw_text(screen, f'Score: {score:,}', 20, side_x, 20)
        draw_text(screen, f'Level: {level}', 20, side_x, 50)
        draw_text(screen, f'Lines: {total_lines}', 20, side_x, 80)
        # Draw Hold above Next for better use of space
        draw_hold(screen, hold, side_x, 120)
        # Larger Next preview below hold
        draw_next(screen, list(queue), side_x, 200)
        # draw music status
        draw_music_status(screen, side_x, 440)
        # draw AI speed slider
        draw_ai_slider(screen, ai_slider_value, side_x, 500)
        # draw volume slider (separate function)
        draw_volume_slider(screen, MUSIC_VOLUME, side_x, 540)

        # optional debug visualization of hitboxes
        if DEBUG_HITBOX:
            music_rect = pygame.Rect(side_x, 440, 150, 20)
            slider_rect = pygame.Rect(side_x, 500, 150, 10)
            vol_rect = pygame.Rect(side_x, 540, 150, 10)
            pygame.draw.rect(screen, (255, 0, 0), music_rect, 2)
            pygame.draw.rect(screen, (0, 255, 0), slider_rect, 2)
            pygame.draw.rect(screen, (0, 0, 255), vol_rect, 2)

        pygame.display.flip()

    return 'exit'


def score_from_lines(lines, level):
    table = {1: 100, 2: 300, 3: 500, 4: 800}
    return table.get(lines, 0) * level


if __name__ == '__main__':
    main()
