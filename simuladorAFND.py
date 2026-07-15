import tkinter as tk
from tkinter import font as tkfont
import math

BG           = "#F0F2F5"
PANEL_BG     = "#FFFFFF"
BORDER       = "#D1D0C9"
TEXT_PRI     = "#1A1A18"
TEXT_SEC     = "#5F5E5A"
TEXT_MUTED   = "#B4B2A9"
ACCENT       = "#3B8BD4"
ACCENT_DARK  = "#185FA5"

STATE_IDLE_FILL    = "#F5F5F4"
STATE_IDLE_STROKE  = "#888780"
STATE_ACTIVE_FILL  = "#E6F1FB"
STATE_ACTIVE_STROKE= "#3B8BD4"
STATE_ACCEPT_FILL  = "#EAF3DE"
STATE_ACCEPT_STROKE= "#639922"
STATE_REJECT_FILL  = "#FCEBEB"
STATE_REJECT_STROKE= "#E24B4A"
STATE_DEAD_STROKE  = "#E87722"

ARROW_IDLE   = "#B4B2A9"
ARROW_ACTIVE = "#3B8BD4"
ARROW_DEAD   = "#E24B4A"

TOK_IDLE_BG     = "#F5F5F4"
TOK_IDLE_FG     = "#5F5E5A"
TOK_IDLE_BD     = "#D1D0C9"
TOK_CURRENT_BG  = "#E6F1FB"
TOK_CURRENT_FG  = "#185FA5"
TOK_CURRENT_BD  = "#3B8BD4"
TOK_DONE_BG     = "#F5F5F4"
TOK_DONE_FG     = "#B4B2A9"
TOK_DONE_BD     = "#E8E7E0"

DELAY_MS = 700

# Dimensiones del lienzo del autómata
CANVAS_W, CANVAS_H = 820, 380
STATE_R = 54

# El AFND reconoce: cadenas que contienen una LETRA seguida
# INMEDIATAMENTE de un DÍGITO (patrón L→D, ej: "a1", "X9").
# Símbolo de entrada: 'L' (letra), 'D' (dígito), 'O' (otro)
#
# Este es un AFND *real*: en q0, cada letra abre DOS caminos a
# la vez (q0 se queda Y q1 se activa como conjetura). Algunas
# conjeturas mueren (q1 con 'O' no tiene a dónde ir: esa rama
# simplemente desaparece, nadie la sustituye).

def clasificar(ch):
    if ch.isalpha():
        return 'L'
    elif ch.isdigit():
        return 'D'
    else:
        return 'O'   # símbolo especial / espacio, no forma parte del patrón

DELTA = {
    # (estado, símbolo) -> conjunto de estados siguientes (puede ser vacío)
    ("q0", "L"): {"q0", "q1"},   # <-- bifurcación real: se queda Y conjetura
    ("q0", "D"): {"q0"},
    ("q0", "O"): {"q0"},
    ("q1", "L"): {"q1"},         # nueva letra reemplaza la conjetura anterior
    ("q1", "D"): {"q2"},         # ¡conjetura confirmada! letra->dígito
    # ("q1", "O") no existe -> esa rama muere, no avanza a ningún lado
    ("q2", "L"): {"q2"},
    ("q2", "D"): {"q2"},
    ("q2", "O"): {"q2"},         # q2 es absorbente (estado de aceptación)
}

ESTADOS_DESC = {
    "q0": "Buscando\npatrón",
    "q1": "Conjetura:\nvio letra",
    "q2": "¡Patrón\nhallado!",
}


