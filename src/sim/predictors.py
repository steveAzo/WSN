"""Univariate predictors for trace-driven dual-prediction (DPS) simulation.

Synchronisation contract (Santini & Romer 2006, paper 24):
  * every predictor is driven ONLY by values the server also knows: the true value when it
    was reported, otherwise the predictor's own prediction ("reconstructed history").
    Node and server therefore hold identical predictor state by construction.
  * information that the node computes from its private true readings and that the server
    needs (DBP's slope) is carried inside the report (cost: a few bytes, same report count).
  * at a data gap (new segment) short-term history is cleared; learned parameters (LMS
    weights, Ridge/RLS coefficients) persist, as they would on a real device.

Interface used by the engine (per parameter):
    predict()                    -> prediction for the current step
    observe(v, reported, node)   -> advance one step; v = server-known value
                                    node = NodeView with the node's private true history
    force_report()               -> True if the method itself demands a report (LMS normal mode)
    reset_history()              -> called at segment start
"""
from collections import deque

import numpy as np


class NodeView:
    """The node's private information: its true readings (never seen by the server)."""

    def __init__(self, maxlen=64):
        self.true = deque(maxlen=maxlen)

    def push(self, x):
        self.true.append(x)

    def clear(self):
        self.true.clear()


class Ring:
    """Fixed-size history of server-known values (fast, no allocations per step)."""

    def __init__(self, n):
        self.buf = np.zeros(n); self.n = n; self.count = 0

    def push(self, v):
        self.buf[:-1] = self.buf[1:]; self.buf[-1] = v; self.count += 1

    def full(self):
        return self.count >= self.n

    def last(self):
        return self.buf[-1]

    def clear(self):
        self.buf[:] = 0.0; self.count = 0


class LastValue:
    """Constant predictor = send-on-delta (Aderohunmu 2013 found it the best trade-off)."""
    name = "SOD"
    self_sync = True        # its whole state is the last value: any received report resyncs it

    def __init__(self, **_):
        self.v = None

    def predict(self):
        return self.v

    def observe(self, v, reported, node):
        self.v = v

    def force_report(self):
        return False

    def reset_history(self):
        self.v = None

    def prime(self, v):
        """resync: start from value v (both sides know it from the resync report)"""
        self.v = v


class LMS:
    """Santini & Romer (2006) LMS dual prediction, faithful to their Sect. III-D.

    * N-tap LMS on the last N server-known values; w[0] = 0 (identical on node and sink).
    * step size mu = 1/(100 * E_x)  ("two orders of magnitude smaller than" the bound 1/E_x),
      E_x = mean input power estimated on the training period.
    * NORMAL mode: every reading is reported and the weights adapt; after N consecutive
      predictions within e_max the node enters STAND-ALONE mode: readings within e_max are
      suppressed, the prediction is fed back (error 0, weights frozen). An exceedance is
      reported and returns the node to normal mode.
    """
    name = "LMS"

    def __init__(self, N=4, Ex=1.0, emax=None, **_):
        self.N, self.mu, self.emax = N, 1.0 / (100.0 * Ex), emax
        self.w = np.zeros(N); self.h = Ring(N)
        self.normal, self.ok_run, self._xhat = True, 0, None

    def predict(self):
        if not self.h.full():
            self._xhat = self.h.last() if self.h.count else None
        else:
            self._xhat = float(self.w @ self.h.buf[::-1])
        return self._xhat

    def observe(self, v, reported, node):
        if self.h.full() and reported and self._xhat is not None:
            e = v - self._xhat                                   # true error (value was sent)
            self.w += self.mu * e * self.h.buf[::-1]
            if self.normal:
                self.ok_run = self.ok_run + 1 if abs(e) <= self.emax else 0
                if self.ok_run >= self.N:
                    self.normal = False
            else:
                self.normal, self.ok_run = True, 0               # exceedance in stand-alone
        self.h.push(v)

    def force_report(self):
        return self.normal

    def reset_history(self):
        self.h.clear(); self.normal, self.ok_run = True, 0


