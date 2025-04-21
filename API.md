Goal is to implement flow 
Client → HTTPS → API Gateway → HTTP → ALB Ingress → Kubernetes Service → Pod

Where in I already have the EKS cluster up and running
AWS Ingress Controller is also installed
AWS Load Balancer Ingress is also up and running
My API is already up and running over http with url
http://k8s-default-quantumm-be275525f6-1236523312.us-east-1.elb.amazonaws.com/api/v1/circuits/execute

e.g post request
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "circuit_file": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nh q[0];\ncx q[0],q[1];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];",
    "shots": 1024,
    "backend_type": "simulator",
    "backend_provider": "qiskit",
    "async_mode": false
  }' \
  http://k8s-default-quantumm-be275525f6-1236523312.us-east-1.elb.amazonaws.com/api/v1/circuits/execute



Client → HTTPS → API Gateway

Client initiates request: The client makes an HTTPS request to the API Gateway endpoint (e.g., https://abcd1234.execute-api.us-east-1.amazonaws.com/prod/api/v1/circuits/execute)
TLS handshake: The client and API Gateway establish an encrypted HTTPS connection. AWS manages all certificates for the API Gateway domain.
API Gateway processing:

Validates the request syntax
Applies any configured authorizers (if authentication is set up)
Checks API keys and usage plans (if configured)
Applies any request throttling/quota rules
Executes request transformations (if configured)



API Gateway → HTTP → ALB Ingress

Integration execution: API Gateway forwards the request to your ALB endpoint using HTTP (not HTTPS)
Path preservation: The original path is typically preserved in the forwarded request. For example, if the original request was to /api/v1/circuits/execute, the same path is forwarded to the ALB.
HTTP headers: API Gateway adds some headers to the request, including:

X-Forwarded-For: The client's IP address
X-Forwarded-Proto: The original protocol (https)
Custom integration headers (if configured)



ALB Ingress → Kubernetes Service

ALB receives request: The ALB receives the HTTP request from API Gateway
Ingress rules processing: The AWS Load Balancer Controller translates your Kubernetes Ingress rules into ALB listener rules
Path-based routing: The ALB examines the path in the request and determines which target group (Kubernetes service) should receive the traffic
Health check verification: The ALB confirms the target is healthy before forwarding traffic
Connection to target: The ALB establishes a connection with a healthy pod (via the Kubernetes service)

Kubernetes Service → Pod

Service receives traffic: The Kubernetes service receives the request from the ALB
Load balancing: kube-proxy (or an alternative CNI) routes traffic to one of the available pods based on the service's load balancing algorithm
Network translation: The service's ClusterIP is translated to a specific pod IP address
Pod receives request: The pod receives the HTTP request and processes it
Response path: The response follows the same path in reverse: Pod → Service → ALB → API Gateway → Client

This multi-layered architecture provides flexibility, security, and separation of concerns between the public-facing API management and the internal service routing.



Got it. Thanks for the clarification. If you don't have an ACM certificate and intend for the API Gateway to communicate with the ALB over HTTP, that simplifies things. The API Gateway will handle the HTTPS termination for the client.

Here's the revised task breakdown reflecting that the connection between API Gateway and ALB will be HTTP:

**Goal:** Put an AWS API Gateway (HTTP API type) in front of your existing ALB Ingress using Terraform, orchestrated by a CI/CD pipeline. The connection flow will be `Client → HTTPS → API Gateway → HTTP → ALB → HTTP → Service → Pod`.

**Assumptions:**
*   Your EKS cluster (`infra/main.tf`) is running.
*   Your application, service, and ingress (`k8s/quantum-microservice-k8s-deployment.yaml`) are deployed, and the ALB created by the Ingress controller is functional and accessible over HTTP port 80 (as per `API.md`).
*   The AWS Load Balancer Controller is installed in your EKS cluster.

---


**Phase 1: Confirm ALB HTTP Setup**

1.  **Task:** "Ensure the `Ingress` resource in `k8s/quantum-microservice-k8s-deployment.yaml` is configured correctly for HTTP (port 80) and does *not* include annotations related to HTTPS or certificates (`alb.ingress.kubernetes.io/listen-ports` should only contain `HTTP:80`, no `certificate-arn` or `ssl-redirect`)."
    *   *(Self-correction: Looking at your current `quantum-microservice-k8s-deployment.yaml`, it has `listen-ports: '[{"HTTPS":443}, {"HTTP":80}]'` and `ssl-redirect: '443'`. These need to be removed or modified if you *only* want HTTP on the ALB.)*
    *   **Revised Task 1:** "Update `k8s/quantum-microservice-k8s-deployment.yaml`: Modify the `Ingress` resource annotations. Remove `alb.ingress.kubernetes.io/ssl-redirect: '443'`. Change `alb.ingress.kubernetes.io/listen-ports` to `'[{"HTTP":80}]'`."
2.  **Task:** "Apply the updated `k8s/quantum-microservice-k8s-deployment.yaml` to the EKS cluster using `kubectl apply -f k8s/quantum-microservice-k8s-deployment.yaml`."
3.  **Task:** "Verify the ALB listener is active only for HTTP on port 80 and note the DNS name of the ALB. You can get the DNS name using `kubectl get ingress quantum-microservice-ingress -n <namespace> -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'`."
    *   *(Context: This DNS name is required for the API Gateway configuration.)*

**Phase 2: Define API Gateway using Terraform (HTTP Integration)**

4.  **Task:** "Create a new Terraform file, e.g., `infra/api_gateway.tf`."
5.  **Task:** "In `infra/api_gateway.tf`, define an input variable named `alb_dns_name` to receive the ALB DNS name obtained in Phase 1."
6.  **Task:** "In `infra/api_gateway.tf`, define an `aws_apigatewayv2_api` resource named `quantum_api` with `protocol_type = "HTTP"`."
7.  **Task:** "In `infra/api_gateway.tf`, define an `aws_apigatewayv2_integration` resource named `quantum_alb_integration`. Configure it with:
    *   `api_id`: Reference to the `aws_apigatewayv2_api` created above.
    *   `integration_type`: `"HTTP_PROXY"`
    *   `integration_method`: `"ANY"`
    *   `integration_uri`: `"http://${var.alb_dns_name}:80"` (Explicitly HTTP and port 80)
    *   `payload_format_version`: `"1.0"`"
8.  **Task:** "In `infra/api_gateway.tf`, define an `aws_apigatewayv2_route` resource named `quantum_proxy_route`. Configure it with:
    *   `api_id`: Reference to the API resource.
    *   `route_key`: `"ANY /{proxy+}"`
    *   `target`: `"integrations/${aws_apigatewayv2_integration.quantum_alb_integration.id}"`"
9.  **Task:** "In `infra/api_gateway.tf`, define an `aws_apigatewayv2_stage` resource named `default_stage`. Configure it with:
    *   `api_id`: Reference to the API resource.
    *   `name`: `"$default"`
    *   `auto_deploy`: `true`"
10. **Task:** "In `infra/api_gateway.tf`, define an output value for the API Gateway invoke URL using `aws_apigatewayv2_api.quantum_api.api_endpoint`."

**Phase 3: Implement CI/CD Pipeline (Conceptual Steps)**

*(Pipeline logic remains largely the same, but ensures the correct K8s manifest and Terraform code are applied)*

11. **Task:** "Design a CI/CD pipeline (e.g., using GitHub Actions). Configure secure access to AWS (Terraform state S3 bucket, EKS, API Gateway permissions) and Kubernetes (via `aws eks update-kubeconfig`)."
12. **Task:** "Add a pipeline stage to lint/validate Terraform (`terraform fmt -check`, `terraform validate`) and Kubernetes YAML (`kubeval` or similar)."
13. **Task:** "Add a pipeline stage to apply the EKS Terraform configuration (`infra/main.tf`) using `terraform apply`."
14. **Task:** "Add a pipeline stage to apply the Kubernetes manifests (`k8s/*.yaml`, including the updated Ingress definition) using `kubectl apply -f k8s/`."
15. **Task:** "Add a pipeline stage to:
    *   Wait for the Ingress resource `quantum-microservice-ingress` to have a status entry under `loadBalancer.ingress`.
    *   Retrieve the ALB DNS name using `kubectl get ingress quantum-microservice-ingress ...` (as in Task 3).
    *   Store this DNS name as a pipeline variable/output for the next stage."
16. **Task:** "Add a pipeline stage to apply the API Gateway Terraform configuration (`infra/api_gateway.tf`) using `terraform apply -var="alb_dns_name=<retrieved_dns_name>"."
17. **Task:** "(Optional) Add a pipeline stage to run basic integration tests against the deployed API Gateway endpoint (using the output from Task 10)."

**Phase 4: Verification and Documentation**

18. **Task:** "Test the end-to-end flow by sending a request (like the example `curl` in `API.md`) to the API Gateway invoke URL (which will be HTTPS)."
19. **Task:** "Update `API.md` or other project documentation to reflect the new API Gateway endpoint and the actual flow: `Client → HTTPS → API Gateway → HTTP → ALB → HTTP → Service → Pod`."

This revised plan aligns with your requirement of using HTTP between the API Gateway and the ALB. Let me know when you're ready to proceed with the first task!
