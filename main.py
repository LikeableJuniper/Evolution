################################################################
# Created on 19.11.2022
# Simulation of Evolution as described by David Miller in his YouTube video "I programmed some creatures. They evolved."
# https://www.youtube.com/watch?v=N3tRFayqVtk
################################################################
import random
import pygame as pg
import ctypes
import math
import brain
from datetime import datetime
import json
import os

random.seed(seed := random.randint(5000, 10_000))
print("Seed: {}".format(seed))

pg.init()
pg.font.init()

mainFont = pg.font.SysFont("Arial Black", 50)
nodeFont = pg.font.SysFont("Arial Black", 15)

screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
user32 = ctypes.windll.user32
screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
textBoxDiff = [-300, 100]
framesPos = [screensize[0]+textBoxDiff[0], 10]
generationPos = [framesPos[0]+textBoxDiff[0], framesPos[1]+textBoxDiff[1]]
criteriaPos = [generationPos[0], generationPos[1]+textBoxDiff[1]]
refreshRect = [screensize[0] - 1000, 0, 1000, 10+textBoxDiff[1]*2]
nodeRadius = 25
nodeTextDiff = nodeRadius/2

USEBRAINS = True
GENOME_LENGTH = 20
GENERATION_LENGTH = 200 # Numbers of frames before next generation is created.
MAX_GENE_VALUE = 0xFFFFFFFF
MUTATION_RATE = 0
SIMULATION_SIZE = [30, 30]
brain.init(SIMULATION_SIZE)
squareSize = min(screensize)
cellDimensions = [math.floor(squareSize/SIMULATION_SIZE[0]), math.floor(squareSize/SIMULATION_SIZE[1])]
fieldDimensions = [cellDimensions[i]*cellDimensions[i] for i in range(len(SIMULATION_SIZE))]
POPULATION_0 = round(SIMULATION_SIZE[0] * SIMULATION_SIZE[1] / 2)
sensoryNodeNames = ["L_x", "L_y", "Rnd", "Bx", "By"]
actionNodeNames = ["Mfd", "Mrv", "Mrn", "MRL", "MX", "MY"]

LOGGING_PATH = "C:/Users/Noa_s/.vscode/Projects/Python/inDev/Etc/Simulations/Evolution/log.txt"
SAVE_PATH = "C:/Users/Noa_s/.vscode/Projects/Python/inDev/Etc/Simulations/Evolution/Saved"


class Criteria:
    class RIGHT:
        id = 1
        quote = 0.5
    class LEFT:
        id = 2
        quote = 0.5
    class UP:
        id = 3
        quote = 0.5
    class DOWN:
        id = 4
        quote = 0.5
    class BORDER:
        id = 5
        quote = 0.1
    class TEMPERATURE:
        id = 6
    class CENTER:
        id = 7


criteriaIDs = [Criteria.RIGHT.id, Criteria.LEFT.id, Criteria.UP.id, Criteria.DOWN.id, Criteria.BORDER.id, Criteria.TEMPERATURE.id, Criteria.CENTER.id]
criteriaQuotes = [Criteria.RIGHT.quote, Criteria.LEFT.quote, Criteria.UP.quote, Criteria.DOWN.quote, Criteria.BORDER.quote]
criteriaNames = ["Right", "Left", "Up", "Down", "Border", "Temperature", "Center"]
reproduceCriteria = Criteria.CENTER.id
criteriaName = criteriaNames[criteriaIDs.index(reproduceCriteria)]


def countObjects(li):
    count = 0
    for x in li:
        for y in x:
            count += 1 if y else 0
    return count


def replaceAtIndex(string, index, newVal):
    tempList = list(string)
    tempList[index] = newVal
    return "".join(tempList)


def mutateGenome(genome):
    genome = genome.copy()
    for index, gene in enumerate(genome):
        if random.random() < MUTATION_RATE:
            binGene = bin(gene).replace("0b", "")
            binGene = f'{binGene:0>32}'
            chosenIndex = random.randint(0, 17) # 17 is the index of the last digit in the binary genome which has significant effects, the rest only influence the weight and are not significant enough to create interesting mutations.
            binGene = replaceAtIndex(binGene, chosenIndex, "0" if binGene[chosenIndex] == "1" else "1")
            genome[index] = int(binGene, 2)
    return genome


def generateField(size):
    return [[None for _ in range(size[1])] for _ in range(size[0])]


def cloneList(clone):
    """
    Clone a list without reference since even pythons built in function "<list>.copy()" doesn't work for lists with sublists.
    This function works for lists with format: list[list[Any]]
    """
    res = list()
    for i in range(len(clone)):
        res.append(clone[i].copy())
    return res


