from itertools import cycle
import random
import sys
import pygame
import os
from pygame.locals import *

FPS = 30
SCREENWIDTH = 288
SCREENHEIGHT = 512
PIPEGAPSIZE = 100
BASEY = SCREENHEIGHT * 0.79

ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")

try:
    xrange
except NameError:
    xrange = range


class FlappyGame:
    def __init__(self):
        pygame.init()
        self.FPSCLOCK = pygame.time.Clock()
        self.SCREEN = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
        pygame.display.set_caption("Flappy Bird")

        self.IMAGES, self.SOUNDS, self.HITMASKS = self.load_assets()
        self.reset()

    def load_assets(self):
        IMAGES, SOUNDS, HITMASKS = {}, {}, {}

        PLAYERS_LIST = (
            (
                "assets/sprites/redbird-upflap.png",
                "assets/sprites/redbird-midflap.png",
                "assets/sprites/redbird-downflap.png",
            ),
            (
                "assets/sprites/bluebird-upflap.png",
                "assets/sprites/bluebird-midflap.png",
                "assets/sprites/bluebird-downflap.png",
            ),
            (
                "assets/sprites/yellowbird-upflap.png",
                "assets/sprites/yellowbird-midflap.png",
                "assets/sprites/yellowbird-downflap.png",
            ),
        )

        BACKGROUNDS_LIST = (
            "assets/sprites/background-day.png",
            "assets/sprites/background-night.png",
        )
        PIPES_LIST = ("assets/sprites/pipe-green.png", "assets/sprites/pipe-red.png")

        # numbers sprites for score display
        IMAGES["numbers"] = tuple(
            [
                pygame.image.load(
                    os.path.join(ASSETS_PATH, f"sprites/{i}.png")
                ).convert_alpha()
                for i in range(10)
            ]
        )

        IMAGES["gameover"] = pygame.image.load(
            os.path.join(ASSETS_PATH, "sprites/gameover.png")
        ).convert_alpha()
        IMAGES["message"] = pygame.image.load(
            os.path.join(ASSETS_PATH, "sprites/message.png")
        ).convert_alpha()
        IMAGES["base"] = pygame.image.load(
            os.path.join(ASSETS_PATH, "sprites/base.png")
        ).convert_alpha()

        if "win" in sys.platform:
            soundExt = ".wav"
        else:
            soundExt = ".ogg"

        SOUNDS["die"] = pygame.mixer.Sound(
            os.path.join(ASSETS_PATH, "audio/die" + soundExt)
        )
        SOUNDS["hit"] = pygame.mixer.Sound(
            os.path.join(ASSETS_PATH, "audio/hit" + soundExt)
        )
        SOUNDS["point"] = pygame.mixer.Sound(
            os.path.join(ASSETS_PATH, "audio/point" + soundExt)
        )
        SOUNDS["swoosh"] = pygame.mixer.Sound(
            os.path.join(ASSETS_PATH, "audio/swoosh" + soundExt)
        )
        SOUNDS["wing"] = pygame.mixer.Sound(
            os.path.join(ASSETS_PATH, "audio/wing" + soundExt)
        )

        randBg = random.randint(0, len(BACKGROUNDS_LIST) - 1)
        IMAGES["background"] = pygame.image.load(
            os.path.join(ASSETS_PATH, BACKGROUNDS_LIST[randBg][len("assets/") :])
        ).convert()

        randPlayer = random.randint(0, len(PLAYERS_LIST) - 1)
        IMAGES["player"] = tuple(
            [
                pygame.image.load(
                    os.path.join(ASSETS_PATH, p[len("assets/") :])
                ).convert_alpha()
                for p in PLAYERS_LIST[randPlayer]
            ]
        )

        pipeindex = random.randint(0, len(PIPES_LIST) - 1)
        IMAGES["pipe"] = (
            pygame.transform.flip(
                pygame.image.load(
                    os.path.join(ASSETS_PATH, PIPES_LIST[pipeindex][len("assets/") :])
                ).convert_alpha(),
                False,
                True,
            ),
            pygame.image.load(
                os.path.join(ASSETS_PATH, PIPES_LIST[pipeindex][len("assets/") :])
            ).convert_alpha(),
        )

        def getHitmask(image):
            mask = []
            for x in xrange(image.get_width()):
                mask.append([])
                for y in xrange(image.get_height()):
                    mask[x].append(bool(image.get_at((x, y))[3]))
            return mask

        HITMASKS["pipe"] = (
            getHitmask(IMAGES["pipe"][0]),
            getHitmask(IMAGES["pipe"][1]),
        )
        HITMASKS["player"] = (
            getHitmask(IMAGES["player"][0]),
            getHitmask(IMAGES["player"][1]),
            getHitmask(IMAGES["player"][2]),
        )

        return IMAGES, SOUNDS, HITMASKS

    def reset(self):
        self.score = 0
        self.playerIndex = 0
        self.loopIter = 0
        self.playerx = int(SCREENWIDTH * 0.2)
        self.playery = int((SCREENHEIGHT - self.IMAGES["player"][0].get_height()) / 2)
        self.basex = 0
        self.baseShift = (
            self.IMAGES["base"].get_width() - self.IMAGES["background"].get_width()
        )

        newPipe1 = self._getRandomPipe()
        newPipe2 = self._getRandomPipe()
        self.upperPipes = [
            {"x": SCREENWIDTH + 200, "y": newPipe1[0]["y"]},
            {"x": SCREENWIDTH + 200 + (SCREENWIDTH / 2), "y": newPipe2[0]["y"]},
        ]
        self.lowerPipes = [
            {"x": SCREENWIDTH + 200, "y": newPipe1[1]["y"]},
            {"x": SCREENWIDTH + 200 + (SCREENWIDTH / 2), "y": newPipe2[1]["y"]},
        ]

        self.pipeVelX = -4
        self.playerVelY = -9
        self.playerMaxVelY = 10
        self.playerMinVelY = -8
        self.playerAccY = 1
        self.playerFlapAcc = -9
        self.playerFlapped = False
        return self._get_state()

    def _get_state(self):
        """Gets the current state of the game for the AI."""
        pipe_ind = 0
        if (
            len(self.upperPipes) > 1
            and self.playerx
            > self.upperPipes[0]["x"] + self.IMAGES["pipe"][0].get_width()
        ):
            pipe_ind = 1

        state = {
            "player_y": self.playery,
            "player_vel": self.playerVelY,
            "next_pipe_dist_to_player": self.lowerPipes[pipe_ind]["x"] - self.playerx,
            "next_pipe_top_y": self.upperPipes[pipe_ind]["y"],
            "next_pipe_bottom_y": self.lowerPipes[pipe_ind]["y"],
        }
        return state

    def frame_step(self, action, draw=True):
        """
        action: 0 for do nothing, 1 for flap
        Returns: (state, reward, done)
        """

        pygame.event.pump()
        reward = 0.1  # Reward for surviving
        done = False

        if action == 1:
            if self.playery > -2 * self.IMAGES["player"][0].get_height():
                self.playerVelY = self.playerFlapAcc
                self.playerFlapped = True
                self.SOUNDS["wing"].play()

        # Check for score
        playerMidPos = self.playerx + self.IMAGES["player"][0].get_width() / 2
        for pipe in self.upperPipes:
            pipeMidPos = pipe["x"] + self.IMAGES["pipe"][0].get_width() / 2
            if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                self.score += 1
                reward = 1  # Reward for passing a pipe
                self.SOUNDS["point"].play()

        # Player's movement
        if self.playerVelY < self.playerMaxVelY and not self.playerFlapped:
            self.playerVelY += self.playerAccY
        if self.playerFlapped:
            self.playerFlapped = False
        playerHeight = self.IMAGES["player"][self.playerIndex].get_height()
        self.playery += min(self.playerVelY, BASEY - self.playery - playerHeight)

        # Move pipes to left
        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            uPipe["x"] += self.pipeVelX
            lPipe["x"] += self.pipeVelX

        # Add new pipe
        if 0 < self.upperPipes[0]["x"] < 5:
            newPipe = self._getRandomPipe()
            self.upperPipes.append(newPipe[0])
            self.lowerPipes.append(newPipe[1])

        # Remove old pipe
        if self.upperPipes[0]["x"] < -self.IMAGES["pipe"][0].get_width():
            self.upperPipes.pop(0)
            self.lowerPipes.pop(0)

        # Check for crash
        crashTest = self._checkCrash()
        if crashTest[0]:
            done = True
            self.SOUNDS["hit"].play()
            if not crashTest[1]:
                self.SOUNDS["die"].play()
            reward = -1  # Penalty for crashing
            # self.reset() # The game reset is now handled by the game loop

        # The drawing logic is now handled by the caller loop
        # to prevent screen flickering and allow for more complex drawing.
        # if draw:
        #     self._draw_game_state()
        #     pygame.display.update()
        #     self.FPSCLOCK.tick(FPS)

        return self._get_state(), reward, done

    def _getRandomPipe(self):
        gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
        gapY += int(BASEY * 0.2)
        pipeHeight = self.IMAGES["pipe"][0].get_height()
        pipeX = SCREENWIDTH + 10
        return [
            {"x": pipeX, "y": gapY - pipeHeight},
            {"x": pipeX, "y": gapY + PIPEGAPSIZE},
        ]

    def _showScore(self):
        scoreDigits = [int(x) for x in list(str(self.score))]
        totalWidth = 0
        for digit in scoreDigits:
            totalWidth += self.IMAGES["numbers"][digit].get_width()
        Xoffset = (SCREENWIDTH - totalWidth) / 2
        for digit in scoreDigits:
            self.SCREEN.blit(
                self.IMAGES["numbers"][digit], (Xoffset, SCREENHEIGHT * 0.1)
            )
            Xoffset += self.IMAGES["numbers"][digit].get_width()

    def _checkCrash(self):
        player = {"x": self.playerx, "y": self.playery, "index": self.playerIndex}
        player["w"] = self.IMAGES["player"][0].get_width()
        player["h"] = self.IMAGES["player"][0].get_height()

        if player["y"] + player["h"] >= BASEY - 1:
            return [True, True]
        else:
            playerRect = pygame.Rect(player["x"], player["y"], player["w"], player["h"])
            pipeW = self.IMAGES["pipe"][0].get_width()
            pipeH = self.IMAGES["pipe"][0].get_height()

            for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
                uPipeRect = pygame.Rect(uPipe["x"], uPipe["y"], pipeW, pipeH)
                lPipeRect = pygame.Rect(lPipe["x"], lPipe["y"], pipeW, pipeH)
                pHitMask = self.HITMASKS["player"][0]
                uHitmask = self.HITMASKS["pipe"][0]
                lHitmask = self.HITMASKS["pipe"][1]

                uCollide = self._pixelCollision(
                    playerRect, uPipeRect, pHitMask, uHitmask
                )
                lCollide = self._pixelCollision(
                    playerRect, lPipeRect, pHitMask, lHitmask
                )

                if uCollide or lCollide:
                    return [True, False]
        return [False, False]

    def _pixelCollision(self, rect1, rect2, hitmask1, hitmask2):
        rect = rect1.clip(rect2)
        if rect.width == 0 or rect.height == 0:
            return False
        x1, y1 = rect.x - rect1.x, rect.y - rect1.y
        x2, y2 = rect.x - rect2.x, rect.y - rect2.y
        for x in xrange(rect.width):
            for y in xrange(rect.height):
                if hitmask1[x1 + x][y1 + y] and hitmask2[x2 + x][y2 + y]:
                    return True
        return False

    def _draw_game_state(self):
        """Draws all the game elements to the screen."""
        # Draw background
        self.SCREEN.blit(self.IMAGES["background"], (0, 0))

        # Draw pipes
        for uPipe, lPipe in zip(self.upperPipes, self.lowerPipes):
            self.SCREEN.blit(self.IMAGES["pipe"][0], (uPipe["x"], uPipe["y"]))
            self.SCREEN.blit(self.IMAGES["pipe"][1], (lPipe["x"], lPipe["y"]))

        # Draw base
        self.basex = -((-self.basex + 100) % self.baseShift)
        self.SCREEN.blit(self.IMAGES["base"], (self.basex, BASEY))
        self._showScore()
        self.SCREEN.blit(self.IMAGES["player"][0], (self.playerx, self.playery))


