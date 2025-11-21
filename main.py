from itertools import cycle
import random
import sys
from environment import FlappyGame, run_manual_play, run_q_learning
import pygame
import os
import neat
import visualize
import pickle

from pygame.locals import *

FPS = 30
SCREENWIDTH = 288
SCREENHEIGHT = 512
PIPEGAPSIZE = 100
BASEY = SCREENHEIGHT * 0.79

# Generation counter
GEN = 0


class BackToMenuException(Exception):
    """Custom exception to break out of the training loop."""

    pass


# Global game environment (initialized later)
game_env = None

# list of all possible players (tuple of 3 positions of flap)
PLAYERS_LIST = (
    # red bird
    (
        "assets/sprites/redbird-upflap.png",
        "assets/sprites/redbird-midflap.png",
        "assets/sprites/redbird-downflap.png",
    ),
    # blue bird
    (
        "assets/sprites/bluebird-upflap.png",
        "assets/sprites/bluebird-midflap.png",
        "assets/sprites/bluebird-downflap.png",
    ),
    # yellow bird
    (
        "assets/sprites/yellowbird-upflap.png",
        "assets/sprites/yellowbird-midflap.png",
        "assets/sprites/yellowbird-downflap.png",
    ),
)

# list of backgrounds
BACKGROUNDS_LIST = (
    "assets/sprites/background-day.png",
    "assets/sprites/background-night.png",
)

# list of pipes
PIPES_LIST = (
    "assets/sprites/pipe-green.png",
    "assets/sprites/pipe-red.png",
)

try:
    xrange
except NameError:
    xrange = range


class Button:
    """A clickable button class for the Pygame menu."""

    def __init__(
        self,
        x,
        y,
        width,
        height,
        text,
        color,
        hover_color,
        text_color=(0, 0, 0),
        border_color=(60, 60, 60),
    ):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.is_hovered = False

        # Automatically adjust font size to fit text inside the button
        font_size = 35
        self.font = pygame.font.SysFont("Arial", font_size, bold=True)
        while (
            self.font.size(text)[0] > width - 20
        ):  # Check if text is wider than button padding
            font_size -= 1
            self.font = pygame.font.SysFont("Arial", font_size, bold=True)

    def draw(self, win):
        """Draws the button on the screen."""
        current_color = self.hover_color if self.is_hovered else self.color

        # Draw border
        pygame.draw.rect(win, self.border_color, self.rect, border_radius=12)
        # Draw inner button
        inner_rect = self.rect.inflate(-8, -8)
        pygame.draw.rect(win, current_color, inner_rect, border_radius=8)

        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        win.blit(text_surf, text_rect)

    def handle_event(self, event):
        """Checks for hover and click events."""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                return True
        return False


def main_menu():
    """Shows the main menu and waits for a choice."""
    button_width = 260
    button_height = 60
    button_x = (SCREENWIDTH - button_width) / 2

    # Define button colors
    BIRD_YELLOW = (253, 187, 46)
    HOVER_YELLOW = (255, 215, 0)
    DISABLED_GRAY = (50, 50, 50)
    BROWN_BORDER = (139, 69, 19)

    neat_button = Button(
        button_x,
        180,
        button_width,
        button_height,
        "Watch NEAT Play",
        BIRD_YELLOW,
        HOVER_YELLOW,
        border_color=BROWN_BORDER,
    )
    manual_button = Button(
        button_x,
        260,
        button_width,
        button_height,
        "Play Manually",
        BIRD_YELLOW,
        HOVER_YELLOW,
        border_color=BROWN_BORDER,
    )
    q_learning_button = Button(
        button_x,
        340,
        button_width,
        button_height,
        "Watch Q-Learning",
        BIRD_YELLOW,
        HOVER_YELLOW,
        text_color=(0, 0, 0),
        border_color=BROWN_BORDER,
    )

    buttons = [neat_button, manual_button, q_learning_button]

    run_game = True
    while run_game:
        game_env.SCREEN.blit(game_env.IMAGES["background"], (0, 0))

        title_font = pygame.font.SysFont("Arial", 50, bold=True)
        title_label = title_font.render("I, Flappy", 1, (255, 255, 255))
        game_env.SCREEN.blit(
            title_label, (SCREENWIDTH / 2 - title_label.get_width() / 2, 100)
        )

        for button in buttons:
            button.draw(game_env.SCREEN)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run_game = False

            for button in buttons:
                if button.handle_event(event):
                    if button == neat_button:
                        local_dir = os.path.dirname(__file__)
                        config_path = os.path.join(local_dir, "config-feedforward.txt")
                        run_neat(config_path, game_env)
                    elif button == manual_button:
                        run_manual_play()
                    elif button == q_learning_button:
                        run_q_learning()

    pygame.quit()
    sys.exit()