class Simulation:
    def __init__(self, fieldSize : list[int], field=[], generation=0):
        self.field : list[list[Organism]] = field if field else generateField(fieldSize)
        self.size = fieldSize
        self.criteriaTolerances = [[i*self.size[0], i*self.size[1]] for i in criteriaQuotes]
        self.limit = [self.size[0]-1, self.size[1]-1]
        self.frames = 0
        self.generation = generation
        self.centerChances = [[math.cos(4*x/self.size[0] - math.pi/2) + math.cos(4*y/self.size[1] - math.pi/2) for y in range(self.size[1])] for x in range(self.size[0])]

        if not generation:
            self.initiateColony(POPULATION_0, screen)
    
    def __repr__(self):
        return "Simulation with field: {}".format(self.field)
    
    def __call__(self, screen):
        nextField = cloneList(self.field)
        for xCoord, xList in enumerate(self.field):
            for yCoord, yObject in enumerate(xList):
                if yObject:
                    beforePos = yObject.pos
                    yObject.move(yObject([xCoord, yCoord]), self.limit, self.field)
                    nextField[yObject.pos[0]][yObject.pos[1]] = yObject
                    if beforePos != yObject.pos: # If the organism hasn't moved, make sure to not replace its place in the list with "None"
                        nextField[xCoord][yCoord] = None
        self.field = nextField
        self.frames += 1
        if self.frames >= GENERATION_LENGTH:
            self.nextGeneration(reproduceCriteria, screen)

    def initiateColony(self, colonySize, screen):
        if colonySize > self.size[0] * self.size[1]:
            raise ValueError("Colony size too big to initiate on field!")
        
        for _ in range(colonySize):
            choice = [random.randint(0, self.limit[0]), random.randint(0, self.limit[1])]
            while self.field[choice[0]][choice[1]] != None:
                choice = [random.randint(0, self.limit[0]), random.randint(0, self.limit[1])]
            self.field[choice[0]][choice[1]] = Organism(choice, brain.generateGenome(GENOME_LENGTH))
        
        drawBrain(screen, self.field[choice[0]][choice[1]])

    def nextGeneration(self, criteria, screen):
        isEmtpy = True
        for x in self.field:
            for y in x:
                if y:
                    isEmtpy = False
                    break
            if not isEmtpy:
                break
        
        if not isEmtpy:
            while self.field[(organismChoice := [random.randint(0, SIMULATION_SIZE[0]-1), random.randint(0, SIMULATION_SIZE[1]-1)])[0]][organismChoice[1]] == None:
                pass
            drawBrain(screen, self.field[organismChoice[0]][organismChoice[1]])

        self.generation += 1
        self.frames = 0
        nextField = generateField(self.size)
        for xCoord, xList in enumerate(self.field):
            for yCoord, yObject in enumerate(xList):
                if yObject == None:
                    continue
                reproduce = False
                # Checks for all criteria and sets "reproduce" to True if the criteria is met.
                if criteria == Criteria.RIGHT.id:
                    if xCoord > self.criteriaTolerances[criteriaIDs.index(criteria)][0]:
                        reproduce = True
                elif criteria == Criteria.LEFT.id:
                    if xCoord < self.criteriaTolerances[criteriaIDs.index(criteria)][0]:
                        reproduce = True
                elif criteria == Criteria.UP.id:
                    if yCoord < self.criteriaTolerances[criteriaIDs.index(criteria)][0]:
                        reproduce = True
                elif criteria == Criteria.DOWN.id:
                    if yCoord > self.criteriaTolerances[criteriaIDs.index(criteria)][0]:
                        reproduce = True
                elif criteria == Criteria.TEMPERATURE.id:
                    if random.random() < min((yCoord/self.size[1])**2, 1):
                        reproduce = True
                elif criteria == Criteria.CENTER.id:
                    if random.random() < self.centerChances[xCoord][yCoord]:
                        reproduce = True
                
                if reproduce:
                    for _ in range(random.randint(1, 3)):
                        choice = [random.randint(0, self.limit[0]), random.randint(0, self.limit[1])]
                        while self.field[choice[0]][choice[1]] != None:
                            choice = [random.randint(0, self.limit[0]), random.randint(0, self.limit[1])]
                        nextField[choice[0]][choice[1]] = Organism(choice, mutateGenome(yObject.genome))
        
        self.field = nextField