def run_manual_play(game=None):
    """Function to run the game for a human player."""
    # This import is local to the function to avoid circular dependencies,
    # as main.py imports this function.
    from main import Button

    # --- Game and High Score Initialization ---
    game = FlappyGame()  # Create a new game instance for manual play

    # High score logic
    high_score = 0
    highscore_file = "highscore.txt"

    # Load high score
    try:
        if os.path.exists(highscore_file):
            with open(highscore_file, "r") as f:
                content = f.read()
                if content:
                    high_score = int(content)
    except (IOError, ValueError):
        print(f"Error reading {highscore_file}, starting high score at 0.")
        high_score = 0

    playerIndex = 0
    playerIndexGen = cycle([0, 1, 2, 1])
    loopIter = 0
    playerx = int(SCREENWIDTH * 0.2)
    playery = int((SCREENHEIGHT - game.IMAGES["player"][0].get_height()) / 2)
    messagex = int((SCREENWIDTH - game.IMAGES["message"].get_width()) / 2)
    messagey = int(SCREENHEIGHT * 0.12)
    basex = 0
    baseShift = game.IMAGES["base"].get_width() - game.IMAGES["background"].get_width()
    playerShmVals = {"val": 0, "dir": 1}

    # --- Welcome Screen Loop ---
    welcome = True
    while welcome:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and (event.key == K_SPACE or event.key == K_UP):
                welcome = False

        if (loopIter + 1) % 5 == 0:
            playerIndex = next(playerIndexGen)
        loopIter = (loopIter + 1) % 30
        basex = -((-basex + 4) % baseShift)

        # player shm
        if abs(playerShmVals["val"]) == 8:
            playerShmVals["dir"] *= -1
        if playerShmVals["dir"] == 1:
            playerShmVals["val"] += 1
        else:
            playerShmVals["val"] -= 1

        game.SCREEN.blit(game.IMAGES["background"], (0, 0))
        game.SCREEN.blit(
            game.IMAGES["player"][playerIndex],
            (playerx, playery + playerShmVals["val"]),
        )
        game.SCREEN.blit(game.IMAGES["message"], (messagex, messagey))
        game.SCREEN.blit(game.IMAGES["base"], (basex, BASEY))
        pygame.display.update()
        game.FPSCLOCK.tick(FPS)

    # --- Helper Functions for Drawing ---
    def show_game_over_screen(final_score, current_high_score):
        """Displays the game over screen with the final score."""
        font = pygame.font.SysFont("Arial", 24, bold=True)
        final_score_label = font.render(
            f"Your Score: {final_score}", 1, (255, 255, 255)
        )
        high_score_label = font.render(
            f"High Score: {current_high_score}", 1, (255, 255, 255)
        )
        game.SCREEN.blit(
            final_score_label,
            (SCREENWIDTH / 2 - final_score_label.get_width() / 2, 240),
        )
        game.SCREEN.blit(
            high_score_label, (SCREENWIDTH / 2 - high_score_label.get_width() / 2, 280)
        )

    def show_high_score(score):
        """Displays the high score."""
        font = pygame.font.SysFont("Arial", 24, bold=True)
        score_label = font.render(f"High Score: {score}", 1, (255, 255, 255))
        game.SCREEN.blit(score_label, (10, 10))

    # =================================
    # Outer loop to allow for restarting the game
    # =================================
    while True:  # This loop allows restarting the game
        game.reset()
        # Main game loop for a single playthrough
        while True:
            action = 0
            for event in pygame.event.get():
                if event.type == QUIT or (
                    event.type == KEYDOWN and event.key == K_ESCAPE
                ):
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN and (
                    event.key == K_SPACE or event.key == K_UP
                ):
                    action = 1

            state, reward, done = game.frame_step(action, draw=False)

            # --- Drawing ---
            game._draw_game_state()
            show_high_score(high_score)
            pygame.display.update()
            game.FPSCLOCK.tick(FPS)

            if done:
                # Update and save high score if necessary
                if game.score > high_score:
                    high_score = game.score
                    try:
                        with open(highscore_file, "w") as f:
                            f.write(str(high_score))
                    except IOError:
                        print(f"Error writing to {highscore_file}.")

                # --- Game Over Screen ---
                restart_button = Button(
                    SCREENWIDTH / 2 - 140,
                    320,
                    120,
                    50,
                    "Restart",
                    (253, 187, 46),
                    (255, 215, 0),
                )
                menu_button = Button(
                    SCREENWIDTH / 2 + 20,
                    320,
                    120,
                    50,
                    "Menu",
                    (200, 200, 200),
                    (230, 230, 230),
                )
                buttons = [restart_button, menu_button]

                game.SCREEN.blit(game.IMAGES["gameover"], (50, 180))
                show_game_over_screen(game.score, high_score)
                for button in buttons:
                    button.draw(game.SCREEN)
                pygame.display.update()

                waiting = True
                while waiting:
                    for event in pygame.event.get():
                        if event.type == QUIT or (
                            event.type == KEYDOWN and event.key == K_ESCAPE
                        ):
                            pygame.quit()
                            sys.exit()

                        # Handle button clicks
                        if restart_button.handle_event(event):
                            waiting = (
                                False  # Will break and restart the inner game loop
                            )
                        elif menu_button.handle_event(event):
                            return  # Exit run_manual_play to go back to the main menu

                    # Redraw buttons to show hover effect
                    for button in buttons:
                        button.draw(game.SCREEN)
                    pygame.display.update()
                    game.FPSCLOCK.tick(15)  # Lower tick rate for menu

                break  # Breaks from the inner game loop to restart


