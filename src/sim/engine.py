"""Trace-driven simulation engine for multi-parameter dual-prediction reporting.

One node samples P parameters every step. At each step it decides which parameters to send.
The server's reconstruction R[t, p] is the true value when parameter p was sent, else the
(shared, synchronised) prediction.

Report accounting modes (they isolate the effect of report-level decisions, RQ2):
  separate : every exceeding parameter is its own report  (how InWaterSense/Weija transmit)
  bundled  : exceeding parameters at the same step share one report (only they are sent)
  report   : any exceedance sends ALL parameters in one report (free riders refresh the
             other predictors) — the report-level scheme
A new segment (data gap > 60 min) forces a full report and clears predictor history.

Decision rules:
  fixed tolerance  : send p if |x - xhat| > delta_p            (bounded: max error <= delta_p)
  ADAPTIVEML       : send p if |x - xhat| > alpha * sigma_p(t) (paper 17, eq. 5; sigma = rolling
                     std of the node's last h TRUE readings; NOT bounded). Start-up case not
                     defined in the paper: with < 2 readings after a gap sigma is undefined and
                     we use sigma = 0 (i.e. report) - the conservative choice.
"""
from dataclasses import dataclass

import numpy as np

from .predictors import NodeView


@dataclass
class SimResult:
    R: np.ndarray          # server reconstruction (N, P)
    sent: np.ndarray       # parameter included in a report at step t (N, P) bool
    report: np.ndarray     # a report was transmitted at step t (N,) bool
    n_reports: np.ndarray  # number of reports counted at step t (N,) int (separate mode: >1)
    alarm: np.ndarray = None  # detector raised a new alarm for parameter p at step t (N, P)


def run_dps(X, seg_start, make_predictors, mode="report", delta=None, alpha=None, h=24,
            make_detectors=None, hour=None, tighten=None):
    """X: (N, P) true values; seg_start: (N,) bool; make_predictors: () -> list of P predictors.
    Exactly one of `delta` (array P) or `alpha` (float, ADAPTIVEML rule) must be given.
    Optional event detection (Phase 3): make_detectors() -> list of P CusumDetector, hour (N,)
    hour-of-day. A new alarm forces parameter p into the report (all of them in report mode).
    tighten (array P, <= delta): tolerance used while p's detector is in its event state."""
    assert (delta is None) != (alpha is None)
    N, P = X.shape
    preds = make_predictors()
    dets = make_detectors() if make_detectors else None
    alarm = np.zeros((N, P), bool)
    nodes = [NodeView(maxlen=max(64, h)) for _ in range(P)]
    R = np.empty_like(X); sent = np.zeros((N, P), bool)
    report = np.zeros(N, bool); n_rep = np.zeros(N, int)
    for t in range(N):
        x = X[t]
        if seg_start[t]:
            for p in range(P):
                preds[p].reset_history(); nodes[p].clear()
                if dets: dets[p].reset_history()
        if dets:
            for p in range(P):
                alarm[t, p] = dets[p].step(x[p], hour[t])
        xhat = [preds[p].predict() for p in range(P)]
        for p in range(P):
            nodes[p].push(x[p])
        if seg_start[t]:
            inc = np.ones(P, bool)
        else:
            inc = np.zeros(P, bool)
            for p in range(P):
                if xhat[p] is None or preds[p].force_report() or alarm[t, p]:
                    inc[p] = True
                    continue
                err = abs(x[p] - xhat[p])
                if delta is not None:
                    d = tighten[p] if (tighten is not None and dets and dets[p].event) else delta[p]
                    inc[p] = err > d
                else:
                    tb = np.asarray(nodes[p].true)[-(h + 1):-1]      # last h readings before t
                    sig = float(np.std(tb, ddof=1)) if len(tb) >= 2 else 0.0
                    inc[p] = err > alpha * sig
            if mode == "report" and inc.any():
                inc[:] = True
        for p in range(P):
            if inc[p]:
                R[t, p] = x[p]; preds[p].observe(x[p], True, nodes[p])
            else:
                R[t, p] = xhat[p]; preds[p].observe(xhat[p], False, nodes[p])
        sent[t] = inc
        report[t] = inc.any()
        n_rep[t] = inc.sum() if mode == "separate" else int(inc.any())
    return SimResult(R, sent, report, n_rep, alarm)