class Organism:
    def __init__(self, pos : list[int], genome : list[int], direction=[]):
        self.pos = pos
        self.genome = genome
        self.motivation = random.random()+0.5
        if USEBRAINS:
            self.brain = brain.Brain(self.genome)
        else:
            # Generate a dummy brain in case no neural network is used.
            self.brain = lambda position, direction: direction
        
        self.direction = [random.randint(-1, 1) for _ in range(2)] if not direction else direction
        self.color = self.getColor()
        for index, val in enumerate(self.color):
            if not 0 <= val <= 255:
                self.color[index] = 0
    
    def __repr__(self):
        return "Organism at position {}".format(self.pos)
    
    def __call__(self, position):
        if random.random() < self.motivation:
            return self.brain(position, self.direction)
        else: return [0, 0]

    def __bool__(self):
        return True

    def move(self, movement : list[int], limit : list[int], field : list[list[None]]):
        finalX, finalY = [self.pos[i] + movement[i] for i in range(len(movement))]

        # Checks for border values
        if finalX < 0:
            finalX = 0
        elif finalX > limit[0]:
            finalX = limit[0]

        if finalY < 0:
            finalY = 0
        elif finalY > limit[1]:
            finalY = limit[1]
        
        # Checks if the cell to move to is occupied by another organism already, make sure to not trigger when not moved.
        if [finalX, finalY] != self.pos:
            if field[finalX][self.pos[1]]:
                finalX -= movement[0]
            if field[finalX][finalY]:
                finalY -= movement[1]
        
        self.pos = [finalX, finalY]
        self.direction = movement
        return self.pos

    def getColor(self):
        colorValue = [[], [], []]
        for i in range(len(self.genome)):
            colorValue[i%3].append(self.genome[i])
        
        for index, value in enumerate(colorValue):
            if len(value) == 0:
                colorValue[index] = 255
            else:
                colorValue[index] = sum(value)/(len(value)*MAX_GENE_VALUE)
        
        return [value*255 for value in colorValue]


def initiateScreen(screen):
    pg.draw.rect(screen, (255, 255, 255), [refreshRect[0], refreshRect[1]+10+textBoxDiff[1]*2, refreshRect[2], refreshRect[1]+100])


def clearScreen(screen):
    pg.draw.rect(screen, (255, 255, 255), [0, 0, squareSize, squareSize])
    pg.draw.rect(screen, (255, 255, 255), refreshRect)


def drawBrain(screen: pg.Surface, organism: Organism):
    pg.draw.rect(screen, (0, 0, 0), [864, 310, screensize[0]-864, screensize[1]-310])
    pg.draw.rect(screen, organism.color, [screensize[0]-40, screensize[1]-100, 40, 40])
    for i in range(5):
        pg.draw.circle(screen, (0, 180, 255), pos := (1200+nodeRadius*(1+2*i)+i*100, 350), nodeRadius)
        screen.blit(nodeFont.render(sensoryNodeNames[i], False, (0, 0, 0)), [pos[0]-nodeTextDiff, pos[1]-nodeTextDiff])
    for i in range(len(brain.internalNodeIDs)):
        pg.draw.circle(screen, (150, 150, 150), pos := ((1200+nodeRadius*(1+2*i)+i*100, 575)), nodeRadius)
        screen.blit(nodeFont.render(str(-(i+1)), False, (0, 0, 0)), [pos[0]-nodeTextDiff, pos[1]-nodeTextDiff])
    for i in range(6):
        pg.draw.circle(screen, (255, 0, 0), pos := (1200+nodeRadius*(1+2*i)+i*60, 800), nodeRadius)
        screen.blit(nodeFont.render(actionNodeNames[i], False, (0, 0, 0)), [pos[0]-nodeTextDiff, pos[1]-nodeTextDiff])
    
    for connection in organism.brain.connections:
        if connection.source > 0:
            i = brain.sensoryNodeIDs.index(connection.source)
            startPos = (1200+nodeRadius*(1+2*i)+i*100, 350)
        else:
            startPos = (1200+nodeRadius*(1+2*(abs(connection.source)-1))+(abs(connection.source)-1)*100, 575)
        
        if connection.target < 0:
            endPos = (1200+nodeRadius*(1+2*(abs(connection.target)-1))+(abs(connection.target)-1)*100, 575)
        else:
            i = brain.actionNodeIDs.index(connection.target)
            endPos = (1200+nodeRadius*(1+2*i)+i*60, 800)
        
        if connection.weight >= 0:
            color = (0, 255, 0)
        else:
            color = (255, 0, 0)

        pg.draw.line(screen, color, startPos, endPos)


