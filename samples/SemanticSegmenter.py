import pathlib
import json
import IPython
import numpy as np
import pygmalion as ml
import pygmalion.neural_networks as nn
import matplotlib.pyplot as plt
plt.style.use("bmh")
data_path = pathlib.Path(__file__).parent / "data" / "cityscapes"

# Download the data
ml.datasets.cityscapes(data_path.parent)

# Load data
with open(data_path / "class_fractions.json", "r") as file:
    fractions = json.load(file)
class_weights = {k: 1/(f+1.0E-8) for k, f in fractions.items()}
mean = sum([w for w in class_weights.values()])
class_weights = {k: w/mean for k, w in class_weights.items()}
with open(data_path / "classes.json", "r") as file:
    classes = json.load(file)
x = np.load(data_path / "train_images.npy")[::10]
y = np.load(data_path / "train_segmented.npy")[::10]
x_test = np.load(data_path / "test_images.npy")[::10]
y_test = np.load(data_path / "test_segmented.npy")[::10]

# Create and train the model
downward = [{"window": (3, 3), "features": 4},
            {"window": (3, 3), "features": 4},
            {"window": (3, 3), "features": 8},
            {"window": (3, 3), "features": 8},
            {"window": (3, 3), "features": 16},
            {"window": (3, 3), "features": 16},
            {"window": (3, 3), "features": 32},
            {"window": (3, 3), "features": 32}]
pooling = [(2, 2), (2, 2), (2, 2), (2, 2), (2, 2), (2, 2), (2, 2), (2, 2)]
upward = downward[::-1]
model = nn.SemanticSegmenter(3, classes,
                             downsampling=downward,
                             pooling=pooling,
                             upsampling=upward,
                             upsampling_method="interpolate",
                             activation="elu",
                             GPU=0)
# print(model.module.shapes)
train_data, val_data = ml.split(x, y, frac=0.2)
model.train(train_data, val_data, n_epochs=5000, batch_size=15, n_batches=1,
            learning_rate=1.0E-3, patience=100)

# Plot metrics
# model.plot_residuals()
# f, ax = plt.subplots()
# y_pred = model(x_test)
# ml.plot_confusion_matrix(y_pred, y_test, ax=ax)
# acc = ml.accuracy(y_pred, y_test)
# ax.set_title(f"Accuracy = {acc:.3g}")
# _Ftight_layout()

# Plot results
model.plot_history()
x_train, y_train = train_data
for x, y_t in zip(x_train[:5], y_train[:5]):
    y_p = model([x])[0]
    f, axes = plt.subplots(figsize=[15, 5], ncols=3)
    for im, ax, title in zip([x, y_p, y_t], axes,
                             ["image", "segmented", "target"]):
        ax.imshow(im)
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
    f.tight_layout()
plt.show()

IPython.embed()
