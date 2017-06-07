_g_leg_map = {}
_cb_id = 0
def on_legend_clicked2(fig, leg_map, event):
    ll = event.artist
    for line in leg_map[ll]:
        line.set_visible(not line.get_visible())
    fig.canvas.draw()

def mk_picker(fig, ax, othermap=None):
    othermap = othermap or {}
    global _g_leg_map, _cb_id
    _g_leg_map[fig] = _g_leg_map.get(fig, {})
    leg_map = _g_leg_map[fig]
    a2l = {}
    def _olc(e):
        on_legend_clicked2(fig, leg_map, e)
    
    for lline in ax.legend_.get_lines():
        for aline in ax.get_lines():
            if lline.get_label() == aline.get_label():
                leg_map[lline] = leg_map.get(lline, [])
                leg_map[lline].append(aline)
                lline.set_picker(10)
                aline.set_visible(True)
                a2l[aline] = lline
    for aline, others in othermap.items():
        lline = a2l[aline]
        leg_map[lline].extend(others)
    fig.canvas.mpl_disconnect(_cb_id)
    _cb_id = fig.canvas.mpl_connect("pick_event", _olc)

def clear_picker():
    global _g_leg_map
    _g_leg_map.clear()