from unityagents import UnityEnvironment

import numpy as np
from collections import deque

import torch
import torch.optim as optim


DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# environment configuration
env = UnityEnvironment(file_name="../Environments/Soccer_Windows_x86_64/Soccer.exe", no_graphics=False, seed=1)

# print the brain names
print(env.brain_names)

# set the goalie brain
g_brain_name = env.brain_names[0]
g_brain = env.brains[g_brain_name]

# set the striker brain
s_brain_name = env.brain_names[1]
s_brain = env.brains[s_brain_name]


# reset the environment
env_info = env.reset(train_mode=True)

# number of agents 
n_goalie_agents = len(env_info[g_brain_name].agents)
print('Number of goalie agents:', n_goalie_agents)
n_striker_agents = len(env_info[s_brain_name].agents)
print('Number of striker agents:', n_striker_agents)

# number of actions
goalie_action_size = g_brain.vector_action_space_size
print('Number of goalie actions:', goalie_action_size)
striker_action_size = s_brain.vector_action_space_size
print('Number of striker actions:', striker_action_size)

# examine the state space 
goalie_states = env_info[g_brain_name].vector_observations
goalie_state_size = goalie_states.shape[1]
print('There are {} goalie agents. Each receives a state with length: {}'.format(goalie_states.shape[0], goalie_state_size))
striker_states = env_info[s_brain_name].vector_observations
striker_state_size = striker_states.shape[1]
print('There are {} striker agents. Each receives a state with length: {}'.format(striker_states.shape[0], striker_state_size))


# Actors
GOALIE_0_KEY = 0
STRIKER_0_KEY = 0
GOALIE_1_KEY = 1
STRIKER_1_KEY = 1

def ppo_train():
    n_episodes = 10000
    team_0_window_score = deque(maxlen=100)
    team_0_window_score_wins = deque(maxlen=100)

    team_1_window_score = deque(maxlen=100)
    team_1_window_score_wins = deque(maxlen=100)

    draws = deque(maxlen=100)

    for episode in range(n_episodes):
        env_info = env.reset(train_mode=True)                        # reset the environment    

        goalies_states = env_info[g_brain_name].vector_observations  # get initial state (goalies)
        strikers_states = env_info[s_brain_name].vector_observations # get initial state (strikers)

        goalies_scores = np.zeros(n_goalie_agents)                   # initialize the score (goalies)
        strikers_scores = np.zeros(n_striker_agents)                 # initialize the score (strikers)         

        steps = 0
        
        while True:       
            # select actions and send to environment
            action_goalie_0, log_prob_goalie_0 = goalie_0.act( goalies_states[goalie_0.KEY] )
            action_striker_0, log_prob_striker_0 = striker_0.act( strikers_states[striker_0.KEY] )

            # random
            action_goalie_1 = np.random.choice(goalie_action_size)
            action_striker_1 = np.random.choice(striker_action_size)


            actions_goalies = np.array( ( action_goalie_0, action_goalie_1 ) )
            actions_strikers = np.array( ( action_striker_0, action_striker_1 ) )

            actions = dict( zip( [g_brain_name, s_brain_name], [actions_goalies, actions_strikers] ) )

        
            env_info = env.step(actions)                                                
            # get next states
            goalies_next_states = env_info[g_brain_name].vector_observations         
            strikers_next_states = env_info[s_brain_name].vector_observations
            
            # get reward and update scores
            goalies_rewards = env_info[g_brain_name].rewards  
            strikers_rewards = env_info[s_brain_name].rewards
            goalies_scores += goalies_rewards
            strikers_scores += strikers_rewards
                        
            # check if episode finished
            done = np.any(env_info[g_brain_name].local_done)

            # store experiences
            goalie_0_reward = goalies_rewards[goalie_0.KEY]
            goalie_0.step( 
                goalies_states[goalie_0.KEY],
                action_goalie_0,
                log_prob_goalie_0,
                goalie_0_reward 
            )

            striker_0_reward = strikers_rewards[striker_0.KEY]
            striker_0.step(                 
                strikers_states[striker_0.KEY],              
                action_striker_0,
                log_prob_striker_0,
                striker_0_reward
            )

            # exit loop if episode finished
            if done:
                break  

            # roll over states to next time step
            goalies_states = goalies_next_states
            strikers_states = strikers_next_states

            steps += 1

        # learn
        goalie_loss = goalie_optimizer.learn(goalie_0.memory)
        striker_loss = striker_optimizer.learn(striker_0.memory)        

        goalie_actor_critic_model.checkpoint( CHECKPOINT_GOALIE )   
        striker_actor_critic_model.checkpoint( CHECKPOINT_STRIKER )    

        team_0_score = goalies_scores[goalie_0.KEY] + strikers_scores[striker_0.KEY]
        team_0_window_score.append( team_0_score )
        team_0_window_score_wins.append( 1 if team_0_score > 0 else 0)        

        team_1_score = goalies_scores[goalie_1.KEY] + strikers_scores[striker_1.KEY]
        team_1_window_score.append( team_1_score )
        team_1_window_score_wins.append( 1 if team_1_score > 0 else 0 )

        draws.append( team_0_score == team_1_score )
        
        print('Episode: {} \tSteps: \t{} \tGoalie Loss: \t {:.10f} \tStriker Loss: \t {:.10f}'.format( episode + 1, steps, goalie_loss, striker_loss ))
        print('\tRed Wins: \t{} \tScore: \t{:.5f} \tAvg: \t{:.2f}'.format( np.count_nonzero(team_0_window_score_wins), team_0_score, np.sum(team_0_window_score) ))
        print('\tBlue Wins: \t{} \tScore: \t{:.5f} \tAvg: \t{:.2f}'.format( np.count_nonzero(team_1_window_score_wins), team_1_score, np.sum(team_1_window_score) ))
        print('\tDraws: \t{}'.format( np.count_nonzero(draws) ))

        if np.count_nonzero( team_0_window_score_wins ) >= 95:
            break
    

