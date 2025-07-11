import board
import digitalio
import busio
from PIL import Image, ImageDraw
import adafruit_ssd1306
import time
import random
import math

# --- OLED Display Configuration ---
# Assuming a 128x32 PiOLED. Adjust if your screen is 128x64.
# Check your PiOLED documentation for exact dimensions.
OLED_WIDTH = 128
OLED_HEIGHT = 32

# I2C setup for the OLED display
# On a Raspberry Pi, the default I2C pins are usually:
# SDA: GPIO 2 (physical pin 3)
# SCL: GPIO 3 (physical pin 5)
i2c = busio.I2C(board.SCL, board.SDA)
# Corrected typo: SSD1306_I2C instead of SSD1306_I21C
display = adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=0x3C)

# Clear the display initially
display.fill(0)
display.show()

# --- Boid Simulation Parameters ---
NUM_BIRDS = 30  # Number of birds in the flock
VISUAL_RANGE = 20  # How far a bird can "see" other birds
MIN_SEPARATION = 5 # Minimum distance to maintain from other birds

# Weights for flocking behaviors (adjust these to change flocking style)
COHESION_WEIGHT = 0.001
ALIGNMENT_WEIGHT = 0.05
SEPARATION_WEIGHT = 0.05
LEADER_FOLLOW_WEIGHT = 0.01 # How strongly non-leader birds follow the leader
RANDOM_JITTER_MAGNITUDE = 0.05 # Small random force applied to all birds for wandering

MAX_SPEED = 2.0
MIN_SPEED = 0.5