def eval_genomes(genomes, config):
    """
    runs the simulation of the current population of
    birds and sets their fitness based on the distance they
    reach in the game.
    """
    global GEN
    GEN += 1

    # start by creating lists holding the genome itself, the
    # neural network associated with the genome and the
    # bird object that uses that network to play
    nets = []
    birds = []
    ge = []

    for genome_id, genome in genomes:
        genome.fitness = 0  # start with fitness level of 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        nets.append(net)
        birds.append(
            {
                "playerx": int(SCREENWIDTH * 0.2),
                "playery": int(
                    (SCREENHEIGHT - game_env.IMAGES["player"][0].get_height()) / 2
                ),
                "playerVelY": -9,  # player's velocity along Y
                "playerFlapped": False,
            }
        )
        ge.append(genome)

    score = 0
    basex = 0
    baseShift = (
        game_env.IMAGES["base"].get_width() - game_env.IMAGES["background"].get_width()
    )

    # get 2 new pipes to add to upperPipes lowerPipes list
    newPipe1 = getRandomPipe()
    newPipe2 = getRandomPipe()

    # list of upper pipes
    upperPipes = [
        {"x": SCREENWIDTH + 200, "y": newPipe1[0]["y"]},
        {"x": SCREENWIDTH + 200 + (SCREENWIDTH / 2), "y": newPipe2[0]["y"]},
    ]

    # list of lowerpipe
    lowerPipes = [
        {"x": SCREENWIDTH + 200, "y": newPipe1[1]["y"]},
        {"x": SCREENWIDTH + 200 + (SCREENWIDTH / 2), "y": newPipe2[1]["y"]},
    ]

    pipeVelX = -4

    # player velocity, max velocity, downward accleration, accleration on flap
    playerMaxVelY = 10  # max vel along Y, max descend speed
    playerAccY = 1  # players downward accleration

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

    run = True
    while run and len(birds) > 0:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                run = False
                pygame.quit()
                sys.exit()
            if back_button.handle_event(event):  # Raise exception to exit training
                raise BackToMenuException()

        pipe_ind = 0
        if len(birds) > 0:
            # determine whether to use the first or second pipe on the screen for neural network input
            if (
                len(upperPipes) > 1
                and birds[0]["playerx"]
                > upperPipes[0]["x"] + game_env.IMAGES["pipe"][0].get_width()
            ):
                pipe_ind = 1

        # Main game logic for each bird
        for i, bird in enumerate(birds):
            ge[i].fitness += 0.1  # Give bird a little fitness for staying alive

            # Bird's movement
            if bird["playerVelY"] < playerMaxVelY and not bird["playerFlapped"]:
                bird["playerVelY"] += playerAccY
            if bird["playerFlapped"]:
                bird["playerFlapped"] = False

            playerHeight = game_env.IMAGES["player"][0].get_height()
            bird["playery"] += min(  # noqa
                bird["playerVelY"], BASEY - bird["playery"] - playerHeight
            )

            # Neural network decision
            output = nets[i].activate(
                (
                    bird["playery"],
                    abs(bird["playery"] - upperPipes[pipe_ind]["y"]),
                    abs(bird["playery"] - lowerPipes[pipe_ind]["y"]),
                )
            )

            if (
                output[0] > 0.5
            ):  # We use a tanh activation function, so result is between -1 and 1. If > 0.5, jump.
                if bird["playery"] > -2 * game_env.IMAGES["player"][0].get_height():
                    bird["playerVelY"] = -9  # playerFlapAcc
                    bird["playerFlapped"] = True

        # --- Collision and scoring logic ---
        birds_to_remove = []
        for i, bird in enumerate(birds):
            # check for crash
            crashTest = checkCrash(
                {"x": bird["playerx"], "y": bird["playery"], "index": 0},
                upperPipes,
                lowerPipes,
            )
            if crashTest[0]:
                ge[i].fitness -= 1  # Penalize for crashing
                birds_to_remove.append(i)

        # Remove crashed birds
        for index in sorted(birds_to_remove, reverse=True):
            birds.pop(index)
            nets.pop(index)
            ge.pop(index)

        # If all birds are gone, end the generation
        if not birds:
            run = False
            break

        # check for score
        playerMidPos = (
            birds[0]["playerx"] + game_env.IMAGES["player"][0].get_width() / 2
        )
        for pipe in upperPipes:
            pipeMidPos = pipe["x"] + game_env.IMAGES["pipe"][0].get_width() / 2
            if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                score += 1
                # Reward all surviving birds for passing a pipe
                for genome in ge:
                    genome.fitness += 5
                break  # Only score once per pipe

        # move pipes to left
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            uPipe["x"] += pipeVelX
            lPipe["x"] += pipeVelX

        # add new pipe when first pipe is about to touch left of screen
        if 0 < upperPipes[0]["x"] < 5:
            newPipe = getRandomPipe()
            upperPipes.append(newPipe[0])
            lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if upperPipes[0]["x"] < -game_env.IMAGES["pipe"][0].get_width():
            upperPipes.pop(0)
            lowerPipes.pop(0)

        # --- Drawing ---
        game_env.SCREEN.blit(game_env.IMAGES["background"], (0, 0))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            game_env.SCREEN.blit(game_env.IMAGES["pipe"][0], (uPipe["x"], uPipe["y"]))
            game_env.SCREEN.blit(game_env.IMAGES["pipe"][1], (lPipe["x"], lPipe["y"]))

        basex = -((-basex + 100) % baseShift)
        game_env.SCREEN.blit(game_env.IMAGES["base"], (basex, BASEY))

        # Draw birds
        for bird in birds:
            playerSurface = game_env.IMAGES["player"][0]  # Simple, non-flapping image
            game_env.SCREEN.blit(playerSurface, (bird["playerx"], bird["playery"]))

        # Display Score, Generation, and Alive count
        showScore(score)
        score_label = pygame.font.SysFont("comicsans", 28).render(
            "Gen: " + str(GEN - 1), 1, (255, 255, 255)
        )
        game_env.SCREEN.blit(
            score_label, (SCREENWIDTH - score_label.get_width() - 10, 10)
        )
        score_label = pygame.font.SysFont("comicsans", 28).render(
            "Alive: " + str(len(birds)), 1, (255, 255, 255)
        )
        game_env.SCREEN.blit(
            score_label, (SCREENWIDTH - score_label.get_width() - 10, 50)
        )

        back_button.draw(game_env.SCREEN)

        pygame.display.update()
        game_env.FPSCLOCK.tick(FPS)