def run_periodic(X, seg_start, k=1):
    """Report every k-th step within each segment; server holds the last value (ZOH)."""
    N, P = X.shape
    R = np.empty_like(X); report = np.zeros(N, bool); j = 0
    for t in range(N):
        if seg_start[t]:
            j = 0
        if j % k == 0:
            report[t] = True; last = X[t].copy()
        R[t] = last; j += 1
    sent = np.repeat(report[:, None], P, axis=1)
    return SimResult(R, sent, report, report.astype(int))


def run_batch(X, seg_start, k):
    """Ghosh-style batching: buffer k samples and send them in one report (exact data,
    delivered late). Returns the result plus per-sample delivery delay in steps."""
    N, P = X.shape
    report = np.zeros(N, bool); delay = np.zeros(N, int)
    seg_id = np.cumsum(seg_start)
    starts = np.flatnonzero(seg_start)
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else N
        for b in range(s, e, k):
            last = min(b + k, e) - 1
            report[last] = True
            delay[b:last + 1] = last - np.arange(b, last + 1)
    sent = np.repeat(report[:, None], P, axis=1)
    return SimResult(X.copy(), sent, report, report.astype(int)), delay


def run_dps_lossy(X, seg_start, make_predictors, delta, loss_p, protocol="ack", retries=2,
                  hb_steps=None, seed=0, ack_loss=0.0):
    """Report-level bounded DPS over a lossy uplink. Node and server hold SEPARATE predictor
    copies (built by the same deterministic factory).

    protocol "ack" (confirmed uplink): each attempt is lost with prob loss_p; up to `retries`
      retransmissions. If all attempts fail the node KNOWS: it treats the step as unreported
      (feeds its prediction, like the server) -> copies stay identical; the server shows the
      prediction (a declared, isolated violation).
    protocol "seq" (unconfirmed uplink + sequence numbers + heartbeat resync): the node never
      learns of a loss, so copies may diverge. The server notices a sequence gap at the next
      received report and flags every step since its last received report, and keeps flagging
      until it receives a heartbeat. A heartbeat (every hb_steps, full report) makes BOTH sides
      rebuild their predictors from the factory (node when sending, server when receiving),
      PRIMED with the report's values (history filled with them) so a model needing w past
      values predicts at once; an empty history after every 6-h heartbeat silently turned RLS
      into SOD (found in the smoke test, 2026-10-03). Learned weights return to the deployment
      model: that adaptation loss is the real cost of this protocol.
      Predictors whose entire state is the last value (SOD, `self_sync`) are resynchronised by
      ANY received report (report-level mode sends every parameter), so the flag clears then.
    A segment start (data gap) is a forced full report; under "seq" it is also a full resync
    point (both rebuild), because learned weights may have diverged before the gap.

    ack_loss (revision 2026-10-10, review M11): probability that the ACK of a DELIVERED attempt is
      lost. The node retries until it receives an ACK, so the server may hold a report that the node
      believes failed. With ack_loss = 0 no extra random numbers are drawn (v0.1 results reproduce).
      Under "ack" such a step silently desynchronises the copies (the node feeds its prediction, the
      server stored the reading): the v0.1 protocol is NOT bounded-or-flagged under ACK loss.
    protocol "ack_rs" (confirmed uplink with flagged resync, the revised protocol): as "ack", but a
      report that ends without an ACK makes the node UNCERTAIN from that step on. Its next step is a
      forced resync report (both sides rebuild their predictors, primed with the reported values, as
      a "seq" heartbeat) that carries the index of the first uncertain step; the server flags every
      step from that index up to the resync, retroactively. The node stays uncertain, and keeps
      sending resync reports, until one is acknowledged. Every unflagged server value is then within
      delta (tests/test_sim.py). hb_steps also applies (liveness heartbeat).
    Returns dict: R, tx (transmissions per step), delivered, flagged, attempts."""
    rng = np.random.default_rng(seed)
    N, P = X.shape
    nodeP, srvP = make_predictors(), make_predictors()
    nodes = [NodeView(64) for _ in range(P)]
    R = np.empty_like(X); tx = np.zeros(N, int); delivered = np.zeros(N, bool)
    flagged = np.zeros(N, bool)
    last_rx, stale, since_hb = -1, False, 0
    confirmed = protocol in ("ack", "ack_rs")
    rebuild = protocol in ("seq", "ack_rs")                   # protocols with rebuilding resyncs
    unc_since = None                                          # ack_rs: first step the node is unsure of
    for t in range(N):
        x = X[t]
        hb_due = bool(rebuild and hb_steps and since_hb >= hb_steps)
        unc = protocol == "ack_rs" and unc_since is not None
        resync = bool(seg_start[t]) or hb_due or unc
        # "seq" rebuilds at every resync; "ack_rs" only when the copies may differ (uncertain) or at a
        # heartbeat - at a plain segment start its copies are known to be identical (as under "ack")
        do_rebuild = resync if protocol == "seq" else (protocol == "ack_rs" and (hb_due or unc))
        if seg_start[t]:
            for p in range(P):
                nodeP[p].reset_history(); srvP[p].reset_history(); nodes[p].clear()
        if do_rebuild:
            nodeP = make_predictors()                         # node rebuilds when sending
            for p in range(P):                                # ...primed with the values it sends
                if hasattr(nodeP[p], "prime"): nodeP[p].prime(x[p])
        if resync:
            since_hb = 0
        xn = [nodeP[p].predict() for p in range(P)]
        for p in range(P):
            nodes[p].push(x[p])
        send = resync or any(xn[p] is None or nodeP[p].force_report() or abs(x[p] - xn[p]) > delta[p]
                             for p in range(P))
        ok = False                                            # server received the report
        acked = False                                         # node received an ACK
        if send:
            tries = 1 + (retries if confirmed else 0)
            for _ in range(tries):
                tx[t] += 1
                if rng.random() >= loss_p:
                    ok = True
                    if not confirmed or ack_loss == 0.0 or rng.random() >= ack_loss:
                        acked = True; break
        delivered[t] = ok
        # ---- server side
        if ok and unc:
            flagged[unc_since:t] = True                       # retroactive, index carried in the report
        if ok and do_rebuild:
            srvP = make_predictors()
            for p in range(P):                                # same values: received in the report
                if hasattr(srvP[p], "prime"): srvP[p].prime(x[p])
        xs = [srvP[p].predict() for p in range(P)]
        if ok:
            if protocol == "seq" and stale:
                flagged[last_rx + 1:t] = True                 # retroactive: gap seen now
            if resync or all(getattr(q, "self_sync", False) for q in srvP):
                stale = False                                 # full report refreshed all state
            last_rx = t
        R[t] = x if ok else np.array([np.nan if v is None else v for v in xs])
        if protocol == "seq" and stale:
            flagged[t] = True
        # ---- advance both copies
        # the node believes delivery if acknowledged (confirmed) or always (seq: it cannot know)
        node_reported = send and (acked if confirmed else True)
        for p in range(P):
            nodeP[p].observe(x[p] if node_reported else xn[p], node_reported, nodes[p])
            srvP[p].observe(x[p] if ok else xs[p], ok, nodes[p])
        if send and not ok and protocol == "seq":
            stale = True                                      # (server learns it at next rx)
        if protocol == "ack_rs":
            if send and not acked and unc_since is None:
                unc_since = t                                 # uncertain from this step on
            elif unc and acked:
                unc_since = None                              # an acknowledged resync clears it
        since_hb += 1
    # flags for losses never followed by a received report
    if protocol == "seq" and stale:
        flagged[last_rx + 1:] = True
    if protocol == "ack_rs" and unc_since is not None:
        flagged[unc_since:] = True
    return {"R": R, "tx": tx, "delivered": delivered, "flagged": flagged}
