import pygame
from pygame.locals import *
import numpy as np
import os
import random
import time
from collections import deque
import asyncio

##### Initializing the Pygame Libraries #####
pygame.init()
pygame.font.init()
pygame.mixer.init()

##### CONSTANTS #####
WINDOWSIZE = WIDTH, HEIGHT = 750, 750
if WIDTH != HEIGHT:
    min_size = min(WIDTH, HEIGHT)
    WIDTH = min_size
    HEIGHT = min_size
GRID_SIZE = 50
CHARACTER_WIDTH, CHARACTER_HEIGHT = GRID_SIZE, GRID_SIZE
# CHARACTERS
CHARACTER_IMAGE = pygame.image.load(os.path.join('Assets', 'character.png'))
CHARACTER = pygame.transform.scale(CHARACTER_IMAGE, (CHARACTER_WIDTH, CHARACTER_HEIGHT))
SHADOW_IMAGE = pygame.image.load(os.path.join('Assets', 'shadow.png'))
SHADOW = pygame.transform.scale(SHADOW_IMAGE, (CHARACTER_WIDTH, CHARACTER_HEIGHT))
SHADOW_DELAY_INIT = 1.5
SHADOW_DELAY_INIT = max(0.5, min(3, SHADOW_DELAY_INIT))
SHADOW_DELAY = SHADOW_DELAY_INIT # Delay in seconds
# COLORS (RGB)
WHITE = (255, 255, 255)
BROWN = (128, 0, 0)
BLACK = (0, 0, 0)
GRAY = (142, 143, 133)
RED = (255, 0, 0)
# FONT
GAME_OVER_FONT = pygame.font.SysFont('times new roman', 96)
FONT = pygame.font.SysFont('times new roman', 48)
# FPS
FPS = 60
##### WINDOW #####
window = pygame.display.set_mode((WINDOWSIZE))
WINDOW_TITLE = "Shadow Paradox"
pygame.display.set_caption(WINDOW_TITLE)
pygame.display.set_icon(SHADOW_IMAGE)

