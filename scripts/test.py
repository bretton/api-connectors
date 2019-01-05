import logging
from time import sleep
from bitmex_websocket import BitMEXWebsocket
from websocket import WebSocketException


FORMAT = '%(asctime)-15s %(message)s'
FORMATTER = logging.Formatter(FORMAT)
FILE_HANDLER = logging.FileHandler('test.log')
FILE_HANDLER.setFormatter(FORMATTER)
handlers = [FILE_HANDLER]
logging.basicConfig(format=FORMAT, level=logging.DEBUG, handlers=handlers)

ws = BitMEXWebsocket(endpoint="https://www.bitmex.com/api/v1", symbol="XBTUSD", api_key=None, api_secret=None)
reconnect_delay = 1

while True:
    try:
        sleep(1)
    except WebSocketException:
        ws.exit()
        if reconnect_delay < 1024:
            logging.info("Reconnecting in %s seconds" % reconnect_delay)
            sleep(reconnect_delay)
            ws = BitMEXWebsocket(endpoint="https://www.bitmex.com/api/v1", symbol="XBTUSD", api_key=None, api_secret=None)
            reconnect_delay *= 2
        raise Exception("Reconnect too many times")
