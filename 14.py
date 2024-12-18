import pygame
import random
import time
from anytree import Node
from collections import deque

pygame.init()

pygame.mixer.init()

wall_sound = pygame.mixer.Sound("wall.mp3")
path_sound = pygame.mixer.Sound("path.mp3")
wall_sound.set_volume(0.7)
path_sound.set_volume(0.7)
sound_queue = deque()

BASE_WIDTH, BASE_HEIGHT = 600, 600
ROWS, COLS = 6, 6

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
GRAY = (50, 50, 50)
RED = (255, 0, 0)

DIRECTIONS = {'W': (0, -1),
              'A': (-1, 0),
              'S': (0, 1),
              'D': (1, 0)}
CARDINAL_DIRECTIONS = {'W': 'N',
                       'A': 'W',
                       'S': 'S',
                       'D': 'E'}
OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

class IRInstruction:
    def __init__(self, command, direction, steps=1):
        self.command = command
        self.direction = direction
        self.steps = steps

    def __repr__(self):
        return f"{self.command}({self.direction}, {self.steps})"


screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT + 165))

pygame.display.set_caption("隠された迷路")
logo = pygame.image.load("logo.png")
pygame.display.set_icon(logo)

font = pygame.font.Font(None, 36)

endpoint_image = pygame.image.load("endpoint.png").convert_alpha()
check_image = pygame.image.load("check.png").convert_alpha()
reveal_image = pygame.image.load("reveal.png").convert_alpha()

sprite_sheet = pygame.image.load("character.png").convert_alpha()
SPRITE_WIDTH = sprite_sheet.get_width() // 6
SPRITE_HEIGHT = sprite_sheet.get_height() // 5

def get_sprite(row, col):
    raw_sprite = sprite_sheet.subsurface(pygame.Rect(col * SPRITE_WIDTH, row * SPRITE_HEIGHT, SPRITE_WIDTH, SPRITE_HEIGHT))
    return pygame.transform.scale(raw_sprite, (CELL_SIZE, CELL_SIZE))


x = 0
hint1 = 5
hint2 = 3
level = 1
walls_visible = True
attempts = 4 + level

