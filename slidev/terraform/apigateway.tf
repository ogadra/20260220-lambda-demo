resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${var.project}-ws"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
}

resource "aws_apigatewayv2_stage" "websocket" {
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = "ws"
  auto_deploy = true
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

# --- Login API Gateway ---

resource "aws_apigatewayv2_api" "login" {
  name          = "${var.project}-login"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "login" {
  api_id      = aws_apigatewayv2_api.login.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "login" {
  api_id                 = aws_apigatewayv2_api.login.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.login.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "login_get" {
  #checkov:skip=CKV_AWS_309:Public login endpoint for presenter authentication
  api_id    = aws_apigatewayv2_api.login.id
  route_key = "GET /login"
  target    = "integrations/${aws_apigatewayv2_integration.login.id}"
}

resource "aws_apigatewayv2_route" "login_post" {
  #checkov:skip=CKV_AWS_309:Public login endpoint for presenter authentication
  api_id    = aws_apigatewayv2_api.login.id
  route_key = "POST /login"
  target    = "integrations/${aws_apigatewayv2_integration.login.id}"
}
