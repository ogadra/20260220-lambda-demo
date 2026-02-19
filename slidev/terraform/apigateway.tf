resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${var.project}-ws"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
}

resource "aws_apigatewayv2_stage" "websocket" {
  #checkov:skip=CKV2_AWS_51:Access logging not needed for demo
  #checkov:skip=CKV_AWS_76:Access logging not needed for demo
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = "production"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}

# --- $connect ---

resource "aws_apigatewayv2_integration" "ws_connect" {
  api_id                    = aws_apigatewayv2_api.websocket.id
  integration_type          = "AWS_PROXY"
  integration_method        = "POST"
  integration_uri           = aws_lambda_function.ws_connect.invoke_arn
  content_handling_strategy = "CONVERT_TO_TEXT"
}

resource "aws_apigatewayv2_route" "ws_connect" {
  #checkov:skip=CKV_AWS_309:Public WebSocket endpoint for browser slide sync
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_connect.id}"
}

# --- $disconnect ---

resource "aws_apigatewayv2_integration" "ws_disconnect" {
  api_id                    = aws_apigatewayv2_api.websocket.id
  integration_type          = "AWS_PROXY"
  integration_method        = "POST"
  integration_uri           = aws_lambda_function.ws_disconnect.invoke_arn
  content_handling_strategy = "CONVERT_TO_TEXT"
}

resource "aws_apigatewayv2_route" "ws_disconnect" {
  #checkov:skip=CKV_AWS_309:Public WebSocket endpoint for browser slide sync
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_disconnect.id}"
}

# --- $default ---

resource "aws_apigatewayv2_integration" "ws_message" {
  api_id                    = aws_apigatewayv2_api.websocket.id
  integration_type          = "AWS_PROXY"
  integration_method        = "POST"
  integration_uri           = aws_lambda_function.ws_message.invoke_arn
  content_handling_strategy = "CONVERT_TO_TEXT"
}

resource "aws_apigatewayv2_route" "ws_message" {
  #checkov:skip=CKV_AWS_309:Public WebSocket endpoint for browser slide sync
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.ws_message.id}"
}
