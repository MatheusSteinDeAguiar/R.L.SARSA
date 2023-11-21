import argparse
import os
import sys
import pandas as pd

if "SUMO_HOME" in os.environ:
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)
else:
    sys.exit("Please declare the environment variable 'SUMO_HOME'")

from sumo_rl import SumoEnvironment
import numpy as np

from sumo_rl.exploration.epsilon_greedy import EpsilonGreedy


class SARSAgent:
    def __init__(self, starting_state, state_space, action_space, alpha=0.5, gamma=0.95, exploration_strategy=EpsilonGreedy()):
        self.state = starting_state
        self.state_space = state_space
        self.action_space = action_space
        self.action = None
        self.alpha = alpha
        self.gamma = gamma
        self.q_table = {self.state: [0 for _ in range(action_space.n)]}
        self.exploration = exploration_strategy
        self.acc_reward = 0

    def act(self):
        self.action = self.exploration.choose(self.q_table, self.state, self.action_space)
        return self.action

    def learn(self, next_state, reward, done=False):
        if next_state not in self.q_table:
            self.q_table[next_state] = [0 for _ in range(self.action_space.n)]

        s = self.state
        s1 = next_state
        a = self.action
        a1 = self.act()  # SARSA: Choose the next action as well
        self.q_table[s][a] = self.q_table[s][a] + self.alpha * (
            reward + self.gamma * self.q_table[s1][a1] - self.q_table[s][a]
        )
        self.state = s1
        self.action = a1
        self.acc_reward += reward


if __name__ == "__main__":
    alpha = 0.1
    gamma = 0.99
    runs = 5
    episodes = 1

    env = SumoEnvironment(
        net_file="nets/4x4-Lucas/4x4.net.xml",
        route_file="nets/4x4-Lucas/4x4c1c2c1c2.rou.xml",
        use_gui=False,
        num_seconds=80000,
        min_green=5,
        delta_time=5,
    )

    for run in range(1, runs + 1):
        initial_states = env.reset()
        sarsa_agents = {
            ts: SARSAgent(
                starting_state=env.encode(initial_states[ts], ts),
                state_space=env.observation_space,
                action_space=env.action_space,
                alpha=alpha,
                gamma=gamma,
            )
            for ts in env.ts_ids
        }

        for episode in range(1, episodes + 1):
            if episode != 1:
                initial_states = env.reset()
                for ts in initial_states.keys():
                    sarsa_agents[ts].state = env.encode(initial_states[ts], ts)

            infos = []
            done = {"__all__": False}
            while not done["__all__"]:
                actions = {ts: sarsa_agents[ts].act() for ts in sarsa_agents.keys()}
                s, r, done, info = env.step(action=actions)

                for agent_id in s.keys():
                    new_state = env.encode(s[agent_id], agent_id)
                    reward = r[agent_id]
                    sarsa_agents[agent_id].learn(new_state, reward)

            env.save_csv(f"outputs/4x4/sarsa-4x4grid_run{run}", episode)

    env.close()

