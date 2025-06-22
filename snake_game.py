import pygame
import random
import time
import os
from pygame import mixer
import json

pygame.init()
mixer.init()

# Sound loading with error handling
try:
    bg_music = mixer.Sound("bg_music.mp3")
    eat_sound = mixer.Sound("eat.wav")
    powerup_sound = mixer.Sound("powerup.wav")
    levelup_sound = mixer.Sound("levelup.wav")
    bg_music.set_volume(0.3)
    bg_music.play(-1)
except pygame.error as e:
    print(f"Warning: Sound file loading failed - {e}. Continuing without sound.")
    bg_music = eat_sound = powerup_sound = levelup_sound = None

# Window setup
width, height = 600, 400
game_window = pygame.display.set_mode((width, height))
pygame.display.set_caption("Snake Game by GKM")

# Colors
bg_color = (20, 20, 30)
snake_color = (0, 255, 100)
fruit_color = (255, 105, 180)
score_box_color = (255, 255, 255)
score_text_color = (0, 0, 0)
button_color = (255, 255, 255)
powerup_color = (255, 215, 0)
speed_powerup_color = (0, 150, 255)
multiplier_powerup_color = (200, 0, 200)
obstacle_color = (200, 200, 200)
glow_color = (50, 255, 150, 50)
trail_color = (0, 255, 100, 50)
particle_color = (255, 255, 255, 100)
achievement_color = (255, 255, 0)

# Fonts
font_big = pygame.font.SysFont("arial", 40, True)
font_small = pygame.font.SysFont("arial", 22)
font_level = pygame.font.SysFont("arial", 18)

# Game settings
block = 10
FPS = 60
clock = pygame.time.Clock()

LEVELS = {
    "Low": {"speed": 10, "powerup_chance": 0.05, "obstacles": 0},
    "Medium": {"speed": 15, "powerup_chance": 0.03, "obstacles": 3},
    "High": {"speed": 20, "powerup_chance": 0.02, "obstacles": 5}
}

# Achievements System
ACHIEVEMENTS = {
    "score_50": {"name": "Score Master", "desc": "Reach a score of 50", "condition": lambda stats: stats["score"] >= 50, "unlocked": False},
    "powerups_3": {"name": "Power-up Pro", "desc": "Collect 3 power-ups", "condition": lambda stats: stats["powerups_collected"] >= 3, "unlocked": False},
    "level_3": {"name": "Level Climber", "desc": "Reach Level 3", "condition": lambda stats: stats["level"] >= 3, "unlocked": False}
}

def load_achievements():
    try:
        if os.path.exists("achievements.json"):
            with open("achievements.json", "r") as f:
                data = json.load(f)
                for key in ACHIEVEMENTS:
                    ACHIEVEMENTS[key]["unlocked"] = data.get(key, False)
    except Exception as e:
        print(f"Error loading achievements: {e}")

def save_achievements():
    try:
        data = {key: ACHIEVEMENTS[key]["unlocked"] for key in ACHIEVEMENTS}
        with open("achievements.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving achievements: {e}")

def check_achievements(stats):
    new_unlocks = []
    for key, ach in ACHIEVEMENTS.items():
        if not ach["unlocked"] and ach["condition"](stats):
            ach["unlocked"] = True
            new_unlocks.append(ach["name"])
    if new_unlocks:
        save_achievements()
    return new_unlocks

load_achievements()

# High Score
def get_high_score():
    try:
        if not os.path.exists("highscore.txt"):
            with open("highscore.txt", "w") as f:
                f.write("0")
        with open("highscore.txt", "r") as f:
            val = f.read().strip()
            return int(val) if val.isdigit() else 0
    except Exception as e:
        print(f"Error reading high score: {e}. Defaulting to 0.")
        return 0

def update_high_score(score):
    try:
        if score > get_high_score():
            with open("highscore.txt", "w") as f:
                f.write(str(score))
    except Exception as e:
        print(f"Error updating high score: {e}")