class SimuladorAFND:
    def __init__(self, root):
        self.root = root
        self.root.title("AFND — Validador de Contraseñas (patrón letra→dígito)")
        self.root.configure(bg=BG)
        self.root.minsize(1180, 660)

        self._sim_after  = None
        self._glow_after = None
        self._pulse_states = set()
        self._pulse_phase  = 0

        self._build_ui()
        self._draw_automaton()


    def _build_ui(self):
        self.font_title   = tkfont.Font(family="Helvetica Neue", size=16, weight="bold")
        self.font_label   = tkfont.Font(family="Helvetica Neue", size=12)
        self.font_state   = tkfont.Font(family="Helvetica Neue", size=13, weight="bold")
        self.font_sub     = tkfont.Font(family="Helvetica Neue", size=9)
        self.font_arrow   = tkfont.Font(family="Helvetica Neue", size=10)
        self.font_mono    = tkfont.Font(family="Courier",        size=14, weight="bold")
        self.font_result  = tkfont.Font(family="Helvetica Neue", size=13, weight="bold")
        self.font_btn     = tkfont.Font(family="Helvetica Neue", size=12)
        self.font_tok     = tkfont.Font(family="Courier",        size=13, weight="bold")
        self.font_pw      = tkfont.Font(family="Courier",        size=18, weight="bold")
        self.font_req     = tkfont.Font(family="Helvetica Neue", size=11)
        self.font_badge   = tkfont.Font(family="Helvetica Neue", size=10, weight="bold")
        self.font_note    = tkfont.Font(family="Helvetica Neue", size=10, slant="italic")

        # ── Encabezado ───────────────────────────────────────
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=30, pady=(22, 0))
        tk.Label(header, text="Simulador AFND  ·  Caso de uso: Validador de Contraseñas",
                 font=self.font_title, bg=BG, fg=TEXT_PRI).pack(side=tk.LEFT)

        sub = tk.Frame(self.root, bg=BG)
        sub.pack(fill=tk.X, padx=30)
        tk.Label(sub, text="Lenguaje: cadenas que contienen una letra seguida inmediatamente "
                            "de un dígito (ej. \"a1\", \"clave9x\")",
                 font=self.font_note, bg=BG, fg=TEXT_SEC).pack(side=tk.LEFT, pady=(2, 0))

        # ── Contenedor principal (dos columnas) ──────────────
        main = tk.Frame(self.root, bg=BG)
        main.pack(padx=30, pady=18, fill=tk.BOTH, expand=True)

        # Columna izquierda: autómata
        left = tk.Frame(main, bg=PANEL_BG, bd=0,
                        highlightthickness=1, highlightbackground=BORDER)
        left.pack(side=tk.LEFT, padx=(0, 14), fill=tk.BOTH, expand=True)

        tk.Label(left, text="Autómata Finito No Determinista",
                 font=self.font_label, bg=PANEL_BG, fg=TEXT_SEC,
                 anchor=tk.W).pack(fill=tk.X, padx=18, pady=(14, 4))

        self.canvas = tk.Canvas(left, width=CANVAS_W, height=CANVAS_H,
                                bg=PANEL_BG, highlightthickness=0)
        self.canvas.pack(padx=14, pady=(0, 4))

        tk.Label(left, text="🔀  En q0, cada letra abre DOS caminos a la vez: sigue en q0 "
                             "Y salta a q1 (conjetura). Así se ve el no-determinismo real.",
                 font=self.font_note, bg=PANEL_BG, fg=ACCENT_DARK,
                 anchor=tk.W, wraplength=680, justify=tk.LEFT).pack(fill=tk.X, padx=18, pady=(0, 8))

        # Cinta simbólica (tokens abstractos)
        tk.Label(left, text="Cinta  (L = letra, D = dígito, O = otro)",
                 font=self.font_req, bg=PANEL_BG, fg=TEXT_MUTED).pack(anchor=tk.W, padx=18)
        self.tape_frame = tk.Frame(left, bg=PANEL_BG, height=56)
        self.tape_frame.pack(fill=tk.X, padx=18, pady=(6, 16))
        self.tape_frame.pack_propagate(False)
        self._tape_labels = []

        # ── Leyenda ───────────────────────────────────────────
        ley = tk.Frame(left, bg=PANEL_BG)
        ley.pack(pady=(0, 16))
        self._leyenda(ley, STATE_ACTIVE_FILL,  STATE_ACTIVE_STROKE, "Activo")
        self._leyenda(ley, STATE_ACCEPT_FILL,  STATE_ACCEPT_STROKE, "Aceptado")
        self._leyenda(ley, STATE_REJECT_FILL,  STATE_REJECT_STROKE, "Rechazado")
        self._leyenda(ley, STATE_IDLE_FILL,    STATE_IDLE_STROKE,   "Inactivo")

        # Columna derecha: caso de uso
        right = tk.Frame(main, bg=PANEL_BG, bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         width=360)
        right.pack(side=tk.LEFT, fill=tk.BOTH)
        right.pack_propagate(False)

        tk.Label(right, text="Caso de uso real",
                 font=self.font_label, bg=PANEL_BG, fg=TEXT_SEC,
                 anchor=tk.W).pack(fill=tk.X, padx=18, pady=(14, 4))

        mock = tk.Frame(right, bg="#F8F9FB",
                        highlightthickness=1, highlightbackground=BORDER)
        mock.pack(padx=18, pady=(0, 14), fill=tk.X)

        header_mock = tk.Frame(mock, bg=ACCENT)
        header_mock.pack(fill=tk.X)
        tk.Label(header_mock, text="🔐  Crear cuenta",
                 font=tkfont.Font(family="Helvetica Neue", size=13, weight="bold"),
                 bg=ACCENT, fg="white", pady=10).pack()

        form = tk.Frame(mock, bg="#F8F9FB")
        form.pack(padx=18, pady=16, fill=tk.X)

        tk.Label(form, text="Contraseña", font=self.font_req,
                 bg="#F8F9FB", fg=TEXT_SEC, anchor=tk.W).pack(fill=tk.X)

        pw_row = tk.Frame(form, bg="#F8F9FB")
        pw_row.pack(fill=tk.X, pady=(4, 10))

        self.pw_var = tk.StringVar()
        self.pw_var.trace_add("write", self._on_pw_change)
        self.pw_entry = tk.Entry(
            pw_row, textvariable=self.pw_var,
            font=self.font_pw, show="●",
            relief=tk.FLAT, bd=0,
            bg=PANEL_BG, fg=TEXT_PRI,
            insertbackground=ACCENT,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            width=18
        )
        self.pw_entry.pack(side=tk.LEFT, ipady=8, fill=tk.X, expand=True)

        self.eye_btn = tk.Button(
            pw_row, text="👁", relief=tk.FLAT, bg=PANEL_BG,
            cursor="hand2", font=self.font_req,
            command=self._toggle_show
        )
        self.eye_btn.pack(side=tk.LEFT, padx=(4, 0))
        self._showing_pw = False

        # Barra de fortaleza
        self.strength_frame = tk.Frame(form, bg="#F8F9FB")
        self.strength_frame.pack(fill=tk.X, pady=(0, 8))
        self.strength_bar = tk.Canvas(
            self.strength_frame, height=7, bg="#E8E7E0",
            highlightthickness=0
        )
        self.strength_bar.pack(fill=tk.X)
        self.strength_lbl = tk.Label(
            self.strength_frame, text="",
            font=self.font_req, bg="#F8F9FB", fg=TEXT_MUTED, anchor=tk.W
        )
        self.strength_lbl.pack(fill=tk.X, pady=(3, 0))

        # Requisitos visuales
        req_frame = tk.Frame(form, bg="#F8F9FB")
        req_frame.pack(fill=tk.X, pady=(0, 6))
        self._req_labels = {}
        requisitos = [
            ("pattern",  "Letra seguida de número (ej: a1)"),
            ("min_len",  "Mínimo 6 caracteres"),
        ]
        for key, txt in requisitos:
            row = tk.Frame(req_frame, bg="#F8F9FB")
            row.pack(fill=tk.X, pady=2)
            icon = tk.Label(row, text="○", font=self.font_req,
                            bg="#F8F9FB", fg=TEXT_MUTED, width=2)
            icon.pack(side=tk.LEFT)
            lbl = tk.Label(row, text=txt, font=self.font_req,
                           bg="#F8F9FB", fg=TEXT_MUTED)
            lbl.pack(side=tk.LEFT)
            self._req_labels[key] = (icon, lbl)

        # Estado del autómata en el mockup
        self.badge_var = tk.StringVar(value="")
        self.badge_lbl = tk.Label(
            form, textvariable=self.badge_var,
            font=self.font_badge, bg="#F8F9FB", fg=TEXT_MUTED,
            anchor=tk.CENTER, relief=tk.FLAT,
            padx=10, pady=5
        )
        self.badge_lbl.pack(fill=tk.X, pady=(6, 0))

        # Botón registrar (mockup)
        self.btn_reg = tk.Button(
            form, text="Crear cuenta →",
            font=self.font_btn, relief=tk.FLAT,
            bg="#C8C7C0", fg="white",
            activebackground=STATE_ACCEPT_STROKE,
            cursor="hand2", pady=8
        )
        self.btn_reg.pack(fill=tk.X, pady=(10, 0))

        ctrl = tk.Frame(right, bg=PANEL_BG)
        ctrl.pack(padx=18, pady=(0, 8), fill=tk.X)

        self.btn_sim = tk.Button(
            ctrl, text="▶  Simular paso a paso",
            font=self.font_btn, relief=tk.FLAT,
            bg=ACCENT, fg="white",
            activebackground=ACCENT_DARK, activeforeground="white",
            cursor="hand2", pady=7,
            command=self._iniciar
        )
        self.btn_sim.pack(fill=tk.X, pady=(0, 6))
        self._add_hover(self.btn_sim, ACCENT, ACCENT_DARK)

        self.btn_reset = tk.Button(
            ctrl, text="Reiniciar",
            font=self.font_btn, relief=tk.FLAT,
            bg=PANEL_BG, fg=TEXT_SEC,
            activebackground=BG,
            highlightthickness=1, highlightbackground=BORDER,
            cursor="hand2", pady=7,
            command=self._reset
        )
        self.btn_reset.pack(fill=tk.X)
        self._add_hover(self.btn_reset, PANEL_BG, BG)

        # Resultado
        self.resultado = tk.Label(
            right, text="",
            font=self.font_result,
            bg=PANEL_BG, fg=TEXT_PRI,
            pady=10, wraplength=310, justify=tk.LEFT
        )
        self.resultado.pack(padx=18, fill=tk.X)

    def _add_hover(self, widget, normal_bg, hover_bg):
        widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg))
        widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg))

    def _leyenda(self, parent, fill, stroke, texto):
        f = tk.Frame(parent, bg=PANEL_BG)
        f.pack(side=tk.LEFT, padx=10)
        c = tk.Canvas(f, width=14, height=14, bg=PANEL_BG, highlightthickness=0)
        c.pack(side=tk.LEFT, padx=(0, 4))
        c.create_oval(1, 1, 13, 13, fill=fill, outline=stroke, width=1.5)
        tk.Label(f, text=texto, font=self.font_req,
                 bg=PANEL_BG, fg=TEXT_SEC).pack(side=tk.LEFT)

    def _toggle_show(self):
        self._showing_pw = not self._showing_pw
        self.pw_entry.config(show="" if self._showing_pw else "●")


    @staticmethod
    def _tiene_patron(pw):
        """Letra inmediatamente seguida de dígito, en algún punto de la cadena."""
        return any(pw[i].isalpha() and pw[i + 1].isdigit() for i in range(len(pw) - 1))

    def _on_pw_change(self, *_):
        pw = self.pw_var.get()
        has_pattern = self._tiene_patron(pw)
        min_len     = len(pw) >= 6

        checks = {"pattern": has_pattern, "min_len": min_len}
        for key, ok in checks.items():
            icon, lbl = self._req_labels[key]
            if ok:
                icon.config(text="✓", fg=STATE_ACCEPT_STROKE)
                lbl.config(fg=TEXT_PRI)
            else:
                icon.config(text="○", fg=TEXT_MUTED)
                lbl.config(fg=TEXT_MUTED)

        # Barra de fortaleza
        score = sum([has_pattern, min_len, len(pw) >= 10, any(c.isupper() for c in pw),
                     any(not c.isalnum() for c in pw)])
        self._update_strength_bar(score)

        # Botón registrar
        valid = has_pattern and min_len
        self.btn_reg.config(
            bg=STATE_ACCEPT_STROKE if valid else "#C8C7C0",
            cursor="hand2" if valid else "arrow"
        )

    def _update_strength_bar(self, score):
        self.strength_bar.delete("all")
        w = self.strength_bar.winfo_width() or 300
        colors = ["#E24B4A", "#E87722", "#F0C419", "#639922", "#2E7D32"]
        labels = ["Muy débil", "Débil", "Regular", "Fuerte", "Muy fuerte"]
        if score == 0:
            self.strength_lbl.config(text="", fg=TEXT_MUTED)
            return
        idx = min(score - 1, 4)
        fill_w = int(w * score / 5)
        self.strength_bar.create_rectangle(0, 0, fill_w, 7, fill=colors[idx], outline="")
        self.strength_lbl.config(text=labels[idx], fg=colors[idx])


    def _draw_automaton(self):
        self.canvas.delete("all")
        r = STATE_R

        self.pos = {
            "q0": (150, 190),
            "q1": (420, 190),
            "q2": (690, 190),
        }

        # Flecha inicio
        self._arrow(30, 190, 95, 190, color=ARROW_IDLE, tag="entry")
        self.canvas.create_text(30, 168, text="inicio",
                                font=self.font_arrow, fill=TEXT_MUTED, anchor=tk.W, tags="entry")

        # q0 → q1 (bifurcación real: L)
        self._draw_horiz("q0", "q1", "L  (bifurca)", tag="arr-q0-q1", offset_y=-16)
        # q1 → q2 (D)
        self._draw_horiz("q1", "q2", "D", tag="arr-q1-q2", offset_y=-16)

        # Auto-loops (arriba de cada estado)
        self._draw_self_loop_top("q0", "L, D, O", tag="loop-q0")
        self._draw_self_loop_top("q1", "L", tag="loop-q1")
        self._draw_self_loop_top("q2", "L, D, O", tag="loop-q2")

        # Rama muerta: q1 con 'O' no tiene transición -> la conjetura desaparece
        self._draw_dead_branch("q1", tag="dead-q1")

        # Glows
        for name in self.pos:
            self.canvas.create_oval(0, 0, 0, 0, fill="", outline="", tags=(f"glow-{name}",))

        # Estados
        for name, (x, y) in self.pos.items():
            final = (name == "q2")
            self._draw_state(name, x, y, r, final=final,
                             fill=STATE_IDLE_FILL, stroke=STATE_IDLE_STROKE)

    def _draw_state(self, name, x, y, r=STATE_R, final=False,
                    fill=STATE_IDLE_FILL, stroke=STATE_IDLE_STROKE):
        self.canvas.delete(f"state-{name}")
        self.canvas.create_oval(x-r+3, y-r+3, x+r+3, y+r+3,
                                fill="#E0DFD8", outline="",
                                tags=(f"state-{name}", "shadow"))
        self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                fill=fill, outline=stroke, width=2.6,
                                tags=(f"state-{name}", "circle"))
        if final:
            ri = r - 9
            self.canvas.create_oval(x-ri, y-ri, x+ri, y+ri,
                                    fill="", outline=stroke, width=1.6,
                                    tags=(f"state-{name}", "inner"))
        self.canvas.create_text(x, y - 10, text=name,
                                font=self.font_state, fill=TEXT_PRI,
                                tags=(f"state-{name}", "label"))
        desc = ESTADOS_DESC.get(name, "")
        self.canvas.create_text(x, y + 13, text=desc,
                                font=self.font_sub, fill=TEXT_SEC,
                                justify=tk.CENTER,
                                tags=(f"state-{name}", "desc"))

    def _draw_horiz(self, src, dst, label, tag, offset_y=0):
        x1, y1 = self.pos[src]
        x2, y2 = self.pos[dst]
        r = STATE_R
        sx = x1 + r; ex = x2 - r
        self.canvas.create_line(sx, y1, ex, y2,
                                fill=ARROW_IDLE, width=1.9,
                                arrow=tk.LAST, arrowshape=(10, 12, 4),
                                tags=(tag,))
        mx = (sx + ex) / 2
        self.canvas.create_text(mx, y1 + offset_y, text=label,
                                font=self.font_arrow, fill=TEXT_SEC, tags=(tag,))

    def _draw_self_loop_top(self, state, label, tag):
        x, y = self.pos[state]
        r = STATE_R
        size = 30
        cx, cy = x, y - r + 4
        self.canvas.create_arc(
            cx - size, cy - size - 16, cx + size, cy + size - 16,
            start=195, extent=150,
            style=tk.ARC, outline=ARROW_IDLE, width=1.7,
            tags=(tag,)
        )
        self.canvas.create_text(
            x, y - r - size - 8, text=label,
            font=self.font_arrow, fill=TEXT_SEC, tags=(tag,)
        )

    def _draw_dead_branch(self, state, tag):
        """Flecha punteada hacia abajo: la conjetura muere al leer 'O'."""
        x, y = self.pos[state]
        r = STATE_R
        x1, y1 = x + r * 0.4, y + r * 0.85
        x2, y2 = x + r * 0.9, y + r + 46
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=ARROW_IDLE, width=1.7, dash=(4, 3),
            arrow=tk.LAST, arrowshape=(8, 10, 3),
            tags=(tag,)
        )
        self.canvas.create_text(
            x2 + 6, y2 + 4, text="O  →  ∅\n(conjetura muere)",
            font=self.font_sub, fill=TEXT_MUTED, anchor=tk.W,
            justify=tk.LEFT, tags=(tag,)
        )

    def _arrow(self, x1, y1, x2, y2, color=ARROW_IDLE, tag=""):
        self.canvas.create_line(x1, y1, x2, y2,
                                fill=color, width=1.9,
                                arrow=tk.LAST, arrowshape=(10, 12, 4),
                                tags=(tag,))

    def _colorear(self, activos, mode="active"):
        fills   = {s: STATE_IDLE_FILL   for s in self.pos}
        strokes = {s: STATE_IDLE_STROKE for s in self.pos}
        for s in activos:
            if mode == "active":
                fills[s]   = STATE_ACTIVE_FILL
                strokes[s] = STATE_ACTIVE_STROKE
            elif mode == "accept":
                fills[s]   = STATE_ACCEPT_FILL
                strokes[s] = STATE_ACCEPT_STROKE
            elif mode == "reject":
                fills[s]   = STATE_REJECT_FILL
                strokes[s] = STATE_REJECT_STROKE

        for name, (x, y) in self.pos.items():
            self._draw_state(name, x, y, r=STATE_R, final=(name == "q2"),
                             fill=fills[name], stroke=strokes[name])

        self._pulse_states = set(activos) if mode == "active" else set()
        if self._glow_after:
            self.root.after_cancel(self._glow_after)
        if self._pulse_states:
            self._pulse_phase = 0
            self._tick_glow()

    def _tick_glow(self):
        if not self._pulse_states:
            return
        t = self._pulse_phase / 10.0
        alpha = int(55 + 40 * math.sin(t * math.pi))
        r_extra = 4 + 3 * math.sin(t * math.pi)

        for name in self._pulse_states:
            x, y = self.pos[name]
            r = STATE_R + r_extra
            self.canvas.delete(f"glow-{name}")
            for dr, op in [(10, 25), (7, 45), (4, 70)]:
                a = min(int(op * alpha / 95), 255)
                color = '#%02x%02x%02x' % (
                    int(59  + (240 - 59)  * (1 - a / 255)),
                    int(139 + (242 - 139) * (1 - a / 255)),
                    int(212 + (245 - 212) * (1 - a / 255)),
                )
                self.canvas.create_oval(
                    x - r - dr, y - r - dr, x + r + dr, y + r + dr,
                    fill="", outline=color, width=1,
                    tags=(f"glow-{name}",)
                )

        self._pulse_phase += 1
        self._glow_after = self.root.after(60, self._tick_glow)


    def _build_tape(self, cadena):
        for w in self._tape_labels:
            w.destroy()
        self._tape_labels = []

        inner = tk.Frame(self.tape_frame, bg=PANEL_BG)
        inner.place(relx=0, rely=0.5, anchor=tk.W)

        for ch in cadena:
            sym = clasificar(ch)
            f = tk.Frame(inner, bg=PANEL_BG)
            f.pack(side=tk.LEFT, padx=3)
            lbl = tk.Label(
                f, text=sym, width=2,
                font=self.font_tok,
                bg=TOK_IDLE_BG, fg=TOK_IDLE_FG,
                relief=tk.FLAT,
                highlightthickness=1, highlightbackground=TOK_IDLE_BD,
                padx=6, pady=4
            )
            lbl.pack()
            tip = tk.Label(f, text=ch if ch != " " else "·",
                           font=self.font_req, bg=PANEL_BG, fg=TEXT_MUTED)
            tip.pack()
            self._tape_labels.append(lbl)

    def _update_tape(self, idx):
        for i, lbl in enumerate(self._tape_labels):
            if i < idx:
                lbl.configure(bg=TOK_DONE_BG, fg=TOK_DONE_FG,
                               highlightbackground=TOK_DONE_BD)
            elif i == idx:
                lbl.configure(bg=TOK_CURRENT_BG, fg=TOK_CURRENT_FG,
                               highlightbackground=TOK_CURRENT_BD)
            else:
                lbl.configure(bg=TOK_IDLE_BG, fg=TOK_IDLE_FG,
                               highlightbackground=TOK_IDLE_BD)

    _ALL_ARROWS = ("arr-q0-q1", "arr-q1-q2", "loop-q0", "loop-q1", "loop-q2", "dead-q1")

    _MAPPING = {
        ("q0", "L"): ["loop-q0", "arr-q0-q1"],   # <- 2 flechas a la vez: bifurcación real
        ("q0", "D"): ["loop-q0"],
        ("q0", "O"): ["loop-q0"],
        ("q1", "L"): ["loop-q1"],
        ("q1", "D"): ["arr-q1-q2"],
        ("q1", "O"): ["dead-q1"],                # rama que muere (no lleva a ningún estado)
        ("q2", "L"): ["loop-q2"],
        ("q2", "D"): ["loop-q2"],
        ("q2", "O"): ["loop-q2"],
    }

    def _highlight_arrows(self, prev, sym):
        for tag in self._ALL_ARROWS:
            self.canvas.itemconfigure(tag, fill=ARROW_IDLE)

        for s in prev:
            for tag in self._MAPPING.get((s, sym), []):
                color = ARROW_DEAD if tag == "dead-q1" else ARROW_ACTIVE
                self.canvas.itemconfigure(tag, fill=color)

    @staticmethod
    def _delta(estados, sym):
        sig = set()
        for e in estados:
            sig |= DELTA.get((e, sym), set())
        return sig

    def _iniciar(self):
        if self._sim_after:
            self.root.after_cancel(self._sim_after)
        if self._glow_after:
            self.root.after_cancel(self._glow_after)

        cadena = self.pw_var.get()
        if not cadena:
            self.resultado.config(text="Escribe una contraseña primero", fg=TEXT_MUTED)
            return

        self.resultado.config(text="", fg=TEXT_PRI)
        self._cadena   = cadena
        self._activos  = {"q0"}
        self._idx      = 0
        self._build_tape(cadena)
        self._draw_automaton()
        self._colorear(self._activos, mode="active")
        self._update_badge(self._activos)
        self._sim_after = self.root.after(DELAY_MS, self._paso)

    def _paso(self):
        if self._idx >= len(self._cadena):
            aceptada = "q2" in self._activos
            self._pulse_states = set()
            if self._glow_after:
                self.root.after_cancel(self._glow_after)
            self._colorear(self._activos, mode="accept" if aceptada else "reject")
            self._highlight_arrows(set(), "")
            if aceptada:
                self.resultado.config(
                    text="✓  Contraseña válida\nEl AFND alcanzó q2 (patrón letra→dígito)",
                    fg=STATE_ACCEPT_STROKE)
                self._update_badge({"q2"})
            else:
                estados_str = ", ".join(sorted(self._activos)) if self._activos else "∅"
                self.resultado.config(
                    text=f"✗  Contraseña inválida\nEstados finales: {{{estados_str}}}\n"
                         "(nunca hubo letra→dígito)",
                    fg=STATE_REJECT_STROKE)
                self._update_badge(None)
            return

        ch   = self._cadena[self._idx]
        sym  = clasificar(ch)
        prev = set(self._activos)
        next_states = self._delta(self._activos, sym)

        self._update_tape(self._idx)
        self._highlight_arrows(prev, sym)
        self._activos = next_states
        self._colorear(self._activos, mode="active")
        self._update_badge(next_states)
        self._idx += 1
        self._sim_after = self.root.after(DELAY_MS, self._paso)

    def _update_badge(self, activos):
        """Muestra TODOS los estados activos a la vez (el corazón del AFND)."""
        if activos is None:
            self.badge_var.set("Estado: inválida ✗")
            self.badge_lbl.config(fg=STATE_REJECT_STROKE, bg="#FCEBEB")
        elif activos == {"q2"}:
            self.badge_var.set("AFND en q2 — ¡patrón hallado! ✓")
            self.badge_lbl.config(fg=STATE_ACCEPT_STROKE, bg=STATE_ACCEPT_FILL)
        elif not activos:
            self.badge_var.set("AFND: ∅ — todas las ramas murieron")
            self.badge_lbl.config(fg=STATE_REJECT_STROKE, bg="#FCEBEB")
        else:
            label = "AFND activo en: {" + ", ".join(sorted(activos)) + "}"
            if len(activos) > 1:
                label += "  🔀"
            self.badge_var.set(label)
            self.badge_lbl.config(fg=ACCENT, bg=STATE_ACTIVE_FILL)

    def _reset(self):
        if self._sim_after:
            self.root.after_cancel(self._sim_after)
        if self._glow_after:
            self.root.after_cancel(self._glow_after)
        self._pulse_states = set()
        self.pw_var.set("")
        self.resultado.config(text="")
        self.badge_var.set("")
        self.badge_lbl.config(bg="#F8F9FB")
        for w in self._tape_labels:
            w.destroy()
        self._tape_labels = []
        self._draw_automaton()
        self._update_strength_bar(0)
        self.strength_lbl.config(text="")
        for key in self._req_labels:
            icon, lbl = self._req_labels[key]
            icon.config(text="○", fg=TEXT_MUTED)
            lbl.config(fg=TEXT_MUTED)
        self.btn_reg.config(bg="#C8C7C0")


if __name__ == "__main__":
    root = tk.Tk()
    app  = SimuladorAFND(root)
    root.mainloop()
