import matplotlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Iterable, Union, Optional, List


def plot_losses(train_losses: List[float], val_losses: Optional[List[float]] = None,
                grad: Optional[List[float]] = None, best_step: Optional[int] = None,
                ax: Optional[matplotlib.axes.Axes] = None):
    """
    plot the losses
    """
    drawn = []
    if ax is None:
        f, ax = plt.subplots()
    drawn.append(ax.scatter(range(len(train_losses)), train_losses, label="training loss"))
    if val_losses is not None:
        drawn.append(ax.scatter(range(len(val_losses)), val_losses, label="validation loss"))
    ax.set_xlabel("steps")
    ax.set_ylabel("loss")
    ax.set_yscale("log")
    if grad is not None:
        ax2 = ax.twinx()
        drawn.append(ax2.scatter(range(len(grad)), grad, marker=".", color="C2", label="gradient"))
        ax2.set_yscale("log")
        ax.set_zorder(ax2.get_zorder()+1)
        ax.set_frame_on(False)
    if best_step is not None:
        drawn.append(ax.axvline(best_step, 0, 1, color="k", label="best step"))
    ax.legend(drawn, [h.get_label() for h in drawn])


def plot_fitting(x: Iterable[float], y: Iterable[float],
                 ax: Optional[matplotlib.axes.Axes] = None,
                 label: Optional[str] = None,
                 **kwargs):
    """
    Plots the correlation between prediction and target of a regressor

    Parameters
    ----------
    x : iterable of str
        the target to predict
    y : iterable of str
        the prediction of the model
    ax : None or matplotlib.axes.Axes
        The axes to draw on. If None a new window is created.
    label : str
        The legend of the data plotted. Ignored if starts with '_'.
    **kwargs : dict
        dict of keywords passed to 'plt.scatter'
    """
    if ax is None:
        f, ax = plt.subplots(figsize=[5, 5])
    ax.scatter(x, y, label=label, **kwargs)
    points = np.concatenate([c.get_offsets() for c in ax.collections])
    inf, sup = points.min(), points.max()
    delta = sup - inf if sup != inf else 1
    sup += 0.05*delta
    inf -= 0.05*delta
    ax.plot([inf, sup], [inf, sup], color="k", zorder=0)
    ax.set_xlim([inf, sup])
    ax.set_ylim([inf, sup])
    ax.set_aspect("equal", "box")
    legend = ax.legend()
    if len(legend.texts) == 0:
        legend.remove()


def plot_bounding_boxes(bboxes: dict, ax: matplotlib.axes.Axes,
                        class_colors: dict = {}, default_color: str = "r",
                        label_class: bool = True):
    """
    plot the image with given bounding boxes

    Parameters
    ----------

    bounding_boxes : dict
        A dict containing the following keys:
        * x, y, w, h : list of int or float
            The coordinates in pixel of each bboxe corner
        * class : list of str
            The name of the class predicted for eahc bboxe
        * [bboxe confidence : list of float]
            The optional confidence of the bounding boxe
        * [class confidence : list of float]
            The optional confidence of detected classes

    ax : matplotlib.axes.Axes
        The matplotlib axes to draw on

    class_colors : dict
        A dictionary of {class: color} for the color of the boxes
        Can be any color format supported by matplotlib

    default_color : str or list
        the default color for classes that are not present in class_colors
        Can be either a string ("#ff0000", "r", ...)
        or a RGB/RGBA list ([255, 0, 0], [255, 0, 0, 255], ...)
    """
    coords = zip(bboxes["x"], bboxes["y"], bboxes["w"], bboxes["h"])
    for i, (x, y, w, h) in enumerate(coords):
        x1, x2 = x-w/2, x+w/2
        y1, y2 = y-h/2, y+h/2
        boxe_class = bboxes["class"][i]
        boxe_color = class_colors.get(boxe_class, default_color)
        rect = patches.Rectangle((x1, y1), w, h,
                                 linewidth=1, edgecolor=boxe_color,
                                 facecolor='none')
        if label_class:
            s = boxe_class
            bboxe_confidence = bboxes.get("bboxe confidence", None)
            class_confidence = bboxes.get("class confidence", None)
            if bboxe_confidence is not None and class_confidence is not None:
                confidence = class_confidence[i] * bboxe_confidence[i]
                s += f": {confidence:.1%}"
            ax.text(x1, y1, s, color=boxe_color)
        ax.add_patch(rect)
    ax.set_xticks([])
    ax.set_yticks([])


def plot_matrix(table: pd.DataFrame,
                ax: Union[None, matplotlib.axes.Axes] = None,
                vmin: Optional[float] = None, vmax: Optional[float] = None,
                cmap: str = "viridis", color_bar: bool = False,
                format: str = ".3g", write_values: bool = False,
                **kwargs):
    """
    Plots the confusion matrix between prediction and target
    of a classifier

    Parameters
    ----------
    table : pd.DataFrame
        The matrix to plot the content of
    ax : None or matplotlib.axes.Axes
        The axis to draw on. If None, a new window is created.
    vmin : float or None
        min value for the colormap
    vmax : float or None
        max value for the colormap
    cmap : str
        The name of the maplotlib colormap
    color_bar : bool
        If True add a colorbar
    write_values : bool
        If True the value of each cell is writen
    format : str
        Formating used for the values writen in cells
    **kwargs : dict
        dict of additional keyword arguments passed to ax.text when writing
        values in cells
    """
    if ax is None:
        f, ax = plt.subplots()
    inf = vmin or table.min().min()
    sup = vmax or table.max().max()
    h = ax.imshow(table.to_numpy(), interpolation="nearest",
                  cmap=cmap, vmin=inf, vmax=sup)
    ax.grid(False)
    ax.set_xticks(range(len(table.columns)))
    ax.set_xticklabels(table.columns, rotation=45)
    ax.set_yticks(range(len(table.index)))
    ax.set_yticklabels(table.index, rotation=45)
    if color_bar:
        ax.get_figure().colorbar(h)
    if write_values:
        if isinstance(cmap, str):
            cmap = getattr(plt.cm, cmap)
        array = (h.get_array() - inf)/(sup - inf + 1.0E-8)
        brightness = np.mean(cmap(array)[:, :, :3], axis=-1)
        for y, cy in enumerate(table.index):
            for x, cx in enumerate(table.columns):
                val = table.loc[cy, cx]
                color = "white" if brightness[y, x] < 0.5 else "black"
                ax.text(x, y, f"{val:{format}}", va='center', ha='center',
                        color=color, **kwargs)
