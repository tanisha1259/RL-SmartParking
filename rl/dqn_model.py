import pickle

import numpy as np


class DQNModel:
    """Small fully connected Q-network: input -> 128 -> 64 -> actions."""

    def __init__(self, input_size, output_size, hidden_sizes=(128, 64), seed=None):
        self.input_size = input_size
        self.output_size = output_size
        self.hidden_sizes = tuple(hidden_sizes)
        self.random = np.random.default_rng(seed)
        layer_sizes = (input_size, *self.hidden_sizes, output_size)
        self.weights = []
        self.biases = []

        for fan_in, fan_out in zip(layer_sizes[:-1], layer_sizes[1:]):
            scale = np.sqrt(2.0 / max(1, fan_in))
            self.weights.append(self.random.normal(0, scale, size=(fan_in, fan_out)))
            self.biases.append(np.zeros(fan_out))

    def predict(self, state):
        activation = np.asarray(state, dtype=float)
        for index, (weights, bias) in enumerate(zip(self.weights, self.biases)):
            activation = activation @ weights + bias
            if index < len(self.weights) - 1:
                activation = np.maximum(activation, 0)
        return activation

    def train_step(self, states, target_q_values, learning_rate):
        states = np.asarray(states, dtype=float)
        targets = np.asarray(target_q_values, dtype=float)

        activations = [states]
        pre_activations = []
        activation = states

        for index, (weights, bias) in enumerate(zip(self.weights, self.biases)):
            z_value = activation @ weights + bias
            pre_activations.append(z_value)
            activation = np.maximum(z_value, 0) if index < len(self.weights) - 1 else z_value
            activations.append(activation)

        batch_size = max(1, states.shape[0])
        gradient = (activations[-1] - targets) / batch_size
        loss = float(np.mean((activations[-1] - targets) ** 2))

        for index in reversed(range(len(self.weights))):
            grad_weights = activations[index].T @ gradient
            grad_bias = gradient.sum(axis=0)

            if index > 0:
                previous_gradient = gradient @ self.weights[index].T
                gradient = previous_gradient * (pre_activations[index - 1] > 0)

            self.weights[index] -= learning_rate * grad_weights
            self.biases[index] -= learning_rate * grad_bias

        return loss

    def copy_from(self, other):
        self.weights = [weights.copy() for weights in other.weights]
        self.biases = [bias.copy() for bias in other.biases]

    def export_policy(self, metadata=None):
        return {
            "type": "dqn_numpy",
            "input_size": self.input_size,
            "output_size": self.output_size,
            "hidden_sizes": self.hidden_sizes,
            "weights": self.weights,
            "biases": self.biases,
            "metadata": metadata or {},
        }

    @classmethod
    def from_policy(cls, policy):
        model = cls(
            input_size=policy["input_size"],
            output_size=policy["output_size"],
            hidden_sizes=tuple(policy.get("hidden_sizes", (128, 64))),
        )
        model.weights = [np.asarray(weights, dtype=float) for weights in policy["weights"]]
        model.biases = [np.asarray(bias, dtype=float) for bias in policy["biases"]]
        return model


def load_dqn_policy(policy_path):
    with open(policy_path, "rb") as file:
        policy = pickle.load(file)
    if not isinstance(policy, dict) or policy.get("type") != "dqn_numpy":
        raise ValueError(f"{policy_path} is not a DQN policy")
    return DQNModel.from_policy(policy), policy.get("metadata", {})
