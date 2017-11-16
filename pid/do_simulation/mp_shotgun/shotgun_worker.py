import socket, pickle
try:
    import checksum
except ImportError:
    from hello.pid.do_simulation.mp_shotgun import checksum

from hello.pid.do_simulation.do_sim import do_sim_coroutine
from hello.pid.do_simulation.options import SimOps
import numpy as np
import select
import os

hours = 3600

# Utilities

def np_unpack(l):
    return [np.array(d) for d in zip(*l)]

# Simulation Machinery

def simulate(ops):
    # slightly optimized copy of do_sim2 for worker purposes...
    state = {}
    class MyList(list): put = list.append
    
    xq   = MyList()
    pvq  = MyList()
    cq   = MyList()
    co2q = MyList()
    n2q  = MyList()
    o2q  = MyList()
    aq   = MyList()
    nukq = MyList()
    nupq = MyList()
    nuiq = MyList()
    nudq = MyList()
    oukq = MyList()
    oupq = MyList()
    ouiq = MyList()
    oudq = MyList()
    o2aq = MyList()
    coro = do_sim_coroutine(ops, state, xq, pvq, cq,
                     co2q, n2q, o2q, aq, 
                     nukq, nupq, nuiq, nudq,
                     oukq, oupq, ouiq, oudq, o2aq)
    
    next(coro)
    coro.send(("SIM_ITERS", ops.end))

    # only need a couple values for calculating get_score
    o2 = np.array(o2q)
    n2 = np.array(n2q)
    pv = np.array(pvq)
    return pv, o2, n2

def getscore(pv_up, n2, pv_down, o2):
    pv1t = 5*hours
    pv2t = 7*hours
    pv1_passed = np.any(np.abs(149 - pv_up[:pv1t]) < 1)  # Settle time < pv1t
    pv2_passed = np.any(np.abs(51 - pv_down[:pv2t]) < 1)  # Settle time < pv2t
    if not (pv1_passed and pv2_passed):
        return -1

    pv_where1 = pv_up[pv1t:]
    pv_where2 = pv_down[pv2t:]
    score1 = n2.sum()**2/len(n2)  # rampup waste
    score2 = o2.sum()**2/len(o2)  # rampdown waste
    score3 = (np.abs(149-pv_where1).sum()/len(pv_where1))*20  # rampup settle time penalty
    score4 = (np.abs(51-pv_where2).sum()/len(pv_where2))*20  # rampdown settle time penalty
    score  =  score1 + score2 + score3 + score4
    return score

def rampup(ops):
    ops.set_point = 150
    ops.initial_pv = 100
    pv, _, n2 = simulate(ops)
    return pv, n2
    
def rampdown(ops):
    ops.set_point = 50
    ops.initial_pv = 100
    pv, o2, _ = simulate(ops)
    return pv, o2

def test(ops):
    pv1, n2 = rampup(ops)
    pv2, o2 = rampdown(ops)
    return getscore(pv1, n2, pv2, o2)

## IPC Machinery

def pm(cmd, o):
    return pickle.dumps((cmd, o))

def run_all(l, ops):
    for params in l:
        o2p, n2p, o2i, n2i = params
        ops.o2_pid.p = o2p
        ops.o2_pid.i = o2i
        ops.n2_pid.p = n2p
        ops.n2_pid.i = n2i
        score = test(ops)
        yield params, score

def main(ip, port):
    s = socket.socket()
    s.connect((ip, port))
    rf = s.makefile("rb")
    wf = s.makefile("wb")
    try:
        _main(s, rf, wf)
    finally:
        wf.write(pm("PROC_EXIT", os.getpid()))

def _main(s, rf, wf):
    def get_cmd(xp):
        wf.flush()
        cmd, ob = pickle.load(rf)
        if cmd != xp:
            raise ValueError("Expected %s, got %s"%(xp, cmd))
        return ob

    q = []
    while True:
        cmd, ob = pickle.load(rf)
        if cmd == "ARGS":
            q.append(ob)
        elif cmd == "END":
            break
    
    wf.write(pm("MSG", "ACK_LIST"))
    cs = checksum.checksum(q)
    wf.write(pm("VERIFY_CHECKSUM", cs))
    wf.flush()
    ob = get_cmd("ACK_CHECKSUM")
    if ob != "SUCCESS":
        raise ValueError("Checksum mismatch")
    ops = get_cmd("SETUP_STATE")
    print(ops.jsonify())
    def drain_if_available():
        while oq:
            _, wl, _ = select.select([], [s], [], 0)
            if wl:
                res = oq.pop()
                wf.write(pm("GOT_RESULT", res))
                wf.flush()
            else:
                break

    oq = []
    for i, res in enumerate(run_all(q, ops), 1):
        key, score = res
        print("Result %d:: %s : %s"%(i, "%s.%s.%s.%s"%key, score))
        oq.append(res)
        drain_if_available()
    while oq:
        drain_if_available()
    

if __name__ == '__main__' and 'get_ipython' not in globals():
    import sys
    ip, port = sys.argv[1:]
    print("Starting Main")
    try:
        main(ip, int(port))
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        input("exiting")