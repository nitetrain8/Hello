from hello.pid.lvpid import PIDController
from hello.pid.do_simulation.doprocess import DOProcess
from hello.pid.delay import m2s
from hello.pid.gas_process import GasController

def _setpid(ob, state, name, value):
    pid = state[ob]
    if name == "pgain":
        pid.pgain = value
    elif name == "itime":
        pid.itime = m2s(value)
    elif name == "dtime":
        pid.dtime = m2s(value)
    elif name == "beta":
        pid.b = value
    elif name == "mode":
        sp = state['sp']
        if ob[:2] == "n2":
            sp += state['db']
        elif ob[:2] == 'o2':
            sp -= state['db']
        else:
            print("BAD PID")
        pid.set_mode(value, state['pv'], sp)
    elif name == "man":
        pid.man_request = int(value)
    else:
        print("WARNING: Invalid attribute for %r: %r" % (ob, name))

def _update_value(state, proc, ob, name, value):
    if ob == "process":
        if name == "delay":
            value *= 60
        proc.set_values(**{name:value})
        return
    elif ob in ("o2_pid", "n2_pid"):
        _setpid(ob, state, name, value)
        return
    print("WARNING: Invalid attribute or object: %r %r" % (ob, name))

    
def _mk_pid(pidops, pv, sp, req, mode):
    c = PIDController(pgain=pidops.p,              itime=pidops.i,
                            dtime=pidops.d,             auto_max=pidops.amax,
                            auto_min=pidops.amin,       
                            beta=pidops.beta,
                            linearity=pidops.linearity, alpha=pidops.alpha,
                            deadband=pidops.deadband,   sp_high=100, sp_low=0,
                            gamma=pidops.gamma,         man_request=pidops.man_request,
                            mode=pidops.mode)
    if mode == "o2a":
        c.off_to_auto(pv, sp)
    elif mode == "m2a":
        c.man_to_auto(pv, sp, req)
    elif mode == "a2a":
        c.man_to_auto(pv, pv, req)
    else:
        raise ValueError(mode)
    return c
    

def do_sim_coroutine(ops, state, xq, pvq, cq,
                     co2q, n2q, o2q, aq, 
                     nukq, nupq, nuiq, nudq,
                     oukq, oupq, ouiq, oudq,
                     o2aq):
    
    """ This is the longest function in the history of man. 
    Its long becaues there are a *lot* of values to use and unpack for the inner PID loop,
    including code needed to synchronize with UI updates.
    Yay. 
    """
    
    co2_req, n2_req, o2_req = ops.initial_request_cno
    air_req = max(1-co2_req - n2_req - o2_req, 0)
    pv = ops.initial_pv
    sp = ops.set_point
    mode = ops.mode
    db = ops.set_point_deadband
    
    o2_pid = _mk_pid(ops.o2_pid, pv, sp-db, o2_req*100, mode)
    n2_pid = _mk_pid(ops.n2_pid, pv, sp+db, n2_req*100, mode)
    
    mg = ops.main_gas

    proc = ops.Process()
    proc.apply_ops(ops)

    # Old process initiation code
    # proc = DOProcess(mg, (co2a, n2a, o2a), 
    #                  ops.reactor_size, ops.reactor_volume, 
    #                  delay)
    
    # proc.set_values(k=ops.k, k_mult=ops.k_mult, c=ops.c, dc=ops.dc, d2c=ops.d2c)
    

    ctrl = GasController(ops.mfcs.co2_max, ops.mfcs.n2_max, ops.mfcs.o2_max, ops.mfcs.air_max)
    
    t = 0
    time_unit = ops.time_unit
    mi = ops.max_iters
    msg = None

    while True:

        cmd, arg = yield msg
        msg = None
        
        state.update(proc.getstate())
        state['sp'] = sp
        state['db'] = db
        state['pv'] = pv
        state['mg'] = mg
        state['t'] = t
        state['co2_req'] = co2_req
        state['n2_req'] = n2_req
        state['o2_req'] = o2_req
        state['air_req'] = air_req
        state['o2_pid'] = o2_pid
        state['n2_pid'] = n2_pid

        if cmd == "SIM_ITERS":
            
            iters = int(arg)
            if iters < 0:
                continue
            elif iters > mi:
                iters = mi

            # One approximation made in this simulation
            # is that no values, including oxygen consumption
            # (c), change during the inner iteration period 
            # outside of modification by the process or PID
            # classes themselves. 

            while iters > 0:

                t += 1
                iters -= 1
                o2_req = o2_pid.step(pv, sp-db) / 100
                n2_req = n2_pid.step(pv, sp+db) / 100
                co2_req, n2_req, o2_req, air_req = ctrl.request(mg, co2_req, n2_req, o2_req)
                pv = proc.step(pv, co2_req, n2_req, o2_req, air_req)

                xq.put(t/time_unit)
                pvq.put(pv)
                cq.put(proc.c * 3600)

                co2q.put(co2_req)
                n2q.put(n2_req)
                o2q.put(o2_req)
                aq.put(air_req)
                o2aq.put(proc.hp.o2A)

                nukq.put(n2_pid.Uk)
                nupq.put(n2_pid.Up)
                nuiq.put(n2_pid.Ui)
                nudq.put(n2_pid.Ud)

                oukq.put(o2_pid.Uk)
                oupq.put(o2_pid.Up)
                ouiq.put(o2_pid.Ui)
                oudq.put(o2_pid.Ud)

        elif cmd == "SET_TIME":
            t = arg
        elif cmd == "UPDATE_VALUE":
            ob, name, value = arg
            _update_value(state, proc, ob, name, value)
        elif cmd == "MODIFY_STATE":
            name, value = arg
            if name == "sp":
                sp = state['sp'] = value
            elif name == "pv":
                pv = state['pv'] = value
            elif name == "main_gas":
                mg = state['mg'] = value
            else:
                print("WARNING: Unrecognized name: %r" % name)
        else:
            raise ValueError(cmd)

    
def do_sim2(ops):
    # standalone sim function compatible with the do_sim_coroutine
    # function used for interactive use
    
    # This one yields the coroutine instead of calling it automatically
    # allowing for complex behavior made by adjusting parameters programmatically
    # mid-run. 
    state = {}
    
    class MyList(list):
        put = list.append
    
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
    yield coro
    data = list(zip(xq, pvq, cq,
                     co2q, n2q, o2q, aq, o2aq))
    data2 = list(zip(nukq, nupq, nuiq, nudq))
    data3 = list(zip(oukq, oupq, ouiq, oudq))
    yield data, data2, data3
    

def do_sim(ops):
    sim = do_sim2(ops)
    coro = next(sim)
    coro.send(("SIM_ITERS", ops.end))
    return next(sim)