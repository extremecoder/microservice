# Task 5: Input variable for ALB DNS name
variable "alb_dns_name" {
  description = "The DNS name of the Application Load Balancer"
  type        = string
}

# Task 6: API Gateway HTTP API resource
resource "aws_apigatewayv2_api" "quantum_api" {
  name          = "quantum-microservice-http-api"
  protocol_type = "HTTP"
  description   = "API Gateway frontend for the Quantum Microservice ALB"
}

# Task 7: API Gateway integration with ALB (HTTP)
resource "aws_apigatewayv2_integration" "quantum_alb_integration" {
  api_id             = aws_apigatewayv2_api.quantum_api.id
  integration_type   = "HTTP_PROXY"
  integration_method = "ANY"
  # Note: Explicitly appending the proxy path to the URI
  integration_uri    = "http://${var.alb_dns_name}:80/{proxy}"
  payload_format_version = "1.0"

  # Optional: Add timeout if needed, default is 30 seconds
  # timeout_milliseconds = 29000
}

# Task 8: API Gateway default route
resource "aws_apigatewayv2_route" "quantum_proxy_route" {
  api_id    = aws_apigatewayv2_api.quantum_api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.quantum_alb_integration.id}"
}

# Log group for API Gateway Access Logs
resource "aws_cloudwatch_log_group" "api_gateway_access_logs" {
  name              = "/aws/api-gateway/${aws_apigatewayv2_api.quantum_api.name}"
  retention_in_days = 30 # Or your desired retention period

  tags = {
    Name        = "api-gateway-quantum-microservice-logs"
    Environment = "dev" # Example tag
  }
}

# Task 9: API Gateway default stage
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.quantum_api.id
  name        = "$default"
  auto_deploy = true

  # Enable access logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_access_logs.arn
    # Using a common JSON format for detailed logs
    format = jsonencode({
      requestId               = "$context.requestId"
      ip                      = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      integrationLatency      = "$context.integrationLatency"
      integrationStatus       = "$context.integration.status"
    })
  }
}

# Task 10: Output the API Gateway invoke URL
output "api_gateway_invoke_url" {
  description = "The invoke URL for the API Gateway stage"
  value       = aws_apigatewayv2_api.quantum_api.api_endpoint
} 