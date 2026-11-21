"""Dark 'whiteboard' architecture diagrams (Eraser-style) as SVG -> PNG via headless Chrome."""
import html
import math
import subprocess
import tempfile
from pathlib import Path

OUT = Path.cwd() / "diagrams"  # default; override with Diagram.save(name, out_dir=...)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
W, H = 1600, 960
T = 44  # icon tile size

GROUP_STYLES = {
    "tan":  ("#8a6a3c", "rgba(70,52,28,0.30)"),
    "blue": ("#4f7bbf", "rgba(28,48,88,0.40)"),
    "red":  ("#c0504d", "rgba(90,25,25,0.30)"),
    "green": ("#4f9a5a", "rgba(25,70,35,0.30)"),
}

def esc(s): return html.escape(s)

# ---------- icons (drawn centred at 0,0) ----------
def tile(color, inner):
    return (f'<rect x="{-T/2}" y="{-T/2}" width="{T}" height="{T}" rx="6" fill="{color}"/>' + inner)

W_ = 'stroke="#fff" stroke-width="1.8" fill="none" stroke-linejoin="round" stroke-linecap="round"'

ICONS = {
    "server": lambda: tile("#E8851A", f'<rect x="-11" y="-9" width="16" height="16" rx="2" {W_}/><rect x="-5" y="-14" width="16" height="16" rx="2" {W_}/>'),
    "lb": lambda: tile("#8C4FFF", f'<circle cx="-9" cy="0" r="3.5" {W_}/><circle cx="9" cy="-9" r="3.5" {W_}/><circle cx="9" cy="0" r="3.5" {W_}/><circle cx="9" cy="9" r="3.5" {W_}/><path d="M-5.5 0 L5.5 -9 M-5.5 0 L5.5 0 M-5.5 0 L5.5 9" {W_}/>'),
    "bucket": lambda: tile("#3F8624", f'<path d="M-12 -8 L-9 12 L9 12 L12 -8 Z" {W_}/><ellipse cx="0" cy="-8" rx="12" ry="3.5" {W_}/>'),
    "queue": lambda: tile("#D6246E", f'<rect x="-13" y="-8" width="6" height="16" rx="1" {W_}/><rect x="-3" y="-8" width="6" height="16" rx="1" {W_}/><rect x="7" y="-8" width="6" height="16" rx="1" {W_}/>'),
    "redis": lambda: tile("#C9302C", f'<path d="M0 -12 L13 -6 L0 0 L-13 -6 Z" {W_}/><path d="M-13 0 L0 6 L13 0" {W_}/><path d="M-13 6 L0 12 L13 6" {W_}/>'),
    "worker": lambda: tile("#0F9D8A", f'<circle cx="0" cy="0" r="6" {W_}/>' + "".join(
        f'<line x1="{8*math.cos(a):.1f}" y1="{8*math.sin(a):.1f}" x2="{12*math.cos(a):.1f}" y2="{12*math.sin(a):.1f}" {W_}/>'
        for a in [i*math.pi/4 for i in range(8)])),
    "card": lambda: tile("#2E73B8", f'<rect x="-13" y="-9" width="26" height="18" rx="2.5" {W_}/><line x1="-13" y1="-3" x2="13" y2="-3" {W_}/><line x1="-8" y1="4" x2="-1" y2="4" {W_}/>'),
    "ai": lambda: tile("#6E56CF", f'<path d="M0 -13 L3 -3 L13 0 L3 3 L0 13 L-3 3 L-13 0 L-3 -3 Z" {W_}/>'),
    "monitor": lambda: tile("#B8860B", f'<rect x="-13" y="-11" width="26" height="22" rx="2" {W_}/><path d="M-9 5 L-3 -1 L2 3 L9 -6" {W_}/>'),
    "shield": lambda: tile("#F38020", f'<path d="M0 -13 L11 -8 L11 1 C11 8 5 12 0 14 C-5 12 -11 8 -11 1 L-11 -8 Z" {W_}/>'),
    "web": lambda: tile("#2b2b2b", f'<rect x="-14" y="-11" width="28" height="22" rx="2" {W_}/><line x1="-14" y1="-5" x2="14" y2="-5" {W_}/><circle cx="-10" cy="-8" r="0.8" fill="#fff"/>'),
    "proxy": lambda: tile("#A8327A", f'<path d="M-13 -5 L9 -5 M5 -10 L10 -5 L5 0 M13 5 L-9 5 M-5 0 L-10 5 L-5 10" {W_}/>'),
    "db": lambda: (f'<ellipse cx="0" cy="-12" rx="15" ry="5" {W_}/><path d="M-15 -12 L-15 12 A15 5 0 0 0 15 12 L15 -12" {W_}/>'
                   f'<path d="M-15 -2 A15 5 0 0 0 15 -2" {W_}/>'),
    "cloud": lambda: f'<path d="M-14 9 C-21 9 -21 -1 -14 -2 C-14 -10 -5 -13 0 -8 C3 -14 14 -12 13 -3 C20 -3 20 9 13 9 Z" {W_}/>',
    "phone": lambda: f'<rect x="-10" y="-17" width="20" height="34" rx="4" {W_}/><line x1="-3" y1="12" x2="3" y2="12" {W_}/>',
    "person": lambda: f'<circle cx="0" cy="-9" r="6" {W_}/><path d="M-13 15 C-13 3 13 3 13 15" {W_}/>',
}

