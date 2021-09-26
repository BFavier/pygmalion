from pygmalion.neural_networks.layers import MultiHeadAttention
import torch
import pandas as pd
import matplotlib.pyplot as plt
from timeit import timeit
import IPython


def naive_m(q, RPE, v):
    return MultiHeadAttention._naive_RPE(None, q, RPE, v, masked=True)


def naive_b(q, RPE, v):
    return MultiHeadAttention._naive_RPE(None, q, RPE, v, masked=False)


def linear_m(q, RPE, v):
    return MultiHeadAttention._linear_RPE(None, q, RPE, v, masked=True)


def linear_b(q, RPE, v):
    return MultiHeadAttention._linear_RPE(None, q, RPE, v, masked=False)


naive_masked = []
naive_bidirectional = []
linear_masked = []
linear_bidirectional = []

n_rep = 10
N, H = 1, 1
D = 256
L = [2**p for p in range(5, 14)]
R = 10
requires_grad = True
device = torch.device("cpu")
for l in L:
    print(l)
    Lq, Lk = l, l
    # vectors
    q = torch.rand((N, H, Lq, D), device=device, requires_grad=requires_grad)
    v = torch.rand((N, H, Lk, D), device=device, requires_grad=requires_grad)
    RPE = torch.rand((2*R+1, D), device=device, requires_grad=requires_grad)
    # attention functions
    _naive_m = lambda: naive_m(q, RPE, v)
    naive_masked.append(timeit(_naive_m, number=n_rep))
    _naive_b = lambda: naive_b(q, RPE, v)
    naive_bidirectional.append(timeit(_naive_b, number=n_rep))
    _linear_m = lambda: linear_m(q, RPE, v)
    linear_masked.append(timeit(_linear_m, number=n_rep))
    _linear_b = lambda: linear_b(q, RPE, v)
    linear_bidirectional.append(timeit(_linear_b, number=n_rep))


df = pd.DataFrame(data=zip(L, naive_masked, naive_bidirectional, linear_masked, linear_bidirectional),
                  columns=["sequences length", "naive masked", "naive bidirectional", "linear masked", "linear bidirectional"])
df.to_csv(r"C:\Users\Benoit\Desktop\RPE_timing.csv", index=False, encoding="utf-8")


plt.style.use("bmh")
f, ax = plt.subplots()
ax.set_title(f"RPE runtime for d={D} (best of {n_rep})")
ax.set_xscale("log", basex=2)
ax.set_yscale("log", basey=2)
ax.set_xlabel("Sequences length")
ax.set_ylabel("runtime (in seconds)")
ax.plot(L, naive_masked, color="C1", linestyle="-", label="naive masked")
ax.plot(L, naive_bidirectional, linestyle="--", color="C1", label="naive bidirectional")
ax.plot(L, linear_masked, linestyle="-", color="C2", label="naive masked")
ax.plot(L, linear_bidirectional, linestyle="--", color="C2", label="naive bidirectional")
f.tight_layout()
plt.legend()
plt.show()

IPython.embed()
