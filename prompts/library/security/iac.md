### Infrastructure as Code (IaC) Security
Review Terraform, Kubernetes, or CloudFormation changes.
- **Permissions**: Flag overly permissive IAM roles or Security Groups (e.g., 0.0.0.0/0).
- **Secrets**: Ensure no secrets are stored in plain text in IaC files.
- **Compliance**: Check for missing encryption (at rest/in transit).