# train the agent
ppo_train()

# test the trained agents
team_0_window_score = deque(maxlen=100)
team_0_window_score_wins = deque(maxlen=100)

team_1_window_score = deque(maxlen=100)
team_1_window_score_wins = deque(maxlen=100)

draws = deque(maxlen=100)

for episode in range(50):                                               # play game for n episodes
    env_info = env.reset(train_mode=False)                              # reset the environment    
    goalies_states = env_info[g_brain_name].vector_observations         # get initial state (goalies)
    strikers_states = env_info[s_brain_name].vector_observations        # get initial state (strikers)

    goalies_scores = np.zeros(n_goalie_agents)                          # initialize the score (goalies)
    strikers_scores = np.zeros(n_striker_agents)                        # initialize the score (strikers)

    steps = 0

    while True:
        # select actions and send to environment
        action_goalie_0, log_prob_goalie_0 = goalie_0.act( goalies_states[goalie_0.KEY] )
        action_striker_0, log_prob_striker_0 = striker_0.act( strikers_states[striker_0.KEY] )

        # action_goalie_1, log_prob_goalie_1 = goalie_1.act( goalies_states[goalie_1.KEY] )
        # action_striker_1, log_prob_striker_1 = striker_1.act( strikers_states[striker_1.KEY] )
        
        # random            
        action_goalie_1 = np.asarray( [np.random.randint(goalie_action_size)] )
        action_striker_1 = np.asarray( [np.random.randint(striker_action_size)] )


        actions_goalies = np.array( (action_goalie_0, action_goalie_1) )                                    
        actions_strikers = np.array( (action_striker_0, action_striker_1) )

        actions = dict( zip( [g_brain_name, s_brain_name], [actions_goalies, actions_strikers] ) )

    
        env_info = env.step(actions)                                                
        # get next states
        goalies_next_states = env_info[g_brain_name].vector_observations         
        strikers_next_states = env_info[s_brain_name].vector_observations
        
        # get reward and update scores
        goalies_rewards = env_info[g_brain_name].rewards  
        strikers_rewards = env_info[s_brain_name].rewards
        goalies_scores += goalies_rewards
        strikers_scores += strikers_rewards
                    
        # check if episode finished
        done = np.any(env_info[g_brain_name].local_done)

        # exit loop if episode finished
        if done:
            break  

        # roll over states to next time step
        goalies_states = goalies_next_states
        strikers_states = strikers_next_states

        steps += 1
        
    team_0_score = goalies_scores[goalie_0.KEY] + strikers_scores[striker_0.KEY]
    team_0_window_score.append( team_0_score )
    team_0_window_score_wins.append( 1 if team_0_score > 0 else 0)        

    team_1_score = goalies_scores[goalie_1.KEY] + strikers_scores[striker_1.KEY]
    team_1_window_score.append( team_1_score )
    team_1_window_score_wins.append( 1 if team_1_score > 0 else 0 )

    draws.append( team_0_score == team_1_score )
    
    print('Episode {}'.format( episode + 1 ))
    print('\tRed Wins: \t{} \tScore: \t{:.5f} \tAvg: \t{:.2f}'.format( np.count_nonzero(team_0_window_score_wins), team_0_score, np.sum(team_0_window_score) ))
    print('\tBlue Wins: \t{} \tScore: \t{:.5f} \tAvg: \t{:.2f}'.format( np.count_nonzero(team_1_window_score_wins), team_1_score, np.sum(team_1_window_score) ))
    print('\tDraws: \t{}'.format( np.count_nonzero( draws ) ))

env.close()