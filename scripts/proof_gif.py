"""Animate how a lean_evolve sketch grows into a full proof.

Walks the ancestry of the solved (or best-scoring) program in an island and, for
each generation, draws the sketch's lemma-dependency tree rooted at the main
theorem: green = proved, red = open (or depends on an open lemma), gray = just
added by the mutation and not yet rated. Open subgoals are labelled.

    python scripts/proof_gif.py results/island_0 -o docs/putnam_2025_a1.gif

Shared lemmas (used by several parents) are drawn once, under their first user.
Parsing follows evolutionary-lean/ddepen_script.py.
"""
from __future__ import annotations

import argparse
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgba
from PIL import Image

# ---------------------------------------------------------------- parsing

_BLOCK_COMMENT = re.compile(r"/-[\s\S]*?-/")
_LINE_COMMENT = re.compile(r"--.*?$", re.MULTILINE)
_DECL = re.compile(r"^\s*(lemma|theorem)\s+([A-Za-z_][A-Za-z0-9_'.]*)(?![A-Za-z0-9_'])", re.MULTILINE)
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*")


@dataclass
class Decl:
    kind: str
    name: str
    body: str


def parse_sketch(src: str) -> list[Decl]:
    src = _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", src))
    ms = list(_DECL.finditer(src))
    return [
        Decl(m.group(1), m.group(2), src[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(src)])
        for i, m in enumerate(ms)
    ]


def proved_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys = json.loads(path.read_text())
    return {m.group(2) for k in keys if (m := _DECL.match(k))}


@dataclass
class Tree:
    root: str
    children: dict[str, list[str]]  # spanning tree, file order
    parent: dict[str, str]
    proved: dict[str, bool]
    subgoal: dict[str, bool]  # body still contains `sorry`


def build_tree(decls: list[Decl], proved: set[str]) -> Tree:
    names = {d.name for d in decls}
    order = {d.name: i for i, d in enumerate(decls)}
    body = {d.name: d.body for d in decls}
    deps = {d.name: sorted((set(_IDENT.findall(d.body)) & names) - {d.name}, key=order.get) for d in decls}
    root = [d.name for d in decls if d.kind == "theorem"][-1]

    status: dict[str, bool] = {}

    def ok(n: str, stack: frozenset = frozenset()) -> bool:
        if n not in status:
            if n in proved:
                status[n] = True
            elif n in stack:
                return False
            else:
                status[n] = "sorry" not in body[n] and all(ok(c, stack | {n}) for c in deps[n])
        return status[n]

    children: dict[str, list[str]] = {}
    parent: dict[str, str] = {}

    def visit(n: str) -> None:
        children[n] = []
        for c in deps[n]:
            if c not in children:
                children[n].append(c)
                parent[c] = n
                visit(c)

    visit(root)
    return Tree(
        root, children, parent,
        {n: ok(n) for n in children},
        {n: "sorry" in body[n] for n in children},
    )


# ---------------------------------------------------------------- lineage

def lineage(island: Path, target: int | None) -> list[int]:
    meta = json.loads((island / "metadata.json").read_text())
    parent = {p["program_id"]: p["parent"] for p in meta["programs"]}
    if target is None:
        solved = [i for i in parent if (island / f"program_{i}" / "full_proof.txt").exists()]
        if solved:
            target = min(solved)
        else:
            score = lambda i: json.loads((island / f"program_{i}" / "rating.json").read_text())["score"]
            target = max((i for i in parent if (island / f"program_{i}" / "rating.json").exists()), key=score)
    chain = [target]
    while parent[chain[-1]] != -1:
        chain.append(parent[chain[-1]])
    return chain[::-1]


def problem_name(island: Path) -> str:
    meta = json.loads((island / "metadata.json").read_text())
    return Path(meta["programs"][0]["path"]).parts[-3]


# ---------------------------------------------------------------- layout

def layout(t: Tree) -> tuple[dict[str, tuple[float, int]], int]:
    """Tidy top-down layout: leaves at consecutive x, parents centred over children."""
    pos: dict[str, tuple[float, int]] = {}
    nxt = [0]

    def place(n: str, d: int) -> float:
        kids = t.children[n]
        if not kids:
            x = float(nxt[0])
            nxt[0] += 1
        else:
            xs = [place(c, d + 1) for c in kids]
            x = (xs[0] + xs[-1]) / 2
        pos[n] = (x, d)
        return x

    place(t.root, 0)
    return pos, nxt[0]


