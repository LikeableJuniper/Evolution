# Classes for brains
import random
import math


def init(fieldSize):
    global Brain, Connection, internalNodeIDs, sensoryNodeIDs, actionNodeIDs
    class nodeTypes:
        class Sensory:
            L_x = 1 # Position x
            L_y = 2 # Position y
            Rnd = 3 # Random
            Bx = 10 # X-Border Distance
            By = 11 # Y-Border Distance
        class Action:
            Mfd = 4 # Move forward
            Mrv = 5 # Move reverse
            Mrn = 6 # Move random
            MRL = 7 # Move right/left (-1, 1)
            MX = 8 # Move x (-1, 1)
            MY = 9 # Move y (-1, 1)


    class Connection:
        def __init__(self, source : int, target : int, weight : float):
            # "source" and "target" are integers taken from the class "nodeTypes" and its subclasses, representing IDs of the nodes.
            self.source = source
            self.target = target
            self.weight = weight
        
        def __repr__(self):
            return "Connection(Source: {}, Target: {}, weight: {})".format(self.source, self.target, self.weight)
        
        def __eq__(self, that):
            return [self.source, self.target] == [that.source, that.target]
        
        def getValue(self, sourceInput):
            return round(sourceInput * self.weight, 5)


    class SensoryNode:
        def __init__(self, nodeType, size=[0, 0]):
            self.nodeType = nodeType
            self.size = size
            self.halfSize = [size[i]/2 for i in range(len(size))]
        
        def __call__(self, **kwargs):
            if self.nodeType in positionRequiredNodes:
                if (position := kwargs.get("position")) != None:
                    if self.nodeType == nodeTypes.Sensory.Bx:
                        return round(position[0]/self.halfSize[0] - 1, 3)
                    if self.nodeType == nodeTypes.Sensory.By:
                        return round(position[1]/self.halfSize[1] - 1, 3)
                    if self.nodeType == nodeTypes.Sensory.L_x:
                        return round(position[0]/self.size[0], 3)
                    if self.nodeType == nodeTypes.Sensory.L_y:
                        return round(position[1]/self.size[1], 3)
            if self.nodeType == nodeTypes.Sensory.Rnd:
                return round(random.random()*2-1, 3)


    class ActionNode:
        def __init__(self, nodeType):
            self.nodeType = nodeType
        
        def __call__(self, **kwargs):
            if (value := kwargs.get("value")) != None:
                value = [-1, 1][int(value > 0)]
            
            if self.nodeType in directionRequiredNodes:
                if (direction := kwargs.get("direction")) != None:
                    if self.nodeType == nodeTypes.Action.Mfd:
                        return direction
                    if self.nodeType == nodeTypes.Action.Mrv:
                        return list(direction[i]*(-1) for i in range(len(direction)))
            
            if self.nodeType == nodeTypes.Action.Mrn:
                return [random.randint(-1, 1) for _ in range(2)]
            
            if self.nodeType in valueRequiredNodes:
                if self.nodeType == nodeTypes.Action.MX:
                    return [value, 0]
                if self.nodeType == nodeTypes.Action.MY:
                    return [0, value]
                if self.nodeType == nodeTypes.Action.MRL:
                    if direction != [0, 0]:
                        rotatedDirection = directionRotations[(directionRotations.index(direction)+1)%len(directionRotations)]
                        return  [value * i for i in rotatedDirection]
                    return direction


    class Brain:
        def __init__(self, genome):
            self.genome = genome
            self.connections = self.getConnections()
            self.optimizeConnections()
        
        def __repr__(self):
            return str(self.connections)
        
        def __call__(self, position, direction):
            activeNode, value = self.getActiveNode(position, direction)
            movement = [0, 0]
            if activeNode != 0:
                movement = actionNodes[actionNodeIDs.index(activeNode)](position=position, direction=direction, value=value)
            return movement
    
        def getActiveNode(self, position, direction):
            actionInputs = [[] for _ in range(len(actionNodeIDs))] # Inputs are in format list[list[int]]
            internalInputs = [[] for _ in range(len(internalNodeIDs))]
            
            # Compute all connections who have their source at a sensory node.
            for sensoryConnection in self.sensorySourceConnections:
                sensoryOutput = sensoryConnection.getValue(sensoryNodes[sensoryNodeIDs.index(sensoryConnection.source)](position=position, direction=direction))
                if sensoryConnection.target > 0: # Target of connection is an action node
                    actionInputs[actionNodeIDs.index(sensoryConnection.target)].append(sensoryOutput)
                elif sensoryConnection.target < 0: # Target of connection is an internal node
                    internalInputs[internalNodeIDs.index(sensoryConnection.target)].append(sensoryOutput)
            
            # Compute outputs of internal nodes.
            internalOutputs = [0 for _ in range(len(internalNodeIDs))]
            for index, internalInput in enumerate(internalInputs):
                internalOutputs[index] = hyperbol(internalInput)

            # Add outputs of internal nodes to action node inputs.
            for actionTargetConnection in self.actionTargetConnections:
                if actionTargetConnection.source < 0: # Source is an internal node, the wanted.
                    idIndex = actionNodeIDs.index(actionTargetConnection.target)
                    actionInputs[idIndex].append(actionTargetConnection.getValue(internalOutputs[internalNodeIDs.index(actionTargetConnection.source)]))

            # Compute outputs of action nodes.
            actionOutputs = [0 for _ in range(len(actionNodeIDs))]
            for index, actionInput in enumerate(actionInputs):
                actionOutputs[index] = hyperbol(actionInput)

            activeNodeID = 0
            if (value := actionOutputs[(probIndex := findMax(actionOutputs, actionSupportsNegativeIndices))]) != 0:
                activeNodeID = actionNodeIDs[probIndex]
            
            return activeNodeID, value

        def getConnections(self):
            result: list[Connection] = []
            for gene in self.genome:
                binary = bin(gene).replace("0b", "")
                binary = f'{binary:0>32}' # Fills the space to the left of the string with "0" so that string indices still correspond to the same values even if the most significant digit isnt 1.
                source = int(binary[0], 2)
                sourceInt = int(binary[1:8], 2)
                target = int(binary[9], 2)
                targetInt = int(binary[10:16], 2)
                isNegative = int(binary[17])
                weight = int(binary[18:], 2)

                if source: # Bit at most significant digit is 1, source is from an internal node.
                    sourceID = internalNodeIDs[sourceInt%len(internalNodeIDs)]
                else: # Bit at most significant digit is 0, source is from sensory node.
                    sourceID = sensoryNodeIDs[sourceInt%len(sensoryNodeIDs)]
                
                if target: # Bit at 9th position is 1, target of connection is an internal node.
                    targetID = internalNodeIDs[targetInt%len(internalNodeIDs)]
                else: # Bit at 9th position is 0, target of connection is an action node.
                    targetID = actionNodeIDs[targetInt%len(actionNodeIDs)]
                
                if (targetID < 0 and sourceID < 0): # Both are internal nodes (not computed for simplicitys sake), therefore doesn't need to be appended to "self.connections".
                    continue
                
                result.append(Connection(sourceID, targetID, (-1 if isNegative else 1) * round((weight/WEIGHT_CONSTANT), 2)))
            return result

        def optimizeConnections(self):
            optimizedConnections = self.connections.copy()
            # Optimize doubled connections by adding their weights and creating one connection with that weight.
            sourceTargetPairs: list[list[int]] = [] # List containing sources and targets in the folllowing format: (sourceID, targetID)
            weights: list[int] = [] # Values correspond to list above, adding up the weights per source and target pair.
            for connection in optimizedConnections:
                if (sourceTargetPair := (connection.source, connection.target)) in sourceTargetPairs:
                    weights[sourceTargetPairs.index(sourceTargetPair)] += connection.weight
                else:
                    sourceTargetPairs.append(sourceTargetPair)
                    weights.append(connection.weight)
            
            optimizedConnections = [Connection(sourceTargetPairs[i][0], sourceTargetPairs[i][1], weights[i]) for i in range(len(sourceTargetPairs))]

            # Create lists of all connections with either end connected to an internal node.
            internalNodeSource: list[list[Connection]] = [[] for _ in range(len(internalNodeIDs))]
            internalNodeTarget: list[list[Connection]] = [[] for _ in range(len(internalNodeIDs))]
            for i in range(len(internalNodeIDs)):
                for connection in optimizedConnections:
                    if connection.source == -(i+1):
                        internalNodeSource[i].append(connection)
                    elif connection.target == -(i+1):
                        internalNodeTarget[i].append(connection)
            
            # Cancel connections that lead to an internal node without any connections to an action node.
            for i, sourceList in enumerate(internalNodeSource):
                if len(sourceList) == 0:
                    a = 0
                    while a < len(optimizedConnections):
                        if optimizedConnections[a].target == -(i+1):
                            del optimizedConnections[a]
                        else:
                            a += 1
            
            # Cancel connections with an internal node as target that has no source connections.
            for i, targetList in enumerate(internalNodeTarget):
                if len(targetList) == 0:
                    a = 0
                    while a < len(optimizedConnections):
                        if optimizedConnections[a].source == -(i+1):
                            del optimizedConnections[a]
                        else:
                            a += 1

            # Split connections in two lists, sensory input and internal input, used for calculating move.
            self.sensorySourceConnections : list[Connection] = [connection for connection in self.connections if connection.source > 0]
            self.internalInputConnections : list[Connection] = [connection for connection in self.connections if connection.source < 0]
            # All connections that lead to an action node. No set-theoretic relation to other two lists above.
            self.actionTargetConnections : list[Connection] = [connection for connection in self.connections if connection.target in actionNodeIDs]
            self.connections = optimizedConnections


    def hyperbol(inputs):
        """Takes a list of inputs and runs their sum through a hpyerbolic tangent function."""
        return round(math.tanh(sum(inputs)), 5)


    def findMax(searchList : list, absIndices):
        """Finds the max value of a list with negative numbers, applying 'abs()' to elements whose index is in 'absIndices'."""
        iterList = searchList.copy()
        for index, value in enumerate(iterList):
            if index in absIndices:
                iterList[index] = abs(value)
        maxFoundIndex = iterList.index(min(iterList))
        for index, val in enumerate(iterList):
            if val > iterList[maxFoundIndex]:
                maxFoundIndex = index

        return maxFoundIndex


    WEIGHT_CONSTANT = 2**12 # Constant by which the weight read from the genome binary number is divided.
    MAX_WEIGHT = 2**14

    sensoryNodeIDs = [nodeTypes.Sensory.L_x, nodeTypes.Sensory.L_y, nodeTypes.Sensory.Rnd, nodeTypes.Sensory.Bx, nodeTypes.Sensory.By]
    actionNodeIDs = [nodeTypes.Action.Mfd, nodeTypes.Action.Mrv, nodeTypes.Action.Mrn, nodeTypes.Action.MRL, nodeTypes.Action.MX, nodeTypes.Action.MY]
    sensoryNodes = [SensoryNode(sensoryNodeIDs[i], size=fieldSize) for i in range(len(sensoryNodeIDs))]
    actionNodes = [ActionNode(actionNodeIDs[i]) for i in range(len(actionNodeIDs))]
    actionSupportsNegative = [nodeTypes.Action.MRL, nodeTypes.Action.MX, nodeTypes.Action.MY]
    actionSupportsNegativeIndices = [actionNodeIDs.index(i) for i in actionSupportsNegative]
    internalNodeIDs = [-1, -2, -3, -4] # Internal neurons have negative IDs to prevent accidental confusion with the action and sensory nodes if more are added. Also used to distinguish between action and internal nodes in many parts of the code.
    positionRequiredNodes = [nodeTypes.Sensory.L_x, nodeTypes.Sensory.L_y, nodeTypes.Sensory.Bx, nodeTypes.Sensory.By]
    directionRequiredNodes = [nodeTypes.Action.Mfd, nodeTypes.Action.Mrv, nodeTypes.Action.MRL]
    valueRequiredNodes = [nodeTypes.Action.MRL, nodeTypes.Action.MX, nodeTypes.Action.MY] # Nodes that require the value to detrmine whether its negative or positive

    directionRotations = [[1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1]]


MAX_GENE_VALUE = 0xFFFFFFFF
def generateGenome(length: int):
    """
    Generates a sequence of genes, each gene consisting of 8 hexadecimal characters. Saved as an integer because python doesnt know how convert strings with hex codes to binary numbers.
    Maximum value can be achieved by 0xFFFFFFFF = 4294967295 in decimal or 0b11111111111111111111111111111111 in binary, which will be important to determine the genes function.
    """
    genome: list[str] = [random.randint(0, MAX_GENE_VALUE) for _ in range(length)]
    return genome


if __name__ == "__main__":
    init([50, 50])
    a = Brain([935341282, 3515951229, 2198879245, 2321375513, 3982911623])
    print(bin(a.genome[0]).replace("0b", ""), a.connections)
