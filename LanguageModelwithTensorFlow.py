import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np

# Sample smart contract snippets
contract_snippets = [
    "require(msg.value > 0); balances[msg.sender] += msg.value;",
    "require(balances[msg.sender] >= _amount); (bool sent, ) = msg.sender.call{value: _amount}(\"\");",
    "require(sent, \"Failed to send Ether\"); balances[msg.sender] -= _amount;"
]

# Labels indicating vulnerability (1: vulnerable, 0: not vulnerable)
# For demonstration, let's assume the second snippet is vulnerable
labels = [0, 1, 0]

# Tokenizing contract snippets
tokenizer = Tokenizer(num_words=100, oov_token="<OOV>")
tokenizer.fit_on_texts(contract_snippets)
sequences = tokenizer.texts_to_sequences(contract_snippets)
padded_sequences = pad_sequences(sequences, maxlen=10, padding='post')

# Simplified model to classify snippets as vulnerable or not
model = tf.keras.Sequential([
    tf.keras.layers.Embedding(100, 16, input_length=10),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(6, activation='relu'),
    tf.keras.layers.Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.fit(np.array(padded_sequences), np.array(labels), epochs=10)

# Simulating prediction for a new contract snippet
new_snippet = ["(bool sent, ) = msg.sender.call{value: _amount}(\"\"); require(sent, \"Failed to send Ether\");"]
new_seq = tokenizer.texts_to_sequences(new_snippet)
new_padded = pad_sequences(new_seq, maxlen=10, padding='post')
prediction = model.predict(new_padded)

print("Vulnerability Prediction (1: vulnerable, 0: not vulnerable):", prediction[0][0])
