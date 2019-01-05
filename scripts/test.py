import logging
import numpy as np
import pandas as pd
from bitmex_websocket import BitMEXWebsocket


class HighResolutionFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = pd.to_datetime(np.int64(record.created * 1000000000))
        t = ct.strftime("%Y-%m-%d %H:%M:%S.%f")
        s = "%s%s" % (t, ct.nanosecond)
        return s


FORMAT = '%(asctime)-15s %(message)s'
# FORMATTER = HighResolutionFormatter(FORMAT)
FORMATTER = logging.Formatter(FORMAT)
FILE_HANDLER = logging.FileHandler('test2.log')
FILE_HANDLER.setFormatter(FORMATTER)
handlers = [FILE_HANDLER]
logging.basicConfig(format=FORMAT, level=logging.DEBUG, handlers=handlers)

ws = BitMEXWebsocket(endpoint="https://www.bitmex.com/api/v1", symbol="XBTUSD", api_key=None, api_secret=None)
while True:
    continue
# ws.exit()