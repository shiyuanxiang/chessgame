from copy import deepcopy
import numpy as np
import queue

DIRECTION_4 = np.array([[0, 1], [1, 0], [0, -1], [-1, 0]])
DIRECTION_8 = np.array([[0, 1], [1, 1], [1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1]])

class MementoBox:
    def __init__(self) -> None:
        self.memento = []
    
    def store(self, state, *args):
        self.memento.append((deepcopy(state), args))
    
    def retract(self, player_id):
        if len(self.memento) < 2:
            return False, self.memento[-1]
        if player_id == self.memento[-2][1]:
            del self.memento[-1]
            return True, self.memento[-1]
        
        if len(self.memento) < 3:
            return False, self.memento[-1]
        del self.memento[-2:]
        return True, self.memento[-1]

class BaseRule:
    def __init__(self, height, width) -> None:
        self.height = height
        self.width = width
        self.shape = (self.height, self.width)
        self.state = None
        self.skip_time = 0
        self.turn = 0
        pass
    
    def reset(self):
        self.state = (np.zeros(self.shape, dtype=np.int8)-1).tolist()
        self.turn = 0
        self.skip_time = 0

    def vaildCoordinate(self, coord):
        if any(coord < 0) or any(coord >= self.shape):
            return False
        return True
    
    def vaildAction(self, action):
        coord, player_id = np.array(action['coord']), action['player_id']
        return self.vaildCoordinate(coord)

    def step(self, action):
        if not self.vaildAction(action):
            return False, "Invaild action"
        return True, "Successfully"
    
    def judgeFinish(self):
        pass
    
    def restore(self, state, turn, skip_time):
        self.state = state
        self.turn = turn
        self.skip_time = skip_time
    
    def store(self):
        return self.state, self.turn, self.skip_time
        

class GobangRule(BaseRule):
    def vaildAction(self, action):
        if not super().vaildAction(action):
            return False
        coord, player_id = action['coord'], action['player_id']
        if not self.state[coord[0]][coord[1]] == -1:
            return False
        return True
        
        
    def step(self, action):
        if not self.vaildAction(action):
            return False, "Invaild action"
        
        coord, player_id = action['coord'], action['player_id']
        if player_id != self.turn:
            return False, "Not the turn of player {}".format(player_id)

        self.state[coord[0]][coord[1]] = player_id
        self.turn ^= 1
        return True, "Successfully"
    
    def judgeFinish(self):
        state = self.state
        assert(np.min(state) >= -1)
        assert(np.max(state) <= 2)
        
        win = [False, False]
        space_count = 0
        
        for dir in DIRECTION_8[:4]:
            count = np.zeros(self.shape, dtype=np.uint8)
            for x in range(self.height):
                for y in range(self.width):
                    if state[x][y] == -1:
                        space_count += 1
                        continue
                    last_pos = np.array([x, y]) - dir
                    if self.vaildCoordinate(last_pos) and state[x][y] == state[last_pos[0]][last_pos[1]]:
                        count[x][y] = count[last_pos[0]][last_pos[1]] + 1
                        if count[x][y] == 5:
                            win[state[x][y]] = True
                    else:
                        count[x][y] = 1
        
        if all(win):
            return True, -1
        for p in [0, 1]:
            if win[p]:
                return True, p
        if space_count == 0:
            return True, -1
        return False, None

