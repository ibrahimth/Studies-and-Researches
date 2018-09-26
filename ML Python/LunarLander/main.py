import gym
from IPython.display import clear_output
import matplotlib.pyplot as plt
from pyvirtualdisplay import Display
import random

env = gym.make('LunarLander-v2')
env.seed(0)
print('State shape: ', env.observation_space.shape)
print('Number of actions: ', env.action_space.n)

# watch an untrained agent
for _ in range(10):
    state = env.reset()
    while True:
        action = env.action_space.sample()
        env.render(mode='rgb_array')            
        state, reward, done, _ = env.step(action)        
        # print(state, reward, done)
        if done:
            break 
        
env.close()