class DBP:
    """Raza et al. (2015) Derivative-Based Prediction, time tolerance eps_T = 0 (bounded).

    Model = (anchor value, slope); prediction = anchor + slope * steps_since_anchor.
    On an exceedance the node rebuilds the model from its buffer of the last m TRUE readings:
    slope = (mean of last l - mean of first l) / (m - l); anchor = current true reading.
    The new (anchor, slope) travels in the report, so the server stays in sync.
    """
    name = "DBP"

    def __init__(self, m=6, l=3, **_):
        self.m, self.l = m, min(l, max(1, m // 2))
        self.a, self.s, self.k = None, 0.0, 0

    def predict(self):
        return None if self.a is None else self.a + self.s * self.k

    def observe(self, v, reported, node):
        if reported:
            buf = list(node.true)[-self.m:]                      # node-private true readings
            if len(buf) >= 2 * self.l:
                n = len(buf)
                self.s = (np.mean(buf[-self.l:]) - np.mean(buf[:self.l])) / (n - self.l)
            else:
                self.s = 0.0
            self.a, self.k = v, 1
        else:
            self.k += 1

    def force_report(self):
        return False

    def reset_history(self):
        self.a, self.s, self.k = None, 0.0, 0


class Ridge:
    """Kangethe et al. (2026) ADAPTIVEML predictor: Ridge on the last w values.

    Fitted ONCE on the training period (standardised inputs, lambda = 1.0, eq. 3), then frozen.
    Falls back to last value until w server-known values exist after a gap.
    """
    name = "RIDGE"

    def __init__(self, w=24, lam=1.0, train=None, **_):
        """train: list of 1-D arrays, one per contiguous training segment (windows never
        span a data gap)."""
        self.w, self.h = w, Ring(w)
        segs = [np.asarray(s, float) for s in train if len(s) > w + 1]
        allx = np.concatenate(segs)
        self.mu, self.sd = float(np.mean(allx)), float(np.std(allx)) or 1.0
        Xs, ys = [], []
        for s in segs:
            z = (s - self.mu) / self.sd
            Xs.append(np.lib.stride_tricks.sliding_window_view(z[:-1], w)); ys.append(z[w:])
        X, y = np.vstack(Xs), np.concatenate(ys)
        self.beta = np.linalg.solve(X.T @ X + lam * np.eye(w), X.T @ y)

    def _z(self):
        return (self.h.buf - self.mu) / self.sd

    def predict(self):
        if not self.h.full():
            return self.h.last() if self.h.count else None
        return float(self._z() @ self.beta) * self.sd + self.mu

    def observe(self, v, reported, node):
        self.h.push(v)

    def force_report(self):
        return False

    def reset_history(self):
        self.h.clear()

    def prime(self, v):
        """resync: history filled with the resync report's value, so it predicts at once"""
        self.h.buf[:] = v; self.h.count = self.h.n


class RLS(Ridge):
    """ADAPTIVEML-RLS (paper 17, Alg. 1): Ridge warm start + exponentially weighted RLS.

    gamma = 0.98, P0 = rho*I with rho = 10 (paper defaults).
    Adaptation for a synchronised DPS: the paper updates every step with the node's TRUE
    reading, which the server does not have. Updating with the fed-back prediction instead
    gives e = 0 but P = P/gamma keeps growing on near-identical inputs ("covariance windup");
    in our first test this overflowed to NaN. We therefore update ONLY on reported steps,
    exactly as Santini freezes LMS weights in stand-alone mode. Both sides know which steps
    were reported, so node and server stay identical.
    Windup still occurred on calm / coarsely quantised stretches (near-identical regressors,
    poor excitation), so we add the standard covariance-bounding safeguard of adaptive
    control: trace(P) is capped at its initial value rho*w. (Reference to verify before
    citing: Astrom & Wittenmark, Adaptive Control.) TODO-CITE
    """
    name = "RLS"

    def __init__(self, w=24, lam=1.0, train=None, gamma=0.98, rho=10.0, update="reported", **_):
        super().__init__(w=w, lam=lam, train=train)
        self.update = update                                   # "reported" | "every"
        self.gamma, self.rho, self.P = gamma, rho, rho * np.eye(w)
        self._zin = None

    def predict(self):
        if not self.h.full():
            self._zin = None
            return self.h.last() if self.h.count else None
        self._zin = self._z().copy()
        return float(self._zin @ self.beta) * self.sd + self.mu

    def observe(self, v, reported, node):
        if self._zin is not None and (reported or self.update == "every"):
            z = self._zin
            e = (v - self.mu) / self.sd - float(z @ self.beta)
            Pz = self.P @ z
            K = Pz / (self.gamma + float(z @ Pz))
            self.beta = self.beta + K * e
            self.P = (self.P - np.outer(K, Pz)) / self.gamma
            tr, cap = np.trace(self.P), self.rho * self.w
            if tr > cap:                                       # covariance bounding (anti-windup)
                self.P *= cap / tr
        self.h.push(v)


class RLSDelta:
    """Phase 3: RLS on CHANGES, shrunk towards persistence ("RLS-D").

    prediction = last server-known value + d_hat, where d_hat is a linear function of the last
    w server-known changes (standardised), Ridge warm start on training changes, then
    exponentially weighted RLS updated on reported steps (as RLS). The ridge penalty shrinks d_hat
    towards 0, i.e. towards send-on-delta, so on unpredictable series it degrades gracefully to
    SOD instead of pulling predictions towards the training mean (the level model's weakness on
    drifting, noise-dominated series; Phase 3 diagnosis 2026-10-03).
    """
    name = "RLS-D"

    def __init__(self, w=24, lam=1.0, train=None, gamma=0.999, rho=10.0, phi=1.0, repair=False,
                 adapt=True, **_):
        """phi < 1: damped trend (Gardner & McKenzie 1985, TODO-CITE verify): the predicted
        change is multiplied by phi**k, k = steps since the last REPORTED value (known to both
        sides), so long blind stretches fade to "hold" instead of extrapolating.
        repair: when a report ends a blind stretch of k steps, the k predicted values in the
        history are replaced by the straight line from the previous reported value r0 to the
        new one (deterministic from server-known data, so both sides do it). Without this the
        correction jump (> delta by construction) enters the history as a fake fast change
        and the change model extrapolates it as momentum.
        rho: initial covariance scale. rho = 0.01 (slow adaptation, trusts the warm start) is the
        proposed setting ("RLS-D"): same or fewer reports than the paper default rho = 10 without
        loss, and no large-gain transient after a resync (rho = 10 doubled the reports under
        heartbeat resync at zero loss, 2026-10-03).
        adapt=False: weights frozen after the warm start ("RIDGE-D"). Up to ~10 % more reports than
        RLS-D (InWaterSense L2), mixed elsewhere (-9..+4 %), but frozen weights cannot diverge under
        loss, so heartbeat resync costs only the heartbeats -> the variant for unconfirmed uplinks."""
        self.phi, self.k, self.repair, self.r0, self.adapt = phi, 0, repair, None, adapt
        self.w, self.h = w, Ring(w + 1)
        segs = [np.diff(np.asarray(s, float)) for s in train if len(s) > w + 2]
        alld = np.concatenate(segs)
        self.sd = float(np.std(alld)) or 1.0
        Xs, ys = [], []
        for d in segs:
            z = d / self.sd
            Xs.append(np.lib.stride_tricks.sliding_window_view(z[:-1], w)); ys.append(z[w:])
        X, y = np.vstack(Xs), np.concatenate(ys)
        self.beta = np.linalg.solve(X.T @ X + lam * np.eye(w), X.T @ y)
        self.gamma, self.rho, self.P = gamma, rho, rho * np.eye(w)
        self._zin = None

    def predict(self):
        if not self.h.full():
            self._zin = None
            return self.h.last() if self.h.count else None
        self._zin = np.diff(self.h.buf) / self.sd
        return float(self.h.last() + (self._zin @ self.beta) * self.sd * self.phi ** self.k)

    def observe(self, v, reported, node):
        if self.adapt and self._zin is not None and reported:
            z = self._zin
            e = (v - self.h.last()) / self.sd - float(z @ self.beta)
            Pz = self.P @ z
            K = Pz / (self.gamma + float(z @ Pz))
            self.beta = self.beta + K * e
            self.P = (self.P - np.outer(K, Pz)) / self.gamma
            tr, cap = np.trace(self.P), self.rho * self.w
            if tr > cap:                                       # covariance bounding (as RLS)
                self.P *= cap / tr
        if reported:
            if self.repair and self.r0 is not None and self.k > 0:
                K = self.k + 1                                 # steps from r0 to v
                for i in range(1, min(self.k, self.h.count, self.h.n) + 1):
                    self.h.buf[-i] = self.r0 + (v - self.r0) * (K - i) / K
            self.r0, self.k = v, 0
        else:
            self.k += 1
        self.h.push(v)

    def force_report(self):
        return False

    def reset_history(self):
        self.h.clear(); self.k = 0; self.r0 = None

    def prime(self, v):
        """resync: flat history at v (predicted change 0 until real changes arrive)"""
        self.h.buf[:] = v; self.h.count = self.h.n; self.k = 0; self.r0 = v


class Switch:
    """Phase 3: online, synchronised choice between two predictors.

    ACTIVE pair: synchronised copies of both predictors, driven by the server-known values on
    node and server alike; only the active one's prediction drives the report decision.
    DECISION (node only): two VIRTUAL single-predictor DPS pipelines run on the node's true
    readings, each with its own reconstruction and its own would-be reports, so each counts
    exactly how often that predictor WOULD have reported (exact counterfactual; v1 evaluated
    the shadow on the active one's reconstruction, which made a "last value" shadow track the
    RLS prediction and caused thrashing, observed 2026-10-03). Exponentially weighted report
    rates (memory `mem_days`); when the inactive one's rate is below (1 - margin) x the
    active's and >= `dwell_days` have passed, a switch flag rides in the NEXT report and both
    sides swap. The bound holds whichever predictor is active; switching only changes cost.
    make_a / make_b: zero-argument factories (4 instances each: active pair + virtual pair).
    """
    name = "SWITCH"

    def __init__(self, make_a, make_b, delta, step_min, mem_days=14.0, margin=0.2, dwell_days=7.0, start=0):
        self.P = [make_a(), make_b()]; self.V = [make_a(), make_b()]
        self.delta, self.margin = delta, margin
        spd = 24 * 60 / step_min
        self.beta, self.dwell = 1.0 / (mem_days * spd), int(dwell_days * spd)
        self.active, self.rate, self.since = start, [0.0, 0.0], 0
        self.want, self.vh, self.n_switch, self.log, self.t = False, [None, None], 0, [], 0

    def predict(self):
        self.vh = [v.predict() for v in self.V]
        ph = [p.predict() for p in self.P]                    # BOTH: RLS caches its regressor in
        return ph[self.active]                                # predict(); a skipped call desyncs it

    def observe(self, v, reported, node):
        x = node.true[-1] if node is not None and len(node.true) else None
        if x is not None:                                     # node-side virtual pipelines
            for i in (0, 1):
                exc = self.vh[i] is None or self.V[i].force_report() or abs(x - self.vh[i]) > self.delta
                self.V[i].observe(x if exc else self.vh[i], exc, node)
                self.rate[i] += self.beta * (float(exc) - self.rate[i])
        for p in self.P:
            p.observe(v, reported, node)
        self.since += 1
        o = 1 - self.active
        if self.since >= self.dwell and self.rate[o] < (1 - self.margin) * self.rate[self.active]:
            self.want = True
        if self.want and reported:                             # flag carried by this report
            self.active, self.since, self.want = o, 0, False
            self.n_switch += 1; self.log.append((self.t, o))
        self.t += 1

    def force_report(self):
        return self.P[self.active].force_report()

    def reset_history(self):
        for p in self.P + self.V:
            p.reset_history()


PREDICTORS = {"SOD": LastValue, "LMS": LMS, "DBP": DBP, "RIDGE": Ridge, "RLS": RLS}
