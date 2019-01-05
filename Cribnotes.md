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