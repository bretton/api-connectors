#!/bin/bash -e

# optional custom config I need in source, enable this if using supervisord to start
# cd ~/api-connectors/official-ws/delta-server

[ ! -f config.js ] && echo 'Place your config in config.js!' && exit 1;

trap finish EXIT
PID=
function finish() {
  kill $PID
}

node index &
PID=$!

./node_modules/.bin/opn "http://localhost:$(node -e "console.log(require('./config.js').port)")"
wait