class Diagram:
    def __init__(self, title, subtitle=""):
        self.title, self.subtitle = title, subtitle
        self.groups, self.nodes, self.edges, self.notes, self.frames = [], {}, [], [], []

    def group(self, x, y, w, h, label, style="tan", icon="▣"):
        self.groups.append((x, y, w, h, label, style, icon))

    def frame(self, x, y, w, h, label):
        self.frames.append((x, y, w, h, label))

    def node(self, key, x, y, kind, label):
        self.nodes[key] = (x, y, kind, label)

    def edge(self, a, b, label="", dashed=False, color="#e8e8e8", side=None):
        self.edges.append((a, b, label, dashed, color, side))

    def note(self, x, y, text, color="#ff6b6b", size=19, rotate=-3):
        self.notes.append((x, y, text, color, size, rotate))

    # ---------- rendering ----------
    def _anchor(self, key, toward):
        x, y, kind, _ = self.nodes[key]
        tx, ty = toward
        half = T / 2 + 2
        if abs(tx - x) >= abs(ty - y) * 0.6:
            return (x + half, y, 1, 0) if tx > x else (x - half, y, -1, 0)
        return (x, y + half + 30, 0, 1) if ty > y else (x, y - half, 0, -1)

    def render(self):
        s = []
        s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
        s.append('<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 '<path d="M0 0 L10 5 L0 10 z" fill="#e8e8e8"/></marker>'
                 '<marker id="ahb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 '<path d="M0 0 L10 5 L0 10 z" fill="#7fb0ff"/></marker></defs>')
        s.append(f'<rect width="{W}" height="{H}" fill="#161616"/>')
        s.append(f'<rect x="8" y="8" width="{W-16}" height="{H-16}" rx="6" fill="#1c1c1c" stroke="#3a3a3a"/>')
        # title chip
        tw = 18 + 8.2 * len(self.title)
        s.append(f'<rect x="22" y="22" width="{tw}" height="30" rx="5" fill="#1c1c1c" stroke="#777"/>')
        s.append(f'<text x="34" y="42" fill="#eee" font-size="15" font-family="Segoe UI" font-weight="600">{esc(self.title)}</text>')
        if self.subtitle:
            s.append(f'<text x="{30+tw}" y="42" fill="#9a9a9a" font-size="13" font-family="Segoe UI">{esc(self.subtitle)}</text>')
        for x, y, w, h, label in self.frames:
            s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="none" stroke="#5d8fd6" stroke-width="1.5" stroke-dasharray="8 6"/>')
            lw = 16 + 7.4 * len(label)
            s.append(f'<rect x="{x+w-lw-14}" y="{y-12}" width="{lw}" height="24" rx="5" fill="#1c1c1c" stroke="#5d8fd6"/>')
            s.append(f'<text x="{x+w-lw-6}" y="{y+4}" fill="#9cc2ff" font-size="12" font-family="Segoe UI" font-weight="700" letter-spacing="1">{esc(label)}</text>')
        for x, y, w, h, label, style, icon in self.groups:
            stroke, fill = GROUP_STYLES[style]
            s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            lw = 38 + 8.1 * len(label)
            s.append(f'<rect x="{x+10}" y="{y+10}" width="{lw}" height="24" rx="5" fill="#202020" stroke="#8d8d8d"/>')
            s.append(f'<text x="{x+19}" y="{y+27}" fill="#ddd" font-size="11" font-family="Segoe UI Symbol">{icon}</text>')
            s.append(f'<text x="{x+34}" y="{y+27}" fill="#e6e6e6" font-size="11.5" font-family="Segoe UI" font-weight="700" letter-spacing="0.6">{esc(label.upper())}</text>')
        # edges
        labels = []
        for a, b, label, dashed, color, side in self.edges:
            ax, ay = self.nodes[a][:2]
            bx, by = self.nodes[b][:2]
            x1, y1, dx1, dy1 = self._anchor(a, (bx, by))
            x2, y2, dx2, dy2 = self._anchor(b, (ax, ay))
            k = max(40, 0.45 * math.hypot(x2 - x1, y2 - y1))
            c1 = (x1 + dx1 * k, y1 + dy1 * k)
            c2 = (x2 + dx2 * k, y2 + dy2 * k)
            mk = "ahb" if color != "#e8e8e8" else "ah"
            dash = ' stroke-dasharray="7 5"' if dashed else ""
            s.append(f'<path d="M{x1:.1f} {y1:.1f} C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {x2:.1f} {y2:.1f}" fill="none" stroke="{color}" stroke-opacity="0.85" stroke-width="1.6"{dash} marker-end="url(#{mk})"/>')
            if label:
                t = 0.5
                mx = (1-t)**3*x1 + 3*(1-t)**2*t*c1[0] + 3*(1-t)*t**2*c2[0] + t**3*x2
                my = (1-t)**3*y1 + 3*(1-t)**2*t*c1[1] + 3*(1-t)*t**2*c2[1] + t**3*y2
                labels.append((mx, my, label, color))
        for mx, my, label, color in labels:
            lw = 10 + 6.3 * len(label)
            s.append(f'<rect x="{mx-lw/2:.1f}" y="{my-10:.1f}" width="{lw:.1f}" height="19" rx="4" fill="#1c1c1c" stroke="#555"/>')
            s.append(f'<text x="{mx:.1f}" y="{my+4:.1f}" text-anchor="middle" fill="{"#dcdcdc" if color=="#e8e8e8" else color}" font-size="11" font-family="Segoe UI">{esc(label)}</text>')
        # nodes
        for key, (x, y, kind, label) in self.nodes.items():
            s.append(f'<g transform="translate({x},{y})">{ICONS[kind]()}</g>')
            for i, line in enumerate(label.split("\n")):
                s.append(f'<text x="{x}" y="{y + T/2 + 16 + i*14}" text-anchor="middle" fill="#ececec" font-size="12" font-family="Segoe UI">{esc(line)}</text>')
        # handwritten notes
        for x, y, text, color, size, rot in self.notes:
            for i, line in enumerate(text.split("\n")):
                s.append(f'<text x="{x}" y="{y + i*(size+4)}" transform="rotate({rot} {x} {y})" fill="{color}" font-size="{size}" font-family="Segoe Print, Comic Sans MS" font-weight="700">{esc(line)}</text>')
        s.append("</svg>")
        return "\n".join(s)

    def save(self, name, out_dir=None):
        out = Path(out_dir) if out_dir else OUT
        out.mkdir(parents=True, exist_ok=True)
        svg = out / f"{name}.svg"
        svg.write_text(self.render(), encoding="utf-8")
        page = out / f"_{name}.html"
        page.write_text(f"<!doctype html><html><body style='margin:0;background:#161616'><img src='{svg.name}' width='{W}' height='{H}'></body></html>", encoding="utf-8")
        png = out / f"{name}.png"
        prof = Path(tempfile.gettempdir()) / "arch-chrome-profile"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                        f"--window-size={W},{H}", "--force-device-scale-factor=2",
                        f"--screenshot={png}", page.as_uri()], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        page.unlink()
        print(png)