# ---------------------------------------------------------------- drawing

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
EDGE = "#c3c2b7"
GOOD = "#0ca30c"
BAD = "#d03b3b"
PENDING = "#a9a89f"

W, H = 1200, 640
TOP, BOTTOM, SIDE = 105, 70, 40
MAX_DX = 70


@dataclass
class Frame:
    tree: Tree
    xy: dict[str, tuple[float, float]]
    program: int
    gen: int
    solved: int
    total: int


def make_frame(t: Tree, prog: int, gen: int, max_depth: int) -> Frame:
    pos, n_leaves = layout(t)
    dx = min(MAX_DX, (W - 2 * SIDE) / max(n_leaves - 1, 1))
    x0 = W / 2 - dx * (n_leaves - 1) / 2
    dy = (H - TOP - BOTTOM) / max(max_depth, 1)
    xy = {n: (x0 + x * dx, TOP + d * dy) for n, (x, d) in pos.items()}
    goals = [n for n in t.children if t.subgoal[n]]
    return Frame(t, xy, prog, gen, sum(t.proved[n] for n in goals), len(goals))


def smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def render(ax, a: Frame | None, b: Frame, t: float, n_gen: int, title: str) -> None:
    """Draw the transition a -> b at time t in [0, 1]; t == 1 is frame b itself."""
    ax.cla()
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    s = smooth(t)
    final = t >= 1.0
    nodes = {}  # name -> (x, y, color, alpha, marker, new)
    bt = b.tree

    def start_xy(n: str) -> tuple[float, float]:
        if a is not None and n in a.xy:
            return a.xy[n]
        p = bt.parent.get(n)
        return start_xy(p) if p else b.xy[n]

    for n, (x1, y1) in b.xy.items():
        x0, y0 = start_xy(n)
        old = a is not None and n in a.xy
        if final:
            color = GOOD if bt.proved[n] else BAD
            marker = "o" if bt.proved[n] else "s"
        elif old:
            color = GOOD if a.tree.proved[n] else BAD
            marker = "o" if a.tree.proved[n] else "s"
        else:
            color, marker = PENDING, "o"
        nodes[n] = (x0 + (x1 - x0) * s, y0 + (y1 - y0) * s, color, 1.0 if old else s, marker, not old and a is not None)

    if a is not None and not final:
        for n, (x, y) in a.xy.items():
            if n not in nodes:
                c = GOOD if a.tree.proved[n] else BAD
                nodes[n] = (x, y, c, 1 - s, "o" if a.tree.proved[n] else "s", False)

    # edges
    segs, cols = [], []
    for n, (x, y, _, al, _, _) in nodes.items():
        tree = bt if n in b.xy else a.tree
        p = tree.parent.get(n)
        if p and p in nodes:
            segs.append([(nodes[p][0], nodes[p][1]), (x, y)])
            cols.append(to_rgba(EDGE, al))
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=1.2, zorder=1))

    # nodes
    for marker in ("o", "s"):
        pts = [(n, v) for n, v in nodes.items() if v[4] == marker]
        if not pts:
            continue
        sizes = [150 if n == bt.root else 42 for n, _ in pts]
        ax.scatter(
            [v[0] for _, v in pts], [v[1] for _, v in pts], s=sizes, marker=marker,
            c=[to_rgba(v[2], v[3]) for _, v in pts],
            edgecolors=[to_rgba(INK if (v[5] and final) else SURFACE, v[3]) for _, v in pts],
            linewidths=[1.4 if (v[5] and final) else 1.0 for _, v in pts], zorder=3,
        )

    # labels: root + open subgoals
    lab_tree, lab_xy = (bt, b.xy) if final or a is None else (a.tree, a.xy)
    for n in lab_xy:
        if n not in nodes:
            continue
        x, y, _, al, _, _ = nodes[n]
        if n == lab_tree.root:
            ax.text(x, y - 14, n, ha="center", va="bottom", fontsize=10, color=INK, weight="bold", alpha=al)
        elif lab_tree.subgoal[n] and not lab_tree.proved[n]:
            right = x > 0.6 * W  # slant labels inward so they stay on canvas
            ax.text(x + (-4 if right else 4), y + 8, n, ha="right" if right else "left", va="top",
                    fontsize=7.5, color=INK_2, rotation=30 if right else -30,
                    rotation_mode="anchor", alpha=al)

    # header
    shown = b if final or a is None else a
    ax.text(SIDE, 30, title, fontsize=15, weight="bold", color=INK, va="center")
    ax.text(SIDE, 58,
            f"generation {shown.gen}/{n_gen - 1}  ·  program {shown.program}  ·  "
            f"{shown.solved}/{shown.total} subgoals proved",
            fontsize=11, color=INK_2, va="center")

    # legend (top right)
    lx, ly = W - SIDE - 445, 58
    for i, (mk, c, ec, lab) in enumerate([
        ("o", GOOD, SURFACE, "proved"),
        ("s", BAD, SURFACE, "open"),
        ("o", PENDING, SURFACE, "new, not yet rated"),
        ("o", GOOD, INK, "added this generation"),
    ]):
        x = lx + [0, 78, 146, 300][i]
        ax.scatter([x], [ly], s=42, marker=mk, c=c, edgecolors=ec, linewidths=1.4 if ec == INK else 1.0)
        ax.text(x + 9, ly, lab, fontsize=9, color=INK_2, va="center")

    # generation progress bar
    by = H - 28
    frac = (shown.gen + (s if not final and a is not None else 0)) / max(n_gen - 1, 1)
    ax.plot([SIDE, W - SIDE], [by, by], color="#e1e0d9", lw=4, solid_capstyle="round")
    ax.plot([SIDE, SIDE + (W - 2 * SIDE) * frac], [by, by], color=INK_2, lw=4, solid_capstyle="round")


