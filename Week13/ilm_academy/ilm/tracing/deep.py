"""Deep knowledge tracing models: DKT (Piech et al., 2015) and SAKT (Pandey & Karypis, 2019).

Both read a student's answers as a sequence of tokens. Token = (skill, right/wrong).
At step t the model has seen tokens 1..t-1 (a START token comes first), and is asked
"will the answer on skill q_t be right?". The answer at step t is NOT in its input, which
is what tests/test_tracing.py checks with the future-blind test.

  DKT   an LSTM keeps a running summary ("memory") of everything so far.
  SAKT  attention: for the current question, weigh the past answers that matter most.

Training: Adam, binary cross-entropy, early stopping on VALIDATION AUC (never test).
Long histories are cut into windows of MAX_LEN for training. For prediction, DKT reads the
whole history; SAKT uses overlapping windows so every prediction has at least half a
window of history (except a student's first answers, which have less history anyway).
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import torch
from torch import nn

from ilm import config
from ilm.tracing.evaluate import metrics

MAX_LEN = 200
PAD = 0


class _DKTNet(nn.Module):
    def __init__(self, n_tokens, n_skills, dim):
        super().__init__()
        self.emb = nn.Embedding(n_tokens, dim, padding_idx=PAD)
        self.lstm = nn.LSTM(dim, dim, batch_first=True)
        self.drop = nn.Dropout(0.2)
        self.out = nn.Linear(dim, n_skills)

    def forward(self, tokens, queries):
        h, _ = self.lstm(self.emb(tokens))
        logits = self.out(self.drop(h))                       # one logit per skill
        return logits.gather(2, queries.unsqueeze(-1)).squeeze(-1)


class _SAKTNet(nn.Module):
    def __init__(self, n_tokens, n_skills, dim, heads=4):
        super().__init__()
        self.emb = nn.Embedding(n_tokens, dim, padding_idx=PAD)
        self.pos = nn.Embedding(MAX_LEN, dim)
        self.query = nn.Embedding(n_skills, dim)
        self.attn = nn.MultiheadAttention(dim, heads, dropout=0.2, batch_first=True)
        self.norm1, self.norm2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
        self.ffn = nn.Sequential(nn.Linear(dim, dim), nn.ReLU(), nn.Dropout(0.2), nn.Linear(dim, dim))
        self.out = nn.Linear(dim, 1)

    def forward(self, tokens, queries):
        L = tokens.shape[1]
        pos = torch.arange(L, device=tokens.device)
        kv = self.emb(tokens) + self.pos(pos)
        q = self.query(queries)
        # position t may look at tokens 0..t (START + answers before t), never later
        causal = torch.triu(torch.ones(L, L, dtype=torch.bool, device=tokens.device), diagonal=1)
        a, _ = self.attn(q, kv, kv, attn_mask=causal)
        x = self.norm1(a + q)
        x = self.norm2(x + self.ffn(x))
        return self.out(x).squeeze(-1)


class DeepKT:
    def __init__(self, arch: str = "dkt", dim: int = 64, epochs: int = 20, lr: float = 1e-3,
                 batch_size: int = 64, patience: int = 3, seed: int = config.RANDOM_SEED):
        assert arch in ("dkt", "sakt")
        self.arch, self.dim, self.epochs, self.lr = arch, dim, epochs, lr
        self.batch_size, self.patience, self.seed = batch_size, patience, seed
        self.name = f"{arch.upper()} (dim={dim})"
        self.history: list[dict] = []

    # ---------------------------------------------------------------- encoding ----
    def _skill_ids(self, df):
        return df["skill"].astype(str).map(self.index).fillna(0).astype(int).to_numpy()  # 0 = unseen

    def _sequences(self, df):
        """Per student: (skill ids, answers, row positions in df)."""
        skills, answers = self._skill_ids(df), df["correct"].to_numpy()
        users = df["user_id"].to_numpy()
        cuts = np.flatnonzero(users[1:] != users[:-1]) + 1
        bounds = zip(np.r_[0, cuts], np.r_[cuts, len(df)])
        return [(skills[a:b], answers[a:b], np.arange(a, b)) for a, b in bounds]

    def _tokens(self, skills, answers):
        """Input at step t = token of answer t-1; token = 2 + skill*2 + correct; 1 = START."""
        toks = 2 + skills * 2 + answers
        return np.r_[1, toks[:-1]]

    def _windows(self, seqs, stride):
        """Cut sequences into windows of <= MAX_LEN. Returns (tokens, queries, targets, rows, keep)
        where keep marks the positions this window is responsible for predicting."""
        out = []
        for skills, answers, rows in seqs:
            toks = self._tokens(skills, answers)
            n = len(skills)
            starts = [0] if n <= MAX_LEN else list(range(0, n - MAX_LEN, stride)) + [n - MAX_LEN]
            done = 0
            for s in starts:
                e = min(s + MAX_LEN, n)
                keep = np.zeros(e - s, bool)
                keep[max(done, s) - s:] = True
                # toks is already shifted, so a window starting at s begins with answer s-1
                out.append((toks[s:e], skills[s:e], answers[s:e], rows[s:e], keep))
                done = e
        return out

    @staticmethod
    def _batch(windows):
        L = max(len(w[0]) for w in windows)
        def pad(i, dtype):
            arr = np.zeros((len(windows), L), dtype)
            for j, w in enumerate(windows):
                arr[j, :len(w[i])] = w[i]
            return arr
        mask = pad(4, bool)
        return (torch.tensor(pad(0, np.int64)), torch.tensor(pad(1, np.int64)),
                torch.tensor(pad(2, np.float32)), mask)

    # ---------------------------------------------------------------- train / predict ----
    def fit(self, train, valid=None):
        torch.manual_seed(self.seed)
        rng = np.random.default_rng(self.seed)
        self.index = {s: i + 1 for i, s in enumerate(sorted(train["skill"].astype(str).unique()))}
        n_skills = len(self.index) + 1
        n_tokens = 2 + n_skills * 2
        Net = _DKTNet if self.arch == "dkt" else _SAKTNet
        self.net = Net(n_tokens, n_skills, self.dim)
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        loss_fn = nn.BCEWithLogitsLoss()
        windows = self._windows(self._sequences(train), stride=MAX_LEN)
        best, best_state, bad = -1.0, None, 0
        for epoch in range(self.epochs):
            self.net.train()
            order = rng.permutation(len(windows))
            for i in range(0, len(order), self.batch_size):
                toks, qs, ys, mask = self._batch([windows[j] for j in order[i:i + self.batch_size]])
                logits = self.net(toks, qs)
                m = torch.tensor(mask)
                loss = loss_fn(logits[m], ys[m])
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
                opt.step()
            if valid is None:
                continue
            auc = metrics(valid["correct"], self.predict(valid))["auc"]
            self.history.append({"epoch": epoch + 1, "valid_auc": auc})
            if auc > best:
                best, best_state, bad = auc, copy.deepcopy(self.net.state_dict()), 0
            else:
                bad += 1
                if bad >= self.patience:
                    break
        if best_state is not None:
            self.net.load_state_dict(best_state)
        return self

    @torch.no_grad()
    def predict(self, df):
        self.net.eval()
        seqs = self._sequences(df)
        out = np.zeros(len(df))
        if self.arch == "dkt":   # an LSTM can read the whole history at once
            for skills, answers, rows in seqs:
                toks = torch.tensor(self._tokens(skills, answers))[None]
                out[rows] = torch.sigmoid(self.net(toks, torch.tensor(skills)[None]))[0].numpy()
            return out
        windows = self._windows(seqs, stride=MAX_LEN // 2)
        for i in range(0, len(windows), 256):
            chunk = windows[i:i + 256]
            toks, qs, _, _ = self._batch(chunk)
            p = torch.sigmoid(self.net(toks, qs)).numpy()
            for j, w in enumerate(chunk):
                n = len(w[0])
                out[w[3][w[4]]] = p[j, :n][w[4]]
        return out