def run_q_learning():
    """
    This function runs the Q-Learning agent from flappy_rl.py
    against the shared FlappyGame environment.
    """
    print("--- Starting Q-Learning Mode ---")

    # This import is local to the function, so we need to import Button here
    # A better long-term solution would be to have a shared utility file.
    from main import Button

    try:
        # Assuming flappy_rl.py provides the Agent object
        from flappy_rl import Agent as QLearningAgent
    except ImportError:
        print("Error: Could not import Q-Learning Agent from flappy_rl.py.")
        print(
            "Please ensure flappy_rl.py and its dependencies (config.py, q_learning.py) are in the directory."
        )
        pygame.time.wait(3000)  # Wait 3 seconds before returning to menu
        return

    game = FlappyGame()
    max_episodes = 500  # You can adjust the number of training episodes

    back_button = Button(  # Small arrow-like button
        10,
        10,
        40,
        40,
        "<",
        (50, 50, 50, 180),  # Semi-transparent dark grey
        (100, 100, 100, 180),  # Lighter grey on hover
        text_color=(255, 255, 255),
        border_color=(30, 30, 30, 220),  # Darker border
    )

    while QLearningAgent.episode < max_episodes:
        game.reset()
        done = False
        while not done:
            # Allow quitting the game
            game.SCREEN.blit(game.IMAGES["background"], (0, 0))  # Redraw background
            for event in pygame.event.get():
                if event.type == QUIT or (
                    event.type == KEYDOWN and event.key == K_ESCAPE
                ):
                    QLearningAgent.save_qvalues()
                    QLearningAgent.save_training_states()
                    print("--- Q-Learning Training Interrupted. Progress Saved. ---")
                    return  # Return to main menu
                if back_button.handle_event(event):
                    QLearningAgent.save_qvalues()
                    QLearningAgent.save_training_states()
                    print("--- Q-Learning Training Interrupted. Progress Saved. ---")
                    return  # Return to main menu

            # Q-learning agent decides action based on state
            action = QLearningAgent.act(
                game.playerx, game.playery, game.playerVelY, game.lowerPipes
            )

            # Game takes a step
            _, _, done = game.frame_step(
                action, draw=False
            )  # Disable drawing in frame_step

            # Manually draw elements to include the back button
            game._draw_game_state()

            # Agent learns
            if done:
                QLearningAgent.update_qvalues(game.score)
                print(
                    f"Episode: {QLearningAgent.episode}, score: {game.score}, max_score: {QLearningAgent.max_score}"
                )

            back_button.draw(game.SCREEN)
            pygame.display.update()
            game.FPSCLOCK.tick(FPS)

    print("--- Q-Learning Training Finished ---")
    QLearningAgent.save_qvalues()
    QLearningAgent.save_training_states()
    # Wait for a key press before returning to the menu
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN):
                waiting = False