def calculate_cell_size(rows, cols):
    return min(BASE_WIDTH // cols, BASE_HEIGHT // rows)

def generate_maze(rows, cols):
    maze = [[{'N': True, 'S': True, 'E': True, 'W': True} for _ in range(cols)] for _ in range(rows)]

    stack = []
    visited = set()
    current_cell = (0, 0)
    visited.add(current_cell)
    stack.append(current_cell)

    def neighbors(cell):
        x, y = cell
        possible_neighbors = [
            ((x, y - 1), 'N', 'S'),
            ((x, y + 1), 'S', 'N'),
            ((x - 1, y), 'W', 'E'),
            ((x + 1, y), 'E', 'W'),
        ]
        return [
            (n_cell, dir1, dir2)
            for n_cell, dir1, dir2 in possible_neighbors
            if 0 <= n_cell[0] < cols and 0 <= n_cell[1] < rows and n_cell not in visited
        ]

    while stack:
        current_cell = stack[-1]
        valid_neighbors = neighbors(current_cell)

        if valid_neighbors:
            chosen_cell, direction, opposite = random.choice(valid_neighbors)
            x, y = current_cell
            maze[y][x][direction] = False
            nx, ny = chosen_cell
            maze[ny][nx][opposite] = False
            visited.add(chosen_cell)
            stack.append(chosen_cell)
        else:
            stack.pop()

    return maze

def draw_maze(maze, visible):
    color = WHITE if visible else BLACK
    for y in range(len(maze)):
        for x in range(len(maze[y])):
            cell = maze[y][x]
            if cell['N']:
                pygame.draw.line(screen, color, (x * CELL_SIZE, y * CELL_SIZE),
                                 ((x + 1) * CELL_SIZE, y * CELL_SIZE), 2)
            if cell['S']:
                pygame.draw.line(screen, color, (x * CELL_SIZE, (y + 1) * CELL_SIZE),
                                 ((x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE), 2)
            if cell['W']:
                pygame.draw.line(screen, color, (x * CELL_SIZE, y * CELL_SIZE),
                                 (x * CELL_SIZE, (y + 1) * CELL_SIZE), 2)
            if cell['E']:
                pygame.draw.line(screen, color, ((x + 1) * CELL_SIZE, y * CELL_SIZE),
                                 ((x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE), 2)

def draw_player(x, y, sprite):
    screen.blit(sprite, (x * CELL_SIZE, y * CELL_SIZE))

def draw_endpoint(x, y):
    scaled_endpoint = pygame.transform.scale(endpoint_image, (CELL_SIZE, CELL_SIZE))
    screen.blit(scaled_endpoint, (x * CELL_SIZE, y * CELL_SIZE))


def draw_special_point(x, y, image):
    if x is not None and y is not None:
        scaled_image = pygame.transform.scale(image, (CELL_SIZE // 2, CELL_SIZE // 2))
        offset_x = (CELL_SIZE - CELL_SIZE // 2) // 2
        offset_y = (CELL_SIZE - CELL_SIZE // 2) // 2
        screen.blit(scaled_image, (x * CELL_SIZE + offset_x, y * CELL_SIZE + offset_y))


def classify_token(token):
    if token in ["UP", "DOWN", "LEFT", "RIGHT"]:
        return "DIRECTION"
    return "UNKNOWN"


def tokenize_arrow_key(key):
    key_mapping = {
        pygame.K_UP: "UP",
        pygame.K_DOWN: "DOWN",
        pygame.K_LEFT: "LEFT",
        pygame.K_RIGHT: "RIGHT"
    }
    return key_mapping.get(key, None)

def parse_arrow_key_input(token):
    if classify_token(token) == "DIRECTION":
        root = Node("Command")
        move_node = Node("Move", parent=root)
        Node(f"Direction: {token}", parent=move_node)
        return root
    else:
        raise ValueError("Invalid token")

def update_animations():
    global animations
    animations = {
        'S': [get_sprite(0, i) for i in range(6)],
        'N': [get_sprite(1, i) for i in range(6)],
        'E': [get_sprite(2, i) for i in range(6)],
        'W': [get_sprite(3, i) for i in range(6)],
        'idle': get_sprite(4, 0)
    }


def parse_to_ir(command):
    ir_list = []
    tokens = list(command.upper())

    root = Node("Command")

    i = 0
    while i < len(tokens):
        move = tokens[i]
        if move in DIRECTIONS:
            move_node = Node("Move", parent=root)
            Node(f"Direction: {move}", parent=move_node)

            steps = 1
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                steps = int(tokens[i + 1])
                Node(f"Steps: {steps}", parent=move_node)
                i += 1

            ir_list.append(IRInstruction("MOVE", move, steps))
        else:
            print(f"Invalid move: {move}")
            return None
        i += 1

    print_parse_tree(root)

    return ir_list


def execute_ir(ir_list, player_x, player_y, maze):
    for instruction in ir_list:
        if instruction.command == "MOVE":
            direction = instruction.direction
            steps = instruction.steps
            dx, dy = DIRECTIONS[direction]

            for _ in range(steps):
                new_x, new_y = player_x + dx, player_y + dy

                if 0 <= new_x < len(maze[0]) and 0 <= new_y < len(maze) and not maze[player_y][player_x][CARDINAL_DIRECTIONS[direction]]:
                    player_x, player_y = new_x, new_y
                else:
                    print("Wall encountered!")
                    break

    return player_x, player_y

def toggle_visibility(x, y, visible):
    color = WHITE if visible else BLACK
    pygame.draw.rect(screen, color, (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

def print_parse_tree(node, level=0):
    indent = " " * (level * 4)
    print(f"{indent}{node.name}")
    for child in node.children:
        print_parse_tree(child, level + 1)

def play_sounds_from_queue():
    if not pygame.mixer.get_busy() and sound_queue:
        next_sound = sound_queue.popleft()
        next_sound.play()

def check_direction(player_x, player_y, direction, maze):
    global hint1
    if hint1 <= 0:
        print("out of clues")
        return
    hint1 -= 1
    dx, dy = DIRECTIONS[direction]
    cardinal = CARDINAL_DIRECTIONS[direction]
    new_x, new_y = player_x + dx, player_y + dy

    if not (0 <= new_x < len(maze[0]) and 0 <= new_y < len(maze)):
        sound_queue.append(wall_sound)
    elif maze[player_y][player_x][cardinal]:
        sound_queue.append(wall_sound)
    else:
        sound_queue.append(path_sound)


def process_input_with_animation(player_x, player_y, command, maze):
    global green_x, green_y, red_x, red_y, hint1, hint2
    try:
        ir_list = parse_to_ir(command)
        if not ir_list:
            print("No valid commands found in input.")
            return player_x, player_y, False

        print("Generated IR:", ir_list)

        for instruction in ir_list:
            if instruction.command == "MOVE":
                direction = instruction.direction
                steps = instruction.steps
                dx, dy = DIRECTIONS[direction]

                for _ in range(steps):
                    new_x, new_y = player_x + dx, player_y + dy

                    if 0 <= new_x < len(maze[0]) and 0 <= new_y < len(maze) and not maze[player_y][player_x][CARDINAL_DIRECTIONS[direction]]:
                        steps_animation = len(animations[CARDINAL_DIRECTIONS[direction]])
                        step_dx = dx * (CELL_SIZE / steps_animation)
                        step_dy = dy * (CELL_SIZE / steps_animation)

                        current_x, current_y = player_x * CELL_SIZE, player_y * CELL_SIZE
                        for frame in animations[CARDINAL_DIRECTIONS[direction]]:
                            current_x += step_dx
                            current_y += step_dy
                            toggle_visibility(player_x, player_y, visible=False)
                            draw_player(current_x / CELL_SIZE, current_y / CELL_SIZE, frame)
                            pygame.display.flip()
                            time.sleep(0.1)

                        player_x, player_y = new_x, new_y
                        toggle_visibility(player_x, player_y, visible=True)

                        if (player_x, player_y) == (green_x, green_y):
                            hint1 += 1
                            green_x, green_y = None, None
                            print("You collected the green circle! Hint1 increased.")

                        if (player_x, player_y) == (red_x, red_y):
                            hint2 += 1
                            red_x, red_y = None, None
                            print("You collected the red circle! Hint2 increased.")

                        if (player_x, player_y) == (end_x, end_y):
                            return player_x, player_y, True

                    else:
                        print("Wall encountered!")
                        break

        draw_player(player_x, player_y, animations['idle'])
        pygame.display.flip()

        success = (player_x, player_y) == (end_x, end_y)
        return player_x, player_y, success
    except Exception as e:
        print(f"Error processing input: {e}")
        return player_x, player_y, False

def main():
    global level, x, hint1, hint2, walls_visible, CELL_SIZE, attempts, animations, green_x, green_y, red_x, red_y, end_x, end_y

    level = 1
    x = 0

    maze = generate_maze(ROWS + x, COLS + x)
    CELL_SIZE = calculate_cell_size(ROWS + x, COLS + x)

    # Generate animation frames
    animations = {
        'S': [get_sprite(0, i) for i in range(6)],
        'N': [get_sprite(1, i) for i in range(6)],
        'E': [get_sprite(2, i) for i in range(6)],
        'W': [get_sprite(3, i) for i in range(6)],
        'idle': get_sprite(4, 0)
    }
    end_x, end_y = random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)

    red_x, red_y = (random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)) if random.randint(1,3) == 1 else (None, None)
    green_x, green_y = (random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)) if random.randint(1,5) == 1 else (None, None)

    start_x, start_y = random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)
    while (start_x == end_x and start_y == end_y) or (start_x == green_x and start_y == green_y) or (
            start_x == red_x and start_y == red_y):
        start_x, start_y = random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)

    player_x, player_y = start_x, start_y
    clock = pygame.time.Clock()
    input_box = pygame.Rect(50, BASE_HEIGHT + 20, BASE_WIDTH - 200, 40)
    submit_button = pygame.Rect(BASE_WIDTH - 145, BASE_HEIGHT + 20, 100, 40)
    reveal_button = pygame.Rect(BASE_WIDTH - 145, BASE_HEIGHT + 70, 100, 40)

    text = ""
    running = True

    start_time = time.time()
    reveal_time = None

    while running:
        play_sounds_from_queue()
        if level > 15:
            print("Game finished")
            running = False
            break

        screen.fill(BLACK)

        if reveal_time:
            if time.time() - reveal_time >= 3:
                walls_visible = False
                reveal_time = None
        elif time.time() - start_time >= 5:
            walls_visible = False

        draw_maze(maze, walls_visible)
        draw_endpoint(end_x, end_y)
        draw_player(player_x, player_y, animations['idle'])

        if red_x is not None:
            draw_special_point(red_x, red_y, reveal_image)

        if green_x is not None:
            draw_special_point(green_x, green_y, check_image)

        hint1_text = font.render(f"Arrow Hints Left: {hint1}", True, WHITE)
        hint2_text = font.render(f"Reveal Hints Left: {hint2}", True, WHITE)
        level_text = font.render(f"Level: {level}", True, WHITE)
        attempts_text = font.render(f"Attempts Left: {attempts}", True, WHITE)

        screen.blit(hint1_text, (50, BASE_HEIGHT + 75))
        screen.blit(hint2_text, (50, BASE_HEIGHT + 110))
        screen.blit(level_text, (50, BASE_HEIGHT + 140))
        screen.blit(attempts_text, (50, BASE_HEIGHT + 175))

        pygame.draw.rect(screen, WHITE, input_box, 2)
        text_surface = font.render(text, True, WHITE)
        screen.blit(text_surface, (input_box.x + 5, input_box.y + 5))

        pygame.draw.rect(screen, WHITE, submit_button)
        pygame.draw.rect(screen, WHITE, reveal_button)
        attempts_text = font.render(f"Attempts Left: {attempts}", True, WHITE)

        screen.blit(font.render("Submit", True, BLACK), (BASE_WIDTH - 140, BASE_HEIGHT + 25))
        screen.blit(font.render("Reveal", True, BLACK), (BASE_WIDTH - 140, BASE_HEIGHT + 75))
        screen.blit(attempts_text, (BASE_WIDTH - 220, BASE_HEIGHT + 130))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if walls_visible:
                        print("You cannot move while walls are visible!")
                        continue
                    attempts -= 1
                    if attempts <= 0:
                        print("Failure! No attempts left.")
                        running = False
                        break

                    new_x, new_y, success = process_input_with_animation(player_x, player_y, text, maze)
                    if (new_x, new_y) != (player_x, player_y):
                        player_x, player_y = new_x, new_y
                    text = ""

                    if event.key == pygame.K_UP:
                        draw_player(player_x, player_y, animations['N'][0])
                        pygame.display.flip()
                    elif event.key == pygame.K_DOWN:
                        draw_player(player_x, player_y, animations['S'][0])
                        pygame.display.flip()
                    elif event.key == pygame.K_LEFT:
                        draw_player(player_x, player_y, animations['W'][0])
                        pygame.display.flip()
                    elif event.key == pygame.K_RIGHT:
                        draw_player(player_x, player_y, animations['E'][0])
                        pygame.display.flip()

                    if (player_x, player_y) == (green_x, green_y):
                        hint1 += 1
                        green_x, green_y = None, None
                        print("You collected the green circle! Hint1 increased.")

                    if (player_x, player_y) == (red_x, red_y):
                        hint2 += 1
                        red_x, red_y = None, None
                        print("You collected the red circle! Hint2 increased.")

                    if (player_x, player_y) == (end_x, end_y):
                        print("End achieved!")

                        level += 1
                        x = min(level - 1, 5)
                        attempts = min(4 + level, 10)

                        screen.fill(BLACK)
                        pygame.display.flip()

                        maze = generate_maze(ROWS + x, COLS + x)
                        CELL_SIZE = calculate_cell_size(ROWS + x, COLS + x)

                        update_animations()
                        start_x, start_y = random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)
                        player_x, player_y = start_x, start_y
                        end_x, end_y = random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)

                        red_x, red_y = (
                            random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)) if random.randint(1,3) == 1 else (None, None)
                        green_x, green_y = (
                            random.randint(0, COLS + x - 1), random.randint(0, ROWS + x - 1)) if random.randint(1,5) == 1 else (None, None)

                        walls_visible = True
                        draw_maze(maze, walls_visible)
                        draw_endpoint(end_x, end_y)
                        if red_x is not None:
                            draw_special_point(red_x, red_y, reveal_image)

                        if green_x is not None:
                            draw_special_point(green_x, green_y, check_image)
                        draw_player(player_x, player_y, animations['idle'])
                        pygame.display.flip()

                        pygame.time.delay(5000)

                        walls_visible = False
                        start_time = time.time()



                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    text += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN:
                if submit_button.collidepoint(event.pos):
                    if walls_visible:
                        print("You cannot move while walls are visible!")
                        continue
                    attempts -= 1
                    if attempts <= 0:
                        print("Failure! No attempts left.")
                        running = False
                        break

                    player_x, player_y, success = process_input_with_animation(player_x, player_y, text, maze)
                    text = ""

                if reveal_button.collidepoint(event.pos) and hint2 > 0:
                    walls_visible = True
                    hint2 -= 1
                    draw_maze(maze, walls_visible)
                    pygame.display.flip()
                    reveal_time = pygame.time.delay(3000)

            if event.type == pygame.KEYDOWN:
                if hint1 > 0:
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                        token = tokenize_arrow_key(event.key)
                        if token:
                            try:

                                parse_tree = parse_arrow_key_input(token)
                                print_parse_tree(parse_tree)

                                direction_map = {"UP": "W", "DOWN": "S", "LEFT": "A", "RIGHT": "D"}
                                mapped_direction = direction_map.get(token)

                                if mapped_direction:
                                    check_direction(player_x, player_y, mapped_direction,maze)


                                    animation_map = {"UP": "idle_up", "DOWN": "idle_down", "LEFT": "idle_left",
                                                     "RIGHT": "idle_right"}
                                    animations['idle'] = animations.get(animation_map[token], animations['idle'])
                                    draw_player(player_x, player_y, animations['idle'])
                                    pygame.display.flip()
                                else:
                                    print(f"Invalid direction token: {token}")
                            except ValueError as e:
                                print(f"Error: {e}")
                    else:
                        print(" ")
                    draw_player(player_x, player_y, animations['idle'])
                    pygame.display.flip()
                else:
                    print("Out of hints!")

        hint1_text = font.render(f"Arrow Hints Left: {hint1}", True, WHITE)
        hint2_text = font.render(f"Reveal Hints Left: {hint2}", True, WHITE)
        screen.blit(hint1_text, (50, BASE_HEIGHT + 75))
        screen.blit(hint2_text, (50, BASE_HEIGHT + 110))
        pygame.display.flip()

        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
