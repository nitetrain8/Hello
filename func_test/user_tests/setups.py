from hello import hello
from hello.logger import BuiltinLogger

_g_logger = BuiltinLogger("User Test Script")

def test_2053(app):
    
    n2i = "n2_i_time_(min)"
    n2d = "n2_d_time (min)"
    do_db = "Deadband (DO%)"
    n2_am = "n2 Auto max (%)"
    n2_P = "n2 p gain (%/DO%)"
    
    # backup settings
    _g_logger.info("Backing up config settings")
    app.login()
    cfg = app.getConfig()
    old_cfg = {}
    old_cfg[n2i] = cfg['DO'][n2i]
    old_cfg[n2d] = cfg['DO'][n2d]
    old_cfg[do_db] = cfg['DO'][do_db]
    old_cfg[n2_am] = cfg['DO'][n2_am]
    old_cfg[n2_P] = cfg['DO'][n2_P]
    
    # set test settings
    _g_logger.info("Setting test settings")
    app.setconfig('DO', n2i, 0)
    app.setconfig('DO', n2d, 0)
    app.setconfig('DO', do_db, 0)
    app.setconfig('DO', n2_am, 100)
    app.setconfig('DO', n2_P, -5)
    
    do_pv = app.getdopv()
    app.setdo(0, do_pv - 10)
    
    input("Press enter when done")
    
    _g_logger.info("Restoring old config")
    for k, v in old_cfg:
        app.setconfig('DO', k, v)
    