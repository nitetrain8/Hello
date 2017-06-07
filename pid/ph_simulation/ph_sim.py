def ph_sim(ops):
    # standalone sim function compatible with the do_sim_coroutine
    # function used for interactive use
    global state
    state = {}
    
    class MyList(list):
        put = list.append
    
    xq = MyList()
    pvq = MyList()
    cq = MyList()
    co2q = MyList()
    n2q = MyList()
    o2q = MyList()
    aq = MyList()
    baseq = MyList()
    co2ukq = MyList()
    co2upq = MyList()
    co2uiq = MyList()
    co2udq = MyList()
    baseukq = MyList()
    baseupq = MyList()
    baseuiq = MyList()
    baseudq = MyList()
    co2slnq = MyList()
    co2hsq = MyList()
    
    coro = ph_sim_coroutine(ops, state, xq, pvq, cq,
                     co2q, n2q, o2q, aq, baseq,
                     co2ukq, co2upq, co2uiq, co2udq,
                     baseukq, baseupq, baseuiq, baseudq,
                     co2slnq, co2hsq)
    
    next(coro)
    coro.send(("SIM_ITERS", ops.end))
    
    data = list(zip(xq, pvq, cq,
                     co2q, n2q, o2q, aq, baseq))
    data2 = list(zip(co2ukq, co2upq, co2uiq, co2udq))
    data3 = list(zip(baseukq, baseupq, baseuiq, baseudq))
    data4 = co2slnq, co2hsq
    return data, data2, data3, data4
    