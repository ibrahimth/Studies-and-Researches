import numpy as np
from collections import deque
import random

class PrioritizedMemory():
    def __init__(self, buffer_size, batch_size):
        self.BUFFER_SIZE = buffer_size
        self.BATCH_SIZE = batch_size

        self.memory = {}
        self.priorities = {}

        self.memory = deque(maxlen=buffer_size)
        self.priorities = deque(maxlen=buffer_size)
        
    def add(self, state, hx, cx, action, reward, next_state, nhx, ncx, done):
        """Add a new experience to memory."""
        e = {
            "state" : state,
            "hx" : hx,
            "cx" : cx,
            "action" : action,
            "reward" : reward,
            "next_state" : next_state,
            "nhx" : nhx,
            "ncx" : ncx,
            "done" : done,
        }

        self.memory.append(e)
        self.priorities.append(max(self.priorities, default=1))
        
    def _get_probabilities(self, priority_scale):
        scaled_priorities = np.array(self.priorities) ** priority_scale
        sample_probabilities = scaled_priorities / sum(scaled_priorities)

        return sample_probabilities
    
    def _get_importance(self, probabilities):
        importance = 1/len(self.memory) * 1/probabilities
        importance_normalized = importance / max(importance)

        return importance_normalized
        
    def enougth_samples(self):
        return len( self.memory ) >= self.BATCH_SIZE

    def sample(self, priority_scale=1.0):
        # sample_size = min(len(self.memory), self.BATCH_SIZE)
        sample_probs = self._get_probabilities(priority_scale)
        sample_indices = random.choices( range( len(self.memory) ), k=self.BATCH_SIZE, weights=sample_probs)
        samples = np.array( self.memory )[sample_indices]
        importance = self._get_importance( sample_probs[sample_indices] )

        states       = []
        hxs          = []
        cxs          = []
        actions      = []
        rewards      = []
        next_states  = []
        nhxs         = []
        ncxs         = []
        dones        = []

        for exp in samples:                        
            states.append     ( exp['state']      )
            hxs.append        ( exp['hx']         )
            cxs.append        ( exp['cx']         )
            actions.append    ( exp['action']     )
            rewards.append    ( exp['reward']     )
            next_states.append( exp['next_state'] )
            nhxs.append       ( exp['nhx']        )
            ncxs.append       ( exp['ncx']        )
            dones.append      ( exp['done']       )

        states       = np.array(states)
        hxs          = np.array(hxs)
        cxs          = np.array(cxs)
        actions      = np.array(actions)
        rewards      = np.array(rewards)
        next_states  = np.array(next_states)
        nhxs         = np.array(nhxs)
        ncxs         = np.array(ncxs)
        dones        = np.array(dones)
        importance   = np.array(importance)

        return states, hxs, cxs, actions, rewards, next_states, nhxs, ncxs, dones, importance, sample_indices
    
    def set_priorities(self, indices, errors, offset=0.1):
        for i, e in zip(indices, errors):
            self.priorities[i] = abs(e) + offset