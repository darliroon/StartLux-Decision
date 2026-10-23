"""用 ~100 行 Python 造一个"游戏 demo" —— 复现官方 Mario / 计算机操作 demo 的机制.

游戏: 6x7 网格, P 从起点走到金子 G, 走最短需 7 步.
循环 = 官方所有游戏 demo 的通用架构:

    while 未结束:
        state  = 游戏状态 -> 文本            (感知, 代码)
        opts   = 枚举合法动作 (+ 预演结果)    (代码)
        answer = model.decide(state, q)       (模型, 一次前向)
        执行 answer                           (代码)

对比两种选项写法, 验证"把后果预演写进选项"是不是关键:
  模式 A: 选项带代码预演出的结果   (官方 Mario demo 的做法)
  模式 B: 光杆 up/down/left/right  (模型自己推空间关系)
"""
import time

from startlux_decision import StartLuxDecision

ROWS = [
    "######",
    "#....#",
    "#.##.#",
    "#.#..#",
    "#..#.#",
    "#....#",
    "######",
]
START, GOAL = (1, 1), (4, 5)          # (x, y)，最短路径 7 步
MOVES = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

m = StartLuxDecision("/data/liufeng/models/StartLux-Decision-4B")


def cell(x, y):
    return ROWS[y][x]


def render(px, py, trail=()):
    g = [list(r) for r in ROWS]
    for x, y in trail:
        g[y][x] = "*"
    g[GOAL[1]][GOAL[0]] = "G"
    g[py][px] = "P"
    return "\n".join("".join(r) for r in g)


def simulate(px, py, mv):
    """harness 预演一步: 返回 (新x, 新y, 后果描述). Mario demo 的核心机关."""
    dx, dy = MOVES[mv]
    nx, ny = px + dx, py + dy
    if cell(nx, ny) == "#":
        return px, py, f"blocked by a wall, you would stay at ({px},{py})"
    if (nx, ny) == GOAL:
        return nx, ny, "you would step onto the gold and WIN the game"
    return nx, ny, f"you would move to ({nx},{ny}), an empty floor"


def play(describe, label):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    px, py = START
    visited = [START]
    t0 = time.perf_counter()
    for step in range(1, 16):
        state = (f"Grid game. Map ('#' is wall, '.' is floor):\n{render(px, py)}\n\n"
                 f"You are P, standing at (x={px}, y={py}). Rows count from the top, so 'up' "
                 f"means y decreases. The gold G is at (x={GOAL[0]}, y={GOAL[1]}). "
                 f"Steps taken so far: {step - 1}.")
        criteria = {mv: (simulate(px, py, mv)[2] if describe else None) for mv in MOVES}
        questions = {
            "move": {"type": "choice", "instructions": "Pick the best move now.",
                     "criteria": criteria},
            "will_win": {"type": "noul",
                         "instructions": "After you make your chosen move, will you be standing on the gold?"},
        }
        if step == 1 and describe:          # 展示一次模型真正读到的东西
            print("---- 第 1 步模型读到的 state: ----")
            print(state)
            print("---- 选项及 criteria (代码预演出的后果): ----")
            for k, v in criteria.items():
                print(f"    {k}: {v}")
            print()
        answers, _ = m.decide(state, questions)
        mv = answers["move"]["choice"]
        top = sorted(answers["move"]["probabilities"].items(), key=lambda kv: -kv[1])
        print(f"  step {step:>2}: at ({px},{py})  pick {mv:<5} "
              f"[{' '.join(f'{k}={v:.2f}' for k, v in top[:3])}]  P(下一步赢)={answers['will_win']['noul']:.2f}")
        px, py, _ = simulate(px, py, mv)
        visited.append((px, py))
        if (px, py) == GOAL:
            ms = (time.perf_counter() - t0) * 1000
            print(f"  >>> WIN: {step} 步到达金子, 总耗时 {ms:.0f} ms ({ms / step:.0f} ms/步), "
                  f"轨迹 (* 为走过的路):")
            print("  " + render(px, py, visited).replace("\n", "\n  "))
            return step
    print("  15 步内未到达:")
    print("  " + render(px, py, visited).replace("\n", "\n  "))
    return None


a = play(True,  "模式 A: 选项带代码预演的后果 (官方 Mario demo 的做法)")
b = play(False, "模式 B: 光杆选项 up/down/left/right (不给预演, 模型自己算空间关系)")
print(f"\n结论: 模式 A 用了 {a} 步, 模式 B 用了 {b} 步 (最短 7 步)")
