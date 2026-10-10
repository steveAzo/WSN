"""Correctness tests for the DPS simulator (run: python -m pytest tests -q).

Each test encodes a property that must hold if the implementation is right:
  * bounded schemes never exceed delta at the server (any predictor, any mode)
  * the server can replay its reconstruction from the reports alone (node/server in sync)
  * accounting: report-level <= bundled <= separate counts on the same decisions
  * sanity on constant / ramp / extreme-threshold signals; periodic and batch baselines
"""
import sys

import numpy as np
import pytest

sys.path.insert(0, "src")
from sim.engine import run_batch, run_dps, run_periodic  # noqa: E402
from sim.predictors import DBP, LMS, LastValue, Ridge, RLS  # noqa: E402

rng = np.random.default_rng(42)


def synth(N=3000, P=3, gaps=(1000, 2200)):
    """random walk + diel sine + noise, with two data gaps"""
    t = np.arange(N)
    X = np.cumsum(rng.normal(0, 0.05, (N, P)), 0) + np.sin(2 * np.pi * t / 96)[:, None] \
        + rng.normal(0, 0.02, (N, P)) + np.arange(P)[None] * 10
    seg = np.zeros(N, bool); seg[0] = True; seg[list(gaps)] = True
    return X, seg


def factory(name, X, seg, delta):
    train = [X[:900, j] for j in range(X.shape[1])]
    def make():
        out = []
        for j in range(X.shape[1]):
            if name == "SOD": out.append(LastValue())
            if name == "LMS": out.append(LMS(N=4, Ex=float(np.mean(train[j] ** 2)), emax=delta[j]))
            if name == "DBP": out.append(DBP(m=6, l=3))
            if name == "RIDGE": out.append(Ridge(w=24, train=[train[j]]))
            if name == "RLS": out.append(RLS(w=24, train=[train[j]]))
        return out
    return make


@pytest.mark.parametrize("name", ["SOD", "LMS", "DBP", "RIDGE", "RLS"])
@pytest.mark.parametrize("mode", ["separate", "bundled", "report"])
def test_bounded(name, mode):
    X, seg = synth()
    delta = np.array([0.1, 0.2, 0.05])
    r = run_dps(X, seg, factory(name, X, seg, delta), mode=mode, delta=delta)
    assert (np.abs(X - r.R) <= delta + 1e-12).all()


@pytest.mark.parametrize("name", ["SOD", "LMS", "RIDGE", "RLS"])
def test_server_replay_in_sync(name):
    """The server, seeing only which values were reported, reproduces R exactly."""
    X, seg = synth()
    delta = np.array([0.1, 0.2, 0.05])
    make = factory(name, X, seg, delta)
    r = run_dps(X, seg, make, mode="report", delta=delta)
    preds, R2 = make(), np.empty_like(X)
    for t in range(len(X)):
        for j, p in enumerate(preds):
            if seg[t]:
                p.reset_history()
            xh = p.predict()
            v = X[t, j] if r.sent[t, j] else xh
            R2[t, j] = v
            p.observe(v, bool(r.sent[t, j]), None)
    np.testing.assert_allclose(R2, r.R)


def test_accounting_order():
    X, seg = synth()
    delta = np.array([0.1, 0.2, 0.05])
    make = factory("SOD", X, seg, delta)
    sep = run_dps(X, seg, make, mode="separate", delta=delta)
    bun = run_dps(X, seg, make, mode="bundled", delta=delta)
    assert bun.n_reports.sum() <= sep.n_reports.sum()
    np.testing.assert_array_equal(sep.sent, bun.sent)       # same decisions, different counting


def test_constant_signal_only_segment_starts():
    X = np.full((500, 2), 3.0); seg = np.zeros(500, bool); seg[[0, 250]] = True
    r = run_dps(X, seg, lambda: [LastValue(), LastValue()], delta=np.array([0.1, 0.1]))
    assert r.n_reports.sum() == 2


def test_dbp_tracks_ramp_better_than_sod():
    X = (np.arange(600) * 0.05)[:, None]; seg = np.zeros(600, bool); seg[0] = True
    d = np.array([0.1])
    sod = run_dps(X, seg, lambda: [LastValue()], delta=d).n_reports.sum()
    dbp = run_dps(X, seg, lambda: [DBP(m=6, l=3)], delta=d).n_reports.sum()
    assert dbp < sod / 10


