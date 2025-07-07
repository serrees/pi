import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import time
import random

# --- Configuration ---
# OLED dimensions (Adafruit PiOLED is typically 128x32)
OLED_WIDTH = 128
OLED_HEIGHT = 32

# I2C address for the SSD1306 display (default is 0x3C)
I2C_ADDRESS = 0x3C

# Number of fireflies to simulate
NUM_FIREFLIES = 15

# Firefly properties
FIREFLY_SIZE = 1  # Size of each firefly (dot)
MOVE_SPEED = 1    # Max pixels a firefly can move per update
BLINK_CHANCE = 0.05 # Probability (0.0 to 1.0) of a firefly blinking on in any given frame
BLINK_DURATION = 5 # Number of frames a firefly stays lit once it blinks on

# --- Initialize I2C and OLED Display ---
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    display = adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=I2C_ADDRESS)
    print("OLED display initialized successfully.")
except ValueError as e:
    print(f"Error initializing I2C or OLED display: {e}")
    print("Please ensure your PiOLED is correctly wired and I2C is enabled on your Raspberry Pi.")
    print("You might need to run 'sudo raspi-config' -> Interface Options -> I2C -> Yes.")
    exit()

# Clear the display
display.fill(0)
display.show()

# Create a blank image for drawing.
# Make sure to create an image with mode '1' for 1-bit color (black and white)
image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
draw = ImageDraw.Draw(image)

# --- Firefly Class/Structure ---
class Firefly:
    def __init__(self):
        self.x = random.randint(0, OLED_WIDTH - 1)
        self.y = random.randint(0, OLED_HEIGHT - 1)
        self.is_lit = False
        self.blink_timer = 0 # How many frames it will stay lit

    def update(self):
        # Random movement
        self.x += random.randint(-MOVE_SPEED, MOVE_SPEED)
        self.y += random.randint(-MOVE_SPEED, MOVE_SPEED)

        # Keep firefly within screen bounds
        self.x = max(0, min(self.x, OLED_WIDTH - 1))
        self.y = max(0, min(self.y, OLED_HEIGHT - 1))

        # Handle blinking
        if self.is_lit:
            self.blink_timer -= 1
            if self.blink_timer <= 0:
                self.is_lit = False
        else:
            if random.random() < BLINK_CHANCE:
                self.is_lit = True
                self.blink_timer = BLINK_DURATION

    def draw(self, drawer):
        if self.is_lit:
            # Draw a white pixel (or small rectangle for larger size)
            drawer.rectangle((self.x, self.y, self.x + FIREFLY_SIZE - 1, self.y + FIREFLY_SIZE - 1), outline=255, fill=255)

# --- Initialize Fireflies ---
fireflies = [Firefly() for _ in range(NUM_FIREFLIES)]

# --- Main Animation Loop ---
print("Starting firefly simulation. Press Ctrl+C to exit.")
try:
    while True:
        # Clear the drawing buffer
        draw.rectangle((0, 0, OLED_WIDTH, OLED_HEIGHT), outline=0, fill=0)

        # Update and draw each firefly
        for firefly in fireflies:
            firefly.update()
            firefly.draw(draw)

        # Display image on the OLED
        display.image(image)
        display.show()

        # Small delay to control animation speed
        time.sleep(0.05) # Adjust this value to make it faster or slower

except KeyboardInterrupt:
    print("\nExiting firefly simulation.")
    # Clear the display before exiting
    display.fill(0)
    display.show()
    print("Display cleared.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

