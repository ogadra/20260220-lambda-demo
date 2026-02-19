resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${var.project}-ws"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
}

resource "aws_apigatewayv2_stage" "websocket" {
  #checkov:skip=CKV2_AWS_51:Access logging not needed for demo
  #checkov:skip=CKV_AWS_76:Access logging not needed for demo
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = "ws"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}

resource "aws_apigatewayv2_integration" "ws" {
  for_each                  = local.ws_handlers
  api_id                    = aws_apigatewayv2_api.websocket.id
  integration_type          = "AWS_PROXY"
  integration_method        = "POST"
  integration_uri           = aws_lambda_function.ws[each.key].invoke_arn
  content_handling_strategy = "CONVERT_TO_TEXT"
}

resource "aws_apigatewayv2_route" "ws" {
  #checkov:skip=CKV_AWS_309:Public WebSocket endpoint for browser slide sync
  for_each  = local.ws_handlers
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = each.value.route_key
  target    = "integrations/${aws_apigatewayv2_integration.ws[each.key].id}"
}
