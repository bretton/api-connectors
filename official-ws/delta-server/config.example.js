// Sample configuration for BitMEX-Delta-Server.
// Copy me to config.js to use custom settings.

module.exports = {
  port: 4444,

  // If false, will connect to live exchange.
  // Testnet is https://testnet.bitmex.com
  testnet: true,

  // get all symbols
  //  curl -s "https://www.bitmex.com/api/v1/instrument?filter=%7B%22state%22%3A%20%22Open%22%7D" | jq -r .[].symbol
  // Symbols to watch. Add any/all symbols you are going to poll here.
  symbols: ['XBTUSD'],

  // Available streams:
  // Public:
  // ["instrument","orderBookL2","quote","trade"]
  // Private:
  // ["execution","margin","order","position"]
  //streams: ["instrument","wallet","margin","order","position","liquidation"],
  //streams: ["wallet","margin","order","position","liquidation"],
  //streams: ["wallet","margin","order","position"],
  streams: ["liquidation"],

  // If you want to use any of the above "private" streams, you must authenticate with an API Key.
  apiKeyID: '',
  apiKeySecret: '',

  // This prevents memory usage from getting out of control. Tweak to your needs.
  maxTableLen: 10000,
  maxListeners: 20,
};
