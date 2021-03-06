import websocket
import threading
import traceback
from time import sleep
import json
import logging
import urllib
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import math
from util.api_key import generate_nonce, generate_signature
import time

# Naive implementation of connecting to BitMEX websocket for streaming realtime data.
# The Marketmaker still interacts with this as if it were a REST Endpoint, but now it can get
# much more realtime data without polling the hell out of the API.
#
# The Websocket offers a bunch of data as raw properties right on the object.
# On connect, it synchronously asks for a push of all this data then returns.
# Right after, the MM can start using its data. It will be updated in realtime, so the MM can
# poll really often if it wants.
class BitMEXWebsocket:

    # Don't grow a table larger than this amount. Helps cap memory usage.
    MAX_TABLE_LEN = 200

    def __init__(self, endpoint, symbol, api_key=None, api_secret=None):
        '''Connect to the websocket and initialize data stores.'''
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initializing WebSocket.")

        self.endpoint = endpoint
        self.symbol = symbol

        if api_key is not None and api_secret is None:
            raise ValueError('api_secret is required if api_key is provided')
        if api_key is None and api_secret is not None:
            raise ValueError('api_key is required if api_secret is provided')

        self.api_key = api_key
        self.api_secret = api_secret

        self.data = {}
        self.keys = {}
        self.exited = False
        self.connected = False

        self.timemark = {}
        self.timemark['find'] = 0
        self.timemark['append'] = 0

        self.rcvcount = {}
        self.rcvdatasize = {}

        # We can subscribe right in the connection querystring, so let's build that.
        # Subscribe to all pertinent endpoints
        wsURL = self.__get_url()
        self.logger.info("Connecting to %s" % wsURL)
        self.__connect(wsURL, symbol)
        self.logger.info('Connected to WS.')

        # Connected. Wait for partials
        self.__wait_for_symbol(symbol)
        if api_key:
            self.__wait_for_account()
        self.logger.info('Got all market data. Starting.')

    def exit(self):
        '''Call this to exit - will close websocket.'''
        self.exited = True
        self.ws.close()

    def get_instrument(self):
        '''Get the raw instrument data for this symbol.'''
        # Turn the 'tickSize' into 'tickLog' for use in rounding
        instrument = self.data['instrument'][0]
        instrument['tickLog'] = int(math.fabs(math.log10(instrument['tickSize'])))
        return instrument

    def get_ticker(self):
        '''Return a ticker object. Generated from quote and trade.'''
        lastQuote = self.data['quote'][-1]
        lastTrade = self.data['trade'][-1]
        ticker = {
            "last": lastTrade['price'],
            "bid": lastQuote['bidPrice'],
            "ask": lastQuote['askPrice'],
            "mid": (float(lastQuote['bidPrice'] or 0) + float(lastQuote['askPrice'] or 0)) / 2
        }

        # The instrument has a tickSize. Use it to round values.
        instrument = self.data['instrument'][0]
        result = {}
        for k in ticker:
            result[k] = round(float(ticker[k] or 0), instrument['tickLog'])
        return result

    def funds(self):
        '''Get your margin details.'''
        return self.data['margin'][0]

    def position(self):
        '''Get your position details.'''
        return self.data['position'][0]

    def get_ohlcv(self, timeframe='1m'):
        bin = 'tradeBin'+timeframe
        return self.data[bin] if bin in self.data else []

    def market_depth(self):
        '''Get market depth (orderbook). Returns all levels.'''
        return self.data['orderBookL2']

    def open_orders(self, clOrdIDPrefix):
        '''Get all your open orders.'''
        orders = self.data['order']
        # Filter to only open orders (leavesQty > 0) and those that we actually placed
        return [o for o in orders if str(o['clOrdID']).startswith(clOrdIDPrefix) and o['leavesQty'] > 0]

    def all_orders(self):
        return self.data['order']

    def recent_trades(self):
        '''Get recent trades.'''
        return self.data['trade']
    
    def get_position(self):
        return self.data['position'][0]

    def connected(self):
        return self.ws.sock.connected

    def get_data(self):
        return self.data

    #
    # End Public Methods
    #

    def __connect(self, wsURL, symbol):
        '''Connect to the websocket in a thread.'''
        self.logger.debug("Starting thread")

        self.ws = websocket.WebSocketApp(wsURL,
                                         on_message=self.__on_message,
                                         on_close=self.__on_close,
                                         on_open=self.__on_open,
                                         on_error=self.__on_error,
                                         header=self.__get_auth())

        self.wst = threading.Thread(target=lambda: self.ws.run_forever())
        self.wst.daemon = True
        self.wst.start()
        self.logger.debug("Started thread")

        self.__wait_for_account()
        # Wait for connect before continuing
        conn_timeout = 5
        while not self.ws.sock or not self.ws.sock.connected and conn_timeout:
            sleep(1)
            conn_timeout -= 1
        if not conn_timeout:
            self.logger.error("Couldn't connect to WS! Exiting.")
            self.exit()
            raise websocket.WebSocketTimeoutException('Couldn\'t connect to WS! Exiting.')

    def __get_auth(self):
        '''Return auth headers. Will use API Keys if present in settings.'''
        if self.api_key:
            self.logger.info("Authenticating with API Key.")
            # To auth to the WS using an API key, we generate a signature of a nonce and
            # the WS API endpoint.
            expires = generate_nonce()
            return [
                "api-expires: " + str(expires),
                "api-signature: " + generate_signature(self.api_secret, 'GET', '/realtime', expires, ''),
                "api-key:" + self.api_key
            ]
        else:
            self.logger.info("Not authenticating.")
            return []

    def __get_url(self):
        '''
        Generate a connection URL. We can define subscriptions right in the querystring.
        Most subscription topics are scoped by the symbol we're listening to.
        '''

        # You can sub to orderBookL2 for all levels, or orderBook10 for top 10 levels & save bandwidth
        symbolSubs = ["execution", "instrument", "order", "orderBookL2", "position", "quote", "trade"]
        genericSubs = ["margin"]

        subscriptions = [sub + ':' + self.symbol for sub in symbolSubs]
        subscriptions += genericSubs

        urlParts = list(urllib.parse.urlparse(self.endpoint))
        urlParts[0] = urlParts[0].replace('http', 'ws')
        urlParts[2] = "/realtime?subscribe=" + ",".join(subscriptions)
        return urlparse.urlunparse(urlParts)

    def __wait_for_account(self):
        '''On subscribe, this data will come down. Wait for it.'''
        # Wait for the keys to show up from the ws
        while not {'margin', 'position', 'order'} <= set(self.data):
            sleep(0.1)

    def __wait_for_symbol(self, symbol):
        '''On subscribe, this data will come down. Wait for it.'''
        while not {'instrument', 'trade', 'quote', 'orderBookL2'} <= set(self.data):
            sleep(0.1)

    def __send_command(self, command, args=None):
        '''Send a raw command.'''
        if args is None:
            args = []
        self.ws.send(json.dumps({"op": command, "args": args}))

    def subscribe(self, topics):
        topics = [topic + ':' + self.symbol for topic in topics]
        self.__send_command('subscribe', topics)

    def unsubscribe(self, topics):
        topics = [topic + ':' + self.symbol for topic in topics]
        self.__send_command('unsubscribe', topics)

    def __on_message(self, ws, message):
        '''Handler for parsing WS messages.'''
        message = json.loads(message)
        self.logger.debug(json.dumps(message))

        table = message['table'] if 'table' in message else None
        action = message['action'] if 'action' in message else None
        try:
            if 'subscribe' in message:
                self.logger.info("Subscribed to %s." % message['subscribe'])
            elif 'unsubscribe' in message:
                self.logger.info("Unsubscribed to %s." % message['unsubscribe'])
            elif action:

                if table not in self.rcvcount:
                    self.rcvcount[table] = 0
                    self.rcvdatasize[table] = 0
                self.rcvcount[table] = self.rcvcount[table] + 1
                self.rcvdatasize[table] = self.rcvdatasize[table] + len(message['data'])

                # There are four possible actions from the WS:
                # 'partial' - full table image
                # 'insert'  - new row
                # 'update'  - update row
                # 'delete'  - delete row
                if action == 'partial':
                    self.logger.debug("%s: partial" % table)
                    # Keys are communicated on partials to let you know how to uniquely identify
                    # an item. We use it for updates.
                    self.keys[table] = message['keys']
                    if table not in self.data:
                        self.data[table] = []
                    self.appendData(self.keys[table], self.data[table], message['data'])
                    #self.data[table] += message['data']

                elif action == 'insert':
                    if table not in self.data:
                        return
                    self.logger.debug('%s: inserting %s' % (table, message['data']))
                    self.appendData(self.keys[table], self.data[table], message['data'])
                    self.rcvcount[table] = self.rcvcount[table] + 1
                    #self.data[table] += message['data']

                    # Limit the max length of the table to avoid excessive memory usage.
                    # Don't trim orders because we'll lose valuable state if we do.
                    if table not in ['order', 'orderBookL2'] and len(self.data[table]) > BitMEXWebsocket.MAX_TABLE_LEN:
                        self.data[table] = self.data[table][int(BitMEXWebsocket.MAX_TABLE_LEN / 2):]

                elif action == 'update':
                    if table not in self.data:
                        return
                    self.logger.debug('%s: updating %s' % (table, message['data']))
                    # Locate the item in the collection and update it.
                    for updateData in message['data']:
                        item = self.fast_findItemByKeys(self.keys[table], self.data[table], updateData)
                        if item is None:
                            return  # No item found to update. Could happen before push
                        item.update(updateData)
                        # Remove cancelled / filled orders
                        if table == 'order' and item['leavesQty'] <= 0:
                            self.data[table].remove(item)

                elif action == 'delete':
                    if table not in self.data:
                        return
                    self.logger.debug('%s: deleting %s' % (table, message['data']))
                    # Locate the item in the collection and remove it.
                    for deleteData in message['data']:
                        item = self.fast_findItemByKeys(self.keys[table], self.data[table], deleteData)
                        if item is None:
                            return
                        self.data[table].remove(item)

                else:
                    raise Exception("Unknown action: %s" % action)
        except:
            self.logger.error(traceback.format_exc())

    def __on_error(self, ws, error):
        '''Called on fatal websocket errors. We exit on these.'''
        if not self.exited:
            self.logger.error("Error : %s" % error)
            raise websocket.WebSocketException(error)

    def __on_open(self, ws):
        '''Called when the WS opens.'''
        self.connected = True
        self.logger.debug("Websocket Opened.")

    def __on_close(self, ws):
        '''Called on websocket close.'''
        self.connected = False
        self.logger.info('Websocket Closed')

    # Utility method for finding an item in the store.
    # When an update comes through on the websocket, we need to figure out which item in the array it is
    # in order to match that item.
    #
    # Helpfully, on a data push (or on an HTTP hit to /api/v1/schema), we have a "keys" array. These are the
    # fields we can use to uniquely identify an item. Sometimes there is more than one, so we iterate through all
    # provided keys.
    def findItemByKeys(self, keys, table, matchData):
        start = time.time()
        if len(keys):
            for item in table:
                matched = True
                for key in keys:
                    if item[key] != matchData[key]:
                        matched = False
                if matched:
                    end = time.time()
                    self.timemark['find'] += (end - start)
                    return item
        end = time.time()
        self.timemark['find'] += (end - start)
        return None

    def appendData(self, keys, table, data):
        start = time.time()
        if len(keys):
            for d in data:
                d['key_pair_id'] = __make_key_pair_id__(keys, d)
                table.append(d)
        else:
            table.extend(data)
        end = time.time()
        self.timemark['append'] += (end - start)

    def fast_findItemByKeys(self, keys, table, matchData):
        start = time.time()
        if len(keys):
            target_id = __make_key_pair_id__(keys, matchData)
            for item in table:
                if item['key_pair_id'] == target_id:
                    end = time.time()
                    self.timemark['find'] += (end - start)
                    return item
        end = time.time()
        self.timemark['find'] += (end - start)
        return None

def __make_key_pair_id__(keys, d):
    return ':'.join([str(v) for k, v in d.items() if k in keys])