# Score and Level Display
def show_score(score, high_score, level, level_progress, speed_boost_timer, multiplier_active):
    pygame.draw.rect(game_window, score_box_color, [width//2 - 140, 10, 280, 35], border_radius=10)
    status = []
    if speed_boost_timer > 0:
        status.append(f"Speed Boost: {int(speed_boost_timer)}s")
    if multiplier_active:
        status.append("2x Score")
    status_text = " | ".join(status)
    score_text = font_small.render(f"Score: {score}  High Score: {high_score}  {status_text}", True, score_text_color)
    game_window.blit(score_text, (width//2 - score_text.get_width()//2, 18))
    
    level_text = font_level.render(f"Level: {level}", True, button_color)
    game_window.blit(level_text, (10, 10))
    
    pygame.draw.rect(game_window, (100, 100, 100), [10, 30, 100, 10])
    progress_width = min(100, (level_progress / 50) * 100)
    pygame.draw.rect(game_window, snake_color, [10, 30, progress_width, 10])

# Draw Snake
def draw_snake(snake_list, frame_count, trail):
    for pos in trail:
        pygame.draw.rect(game_window, trail_color, [pos[0], pos[1], block, block], border_radius=5)
    
    for i, part in enumerate(snake_list):
        intensity = 255 - (i * 15) % 255
        base_color = (0, intensity, 100)
        pulse = 1.0 + 0.1 * (1 + (frame_count % 60) / 30.0)
        size = block * pulse
        offset = (block - size) / 2
        pygame.draw.rect(
            game_window, base_color,
            [part[0] + offset, part[1] + offset, size, size],
            border_radius=5
        )
        if i == len(snake_list) - 1:
            pygame.draw.rect(
                game_window, glow_color,
                [part[0] - 2, part[1] - 2, block + 4, block + 4],
                border_radius=7
            )

# Draw Obstacles
def draw_obstacles(obstacles):
    for obs in obstacles:
        pygame.draw.rect(game_window, obstacle_color, [obs[0], obs[1], block, block], border_radius=3)

# Draw Animated Food/Power-ups
def draw_animated_item(x, y, color, frame_count, is_powerup=False):
    pulse = 1.0 + 0.15 * (1 + (frame_count % 60) / 30.0)
    size = block * pulse
    offset = (block - size) / 2
    pygame.draw.rect(
        game_window, color,
        [x + offset, y + offset, size, size],
        border_radius=5
    )
    if is_powerup:
        glow_size = block * 1.5 * pulse
        glow_offset = (block - glow_size) / 2
        pygame.draw.rect(
            game_window, (*color[:3], 50),
            [x + glow_offset, y + glow_offset, glow_size, glow_size],
            border_radius=7
        )

# Particle Effect for Game Over
def draw_particles(particles):
    for particle in particles:
        pygame.draw.circle(game_window, particle_color, (int(particle[0]), int(particle[1])), particle[2])
        particle[0] += particle[3]
        particle[1] += particle[4]
        particle[2] -= 0.1
        particle[5] -= 0.05

# Dynamic Background
def draw_background(frame_count):
    game_window.fill(bg_color)
    for x in range(0, width, block * 2):
        pygame.draw.line(game_window, (30, 30, 40), (x, 40), (x, height), 1)
    for y in range(40, height, block * 2):
        pygame.draw.line(game_window, (30, 30, 40), (0, y), (width, y), 1)
    
    for i in range(20):
        x = (i * 50 + frame_count) % width
        y = 40 + (i * 20) % (height - 40)
        pygame.draw.circle(game_window, (200, 200, 200), (int(x), int(y)), 2)

# Message Box
def show_message(msg, sub=None, fade=False, scale=False, achievements=None):
    game_window.fill(bg_color)
    main_text = font_big.render(msg, True, button_color)
    sub_text = font_small.render(sub, True, button_color) if sub else None
    
    if scale:
        for scale_factor in [1.0 + 0.1 * (i / 10) for i in range(20)] + [1.2, 1.2]:
            game_window.fill(bg_color)
            scaled_text = pygame.transform.scale(
                main_text, (int(main_text.get_width() * scale_factor), int(main_text.get_height() * scale_factor))
            )
            main_rect = scaled_text.get_rect(center=(width//2, height//2 - 40))
            game_window.blit(scaled_text, main_rect)
            if sub_text:
                game_window.blit(sub_text, (width//2 - sub_text.get_width()//2, height//2 + 10))
            pygame.display.update()
            clock.tick(60)
    
    if fade:
        alpha_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for alpha in range(0, 255, 5):
            alpha_surface.fill((0, 0, 0, alpha))
            game_window.blit(alpha_surface, (0, 0))
            pygame.display.update()
            clock.tick(60)
    
    game_window.fill(bg_color)
    main_rect = main_text.get_rect(center=(width//2, height//2 - 40))
    game_window.blit(main_text, main_rect)
    if sub_text:
        game_window.blit(sub_text, (width//2 - sub_text.get_width()//2, height//2 + 10))
    
    if achievements:
        for i, ach in enumerate(achievements):
            ach_text = font_small.render(f"Achievement Unlocked: {ach}", True, achievement_color)
            game_window.blit(ach_text, (width//2 - ach_text.get_width()//2, height//2 + 40 + i*30))
    
    pygame.display.update()

# Achievements Menu
def show_achievements():
    frame_count = 0
    while True:
        draw_background(frame_count)
        show_message("Achievements", "Press ESC to return")
        
        y_offset = height//2 - 50
        for key, ach in ACHIEVEMENTS.items():
            status = "Unlocked" if ach["unlocked"] else "Locked"
            text = font_small.render(f"{ach['name']}: {ach['desc']} ({status})", True, button_color)
            game_window.blit(text, (width//2 - text.get_width()//2, y_offset))
            y_offset += 30
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
        
        frame_count += 1
        pygame.display.update()
        clock.tick(30)

# Level Selection Menu
def select_level():
    selected = "Low"
    frame_count = 0
    while True:
        draw_background(frame_count)
        show_message("Select Difficulty", "Use Left/Right to choose, Enter to start, A for Achievements")
        
        level_text = font_small.render(f"Difficulty: {selected}", True, button_color)
        game_window.blit(level_text, (width//2 - level_text.get_width()//2, height//2 + 60))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    selected = {"Low": "High", "Medium": "Low", "High": "Medium"}[selected]
                elif event.key == pygame.K_RIGHT:
                    selected = {"Low": "Medium", "Medium": "High", "High": "Low"}[selected]
                elif event.key == pygame.K_RETURN:
                    return selected
                elif event.key == pygame.K_a:
                    show_achievements()
        
        frame_count += 1
        pygame.display.update()
        clock.tick(30)

# Main Game
def game_loop():
    high_score = get_high_score()
    level = select_level()
    base_speed = LEVELS[level]["speed"]
    powerup_chance = LEVELS[level]["powerup_chance"]
    num_obstacles = LEVELS[level]["obstacles"]
    
    x, y = width//2, height//2
    dx, dy = 0, 0
    snake = [[x, y]]
    length = 1
    score = 0
    level_progress = 0
    current_level = 1
    game_over = False
    paused = False
    speed_boost_timer = 0
    multiplier_active = False
    multiplier_timer = 0
    speed_boost_cooldown = 0
    frame_count = 0
    trail = []
    stats = {"score": 0, "powerups_collected": 0, "level": 1}

    def is_valid_position(pos, snake, obstacles, food=None, powerup=None):
        if not (0 <= pos[0] < width and 40 <= pos[1] < height):
            return False
        if pos in snake or pos in obstacles:
            return False
        if food and pos == [food[0], food[1]]:
            return False
        if powerup and pos == [powerup[0], powerup[1]]:
            return False
        return True

    food_x = round(random.randrange(0, width - block) / 10) * 10
    food_y = round(random.randrange(40, height - block) / 10) * 10
    powerup_x, powerup_y, powerup_type = None, None, None

    obstacles = []
    for _ in range(num_obstacles):
        while True:
            ox = round(random.randrange(0, width - block) / 10) * 10
            oy = round(random.randrange(40, height - block) / 10) * 10
            if is_valid_position([ox, oy], snake, obstacles, [food_x, food_y]):
                obstacles.append([ox, oy])
                break

    achievement_notification = []
    notification_timer = 0

    while not game_over:
        while paused:
            show_message("Paused", "Press P to Resume")
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                    paused = False
                elif event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and dx == 0:
            dx = -block
            dy = 0
        elif keys[pygame.K_RIGHT] and dx == 0:
            dx = block
            dy = 0
        elif keys[pygame.K_UP] and dy == 0:
            dy = -block
            dx = 0
        elif keys[pygame.K_DOWN] and dy == 0:
            dy = block
            dx = 0
        elif keys[pygame.K_SPACE] and speed_boost_cooldown <= 0:
            speed_boost_timer = 5
            speed_boost_cooldown = 15
            if powerup_sound:
                powerup_sound.play()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    paused = True
                elif event.key == pygame.K_r:
                    if bg_music:
                        bg_music.play(-1)
                    game_loop()
                elif event.key == pygame.K_q:
                    pygame.quit()
                    quit()

        effective_speed = (base_speed + score // 50) * (2 if speed_boost_timer > 0 else 1)
        if frame_count % max(1, 60 // effective_speed) == 0:
            x += dx
            y += dy

            if x >= width: x = 0
            elif x < 0: x = width - block
            if y >= height: y = 40
            elif y < 40: y = height - block

            head = [x, y]
            snake.append(head)
            trail.append([x, y])
            if len(trail) > 10:
                trail.pop(0)

            if len(snake) > length:
                del snake[0]

            if head in snake[:-1] or any(head[0] == obs[0] and head[1] == obs[1] for obs in obstacles):
                if bg_music:
                    bg_music.stop()
                particles = [[x, y, random.uniform(2, 5), random.uniform(-2, 2), random.uniform(-2, 2), 1.0] for _ in range(20)]
                for _ in range(60):
                    game_window.fill(bg_color)
                    draw_particles(particles)
                    pygame.display.update()
                    clock.tick(60)
                show_message("Game Over", "Press R to Restart or Q to Quit", fade=True, achievements=achievement_notification)
                update_high_score(score)
                while True:
                    for event in pygame.event.get():
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_r:
                                if bg_music:
                                    bg_music.play(-1)
                                game_loop()
                            elif event.key == pygame.K_q:
                                pygame.quit()
                                quit()

        draw_background(frame_count)
        draw_animated_item(food_x, food_y, fruit_color, frame_count)

        if powerup_x is not None and powerup_y is not None:
            color = {
                "length": powerup_color,
                "speed": speed_powerup_color,
                "multiplier": multiplier_powerup_color
            }[powerup_type]
            draw_animated_item(powerup_x, powerup_y, color, frame_count, is_powerup=True)

        draw_obstacles(obstacles)
        draw_snake(snake, frame_count, trail)
        show_score(score, high_score, current_level, level_progress, speed_boost_timer, multiplier_active)
        
        # Draw achievement notification
        if notification_timer > 0:
            for i, ach in enumerate(achievement_notification):
                ach_text = font_small.render(f"Achievement: {ach}", True, achievement_color)
                game_window.blit(ach_text, (width - ach_text.get_width() - 10, 50 + i*30))
            notification_timer -= 1 / FPS
        
        pygame.display.update()

        if x == food_x and y == food_y:
            if eat_sound:
                eat_sound.play()
            score += 10 * (2 if multiplier_active else 1)
            stats["score"] = score
            length += 1
            level_progress += 10
            while True:
                food_x = round(random.randrange(0, width - block) / 10) * 10
                food_y = round(random.randrange(40, height - block) / 10) * 10
                if is_valid_position([food_x, food_y], snake, obstacles, powerup=[powerup_x, powerup_y]):
                    break

            if random.random() < powerup_chance and powerup_x is None:
                attempts = 0
                while attempts < 100:
                    powerup_x = round(random.randrange(0, width - block) / 10) * 10
                    powerup_y = round(random.randrange(40, height - block) / 10) * 10
                    if is_valid_position([powerup_x, powerup_y], snake, obstacles, [food_x, food_y]):
                        break
                    attempts += 1
                else:
                    powerup_x, powerup_y = None, None
                if powerup_x is not None:
                    powerup_type = random.choice(["length", "speed", "multiplier"])

            if level_progress >= 50:
                current_level += 1
                stats["level"] = current_level
                level_progress = 0
                base_speed += 2
                if levelup_sound:
                    levelup_sound.play()
                show_message(f"Level {current_level}", "Press any key to continue", fade=True, scale=True)
                pygame.event.clear()
                while True:
                    event = pygame.event.wait()
                    if event.type == pygame.KEYDOWN:
                        break

        if powerup_x is not None and x == powerup_x and y == powerup_y:
            if powerup_sound:
                powerup_sound.play()
            stats["powerups_collected"] += 1
            if powerup_type == "length":
                score += 20 * (2 if multiplier_active else 1)
                stats["score"] = score
                length += 2
            elif powerup_type == "speed":
                speed_boost_timer = 5
            elif powerup_type == "multiplier":
                multiplier_active = True
                multiplier_timer = time.time()
            powerup_x, powerup_y, powerup_type = None, None, None

        # Check achievements
        new_achievements = check_achievements(stats)
        if new_achievements:
            achievement_notification.extend(new_achievements)
            notification_timer = 3  # Show for 3 seconds

        if speed_boost_timer > 0:
            speed_boost_timer -= 1 / FPS
        if speed_boost_cooldown > 0:
            speed_boost_cooldown -= 1 / FPS
        if multiplier_active and time.time() - multiplier_timer > 10:
            multiplier_active = False

        frame_count += 1
        clock.tick(FPS)

    pygame.quit()
    quit()

if __name__ == "__main__":
    game_loop()