def inRect(pos, rect):
    return rect[0] <= pos[0] <= rect[2] and rect[1] <= pos[1] <= rect[3]


def save(simulation: Simulation):
    saveData = {"generation": simulation.generation, "field": []}
    saveField = [[None for _ in range(SIMULATION_SIZE[0])] for _ in range(SIMULATION_SIZE[1])]

    for ix, x in enumerate(simulation.field):
        for iy, y in enumerate(x):
            if isinstance(y, Organism):
                saveField[ix][iy] = {"genome": y.genome, "direction": y.direction}

    saveData["field"] = saveField

    idList = []
    for file in os.listdir(SAVE_PATH):
        currentID = file.replace(".json", "")
        try:
            currentID = int(currentID)
            idList.append(currentID)
        except:
            continue
    
    fileID = 0
    while fileID in idList:
        fileID += 1
    
    with open(f"{SAVE_PATH}/{fileID}.json", "w") as f:
        json.dump(saveData, f)


def load(path):
    with open(path, "r") as f:
        loaded: dict = json.load(f)
    
    loadField = [[None for _ in range(len(loaded["field"][0]))].copy() for _ in range(len(loaded["field"]))]
    for ix, x in enumerate(loaded["field"]):
        for iy, y in enumerate(x):
            if y:
                loadField[ix][iy] = Organism((ix, iy), y.get("genome"), direction=y.get("direction"))
    
    brain.init([len(loadField), len(loadField[0])])
    return Simulation(fieldSize=[len(loadField), len(loadField[0])], field=loadField, generation=loaded.get("generation"))


#simulation = load("C:/Users/Noa_s/.vscode/Projects/Python/inDev/Etc/Simulations/Evolution/Saved/3.json")
simulation = Simulation(SIMULATION_SIZE)
initiateScreen(screen)

running = True
paused = False
waitRelease = {
    str(pg.K_SPACE): False,
    str(pg.K_i): False,
    str(pg.K_s): False
}
i = 1
selected = None

while running:
    i += 1
    pg.display.update()
    clearScreen(screen)

    for xCoord, xList in enumerate(simulation.field):
        for yCoord, yObject in enumerate(xList):
            drawPos = [xCoord*cellDimensions[0], yCoord*cellDimensions[1]]
            pg.draw.rect(screen, (0, 0, 0), drawPos+cellDimensions, 1)
            if yObject:
                pg.draw.rect(screen, yObject.color, drawPos+cellDimensions)
    
    screen.blit(mainFont.render(str(simulation.frames), False, (0, 0, 0)), framesPos)
    screen.blit(mainFont.render("Generation: {}".format(simulation.generation), False, (0, 0, 0)), generationPos)
    screen.blit(mainFont.render("Criteria: {}".format(criteriaName), False, (0, 0, 0)), criteriaPos)
    
    if i % 10 == 0 and not paused:
        i = 0
        simulation(screen)
    
    pressed = pg.key.get_pressed()
    if pressed[pg.K_SPACE]:
        if not waitRelease[pg.K_SPACE]:
            waitRelease[pg.K_SPACE] = True
            paused = False if paused else True
    else:
        waitRelease[pg.K_SPACE] = False
    
    if pressed[pg.K_d]:
        if selected:
            simulation.field[selected[0]][selected[1]] = None
            selected = None
    
    if pressed[pg.K_s]:
        if not waitRelease[pg.K_s]:
            waitRelease[pg.K_s] = True
            save(simulation)
            print(f"Saved current simulation state at {datetime.now().strftime('%H:%M:%S')}.")
    else:
        waitRelease[pg.K_s] = False
    
    if pressed[pg.K_i]:
        if not waitRelease[pg.K_i]:
            waitRelease[pg.K_i] = True
            if selected:
                if organism := simulation.field[selected[0]][selected[1]]:
                    with open(LOGGING_PATH, "a") as f:
                        f.write(f"{datetime.now().strftime('%H:%M:%S')} {organism}, {organism.brain.genome}, {organism.brain.connections}/n")
                    print(f"Logged organism info to {LOGGING_PATH}")
    else:
        waitRelease[pg.K_i] = False
    
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            running = False
        if event.type == pg.MOUSEBUTTONDOWN:
            mousePos = pg.mouse.get_pos()
            if inRect(mousePos, [0, 0]+fieldDimensions):
                cellCoords = [math.floor(mousePos[0]/cellDimensions[0]), math.floor(mousePos[1]/cellDimensions[1])]
                selected = cellCoords
                if (organism := simulation.field[cellCoords[0]][cellCoords[1]]):
                    drawBrain(screen, organism)
