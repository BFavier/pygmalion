from ._download import download


def fashion_mnist(directory: str):
    """downloads the 'fashion MNIST' dataset in the given directory"""
    download(directory, "fashion-MNIST.npz",
             "https://drive.google.com/file/d/131TqEL3pSWKaz94g8nkDzaVgwtmEiLXu/view?usp=share_link")
