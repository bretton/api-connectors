# Cribnotes

## Shameless promotion

Sign up using my [Bitmex referral link](https://www.bitmex.com/register/0Pl1vK)

Alternatively leave a tip via LN [here](https://lnd3.vanilla.co.za)

## Delta-server trade bucketed table error

The documentation refers to running the following commands to get bucketed trades
```
curl -s "http://localhost:4444/trade/bucketed?symbol=XBTUSD"
```

However, this command produces an error:

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

Configure the delta server `config.js` to subscribe to the following additional, non-documented streams
```
"tradeBin1m","tradeBin1h","tradeBin1d"
```

Historical data appears when subscribed to over time, and only as much as received since the start.

## Alternate sources for historical trade data

Using Chrome browser visit [public.bitmex.com](https://public.bitmex.com/?prefix=data/trade/) to download daily datasets of trades for all tokens.

You can also download direct with curl such as
```
wget https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/20191025.csv.gz
```

It might prove move useful to build an archive from the public data, and update it by polling `tradeBin1m`?

## Supervisord auto-starting
If starting the delta server from a `supervisord` config file like:
```
/etc/supervisor/conf.d/deltaserver.conf 
```

with contents:
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

Then make sure the following `run.sh` file
```
/home/ubuntu/api-connectors/official-ws/delta-server/run.sh
```

includes the following content
```
# optional custom config needed in source, enable this if using supervisord to start
cd /home/ubuntu/api-connectors/official-ws/delta-server
```

This will allow `supervisord` to launch appropriately with all paths working properly.

## Pending Merges

There are a updated Go library files at [Investabit Github fork](https://github.com/Investabit/api-connectors) however a clean merge wasn't possible for this fork. 

## Date format

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

Code to convert from epoch seconds to Bitmex-suitable time is still being tested, the following works in python, but missing some steps for completion until testing done:
```

var = nowTimeStamp.isoformat()[:-3]+'Z'
```

This python module seems to work for conversions for iso8601 too:

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

Of relevance is [RFC3339](https://tools.ietf.org/html/rfc3339) and scroll down to examples of internet date formats. They don't match what Bitmex is using.

Additionally the [ccxt manual](https://github.com/ccxt/ccxt/wiki/Manual#overriding-unified-api-params) refers to

```
exchange.parse8601 ('2018-01-01T00:00:00Z') == 1514764800000 // integer, Z = UTC
exchange.iso8601 (1514764800000) == '2018-01-01T00:00:00Z'   // iso8601 string
exchange.seconds ()      // integer UTC timestamp in seconds
exchange.milliseconds () // integer UTC timestamp in milliseconds
```

# ccxt
If running the Delta server on localhost, and use of a library like [ccxt](https://github.com/ccxt/ccxt) is required, then separate API keys and passwords will be required for the delta server and ccxt, otherwise an invalid nonce error results.

Work-arounds below, the simplest is two API keys:
* One: used for Delta server, staying synchronised, per-second queries
* Two: used for order placement directly on the REST API, once every 10 seconds query

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

The issue is outlined in the [ccxt documentation](https://github.com/ccxt/ccxt/wiki/Manual#overriding-the-nonce).

If using [ccxt](https://github.com/ccxt/ccxt/) the correct symbol for XBTUSD is actually `BTC/USD`. 

`XBTUSD` will work on the Delta server. 