def test_adaptiveml_extremes():
    X, seg = synth()
    make = lambda: [LastValue() for _ in range(3)]
    lo = run_dps(X, seg, make, alpha=0.0)
    hi = run_dps(X, seg, make, alpha=1e9)
    # forced segment-start report + one start-up report (sigma undefined with < 2 readings)
    assert hi.n_reports.sum() == 2 * seg.sum()
    assert lo.n_reports.sum() > 0.9 * len(X)                 # every non-zero error is reported


def test_periodic_and_batch():
    X, seg = synth()
    p = run_periodic(X, seg, 1)
    assert p.n_reports.sum() == len(X) and np.allclose(p.R, X)
    b, delay = run_batch(X, seg, 4)
    lens = np.diff(np.r_[np.flatnonzero(seg), len(X)])
    assert b.n_reports.sum() == sum(int(np.ceil(n / 4)) for n in lens)
    assert delay.max() <= 3 and np.allclose(b.R, X)


def test_ridge_learns_ar1():
    x = np.zeros(5000)
    for i in range(1, 5000):
        x[i] = 0.9 * x[i - 1] + rng.normal()
    r = Ridge(w=24, train=[x])
    z = (x[-24:] - r.mu) / r.sd
    assert abs(r.beta[-1] - 0.9) < 0.1 and np.abs(r.beta[:-1]).max() < 0.1


