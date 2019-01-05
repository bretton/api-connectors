# Cribnotes

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