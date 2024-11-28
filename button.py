import pygame

class Button:
    def __init__(self, x_pos, y_pos, texture, scale_factor):
        # Rescale the image
        original_width, original_height = texture.get_width(), texture.get_height()
        self.texture = pygame.transform.scale(texture, (int(original_width * scale_factor), int(original_height * scale_factor)))
        
        # Set the button's position using its center
        self.area = self.texture.get_rect(center=(x_pos, y_pos))
        
        # Track the button's clicked state
        self.is_pressed = False

    def render(self, screen):
        action_triggered = False
        
        # Get the current position of the mouse
        mouse_pos = pygame.mouse.get_pos()

        # Check if the mouse is hovering over the button
        if self.area.collidepoint(mouse_pos):
            # Check for a mouse click (left button)
            if pygame.mouse.get_pressed()[0] == 1 and not self.is_pressed:
                self.is_pressed = True
                action_triggered = True

        # Reset the click state when the mouse button is released
        if pygame.mouse.get_pressed()[0] == 0:
            self.is_pressed = False

        # Draw the button image on the screen
        screen.blit(self.texture, self.area)

        return action_triggered