@pytest.mark.parametrize("mode", ["median", "lag"])
def test_detector_fast_path_identical(mode):
    """CusumDetector.run (precomputed medians) == step-by-step online use"""
    from sim.detector import CusumDetector
    X, seg = synth(N=2500)
    x = X[:, 0]; hrs = (np.arange(len(x)) // 4) % 24
    mk = lambda: CusumDetector(15, [x[:600]], 0.01, k=2, H=4, c=5, hours_train=[hrs[:600]], mode=mode)
    x2 = x.copy(); x2[1500:1530] += 1.0                       # an event, so alarms occur
    d1, d2 = mk(), mk()
    a1 = np.array([(d1.reset_history() if seg[t] else None, d1.step(x2[t], hrs[t]))[1] for t in range(len(x2))])
    a2 = d2.run(x2, hrs, seg)
    np.testing.assert_array_equal(a1, a2)
    assert a1[1500:1530].any()


def test_detector_ignores_short_glitch():
    """one-sample spike cannot alarm when H > c - k (glitch robustness by construction)"""
    from sim.detector import CusumDetector
    x = np.full(2000, 5.0) + rng.normal(0, 0.01, 2000); x[1500] += 10
    hrs = (np.arange(2000) // 4) % 24; seg = np.zeros(2000, bool); seg[0] = True
    d = CusumDetector(15, [x[:600]], 0.01, k=3, H=4, c=6, hours_train=[hrs[:600]], mode="lag", lag_min=60)
    assert not d.run(x, hrs, seg)[1495:1510].any()


def _switch_factory(X, delta):
    from sim.predictors import Switch
    train = [X[:900, j] for j in range(X.shape[1])]
    return lambda: [Switch(LastValue, lambda j=j: RLS(w=24, train=[train[j]], gamma=0.999), delta[j], 15,
                           mem_days=2, dwell_days=0.5, margin=0.05) for j in range(X.shape[1])]


@pytest.mark.parametrize("mode", ["separate", "report"])
def test_switch_bounded(mode):
    X, seg = synth()
    delta = np.array([0.1, 0.2, 0.05])
    r = run_dps(X, seg, _switch_factory(X, delta), mode=mode, delta=delta)
    assert (np.abs(X - r.R) <= delta + 1e-12).all()


def test_switch_server_replay():
    """server knows only reported values and the switch flags carried by reports"""
    from sim.predictors import Switch
    X, seg = synth()
    delta = np.array([0.1, 0.2, 0.05])
    make = _switch_factory(X, delta)
    holder = {}
    def make_keep():
        holder["p"] = make(); return holder["p"]
    r = run_dps(X, seg, make_keep, mode="report", delta=delta)
    logs = [dict(p.log) for p in holder["p"]]
    assert sum(len(l) for l in logs) > 0, "test needs at least one switch"
    for j, l in enumerate(logs):                               # switches only at reported steps
        assert all(r.sent[t, j] for t in l)
    srv = make(); R2 = np.empty_like(X)
    for t in range(len(X)):
        for j, s in enumerate(srv):
            if seg[t]:
                s.reset_history()
            xh = [p.predict() for p in s.P]
            v = X[t, j] if r.sent[t, j] else xh[s.active]
            R2[t, j] = v
            for p in s.P:
                p.observe(v, bool(r.sent[t, j]), None)
            if t in logs[j]:
                s.active = logs[j][t]
    np.testing.assert_allclose(R2, r.R)


@pytest.mark.parametrize("name", ["SOD", "RLS"])
def test_lossy_zero_loss_is_bounded_and_unflagged(name):
    from sim.engine import run_dps_lossy
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    for proto in ("ack", "seq"):
        o = run_dps_lossy(X, seg, factory(name, X, seg, delta), delta, 0.0, proto, hb_steps=96)
        assert (np.abs(X - o["R"]) <= delta + 1e-12).all() and not o["flagged"].any()


@pytest.mark.parametrize("name", ["SOD", "RLS"])
def test_lossy_ack_keeps_sync(name):
    """confirmed uplink: violations only at steps whose delivery failed after all retries"""
    from sim.engine import run_dps_lossy
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    o = run_dps_lossy(X, seg, factory(name, X, seg, delta), delta, 0.3, "ack", retries=0, seed=1)
    bad = (np.abs(X - o["R"]) > delta + 1e-12).any(1)
    assert bad.any()                                           # loss does cause violations...
    assert not (bad & o["delivered"]).any()                   # ...never on delivered steps
    failed = (o["tx"] > 0) & ~o["delivered"]
    assert bad.sum() <= failed.sum() * 1 + 0                   # only failed-delivery steps
    assert (bad <= failed).all()


@pytest.mark.parametrize("name", ["SOD", "RLS"])
@pytest.mark.parametrize("p", [0.01, 0.1, 0.3])
def test_lossy_seq_bounded_or_flagged(name, p):
    """unconfirmed uplink: every UNFLAGGED value at the server is within delta"""
    from sim.engine import run_dps_lossy
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    o = run_dps_lossy(X, seg, factory(name, X, seg, delta), delta, p, "seq", hb_steps=96, seed=2)
    err = np.abs(X - o["R"]); err[np.isnan(err)] = np.inf
    bad = (err > delta + 1e-12).any(1)
    assert not (bad & ~o["flagged"]).any()


def test_detector_bank_is_or_of_members():
    """bank alarms == OR of member alarms run separately (the members are independent, and
    alarm sets of separately-run members match the members inside the bank)"""
    from sim.detector import CusumDetector, DetectorBank
    X, seg = synth(N=2500); x = X[:, 0].copy(); x[1500:1540] += 1.0
    hrs = (np.arange(len(x)) // 4) % 24
    cfgs = [dict(mode="lag", lag_min=60, k=2, H=4, c=5), dict(mode="median", k=2, H=8, c=5)]
    b = DetectorBank(15, [x[:600]], 0.01, [hrs[:600]], cfgs)
    a_online = np.array([(b.reset_history() if seg[t] else None, b.step(x[t], hrs[t]))[1] for t in range(len(x))])
    sep = np.zeros(len(x), bool)
    for c in cfgs:
        sep |= CusumDetector(15, [x[:600]], 0.01, hours_train=[hrs[:600]], **c).run(x, hrs, seg)
    np.testing.assert_array_equal(a_online, sep)


@pytest.mark.parametrize("kw", [dict(), dict(phi=0.9), dict(phi=0.9, repair=True)])
@pytest.mark.parametrize("mode", ["separate", "report"])
def test_rlsd_bounded_and_in_sync(kw, mode):
    from sim.predictors import RLSDelta
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    train = [X[:900, j] for j in range(X.shape[1])]
    make = lambda: [RLSDelta(w=24, train=[train[j]], **kw) for j in range(X.shape[1])]
    r = run_dps(X, seg, make, mode=mode, delta=delta)
    assert (np.abs(X - r.R) <= delta + 1e-12).all()
    preds, R2 = make(), np.empty_like(X)                       # server replay from reports only
    for t in range(len(X)):
        for j, p in enumerate(preds):
            if seg[t]:
                p.reset_history()
            xh = p.predict(); v = X[t, j] if r.sent[t, j] else xh
            R2[t, j] = v; p.observe(v, bool(r.sent[t, j]), None)
    np.testing.assert_allclose(R2, r.R)


def test_rlsd_repair_interpolates():
    from sim.predictors import RLSDelta
    p = RLSDelta(w=4, train=[np.arange(100.0)], repair=True)
    for v, rep in [(0.0, True), (0, False), (0, False), (0, False), (8.0, True)]:
        p.predict(); p.observe(v, rep, None)
    np.testing.assert_allclose(p.h.buf[-5:], [0, 2, 4, 6, 8])


def test_lossy_seq_heartbeat_keeps_model_active():
    """regression: after a heartbeat the model must predict at once (not fall back to SOD);
    with zero loss and a short heartbeat, RLS-D must still differ from SOD"""
    from sim.engine import run_dps_lossy
    from sim.predictors import RLSDelta
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    train = [X[:900, j] for j in range(3)]
    mk_d = lambda: [RLSDelta(w=24, train=[train[j]], phi=0.97, repair=True) for j in range(3)]
    mk_s = lambda: [LastValue() for _ in range(3)]
    od = run_dps_lossy(X, seg, mk_d, delta, 0.0, "seq", hb_steps=24)
    os_ = run_dps_lossy(X, seg, mk_s, delta, 0.0, "seq", hb_steps=24)
    assert od["tx"].sum() != os_["tx"].sum()
    assert (np.abs(X - od["R"]) <= delta + 1e-12).all() and not od["flagged"].any()


# ---- revision 2026-10-10 (review M11): ACK loss and the flagged-resync confirmed protocol "ack_rs"
@pytest.mark.parametrize("name", ["SOD", "RLS"])
def test_ack_rs_identical_to_ack_without_ack_loss(name):
    """with no ACK loss the revised protocol changes nothing (v0.1 confirmed-uplink results stand)"""
    from sim.engine import run_dps_lossy
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    for p in (0.0, 0.1):
        a = run_dps_lossy(X, seg, factory(name, X, seg, delta), delta, p, "ack", seed=4)
        b = run_dps_lossy(X, seg, factory(name, X, seg, delta), delta, p, "ack_rs", seed=4)
        np.testing.assert_array_equal(a["tx"], b["tx"])
        np.testing.assert_array_equal(np.nan_to_num(a["R"]), np.nan_to_num(b["R"]))


def test_ack_v01_protocol_silently_desyncs_under_ack_loss():
    """documents the gap found in revision: a delivered report whose ACK is lost leaves the copies
    different, and the v0.1 confirmed protocol never flags the resulting violations"""
    from sim.engine import run_dps_lossy
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    o = run_dps_lossy(X, seg, factory("RLS", X, seg, delta), delta, 0.1, "ack", seed=3, ack_loss=0.3)
    err = np.abs(X - o["R"]); err[np.isnan(err)] = np.inf
    assert ((err > delta + 1e-12).any(1) & ~o["flagged"]).sum() > 0


@pytest.mark.parametrize("name", ["SOD", "RLS"])
@pytest.mark.parametrize("p,ack_loss", [(0.01, 0.01), (0.05, 0.05), (0.1, 0.3), (0.3, 0.3), (0.3, 0.0)])
@pytest.mark.parametrize("hb", [None, 96])
def test_ack_rs_bounded_or_flagged(name, p, ack_loss, hb):
    """revised confirmed protocol: every UNFLAGGED server value is within delta, under uplink and ACK loss"""
    from sim.engine import run_dps_lossy
    X, seg = synth(); delta = np.array([0.1, 0.2, 0.05])
    o = run_dps_lossy(X, seg, factory(name, X, seg, delta), delta, p, "ack_rs", hb_steps=hb, seed=5,
                      ack_loss=ack_loss)
    err = np.abs(X - o["R"]); err[np.isnan(err)] = np.inf
    assert not ((err > delta + 1e-12).any(1) & ~o["flagged"]).any()
