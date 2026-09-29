"""Small BM25 index: the retrieval fallback when the vector extra is not installed."""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set(
    "a an and are as at be by can for from has have how i in is it its my of on or that the this to was what when which with you your".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.4, b: float = 0.75):
        self.tokens = [tokenize(d) for d in docs]
        self.k1, self.b = k1, b
        self.avgdl = sum(map(len, self.tokens)) / max(1, len(self.tokens))
        df = Counter(t for toks in self.tokens for t in set(toks))
        n = len(self.tokens)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(toks) for toks in self.tokens]

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for tf, toks in zip(self.tf, self.tokens, strict=True):
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                f = tf[t]
                s += (
                    self.idf[t]
                    * f
                    * (self.k1 + 1)
                    / (f + self.k1 * (1 - self.b + self.b * len(toks) / self.avgdl))
                )
            out.append(s)
        return out
