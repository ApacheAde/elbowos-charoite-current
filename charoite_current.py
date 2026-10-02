"""Charoite Current — neon tide-hopper for ElbowOS. Python 3 + pygame.

Hop a cream moth across drifting copper logs on a lilac charoite river.
Pearls score. Coral eels punish a bad landing. Reach the beacon to bank a run.
"""
import math
import os
import random
import subprocess
import sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/CHAROITE_CURRENT_ElbowOS.mp4")
LANES = 7
INK = (22, 8, 40)
LILAC = (176, 112, 255)
CREAM = (255, 236, 198)
COPPER = (214, 126, 62)
MINT = (126, 255, 198)
CORAL = (255, 78, 118)
GOLD = (255, 214, 78)
TEAL = (46, 196, 204)

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.Surface((W, H))
        pygame.display.set_caption("Charoite Current")
        self.font = pygame.font.SysFont("dejavusans", 64, bold=True)
        self.mid = pygame.font.SysFont("dejavusans", 42, bold=True)
        self.small = pygame.font.SysFont("dejavusans", 32, bold=True)
        self.rng = random.Random(7)
        self.t = 0
        self.reset_run()

    def reset_run(self):
        self.score = 0
        self.lives = 3
        self.speed = 1.0
        self.crosses = 0
        self.flash = 0
        self.sparks = []
        self.x = W * 0.5
        self.lane = 0
        self.hop = 0.0
        self.hop_from = 0
        self.aim = self.x
        self.logs = []
        self.eels = []
        for lane in range(1, LANES):
            direction = -1 if lane % 2 else 1
            n = 3 if lane % 2 else 4
            span = W + 280
            for i in range(n):
                self.logs.append({
                    "lane": lane,
                    "x": i * (span / n) - 80,
                    "w": self.rng.choice((220, 280, 340)),
                    "dir": direction,
                    "spd": self.rng.uniform(3.2, 6.4),
                    "pearl": self.rng.random() < 0.55,
                })
            self.eels.append({
                "lane": lane,
                "x": self.rng.uniform(0, W),
                "dir": -direction,
                "spd": self.rng.uniform(4.5, 8.0),
                "ph": self.rng.random() * 6,
            })

    def lane_y(self, lane):
        top, bot = 250, H - 210
        return bot - (bot - top) * (lane / (LANES - 1))

    def riding(self):
        if self.lane <= 0 or self.hop > 0:
            return None
        y = self.lane
        for log in self.logs:
            if log["lane"] == y and log["x"] - 18 <= self.x <= log["x"] + log["w"] + 18:
                return log
        return None

    def start_hop(self, aim):
        if self.hop > 0 or self.lane >= LANES - 1:
            return
        self.hop = 1.0
        self.hop_from = self.lane
        self.aim = max(70, min(W - 70, aim))

    def update(self, keys=None, auto=False):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        for log in self.logs:
            log["x"] += log["dir"] * log["spd"] * self.speed
            if log["x"] > W + 60:
                log["x"] = -log["w"] - 40
                log["pearl"] = self.rng.random() < 0.5
            if log["x"] < -log["w"] - 60:
                log["x"] = W + 40
                log["pearl"] = self.rng.random() < 0.5
        for eel in self.eels:
            eel["x"] += eel["dir"] * eel["spd"] * self.speed
            eel["ph"] += 0.15
            if eel["x"] > W + 80:
                eel["x"] = -80
            if eel["x"] < -80:
                eel["x"] = W + 80
        if self.hop > 0:
            self.hop = max(0.0, self.hop - 0.085)
            self.x += (self.aim - self.x) * 0.28
            if self.hop == 0.0:
                self.lane = self.hop_from + 1
                log = self.riding()
                if self.lane >= LANES - 1:
                    self.score += 150 + self.crosses * 20
                    self.crosses += 1
                    self.speed = min(2.2, self.speed + 0.12)
                    self.flash = 12
                    self.burst(self.x, self.lane_y(self.lane), GOLD)
                    self.lane = 0
                    self.x = W * 0.5
                elif log is None:
                    self.lives = max(0, self.lives - 1)
                    self.score = max(0, self.score - 20)
                    self.burst(self.x, self.lane_y(self.lane), CORAL)
                    self.lane = max(0, self.lane - 1)
                elif log["pearl"]:
                    log["pearl"] = False
                    self.score += 40
                    self.burst(self.x, self.lane_y(self.lane), MINT)
        else:
            log = self.riding()
            if log:
                self.x += log["dir"] * log["spd"] * self.speed
                self.x = max(60, min(W - 60, self.x))
        if auto:
            self.autopilot()
        elif keys:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.x -= 9
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.x += 9
            self.x = max(60, min(W - 60, self.x))
        nxt = []
        for s in self.sparks:
            s["life"] -= 1
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["vy"] += 0.25
            if s["life"] > 0:
                nxt.append(s)
        self.sparks = nxt

    def autopilot(self):
        if self.hop > 0 or self.lane >= LANES - 1:
            return
        nxt = self.lane + 1
        best = None
        best_d = 1e9
        for log in self.logs:
            if log["lane"] != nxt:
                continue
            cx = log["x"] + log["w"] * 0.5
            # predict a little so the hop lands on the moving log
            cx += log["dir"] * log["spd"] * self.speed * 6
            if -40 < cx < W + 40 and abs(cx - self.x) < best_d and abs(cx - self.x) < log["w"] * 0.55 + 90:
                best, best_d = cx, abs(cx - self.x)
        if best is not None and self.t % 8 == 0:
            self.start_hop(best)
        elif best is None:
            # sidle toward the nearest future log
            near = min(self.logs, key=lambda g: abs((g["x"] + g["w"] * 0.5) - self.x) if g["lane"] == nxt else 1e9)
            if near["lane"] == nxt:
                self.x += 6 if near["x"] + near["w"] * 0.5 > self.x else -6

    def burst(self, x, y, col):
        for _ in range(14):
            ang = self.rng.random() * math.tau
            sp = self.rng.uniform(2, 8)
            self.sparks.append({"x": x, "y": y, "vx": math.cos(ang) * sp, "vy": math.sin(ang) * sp - 2, "life": 16, "col": col})

    def draw(self, surf):
        surf.fill(INK)
        # charoite swirl bands
        for i in range(14):
            yy = int((i * 140 + self.t * (2 + i % 3)) % (H + 160)) - 80
            shade = 36 + (i * 11) % 40
            pygame.draw.ellipse(surf, (shade, 16 + i % 12, 58), (-120, yy, W + 240, 90))
        top, bot = 250, H - 210
        pygame.draw.rect(surf, (12, 28, 48), (40, top - 70, W - 80, bot - top + 150), border_radius=36)
        for lane in range(LANES):
            y = self.lane_y(lane)
            pygame.draw.line(surf, (70, 40, 110), (70, int(y)), (W - 70, int(y)), 2)
        # dock + beacon
        pygame.draw.rect(surf, (70, 48, 36), (80, self.lane_y(0) - 18, W - 160, 36), border_radius=10)
        bx, by = W // 2, self.lane_y(LANES - 1) - 70
        pygame.draw.rect(surf, (255, 220, 120), (bx - 18, by, 36, 78), border_radius=6)
        glow = 80 + int(40 * math.sin(self.t * 0.2))
        pygame.draw.circle(surf, (255, glow, 60), (bx, by - 8), 28)
        pygame.draw.circle(surf, CREAM, (bx, by - 8), 12)
        for log in self.logs:
            y = self.lane_y(log["lane"])
            rect = pygame.Rect(int(log["x"]), int(y - 28), int(log["w"]), 56)
            pygame.draw.rect(surf, COPPER, rect, border_radius=16)
            pygame.draw.rect(surf, (255, 176, 96), rect.inflate(-16, -18), border_radius=10)
            for k in range(3):
                pygame.draw.arc(surf, (120, 64, 28), rect.inflate(-20 - k * 30, -8), 0.3, 2.6, 2)
            if log["pearl"]:
                pygame.draw.circle(surf, MINT, (int(log["x"] + log["w"] * 0.5), int(y - 6)), 12)
                pygame.draw.circle(surf, CREAM, (int(log["x"] + log["w"] * 0.5) - 3, int(y - 10)), 4)
        for eel in self.eels:
            y = self.lane_y(eel["lane"]) + 46
            ex = eel["x"]
            body = [(ex + math.sin(eel["ph"] + k) * 8, y + math.sin(eel["ph"] * 1.4 + k * 0.6) * 10) for k in range(0, 70, 8)]
            if len(body) > 1:
                pygame.draw.lines(surf, CORAL, False, body, 6)
            pygame.draw.circle(surf, (255, 180, 80), (int(ex), int(y)), 7)
        # moth
        ly = self.lane
        if self.hop > 0:
            a = 1.0 - self.hop
            ly = self.hop_from + a
            arc = math.sin(a * math.pi) * 70
        else:
            arc = 0
        my = self.lane_y(ly) - arc - 8
        flap = math.sin(self.t * 0.7) * 16
        pygame.draw.ellipse(surf, LILAC, (self.x - 34, my - 8 + flap * 0.2, 28, 18))
        pygame.draw.ellipse(surf, LILAC, (self.x + 6, my - 8 - flap * 0.2, 28, 18))
        pygame.draw.circle(surf, CREAM, (int(self.x), int(my)), 16)
        pygame.draw.circle(surf, (40, 20, 50), (int(self.x) - 5, int(my) - 2), 3)
        pygame.draw.circle(surf, (40, 20, 50), (int(self.x) + 5, int(my) - 2), 3)
        for s in self.sparks:
            pygame.draw.circle(surf, s["col"], (int(s["x"]), int(s["y"])), 4)
        if self.flash:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 220, 120, 50))
            surf.blit(veil, (0, 0))
        title = self.font.render("CHAROITE CURRENT", True, CREAM)
        surf.blit(title, title.get_rect(center=(W // 2, 90)))
        sub = self.small.render("tide hopper  ·  python 3", True, LILAC)
        surf.blit(sub, sub.get_rect(center=(W // 2, 150)))
        sc = self.mid.render(f"SCORE  {self.score}", True, GOLD)
        surf.blit(sc, sc.get_rect(center=(W // 2, 210)))
        hearts = " ".join("●" if i < self.lives else "○" for i in range(3))
        lv = self.small.render(hearts, True, CORAL)
        surf.blit(lv, lv.get_rect(center=(W // 2, H - 130)))
        tag = self.mid.render("x.com/ElbowOS", True, TEAL)
        surf.blit(tag, tag.get_rect(center=(W // 2, H - 72)))

    def play_interactive(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            keys = pygame.key.get_pressed()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.start_hop(self.x)
            self.update(keys, auto=False)
            self.draw(self.screen)
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()

    def record(self):
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
            "-preset", "veryfast", "-movflags", "+faststart", OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        frames = FPS * SECS
        try:
            for _ in range(frames):
                self.update(auto=True)
                self.draw(self.screen)
                raw = pygame.image.tobytes(self.screen, "RGB")
                proc.stdin.write(raw)
        finally:
            proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1500:]}")
        print("wrote", OUT)
        pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()