class MazeManager:
    def __init__(self, width, height):
        self.width = width // GRID_SIZE
        self.section_height = height // GRID_SIZE
        self.current_section = 0
        self.maze_sections = {}
        self.lowest_section = 0
        self.highest_section = 1
        self.vertical_paths = set()
        self.path_memory = {}
        self.minimum_paths = 3  # Ensure at least 3 paths between sections
        self.generate_initial_sections()
    
    def get_neighbors(self, x, y, grid):
        """Get valid neighboring cells for maze generation"""
        directions = [(0, 2), (2, 0), (0, -2), (-2, 0)]
        neighbors = []
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if (0 < new_x < len(grid[0]) - 1 and 
                0 < new_y < len(grid) - 1 and 
                grid[new_y][new_x] == 1):
                neighbors.append((new_x, new_y, dx, dy))
        random.shuffle(neighbors)
        return neighbors
    
    def carve_path(self, grid, start_x, start_y, entry_points=None, exit_points=None):
        """Generate maze paths using modified DFS with guaranteed connectivity"""
        stack = [(start_x, start_y)]
        grid[start_y][start_x] = 0
        
        # Ensure entry points are open
        if entry_points:
            for x in entry_points:
                grid[0][x] = 0
                grid[1][x] = 0
        
        # Ensure exit points are open
        if exit_points:
            for x in exit_points:
                grid[-1][x] = 0
                grid[-2][x] = 0
        
        while stack:
            current = stack[-1]
            neighbors = self.get_neighbors(current[0], current[1], grid)
            
            if not neighbors:
                stack.pop()
                continue
            
            next_x, next_y, dx, dy = neighbors[0]
            # Carve passage
            grid[current[1] + dy//2][current[0] + dx//2] = 0
            grid[next_y][next_x] = 0
            stack.append((next_x, next_y))
        
        return grid

    def ensure_vertical_connectivity(self, grid, section_number):
        """Ensure vertical connectivity between sections with multiple guaranteed paths"""
        if section_number in self.path_memory:
            entry_points = self.path_memory[section_number]['entries']
        else:
            # Generate more entry points for better connectivity
            entry_points = set(random.sample(range(1, self.width-1, 2), 
                                          random.randint(self.minimum_paths, min(5, self.width // 2))))
        
        # Generate more exit points for better connectivity
        exit_points = set(random.sample(range(1, self.width-1, 2), 
                                      random.randint(self.minimum_paths, min(5, self.width // 2))))
        
        # Ensure at least one exit point is near each entry point for better vertical progression
        for entry in entry_points:
            nearby_range = range(max(1, entry - 2), min(self.width - 1, entry + 3), 2)
            if not any(x in exit_points for x in nearby_range):
                potential_exit = random.choice(list(nearby_range))
                exit_points.add(potential_exit)
        
        # Store exit points as entry points for next section
        self.path_memory[section_number + 1] = {'entries': exit_points}
        
        # Create wider passages
        for x in entry_points:
            grid[0][x] = 0
            grid[1][x] = 0
            if x > 1:  # Add side passages
                grid[1][x-1] = 0
            if x < len(grid[0])-2:
                grid[1][x+1] = 0
        
        for x in exit_points:
            grid[-1][x] = 0
            grid[-2][x] = 0
            if x > 1:  # Add side passages
                grid[-2][x-1] = 0
            if x < len(grid[0])-2:
                grid[-2][x+1] = 0
        
        return grid, entry_points, exit_points

    def generate_maze_section(self, section_number):
        """Generate a new maze section with guaranteed paths"""
        grid = np.ones((self.section_height, self.width), dtype=int)
        
        # Get or generate entry/exit points
        grid, entry_points, exit_points = self.ensure_vertical_connectivity(grid, section_number)
        
        # Generate the maze paths starting from multiple points
        for start_x in entry_points:
            grid = self.carve_path(grid, start_x, 1, entry_points, exit_points)
        
        # Additional path generation from exit points upward
        for end_x in exit_points:
            grid = self.carve_path(grid, end_x, self.section_height - 2, entry_points, exit_points)
        
        # Ensure all points are connected
        self.connect_all_points(grid, entry_points, exit_points)
        
        # Add some random extra passages for variety
        self.add_extra_passages(grid)
        
        return grid
    
    def connect_all_points(self, grid, entry_points, exit_points):
        """Ensure all entry and exit points are connected to the maze"""
        def find_nearest_path(x, y, grid):
            visited = set()
            queue = deque([(x, y, [])])
            
            while queue:
                curr_x, curr_y, path = queue.popleft()
                if grid[curr_y][curr_x] == 0:
                    return path
                
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    next_x, next_y = curr_x + dx, curr_y + dy
                    if (0 < next_x < len(grid[0]) - 1 and 
                        0 < next_y < len(grid) - 1 and 
                        (next_x, next_y) not in visited):
                        visited.add((next_x, next_y))
                        new_path = path + [(next_x, next_y)]
                        queue.append((next_x, next_y, new_path))
            return []
        
        # Connect entry points
        for x in entry_points:
            if grid[1][x] == 1:  # If not already connected
                path = find_nearest_path(x, 1, grid)
                for px, py in path:
                    grid[py][px] = 0
        
        # Connect exit points
        for x in exit_points:
            if grid[-2][x] == 1:  # If not already connected
                path = find_nearest_path(x, len(grid)-2, grid)
                for px, py in path:
                    grid[py][px] = 0

    def generate_initial_sections(self):
        """Generate initial maze sections"""
        self.maze_sections[0] = self.generate_maze_section(0)
        self.maze_sections[1] = self.generate_maze_section(1)
    
    def get_current_grid_position(self, pixel_y):
        """Convert pixel Y position to grid coordinates and section number"""
        section = pixel_y // (self.section_height * GRID_SIZE)
        return section
    
    def ensure_section_exists(self, section):
        """Ensure that the required maze section exists and manage section cleanup"""
        # Generate new sections above as needed
        while section >= self.highest_section:
            self.highest_section += 1
            self.maze_sections[self.highest_section] = self.generate_maze_section(self.highest_section)
        
        # Generate new sections below if needed
        while section < self.lowest_section:
            self.lowest_section -= 1
            self.maze_sections[self.lowest_section] = self.generate_maze_section(self.lowest_section)
        
        # Cleanup old sections
        sections_to_remove = []
        for old_section in self.maze_sections:
            if old_section < section - 2 or old_section > section + 2:
                sections_to_remove.append(old_section)
        
        for old_section in sections_to_remove:
            del self.maze_sections[old_section]
            if old_section == self.lowest_section:
                self.lowest_section = min(self.maze_sections.keys())
            if old_section == self.highest_section:
                self.highest_section = max(self.maze_sections.keys())
    
    def get_cell(self, pixel_x, pixel_y):
        """Get the value of a cell at the given pixel coordinates"""
        grid_x = pixel_x // GRID_SIZE
        grid_y = pixel_y // GRID_SIZE
        section = self.get_current_grid_position(pixel_y)
        local_y = grid_y % self.section_height
        
        self.ensure_section_exists(section)
        
        if section in self.maze_sections and 0 <= grid_x < self.width:
            try:
                return self.maze_sections[section][local_y][grid_x]
            except IndexError:
                return 1
        return 1
    
    def add_extra_passages(self, grid):
        """Add some random extra passages to prevent dead ends"""
        for _ in range(self.width // 2):
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.section_height - 2)
            if grid[y][x] == 1:
                # Check if adding a passage here would connect two existing paths
                neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
                path_count = sum(1 for nx, ny in neighbors if 0 <= nx < self.width and 
                               0 <= ny < self.section_height and grid[ny][nx] == 0)
                if path_count >= 2:
                    grid[y][x] = 0
        
        return grid

def show_game_over_screen(window, score, shadow_delay): # returns whether player wants to restart
    """Display the Game Over screen with the final score and shadow delay."""
    window.fill(BLACK)
    
    # Render "Game Over" text
    game_over_text = GAME_OVER_FONT.render("GAME OVER", True, RED)
    text_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 3))
    window.blit(game_over_text, text_rect)
    
    # Render Score
    score_text = FONT.render(f"Score: {score}", True, WHITE)
    score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    window.blit(score_text, score_rect)
    
    # Render Shadow Delay
    delay_text = FONT.render(f"Shadow Delay: {shadow_delay:.2f}s", True, WHITE)
    delay_rect = delay_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    window.blit(delay_text, delay_rect)
    
    # Update the display
    pygame.display.flip()
    
    # Wait for player to quit
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                return True

async def main():
    clock = pygame.time.Clock()
    run = True

    # Initialize player position
    player_x, player_y = GRID_SIZE * 1, HEIGHT - CHARACTER_HEIGHT - GRID_SIZE
    player_speed = GRID_SIZE
    shadow_x, shadow_y = GRID_SIZE * 1, HEIGHT - CHARACTER_HEIGHT - GRID_SIZE
    shadow_speed = GRID_SIZE
    moved = False
    
    # Movement history system
    movement_history = deque()
    last_move_time = time.time()

    # Initialize maze manager
    maze_manager = MazeManager(WIDTH, HEIGHT)

    # Camera position
    camera_x, camera_y = 0, 0

    while run:
        clock.tick(FPS)
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    print("error: Pause menu to be added.")
                    #TODO

                new_x, new_y = player_x, player_y
                
                if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_j):
                    new_x -= player_speed
                if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_l):
                    new_x += player_speed
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_i):
                    new_y -= player_speed
                if event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_k):
                    new_y += player_speed
                
                # Check if the new position is valid
                if maze_manager.get_cell(new_x, new_y) != 1:
                    if not moved:
                        moved = True
                    # Record the movement
                    if moved:
                        movement_history.append({
                            'position': (new_x, new_y),
                            'time': current_time
                        })
                        player_x, player_y = new_x, new_y

        # Update shadow position based on movement history
        while movement_history and current_time - movement_history[0]['time'] >= SHADOW_DELAY:
            shadow_move = movement_history.popleft()
            shadow_x, shadow_y = shadow_move['position']

        # Update camera position to follow player smoothly
        target_camera_y = player_y - HEIGHT // 2
        camera_y += (target_camera_y - camera_y) * 0.1

        # Draw background
        window.fill(GRAY)

        # Calculate visible range
        visible_sections = set([
            maze_manager.get_current_grid_position(player_y - HEIGHT),
            maze_manager.get_current_grid_position(player_y),
            maze_manager.get_current_grid_position(player_y + HEIGHT)
        ])

        # Draw visible maze sections
        for section in visible_sections:
            maze_manager.ensure_section_exists(section)
            base_y = section * maze_manager.section_height * GRID_SIZE
            
            for y in range(maze_manager.section_height):
                for x in range(maze_manager.width):
                    absolute_y = base_y + y * GRID_SIZE
                    cell = maze_manager.get_cell(x * GRID_SIZE, absolute_y)
                    
                    screen_x = x * GRID_SIZE
                    screen_y = absolute_y - int(camera_y)
                    
                    if -GRID_SIZE <= screen_y <= HEIGHT:
                        if cell == 1:  # Wall
                            pygame.draw.rect(window, BROWN, (screen_x, screen_y, GRID_SIZE, GRID_SIZE))
                        else:  # Path
                            pygame.draw.rect(window, GRAY, (screen_x, screen_y, GRID_SIZE, GRID_SIZE))
                        
                        # Grid lines
                        pygame.draw.rect(window, BLACK, (screen_x, screen_y, GRID_SIZE, GRID_SIZE), 1)

        # Draw shadow (only if movement history exists)
        if movement_history:
            window.blit(SHADOW, (shadow_x, shadow_y - camera_y))

        # Draw character
        window.blit(CHARACTER, (player_x, player_y - camera_y))

        # score (height reached)
        score = abs(player_y // GRID_SIZE - 13)
        if score > 0:
            pygame.display.set_caption(f"Score: {score}")
        else:
            pygame.display.set_caption(WINDOW_TITLE)

        # Calculate how many multiples of 20 the score has reached
        delay_reduction = (score // 20) * 0.05
        # New delay, ensuring it does not drop below 0
        SHADOW_DELAY = max(0.5, SHADOW_DELAY_INIT - delay_reduction)

        # Check for collision between shadow and player
        if shadow_x == player_x and shadow_y == player_y and moved:
            if show_game_over_screen(window, score, SHADOW_DELAY): # returns whether player wants to restart
                print("error: Restart functionality to be added.")
                #TODO: restart
                #waiting = False
                #break
            run = False  # End game after showing Game Over screen
            break

        pygame.display.flip()

    print(f"Final Score: {score}")
    print(f"Final Shadow Delay: {SHADOW_DELAY:.2f}")
    await asyncio.sleep(0)
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