class GoRule(BaseRule):
    def calcQi(self, state):
        qi = np.zeros(self.shape, dtype=np.int8)
        belong = np.zeros(self.shape, dtype=np.int8)-1
        block_num = 0
        block_qi = []
        # bfs
        for x in range(self.height):
            for y in range(self.width):
                if belong[x][y] == -1 and state[x][y] != -1:
                    belong[x][y] = block_num
                    block_qi.append(0)
                    q = queue.Queue()
                    q.put(np.array((x, y)))
                    while not q.empty():
                        now = q.get()
                        for dir in DIRECTION_4:
                            next = now + dir
                            if self.vaildCoordinate(next) and belong[next[0]][next[1]] == -1:
                                if state[next[0]][next[1]] == state[x][y]:
                                    belong[next[0]][next[1]] = block_num
                                    q.put(next)
                                elif state[next[0]][next[1]] == -1:
                                    block_qi[-1] += 1
                    block_num += 1
                if state[x][y] != -1:
                    qi[x][y] = block_qi[belong[x][y]]
        return qi
        
    def vaildAction(self, action):
        if not super().vaildAction(action):
            return False
        coord, player_id = action['coord'], action['player_id']
        if not self.state[coord[0]][coord[1]] == -1:
            return False
        self.state[coord[0]][coord[1]] = player_id
        self.qi = self.calcQi(self.state)
        self.state[coord[0]][coord[1]] = -1
        if self.qi[coord[0]][coord[1]] == 0:
            remove = False
            for dir in DIRECTION_4:
                next = coord + dir
                if self.vaildCoordinate(next) and self.state[next[0]][next[1]] == (player_id^1) and self.qi[next[0]][next[1]] == 0:
                    remove = True
            if remove == False:
                return False
        return True
    
    def step(self, action):
        coord, player_id = action['coord'], action['player_id']
        if player_id != self.turn:
            return False, "Not the turn of player {}".format(player_id)
        
        self.skip_time += 1
        
        if action['coord'][0] == -1:
            self.turn ^= 1
            return True, "Successfully"
        
        if not self.vaildAction(action):
            return False, "Invaild action"

        self.state[coord[0]][coord[1]] = player_id
        self.turn ^= 1
        self.skip_time = 0
        for x in range(self.height):
            for y in range(self.width):
                if self.state[x][y] == (player_id^1) and self.qi[x][y] == 0:
                    self.state[x][y] = -1
        return True, "Successfully"
    
    def judgeFinish(self):
        state = self.state
        assert(np.min(state) >= -1)
        assert(np.max(state) <= 2)
        
        win = [False, False]
        q = queue.Queue()
        belong = np.copy(state)
        
        for x in range(self.height):
            for y in range(self.width):
                if self.state[x][y] > -1:
                    q.put(np.array([x,y]))
        while not q.empty():
            pos = q.get()
            for dir in DIRECTION_4:
                next_pos = pos + dir
                if self.vaildCoordinate(next_pos) and belong[next_pos[0]][next_pos[1]]==-1:
                    belong[next_pos[0]][next_pos[1]] = belong[pos[0]][pos[1]]
                    q.put(next_pos)
        score = [np.sum(belong == pid) for pid in [0, 1]]
        done = self.skip_time >= 2
        return done, int(score[1] > score[0])
                    

class ReversiRule(BaseRule):
    def reset(self):
        self.state = (np.zeros(self.shape, dtype=np.int8)-1).tolist()
        self.state[self.height//2][self.width//2] = 0
        self.state[self.height//2-1][self.width//2-1] = 0
        self.state[self.height//2][self.width//2-1] = 1
        self.state[self.height//2-1][self.width//2] = 1
        self.turn = 0
        self.skip_time = 0
    
    
    def vaildAction(self, coord):
        action = {
            'coord': coord,
            'player_id': self.turn
        }
        if not super().vaildAction(action) or not self.state[coord[0]][coord[1]] == -1:
            return False
        
        tmp_game = deepcopy(self)
        res, _ = tmp_game.step(action)
        return res
    
    def step(self, action):
        coord, player_id = action['coord'], action['player_id']
        if player_id != self.turn:
            return False, "Not the turn of player {}".format(player_id)
        
        if action['coord'][0] == -1:
            self.turn ^= 1
            return True, "Successfully"
        
        if not super().vaildAction(action):
            return False, "Invaild action"
        
        if not self.state[coord[0]][coord[1]] == -1:
            return False, "Invaild action"

        nof_trunover = 0
        for dir in DIRECTION_8:
            pos = np.array(coord)
            while self.vaildCoordinate(pos + dir):
                pos = pos + dir
                if self.state[pos[0]][pos[1]] == -1:
                    break
                elif self.state[pos[0]][pos[1]] == player_id:
                    pos -= dir
                    while pos[0]!=coord[0] or pos[1]!=coord[1]:
                        self.state[pos[0]][pos[1]] = player_id
                        pos -= dir
                        nof_trunover += 1
                    break
        if nof_trunover == 0:
            return False, "Invaild action"
        
        self.state[coord[0]][coord[1]] = player_id
        self.turn ^= 1
        return True, "Successfully"
    
    def judgeFinish(self):
        score = [np.sum(np.array(self.state) == pid) for pid in [0, 1]]
        done = False
        for i in [-1, 0, 1]:
            if np.sum(np.array(self.state) == i) == 0:
                done = True
        return done, int(score[1] > score[0])

    def getScore(self, turn=None):
        score = [np.sum(np.array(self.state) == pid) for pid in [0, 1]]
        if turn is None:
            return score
        else:
            return score[turn] - score[turn^1]
        
class RuleFactory:
    def create(gameType, *argv):
        if gameType == 'Gobang':
            return GobangRule(*argv)
        elif gameType == 'Go':
            return GoRule(*argv)
        elif gameType == 'Reversi':
            return ReversiRule(*argv)
        else:
            raise ValueError("Invaild product name.")