def to_image(fig) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("island", type=Path, help="island directory, e.g. results/island_0")
    ap.add_argument("-o", "--out", type=Path, default=Path("proof.gif"))
    ap.add_argument("--program", type=int, help="final program (default: first solved, else best score)")
    ap.add_argument("--title", help="default: problem name from island metadata")
    ap.add_argument("--tween", type=int, default=4, help="interpolated frames per transition (0 = none)")
    ap.add_argument("--hold-ms", type=int, default=550)
    args = ap.parse_args()

    chain = lineage(args.island, args.program)
    trees = []
    for p in chain:
        d = args.island / f"program_{p}"
        decls = parse_sketch((d / "sketch.txt").read_text())
        trees.append(build_tree(decls, proved_names(d / "eval" / "succeeded_proofs.json")))
    max_depth = max(max(layout(t)[0][n][1] for n in t.children) for t in trees)
    frames = [make_frame(t, p, g, max_depth) for g, (t, p) in enumerate(zip(trees, chain))]
    # drop generations whose tree and colours are unchanged from the previous one
    sig = lambda f: (f.tree.parent, f.tree.proved)
    frames = [f for i, f in enumerate(frames) if i == 0 or i == len(frames) - 1 or sig(f) != sig(frames[i - 1])]
    title = args.title or problem_name(args.island)

    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    images, durations = [], []
    for i, b in enumerate(frames):
        a = frames[i - 1] if i else None
        if a is not None:
            for k in range(1, args.tween + 1):
                render(ax, a, b, k / (args.tween + 1), len(chain), title)
                images.append(to_image(fig))
                durations.append(50)
        render(ax, a, b, 1.0, len(chain), title)
        images.append(to_image(fig))
        durations.append(args.hold_ms)
    durations[0] = 1500
    durations[-1] = 4000
    plt.close(fig)

    # one shared palette so colours don't flicker between frames
    sample = Image.new("RGB", (W, H * 3))
    for j, im in enumerate([images[0], images[len(images) // 2], images[-1]]):
        sample.paste(im, (0, H * j))
    pal = sample.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    frames_p = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in images]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frames_p[0].save(args.out, save_all=True, append_images=frames_p[1:], duration=durations, loop=0, optimize=True)
    print(f"{args.out}: {len(chain)} generations, {len(images)} frames, {args.out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
