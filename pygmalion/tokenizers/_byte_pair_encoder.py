from typing import Any, Tuple, List, Iterable, Optional, Dict, Union
from collections import Counter
from unidecode import unidecode
from warnings import warn
from ._utilities import SpecialToken, zip_pairs, split_wordpiece, BytesTree
from pygmalion._model_base import ModelBase


class BytePairEncoder(ModelBase):

    @classmethod
    def from_dump(cls, dump: dict) -> "BytePairEncoder":
        assert dump["type"] == cls.__name__
        kwargs = dict(dump)
        kwargs.pop("type")
        code = {int(k): v for k, v in kwargs.pop("code").items()}
        return cls(code=code, **kwargs)

    def __init__(self, code: Dict[int, Tuple[int, ...]] = {i: [i] for i in range(256)},
                 dropout: Optional[float] = None, ascii: bool = False,
                 lowercase: bool = False, special_tokens: Iterable[str] = ["START", "PAD", "END"]):
        """
        Build a BytePairEncoder tokenizer

        Parameters
        ----------
        code : dict of {int: tuple of int}
            a dict of {token: subtokens} token pair merges
        dropout : float or None
            either None (no dropout used) or a float between 0 and 1
            the dropout is the probability of a byte pair merge to be skipped
            during encoding
        ascii : bool
            If True, the text is converted to ascii before tokenizing.
            Warning: if True, the decoded encoded result is not necesserly
            equal to the input, and the number of bytes might not be preserved.
        lowercase : bool
            If True, the text is converted to lowercase before tokenizing
        special_tokens : iterable of str
            all the special tokens available with the tokenizer
        """
        self.dropout = dropout
        self._ascii = ascii
        self._lowercase = lowercase
        self.special_tokens = special_tokens
        self.code = dict(code)

    def __getattr__(self, attr):
        """
        indexes of special tokens in the vocabulary can be accessed as attributes
        """
        if attr in object.__getattribute__(self, "_special_token_names"):
            return object.__getattribute__(self, "_word_indexes")[SpecialToken(attr)]
        else:
            return object.__getattribute__(self, attr)

    def __repr__(self):
        return f"{type(self).__name__}({len(self.vocabulary)} words, dropout={self.dropout})"

    def fit(self, batch_generator: Iterable[List[str]], max_vocabulary_size: int = 5000,
            min_frequency: float = 1.0E-6, verbose: bool = True, 
            pre_tokenize: bool = False, count_duplicates: bool = False):
        """
        Trains the byte pair encoding

        Parameters
        ----------
        batch_generator : Iterable of list of str
            A generator that yields a list of strings when iterated over.
            The training stops when there is no more item to iterate over.
            For common usage, this should be an iterable that yields random
            subsamples of all the sentences in the corpus indefinitely.
        max_vocabulary_size : int
            the maximum number of tokens in the resulting vocabulary
        min_frequency : float
            the minimum frequency of each new token in the corpus to be valid
        verbose : bool
            If True, display progress
        pre_tokenize : bool
            If True, each string is splited into
            single words/numbers/punctuation with trailing white spaces in a
            wordpiece fashion. Subwords can't cross the white space boundaries.
        count_duplicates : bool
            Count occurence of each unique string in the batch to speed up the
            algorithm if some strings are repeated many times.
            Usefull if tokenizing with 'pre_tokenize=True'.
        """
        code = dict(self.code)
        word_indexes = dict(self._word_indexes)
        bytes_tree = BytesTree(bytes_tree)
        try:
            for i, batch in enumerate(batch_generator):
                if len(code) >= max_vocabulary_size:
                    if verbose:
                        print("\nmaximum number of tokens reached", end="", flush=True)
                    break
                if pre_tokenize:
                    batch = (chunk for string in batch for chunk in split_wordpiece(string))
                if count_duplicates:
                    sequences_count = Counter(batch)
                    sequences = [self.split(unique, with_dropout=True) for unique in sequences_count.keys()]
                    weights = sequences_count.values()
                else:
                    sequences = [self.split(string, with_dropout=True) for string in batch]
                    weights = None
                n_tokens = sum(len(seq) * w for seq, w in zip(sequences, weights or [1]*len(sequences)))
                pairs = self._pairs_count(sequences, weights)
                if len(pairs) == 0:
                    if verbose:
                        print("\nno more pairs to merge", end="", flush=True)
                    break
                best_pair, pair_count = max(pairs.items(), key=lambda x: x[1])
                new_token = len(code)
                new_token_frequency = pair_count / (n_tokens - pair_count)
                if new_token_frequency < min_frequency:
                    if verbose:
                        print("\nminimum token frequency reached", end="", flush=True)
                    break
                code[new_token] = [word_indexes[b] for b in best_pair]
                new_token_bytes = b"".join(best_pair)
                bytes_tree.push(new_token_bytes)
                word_indexes[new_token_bytes] = new_token
                if verbose:
                    print(f"\r\033[K\rMerge iteration {i}: "
                          f"{len(self.code)} tokens, "
                          f"new token frequency={new_token_frequency:.3g}",
                          end="", flush=True)
        except KeyboardInterrupt:
            print("\nInterupted by the user", end="")
        finally:
            print("")
        self.code = code

    def encode(self, string: str, with_dropout: bool = True,
               start_token: bool = False, end_token: bool = False,
               padded_size: Optional[int] = None) -> List[int]:
        """
        Apply the tokenization
        """
        string = [self._word_indexes[token] for token in self.split(string, with_dropout)]
        if start_token:
            string.insert(0, self.START)
        if end_token:
            string.append(self.END)
        if padded_size is not None:
            if len(string) > padded_size:
                raise ValueError(f"Cannot pad string of size {len(string)}"
                                 f" to size {padded_size}")
            string.extend([self.PAD]*(padded_size-len(string)))
        return string

    def decode(self, encoded: List[int]) -> str:
        """
        Decode a tokenized string
        """
        vocabulary = self.vocabulary
        subwords = [vocabulary[i] for i in encoded]
        decoded = b"".join(b for b in subwords if isinstance(b, bytes))
        return decoded.decode("utf-8", errors="replace")

    def split(self, string: str, with_dropout: bool = True) -> List[bytes]:
        """
        Returns the string splited token by token
        """
        if self.ascii:
            string = unidecode(string)
        if self.lowercase:
            string = string.lower()
        return self._bytes_tree.split(string.encode("utf-8"), p_dropout=self.dropout if with_dropout else None)

    @property
    def code(self) -> Dict[int: List[int]]:
        return self._code

    @code.setter
    def code(self, other):
        self._code = other
        # setting vocabulary
        code_bytes = {i: bytes([i]) for i in range(256)}
        not_represented = {i: c for i, c in self.code.items() if i not in code_bytes.keys()}
        while len(not_represented) > 0:
            tmp = {}
            for i, c in not_represented.items():
                if all(j in code_bytes.keys() for j in c):
                    code_bytes[i] = b"".join(code_bytes[j] for j in c)
                else:
                    tmp[i] = c
            not_represented = tmp
        self._vocabulary = tuple(code_bytes.values()) + self.special_tokens
        # setting word indexes
        self._word_indexes = {w: i for i, w in enumerate(self.vocabulary)}
        # setting the BytesTree
        self._bytes_tree = BytesTree(sorted(self._vocabulary, key=lambda x: len(x)))

    @property
    def vocabulary(self) -> Tuple[Union[bytes, SpecialToken], ...]:
        return self._vocabulary

    @property
    def special_tokens(self) -> Tuple[SpecialToken, ...]:
        return tuple(SpecialToken(name) for name in self._special_token_names)

    @special_tokens.setter
    def special_tokens(self, other: Iterable[Union[str, SpecialToken]]):
        if any(a != b for a, b in zip(self.special_tokens, other)):
            warn(f"Order of special tokens have changed.")
        self._special_token_names = tuple(token if isinstance(token, str) else token.name for token in other)
        self._vocabulary = tuple(bytes(k) for k in self.code.keys()) + self.special_tokens

    @property
    def ascii(self) -> bool:
        return self._ascii

    @property
    def lowercase(self) -> int:
        return self._lowercase

    @property
    def dump(self):
        return {"type": type(self).__name__,
                "code": self.code,
                "dropout": self.dropout,
                "ascii": self.ascii,
                "lowercase": self.lowercase,
                "special_tokens": self._special_token_names}

    def _bytes(self, token_index: int, code: Dict[int, Tuple[int]]) -> bytes:
        """
        returns the bytes representation of a token from a (potentially unordered) code
        """
        if token_index < 256:
            return bytes([token_index])
        else:
            return b"".join((self._bytes(t, code) for t in code[token_index]))

    @staticmethod
    def _pairs_count(sequences: List[List[bytes]],
                     weights: Optional[List[float]]) -> Counter:
        """
        returns a Counter of all pairs encountered in the tokens sequences
        """
        if weights is None:
            return Counter(pair for sequence in sequences for pair in zip_pairs(sequence))
        else:
            counter = Counter()
            for weight, sequence in zip(weights, sequences):
                for pair in zip_pairs(sequence):
                    counter[pair] += weight
            return counter