def getRandomPipe():
    """returns a randomly generated pipe"""
    # y of gap between upper and lower pipe
    gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
    gapY += int(BASEY * 0.2)
    pipeHeight = game_env.IMAGES["pipe"][0].get_height()
    pipeX = SCREENWIDTH + 10

    return [
        {"x": pipeX, "y": gapY - pipeHeight},  # upper pipe
        {"x": pipeX, "y": gapY + PIPEGAPSIZE},  # lower pipe
    ]


def showScore(score):
    """displays score in center of screen"""
    scoreDigits = [int(x) for x in list(str(score))]
    totalWidth = 0  # total width of all numbers to be printed

    for digit in scoreDigits:
        totalWidth += game_env.IMAGES["numbers"][digit].get_width()

    Xoffset = (SCREENWIDTH - totalWidth) / 2

    for digit in scoreDigits:
        game_env.SCREEN.blit(
            game_env.IMAGES["numbers"][digit], (Xoffset, SCREENHEIGHT * 0.1)
        )
        Xoffset += game_env.IMAGES["numbers"][digit].get_width()


def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collders with base or pipes."""
    pi = 0  # player['index']
    player["w"] = game_env.IMAGES["player"][0].get_width()
    player["h"] = game_env.IMAGES["player"][0].get_height()

    # if player crashes into ground
    if player["y"] + player["h"] >= BASEY - 1:
        return [True, True]
    else:

        playerRect = pygame.Rect(player["x"], player["y"], player["w"], player["h"])
        pipeW = game_env.IMAGES["pipe"][0].get_width()
        pipeH = game_env.IMAGES["pipe"][0].get_height()

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            # upper and lower pipe rects
            uPipeRect = pygame.Rect(uPipe["x"], uPipe["y"], pipeW, pipeH)
            lPipeRect = pygame.Rect(lPipe["x"], lPipe["y"], pipeW, pipeH)

            # player and upper/lower pipe hitmasks
            pHitMask = game_env.HITMASKS["player"][pi]
            uHitmask = game_env.HITMASKS["pipe"][0]
            lHitmask = game_env.HITMASKS["pipe"][1]

            # if bird collided with upipe or lpipe
            uCollide = pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
            lCollide = pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

            if uCollide or lCollide:
                return [True, False]

    return [False, False]


def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
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


def getHitmask(image):
    """returns a hitmask using an image's alpha."""
    mask = []
    for x in xrange(image.get_width()):
        mask.append([])
        for y in xrange(image.get_height()):
            mask[x].append(bool(image.get_at((x, y))[3]))
    return mask


def run_neat(config_file, game):
    """
    runs the NEAT algorithm to train a neural network to play flappy bird.
    :param config_file: location of config file
    :return: None
    """

    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_file,
    )

    # Create the population, which is the top-level object for a NEAT run.
    p = neat.Population(config)

    # Add a stdout reporter to show progress in the terminal.
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    # Run for up to 50 generations.
    try:
        winner = p.run(eval_genomes, 50)

        # Generate learning graphs after training is complete
        visualize.plot_stats(stats, ylog=False, view=False, filename="avg_fitness.svg")
        visualize.plot_species(stats, view=False, filename="speciation.svg")

        # show final stats
        print("\nBest genome:\n{!s}".format(winner))

        # Save the winner.
        with open("winner.pkl", "wb") as f:
            pickle.dump(winner, f)
    except BackToMenuException:
        print("--- NEAT Training Interrupted. Returning to menu. ---")
        return  # This will go back to the main_menu loop


if __name__ == "__main__":
    # Initialize the global game environment
    game_env = FlappyGame()

    # Start with the main menu
    main_menu()
