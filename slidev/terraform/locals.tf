locals {
  ws_handlers = {
    connect    = { route_key = "$connect" }
    disconnect = { route_key = "$disconnect" }
    message    = { route_key = "$default" }
  }
}
