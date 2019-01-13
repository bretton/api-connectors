# Cribnotes

Please sign up using my [Bitmex referral link](https://www.bitmex.com/register/0Pl1vK)

## Delta-server trade bucketed table

The documentation refers to running a command like

```
curl -s "http://localhost:4444/trade/bucketed?symbol=XBTUSD"
```

However this produces an error as follows:

```
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Error</title>
</head>
<body>
<pre>Cannot GET /trade/bucketed</pre>
</body>
</html>
```

The solution appears to be to use a `?` as follows
```
curl -s "http://localhost:4444/trade?/bucketed?symbol=XBTUSD"
```

which returns the expected JSON as follows:
```
[
  {
    "timestamp": "2019-01-05T21:45:31.597Z",
    "symbol": "XBTUSD",
    "side": "Sell",
    "size": 180,
    "price": 3838,
    "tickDirection": "ZeroMinusTick",
    "trdMatchID": "cb96e6d2-0bc9-d921-dafe-f96857773931",
    "grossValue": 4689900,
    "homeNotional": 0.046899,
    "foreignNotional": 180
  },
  {
  ...
```

## Supervisord auto-starting
If you're starting the delta server from a `supervisord` config file such as the following:
```
/etc/supervisor/conf.d/deltaserver.conf 
```

with content:
```
[program:deltaserver]
command=/home/ubuntu/api-connectors/official-ws/delta-server/run.sh
environment=HOME="/home/ubuntu/api-connectors/official-ws/delta-server/",USER="ubuntu"
startretries=999999999999999999999999999
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/ubuntu/api-connectors/official-ws/delta-server/logs/deltaserver.log
```

Then you need to make sure your `run.sh` file includes the following

```
/home/ubuntu/api-connectors/official-ws/delta-server/run.sh
```

with content
```
# optional custom config I need in source, enable this if using supervisord to start
cd /home/ubuntu/api-connectors/official-ws/delta-server
```

This will allow `supervisord` to launch appropriately with all paths working properly.

For some reason I couldn't get this happening from within `supervisord` itself.


## Pending Merges

It looks like there are a lot of updated Go library files at [Investabit Github fork](https://github.com/Investabit/api-connectors) however a clean merge wasn't possible. Pending?

## Date formats

Bitmex expects the date field for `startTime` and `endTime` to be in the format `2017-01-01T00:00:00.000Z` for some API queries, yet allows datetime in the format of Unix epoch time in seconds for the UDF API too.

In order to generate date-time fields in the `2017-01-01T00:00:00.000Z` format, you can use string formatting of `%Y-%m-%dT%H:%M:%S.%fZ` however this has too many decimals, 6 instead of 3.

So you can generate a date string in the format "%Y-%m-%dT%H:%M:%S.%f", make sure timezone is correct, and truncate the value by 3-6 digits depending on the resulting format, and then append a `Z`.

Converting back would be a manual process too, best automated, as storing dates in normal unix time format may be more useful on your systems.

Code to convert from Bitmex date-time to regular date-time objects:

```
# go from Bitmex time format to normal time like unix epoch seconds

import datetime, pytz

a = '2017-01-01T00:00:00.000Z'
local_tz = pytz.timezone('UTC')
local_dt = datetime.datetime.strptime(a, '%Y-%m-%dT%H:%M:%S.000Z').replace(tzinfo=pytz.utc).astimezone(local_tz)
print(local_dt)
epochseconds = local_dt.replace(tzinfo=pytz.utc).timestamp()
print(epochseconds)
```

Code to convert from epoch seconds to Bitmex-suitable time is still being tested, the following works in python, but missing some steps for completion until testing done.

```

var = nowTimeStamp.isoformat()[:-3]+'Z'
```

However this python module seems to work for conversions for iso8601 too:

https://bitbucket.org/micktwomey/pyiso8601

```
pip3 install iso8601
python3

Python 3.6.8 
Type "help", "copyright", "credits" or "license" for more information.
>>> import iso8601
>>> iso8601.parse_date("2019-01-07T16:40:36.554749Z")
datetime.datetime(2019, 1, 7, 16, 40, 36, 554749, tzinfo=datetime.timezone.utc)
>>> iso8601.parse_date("2019-01-07T16:40:36.554Z")
datetime.datetime(2019, 1, 7, 16, 40, 36, 554000, tzinfo=datetime.timezone.utc)
>>> 
```

Of relevant is [RFC3339](https://tools.ietf.org/html/rfc3339) and scroll down to examples of internet date formats. They don't match what Bitmex is using.

Additionally the [ccxt manual](https://github.com/ccxt/ccxt/wiki/Manual#overriding-unified-api-params) refers to

```
exchange.parse8601 ('2018-01-01T00:00:00Z') == 1514764800000 // integer, Z = UTC
exchange.iso8601 (1514764800000) == '2018-01-01T00:00:00Z'   // iso8601 string
exchange.seconds ()      // integer UTC timestamp in seconds
exchange.milliseconds () // integer UTC timestamp in milliseconds
```

# ccxt
If you're running the Delta server on localhost, and want to use a library like [ccxt](https://github.com/ccxt/ccxt) too, you need separate API keys and passwords for each otherwise you will get an invalid nonce error.

There are work-arounds below, the simplest is just to have two API keys in use:
* One: used for Delta server, staying synchronised
* Two: used for order placement directly on their API

The reasons for this are load-based. You can query the Delta server every second, but you can query the primary Bitmex API once every 10 seconds.

According to [this github issue](https://github.com/ccxt/ccxt/issues/147#issuecomment-324355752) the solution is to include variables to set the nonce correctly:

```
# Python
import ccxt
import time
bitmex = ccxt.bitmex({
    "apiKey": BITMEX_API_KEY,
    "secret": BITMEX_API_SECRET,
    "nonce": lambda: time.time() * 1000, #  ← milliseconds nonce
})
balance = bitmex.privateGetUserWalletHistory()
```

```
// JavaScript
let bitmex = new ccxt.bitmex({
    "apiKey": BITMEX_API_KEY,
    "secret": BITMEX_API_SECRET,
    "nonce": Date.now, // ← milliseconds nonce
})
balance = bitmex.privateGetUserWalletHistory()
```

The issue is also outlined in the [ccxt documentation](https://github.com/ccxt/ccxt/wiki/Manual#overriding-the-nonce).

Additionally, if using [ccxt](https://github.com/ccxt/ccxt/) the correct symbol for XBTUSD is actually `BTC/USD` despite working fine with `XBTUSD` on the Delta server. Other instruments seem to work fine with the name, it's just this quirk with `ccxt` and Bitmex XBTUSD.