# --- Bird Class Definition ---
class Bird:
    def __init__(self, width, height):
        """
        Initializes a new bird with a random position and velocity.
        :param width: The width of the simulation area (OLED screen width).
        :param height: The height of the simulation area (OLED screen height).
        """
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, height)
        self.vx = random.uniform(-1, 1) * MAX_SPEED
        self.vy = random.uniform(-1, 1) * MAX_SPEED
        self.width = width
        self.height = height

    def _distance(self, other_bird):
        """Calculates the Euclidean distance to another bird."""
        return math.sqrt((self.x - other_bird.x)**2 + (self.y - other_bird.y)**2)

    def _get_neighbors(self, flock):
        """Returns a list of birds within the visual range."""
        neighbors = []
        for other_bird in flock:
            if other_bird is not self:
                dist = self._distance(other_bird)
                if dist < VISUAL_RANGE:
                    neighbors.append(other_bird)
        return neighbors

    def _rule_cohesion(self, neighbors):
        """
        Steers the bird towards the average position of local flockmates.
        """
        if not neighbors:
            return 0, 0

        center_x = sum(b.x for b in neighbors) / len(neighbors)
        center_y = sum(b.y for b in neighbors) / len(neighbors)

        return (center_x - self.x) * COHESION_WEIGHT, \
               (center_y - self.y) * COHESION_WEIGHT

    def _rule_alignment(self, neighbors):
        """
        Steers the bird towards the average heading (velocity) of local flockmates.
        """
        if not neighbors:
            return 0, 0

        avg_vx = sum(b.vx for b in neighbors) / len(neighbors)
        avg_vy = sum(b.vy for b in neighbors) / len(neighbors)

        return (avg_vx - self.vx) * ALIGNMENT_WEIGHT, \
               (avg_vy - self.vy) * ALIGNMENT_WEIGHT

    def _rule_separation(self, neighbors):
        """
        Avoids crowding local flockmates by steering away from them.
        """
        if not neighbors:
            return 0, 0

        steer_x, steer_y = 0, 0
        for other_bird in neighbors:
            dist = self._distance(other_bird)
            if dist < MIN_SEPARATION and dist > 0: # Avoid division by zero
                # Steer away, inversely proportional to distance
                steer_x += (self.x - other_bird.x) / dist
                steer_y += (self.y - other_bird.y) / dist

        return steer_x * SEPARATION_WEIGHT, steer_y * SEPARATION_WEIGHT

    def _rule_follow_leader(self, leader_bird):
        """
        Steers the bird towards the leader's position.
        """
        if leader_bird is None:
            return 0, 0

        return (leader_bird.x - self.x) * LEADER_FOLLOW_WEIGHT, \
               (leader_bird.y - self.y) * LEADER_FOLLOW_WEIGHT

    def update(self, flock, is_leader=False):
        """
        Updates the bird's position and velocity based on flocking rules and
        handles boundary collisions (bouncing off edges).
        :param flock: The list of all birds in the simulation.
        :param is_leader: True if this bird is the designated leader.
        """
        # Add random jitter for more organic movement to all birds
        self.vx += random.uniform(-RANDOM_JITTER_MAGNITUDE, RANDOM_JITTER_MAGNITUDE)
        self.vy += random.uniform(-RANDOM_JITTER_MAGNITUDE, RANDOM_JITTER_MAGNITUDE)

        if not is_leader:
            neighbors = self._get_neighbors(flock)
            leader_bird = flock[0] # Assuming flock[0] is always the leader

            # Calculate steering forces from each rule
            coh_vx, coh_vy = self._rule_cohesion(neighbors)
            ali_vx, ali_vy = self._rule_alignment(neighbors)
            sep_vx, sep_vy = self._rule_separation(neighbors)
            follow_vx, follow_vy = self._rule_follow_leader(leader_bird)

            # Apply forces to velocity
            self.vx += coh_vx + ali_vx + sep_vx + follow_vx
            self.vy += coh_vy + ali_vy + sep_vy + follow_vy
        else:
            # Leader's movement is primarily random and then boundary-checked
            # No flocking rules for the leader itself
            pass

        # Limit speed
        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > MAX_SPEED:
            self.vx = (self.vx / speed) * MAX_SPEED
            self.vy = (self.vy / speed) * MAX_SPEED
        elif speed < MIN_SPEED:
            # Prevent birds from stopping completely. If speed is zero, give it a random impulse.
            if speed > 0:
                self.vx = (self.vx / speed) * MIN_SPEED
                self.vy = (self.vy / speed) * MIN_SPEED
            else:
                self.vx = random.uniform(-1, 1) * MIN_SPEED
                self.vy = random.uniform(-1, 1) * MIN_SPEED


        # Update position
        self.x += self.vx
        self.y += self.vy

        # --- Boundary Bounce Logic ---
        # If a bird hits the horizontal boundary, reverse its horizontal velocity
        # and clamp its position to the edge. Add a small push to prevent sticking.
        if self.x < 0:
            self.x = 0
            self.vx *= -1
            self.vx += 0.1 # Small positive push away from the wall
        elif self.x >= self.width: # Use >= width as pixels are 0 to width-1
            self.x = self.width - 1 # Clamp to the last valid pixel
            self.vx *= -1
            self.vx -= 0.1 # Small negative push away from the wall

        # If a bird hits the vertical boundary, reverse its vertical velocity
        # and clamp its position to the edge. Add a small push to prevent sticking.
        if self.y < 0:
            self.y = 0
            self.vy *= -1
            self.vy += 0.1 # Small positive push away from the wall
        elif self.y >= self.height: # Use >= height as pixels are 0 to height-1
            self.y = self.height - 1 # Clamp to the last valid pixel
            self.vy *= -1
            self.vy -= 0.1 # Small negative push away from the wall

# --- Main Simulation Loop ---
def run_simulation():
    """
    Initializes birds and runs the main simulation loop, updating and
    drawing birds on the OLED display.
    """
    flock = [Bird(OLED_WIDTH, OLED_HEIGHT) for _ in range(NUM_BIRDS)]

    print("Starting bird flocking simulation...")
    print("Press Ctrl+C to exit.")

    try:
        while True:
            # Create a blank image for the display
            image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
            draw = ImageDraw.Draw(image)

            # Update and draw each bird
            for i, bird in enumerate(flock):
                # Pass is_leader=True for the first bird (index 0)
                bird.update(flock, is_leader=(i == 0))
                # Draw the bird as a single white pixel
                # Ensure coordinates are integers and within bounds
                draw.point((int(bird.x), int(bird.y)), fill=255)

            # Display the image on the OLED
            display.image(image)
            display.show()

            # Small delay to control simulation speed
            time.sleep(0.05) # Adjust this value to make the simulation faster/slower

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    finally:
        # Clear the display before exiting
        display.fill(0)
        display.show()

if __name__ == "__main__":
    run_simulation()
