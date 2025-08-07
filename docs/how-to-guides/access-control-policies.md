# Access Control Policies

Learn how to implement sophisticated access control that goes beyond simple role-based permissions using CEL expressions.

## The Problem

Your application needs sophisticated access control that goes beyond simple role-based permissions. You need to handle multiple factors like:

- Time of day restrictions
- Resource ownership
- Collaboration permissions  
- Context-sensitive rules

Hard-coding these rules makes them difficult to update and test.

## The CEL Solution

Instead of complex if/else chains in your application code, define access policies as portable, safe expressions that can be updated without code changes.

CEL enables sophisticated, multi-factor access control policies that handle complex business rules:

```python
from cel import evaluate
from datetime import datetime

def check_advanced_access_policy(user, resource, action, current_time=None):
    """Enterprise-grade multi-factor access control policy."""
    
    if current_time is None:
        current_time = datetime.now()
    
    # Advanced policy with multiple business rules:
    # 1. Admins can do anything, anytime
    # 2. Resource owners have full access during business hours
    # 3. Department members can read/collaborate on shared resources
    # 4. External users need approval for sensitive resources
    # 5. Compliance: audit logs required for financial data access
    policy = """
    (user.role == "admin") ||
    (resource.owner == user.id && user.verified && 
     (action != "delete" || user.department == resource.department)) ||
    (user.department == resource.department && user.clearance_level >= resource.sensitivity_level &&
     action in ["read", "comment"] && is_business_hours(current_hour)) ||
    (user.role == "external" && user.id in resource.approved_external_users &&
     action == "read" && resource.external_access_allowed) ||
    (action == "read" && resource.public && 
     (user.role != "guest" || is_business_hours(current_hour)))
    """
    
    def is_business_hours(hour):
        return 9 <= hour <= 17
    
    context = {
        "user": user,
        "resource": resource, 
        "action": action,
        "current_hour": current_time.hour,
        "is_business_hours": is_business_hours
    }
    
    return evaluate(policy, context)

# Example: Financial data access
financial_user = {
    "id": "analyst1", 
    "role": "analyst",
    "department": "finance",
    "clearance_level": 3,
    "verified": True
}

financial_resource = {
    "id": "q4_report",
    "owner": "cfo",
    "department": "finance", 
    "sensitivity_level": 3,
    "external_access_allowed": False,
    "approved_external_users": [],
    "public": False
}

# Test access during business hours
business_hour_time = datetime.now().replace(hour=14)  # 2 PM
access_granted = check_advanced_access_policy(
    financial_user, financial_resource, "read", business_hour_time
)
assert access_granted == True  # → Access GRANTED: Department member reading financial data during business hours

# Test access after hours (should be denied for non-admin)
after_hours_time = datetime.now().replace(hour=22)  # 10 PM
access_denied = check_advanced_access_policy(
    financial_user, financial_resource, "read", after_hours_time
)
assert access_denied == False  # → Access DENIED: Time-based security - financial data restricted after business hours

print("✓ Advanced access control policies working correctly")
```

## Advanced Policy Patterns

### Role Hierarchy

```python
def check_hierarchical_access(user, resource, action):
    """Implement role hierarchy where higher roles inherit lower permissions."""
    
    role_hierarchy = {
        "guest": 0,
        "user": 1, 
        "member": 2,
        "manager": 3,
        "admin": 4
    }
    
    policy = """
    user.role_level >= required_level &&
    (
        (action == "read" && resource.public) ||
        (action == "read" && user.id in resource.collaborators) ||
        (action in ["read", "write"] && resource.owner == user.id) ||
        (action in ["read", "write", "delete"] && user.role_level >= 3)
    )
    """
    
    context = {
        "user": {**user, "role_level": role_hierarchy.get(user["role"], 0)},
        "resource": resource,
        "action": action,
        "required_level": 0  # Minimum level to access system
    }
    
    return evaluate(policy, context)

# Test the hierarchical access control
guest_user = {"role": "guest", "id": "guest1"}
user_account = {"role": "user", "id": "user1"}
manager_account = {"role": "manager", "id": "mgr1"}

public_resource = {"public": True, "owner": "admin", "collaborators": []}
private_resource = {"public": False, "owner": "user1", "collaborators": ["guest1"]}

# Test 1: Guest accessing public resource
result = check_hierarchical_access(guest_user, public_resource, "read")
assert result == True  # → Access GRANTED: Public resources accessible to all authenticated users

# Test 2: Guest accessing private resource (denied)  
result = check_hierarchical_access(guest_user, private_resource, "write")
assert result == False  # → Access DENIED: Insufficient role level - guests cannot write to private resources

# Test 3: User accessing owned resource
result = check_hierarchical_access(user_account, private_resource, "write")
assert result == True  # → Access GRANTED: Resource ownership grants full read/write permissions

# Test 4: Manager can delete (role_level >= 3)
result = check_hierarchical_access(manager_account, private_resource, "delete")
assert result == True  # → Access GRANTED: Management role hierarchy allows deletion of any resource

# Test 5: Guest as collaborator can read
result = check_hierarchical_access(guest_user, private_resource, "read")
assert result == True  # → Access GRANTED: Collaboration permissions override role restrictions for read access

print("✓ Hierarchical access control working correctly")
```

### Time-Based Access

```python
def check_time_based_access(user, resource, action, current_time=None):
    """Implement time-based access restrictions."""
    
    if current_time is None:
        current_time = datetime.now()
    
    policy = """
    user.role == "admin" ||
    (
        user.role in ["member", "user"] &&
        (
            (user.schedule == "standard" && hour >= 9 && hour <= 17) ||
            (user.schedule == "flexible" && (hour >= 6 && hour <= 22)) ||
            (user.schedule == "always")
        )
    )
    """
    
    context = {
        "user": user,
        "resource": resource,
        "action": action,
        "hour": current_time.hour,
        "day_of_week": current_time.weekday()
    }
    
    return evaluate(policy, context)

# Test time-based access control
standard_user = {"role": "user", "schedule": "standard"}
flexible_user = {"role": "user", "schedule": "flexible"}
admin_user = {"role": "admin", "schedule": "standard"}
test_resource = {"id": "test_doc"}

# Test 1: Standard user during business hours
business_time = datetime.now().replace(hour=14)  # 2 PM
result = check_time_based_access(standard_user, test_resource, "read", business_time)
assert result == True  # → Access GRANTED: Standard work schedule allows access during 9-5 business hours

# Test 2: Standard user after hours (denied)
after_hours = datetime.now().replace(hour=22)  # 10 PM
result = check_time_based_access(standard_user, test_resource, "read", after_hours)
assert result == False  # → Access DENIED: Standard schedule restrictions prevent after-hours access

# Test 3: Flexible user during extended hours
result = check_time_based_access(flexible_user, test_resource, "read", after_hours)
assert result == True  # → Access GRANTED: Flexible schedule allows extended hours (6 AM - 10 PM)

# Test 4: Admin always has access
early_morning = datetime.now().replace(hour=5)  # 5 AM
result = check_time_based_access(admin_user, test_resource, "read", early_morning)
assert result == True  # → Access GRANTED: Admin role bypasses all time-based restrictions

print("✓ Time-based access control working correctly")
```

### Resource-Specific Policies

```python
def check_resource_specific_access(user, resource, action):
    """Different rules for different resource types."""
    
    policies = {
        "document": """
            user.role == "admin" ||
            (resource.owner == user.id) ||
            (resource.public && action == "read") ||
            (user.id in resource.collaborators && action in ["read", "comment"])
        """,
        
        "database": """
            user.role == "admin" ||
            (user.role == "developer" && action in ["read", "write"]) ||
            (user.role == "analyst" && action == "read")
        """,
        
        "system": """
            user.role == "admin" ||
            (user.role == "operator" && action in ["read", "restart"]) ||
            (user.role == "monitor" && action == "read")
        """
    }
    
    policy = policies.get(resource.get("type", "document"), policies["document"])
    
    context = {
        "user": user,
        "resource": resource,
        "action": action
    }
    
    return evaluate(policy, context)

# Test resource-specific access control
developer = {"role": "developer", "id": "dev1"}
analyst = {"role": "analyst", "id": "analyst1"}
operator = {"role": "operator", "id": "ops1"}

document_resource = {"type": "document", "owner": "dev1", "public": False, "collaborators": ["analyst1"]}
database_resource = {"type": "database", "name": "prod_db"}
system_resource = {"type": "system", "name": "web_server"}

# Test 1: Developer with database (can read/write)
result = check_resource_specific_access(developer, database_resource, "write")
assert result == True  # → Access GRANTED: Developer role has full database read/write permissions

result = check_resource_specific_access(developer, database_resource, "read")
assert result == True  # → Access GRANTED: Developer role includes database read access

# Test 2: Analyst with database (read-only)
result = check_resource_specific_access(analyst, database_resource, "read")
assert result == True  # → Access GRANTED: Analyst role has read-only database access for reporting

result = check_resource_specific_access(analyst, database_resource, "write")
assert result == False  # → Access DENIED: Analyst role restricted from database modifications

# Test 3: Operator with system (can read/restart)
result = check_resource_specific_access(operator, system_resource, "restart")
assert result == True  # → Access GRANTED: Operator role can restart systems for maintenance

# Test 4: Analyst as document collaborator
result = check_resource_specific_access(analyst, document_resource, "read")
assert result == True  # → Access GRANTED: Collaborator status grants read access regardless of role

result = check_resource_specific_access(analyst, document_resource, "write")
assert result == False  # → Access DENIED: Collaborator read-only access - ownership required for writes

print("✓ Resource-specific access control working correctly")
```

## Kubernetes Validation Rules

One of the most common real-world applications of CEL is in Kubernetes ValidatingAdmissionPolicies. CEL enables cluster administrators to write sophisticated admission control policies that validate resources before they're created or updated.

### ValidatingAdmissionPolicy Examples

```python
from cel import evaluate
import json

def validate_kubernetes_pod(pod_spec, policy_expression):
    """Validate a Kubernetes Pod specification using CEL expressions."""
    
    # Convert pod spec to CEL-compatible context
    context = {
        "object": pod_spec,
        "request": {
            "operation": "CREATE",
            "userInfo": {
                "username": "developer@company.com",
                "groups": ["developers", "system:authenticated"]
            }
        }
    }
    
    try:
        return evaluate(policy_expression, context)
    except Exception as e:
        print(f"Policy validation failed: {e}")
        return False

# Example 1: Security Policy - Require non-root containers
pod_security_policy = """
    !has(object.spec.securityContext.runAsUser) || 
    object.spec.securityContext.runAsUser != 0
"""

# Valid pod - runs as non-root user
secure_pod = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {"name": "secure-app"},
    "spec": {
        "securityContext": {"runAsUser": 1000},
        "containers": [{
            "name": "app",
            "image": "nginx:1.21"
        }]
    }
}

# Test secure pod passes validation
assert validate_kubernetes_pod(secure_pod, pod_security_policy) == True  # → SECURITY CHECK PASSED: Non-root user (1000) complies with security policy

# Invalid pod - runs as root
insecure_pod = {
    "apiVersion": "v1", 
    "kind": "Pod",
    "metadata": {"name": "insecure-app"},
    "spec": {
        "securityContext": {"runAsUser": 0},  # Root user!
        "containers": [{
            "name": "app",
            "image": "nginx:1.21"
        }]
    }
}

# Test insecure pod fails validation
assert validate_kubernetes_pod(insecure_pod, pod_security_policy) == False  # → SECURITY VIOLATION: Root user (UID 0) blocked by admission policy

print("✓ Kubernetes pod security validation working correctly")
```

### Resource Limit Enforcement

```python
def validate_resource_limits(workload_spec):
    """Enforce resource limits and requests for production workloads."""
    
    # Policy: All containers must have CPU and memory limits set
    # and requests must be at least 50% of limits
    resource_policy = """
        object.spec.containers.all(container,
            has(container.resources) &&
            has(container.resources.limits) &&
            has(container.resources.requests) &&
            has(container.resources.limits.cpu) &&
            has(container.resources.limits.memory) &&
            has(container.resources.requests.cpu) &&
            has(container.resources.requests.memory)
        )
    """
    
    context = {"object": workload_spec}
    return evaluate(resource_policy, context)

# Valid deployment with proper resource management
deployment_with_limits = {
    "apiVersion": "apps/v1",
    "kind": "Deployment", 
    "metadata": {"name": "web-app"},
    "spec": {
        "containers": [{
            "name": "web",
            "image": "nginx:1.21",
            "resources": {
                "limits": {"cpu": "200m", "memory": "256Mi"},
                "requests": {"cpu": "100m", "memory": "128Mi"}  # 50% of limits
            }
        }]
    }
}

# Test deployment passes resource validation
assert validate_resource_limits(deployment_with_limits) == True  # → RESOURCE POLICY PASSED: All containers have proper CPU/memory limits and requests

print("✓ Kubernetes resource limit validation working correctly")
```

### Network Policy Validation

```python
def validate_network_policy(network_policy_spec):
    """Validate NetworkPolicy configurations for security compliance."""
    
    # Policy: Ensure network policies have both ingress and egress rules
    # and don't allow unrestricted access
    network_security_policy = """
        has(object.spec.ingress) && size(object.spec.ingress) > 0 &&
        has(object.spec.egress) && size(object.spec.egress) > 0 &&
        object.spec.ingress.all(rule, 
            !has(rule.from) || size(rule.from) > 0
        ) &&
        object.spec.egress.all(rule,
            !has(rule.to) || size(rule.to) > 0
        )
    """
    
    context = {"object": network_policy_spec}
    return evaluate(network_security_policy, context)

# Valid network policy with restricted access
secure_network_policy = {
    "apiVersion": "networking.k8s.io/v1",
    "kind": "NetworkPolicy",
    "metadata": {"name": "web-netpol"},
    "spec": {
        "podSelector": {"matchLabels": {"app": "web"}},
        "ingress": [{
            "from": [{"podSelector": {"matchLabels": {"app": "frontend"}}}],
            "ports": [{"protocol": "TCP", "port": 80}]
        }],
        "egress": [{
            "to": [{"podSelector": {"matchLabels": {"app": "database"}}}],
            "ports": [{"protocol": "TCP", "port": 5432}]
        }]
    }
}

# Test network policy passes validation
assert validate_network_policy(secure_network_policy) == True  # → NETWORK SECURITY PASSED: Ingress/egress rules properly restrict traffic flow

print("✓ Kubernetes network policy validation working correctly")
```

### Custom Resource Validation

```python
def validate_custom_resource(custom_resource_spec, crd_validation_rules):
    """Validate custom resources using CEL expressions."""
    
    # Example: Validate a custom Application resource
    app_validation_policy = """
        has(object.spec.replicas) && object.spec.replicas >= 1 &&
        has(object.spec.image) && object.spec.image.contains(':') &&
        !object.spec.image.endsWith(':latest') &&
        has(object.spec.environment) && 
        object.spec.environment in ['dev', 'staging', 'prod'] &&
        (object.spec.environment == 'prod' ? object.spec.replicas >= 3 : true)
    """
    
    context = {"object": custom_resource_spec}
    return evaluate(app_validation_policy, context)

# Valid production application
production_app = {
    "apiVersion": "platform.company.com/v1",
    "kind": "Application",
    "metadata": {"name": "payment-service"},
    "spec": {
        "replicas": 3,  # Production requires >= 3 replicas
        "image": "payment-service:v1.2.3",  # Specific version, not latest
        "environment": "prod"
    }
}

# Valid development application  
development_app = {
    "apiVersion": "platform.company.com/v1",
    "kind": "Application", 
    "metadata": {"name": "test-service"},
    "spec": {
        "replicas": 1,  # Dev can have 1 replica
        "image": "test-service:v0.1.0",
        "environment": "dev"
    }
}

# Test both applications pass validation
assert validate_custom_resource(production_app, {}) == True  # → COMPLIANCE PASSED: Production app meets replica and versioning requirements
assert validate_custom_resource(development_app, {}) == True  # → COMPLIANCE PASSED: Development app allows lower replica count with proper versioning

print("✓ Kubernetes custom resource validation working correctly")
```

### Production Kubernetes Policy Engine

```python
from cel import evaluate, Context
from datetime import datetime
import re

class KubernetesPolicyEngine:
    """Production-grade policy engine for Kubernetes admission control."""
    
    def __init__(self):
        self.policies = {}
        self.load_default_policies()
    
    def load_default_policies(self):
        """Load standard security and compliance policies."""
        
        self.policies = {
            "pod-security": {
                "expression": """
                    (!has(object.spec.securityContext) || 
                     !has(object.spec.securityContext.runAsUser) || 
                     object.spec.securityContext.runAsUser != 0) &&
                    (!has(object.spec.securityContext) ||
                     !has(object.spec.securityContext.privileged) ||
                     object.spec.securityContext.privileged == false) &&
                    object.spec.containers.all(container,
                        !has(container.securityContext) ||
                        !has(container.securityContext.privileged) ||
                        container.securityContext.privileged == false
                    )
                """,
                "message": "Pods must not run as root or with privileged access"
            },
            
            "resource-quotas": {
                "expression": """
                    object.spec.containers.all(container,
                        has(container.resources.limits) &&
                        has(container.resources.requests)
                    )
                """,
                "message": "All containers must specify resource limits and requests"
            },
            
            "image-policy": {
                "expression": """
                    object.spec.containers.all(container,
                        container.image.startsWith('company-registry.com/') &&
                        !container.image.endsWith(':latest') &&
                        container.image.contains(':v')
                    )
                """,
                "message": "Images must be from company registry with semantic versioning"
            },
            
            "namespace-compliance": {
                "expression": """
                    has(object.metadata.namespace) &&
                    object.metadata.namespace != 'default' &&
                    (object.metadata.namespace.startsWith('prod-') ? 
                        (has(object.metadata.labels) && 'compliance.company.com/approved' in object.metadata.labels) : true)
                """,
                "message": "Production namespaces require compliance approval labels"
            }
        }
    
    def validate_admission(self, resource_spec, operation="CREATE", user_info=None):
        """Validate a Kubernetes resource admission request."""
        
        if user_info is None:
            user_info = {"username": "system", "groups": ["system:authenticated"]}
        
        context = Context()
        context.add_variable("object", resource_spec)
        context.add_variable("operation", operation) 
        context.add_variable("userInfo", user_info)
        context.add_variable("timestamp", datetime.now().isoformat())
        
        results = []
        
        for policy_name, policy_config in self.policies.items():
            try:
                # Skip certain policies for system users
                if (user_info.get("username", "").startswith("system:") and 
                    policy_name == "image-policy"):
                    continue
                    
                result = evaluate(policy_config["expression"], context)
                results.append({
                    "policy": policy_name,
                    "allowed": result,
                    "message": policy_config["message"] if not result else "Policy passed"
                })
                
            except Exception as e:
                results.append({
                    "policy": policy_name,
                    "allowed": False,
                    "message": f"Policy evaluation error: {e}"
                })
        
        # Overall admission decision
        admission_allowed = all(r["allowed"] for r in results)
        
        return {
            "allowed": admission_allowed,
            "message": "Admission approved" if admission_allowed else "Admission denied",
            "policy_results": results
        }

# Test the production policy engine
policy_engine = KubernetesPolicyEngine()

# Test with a compliant pod
compliant_pod = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "web-app",
        "namespace": "prod-payments",
        "labels": {"compliance.company.com/approved": "true"}
    },
    "spec": {
        "securityContext": {"runAsUser": 1000},
        "containers": [{
            "name": "app",
            "image": "company-registry.com/web-app:v1.2.3",
            "resources": {
                "limits": {"cpu": "500m", "memory": "256Mi"},
                "requests": {"cpu": "250m", "memory": "128Mi"}
            }
        }]
    }
}

# Test admission
result = policy_engine.validate_admission(
    compliant_pod, 
    operation="CREATE",
    user_info={"username": "developer@company.com", "groups": ["developers"]}
)

print(f"Admission allowed: {result['allowed']}")
print(f"Message: {result['message']}")
for policy_result in result['policy_results']:
    status = "✓" if policy_result['allowed'] else "✗"
    print(f"  {status} {policy_result['policy']}: {policy_result['message']}")

# The compliant pod should pass all policies
assert result['allowed'] == True  # → ADMISSION APPROVED: Pod meets all security, resource, and compliance policies

print("\n✓ Kubernetes production policy engine working correctly")
```

### Testing Kubernetes Policies with Python

```python
import pytest
from cel import evaluate

def test_kubernetes_pod_security_policies():
    """Comprehensive test suite for Kubernetes pod security policies."""
    
    def check_pod_security(pod_spec):
        policy = """
            (!has(object.spec.securityContext) || 
             !has(object.spec.securityContext.runAsUser) || 
             object.spec.securityContext.runAsUser != 0) &&
            object.spec.containers.all(container,
                !has(container.securityContext) ||
                !has(container.securityContext.privileged) ||
                container.securityContext.privileged == false
            )
        """
        return evaluate(policy, {"object": pod_spec})
    
    # Test case 1: Secure pod should pass
    secure_pod = {
        "spec": {
            "securityContext": {"runAsUser": 1000},
            "containers": [{"name": "app", "image": "nginx"}]
        }
    }
    assert check_pod_security(secure_pod) == True  # → SECURITY VALID: Non-root user and no privileged containers
    
    # Test case 2: Root user should fail
    root_pod = {
        "spec": {
            "securityContext": {"runAsUser": 0},
            "containers": [{"name": "app", "image": "nginx"}]
        }
    }
    assert check_pod_security(root_pod) == False  # → SECURITY VIOLATION: Root user (UID 0) poses container escape risk
    
    # Test case 3: Privileged container should fail
    privileged_pod = {
        "spec": {
            "securityContext": {"runAsUser": 1000},
            "containers": [{
                "name": "app", 
                "image": "nginx",
                "securityContext": {"privileged": True}
            }]
        }
    }
    assert check_pod_security(privileged_pod) == False  # → SECURITY VIOLATION: Privileged containers bypass kernel security
    
    # Test case 4: Missing security context should pass (default behavior)
    default_pod = {
        "spec": {
            "containers": [{"name": "app", "image": "nginx"}]
        }
    }
    assert check_pod_security(default_pod) == True  # → SECURITY ACCEPTABLE: Default runtime security context applied

# Run the test
test_kubernetes_pod_security_policies()
print("✓ All Kubernetes policy tests passed")
```

These Kubernetes examples demonstrate CEL's real-world power in:

- **ValidatingAdmissionPolicies**: Prevent insecure or non-compliant resources
- **Resource Management**: Enforce CPU/memory limits and requests
- **Security Compliance**: Block privileged containers and root users  
- **Network Security**: Validate NetworkPolicy configurations
- **Custom Resources**: Validate application-specific requirements
- **Production Workflows**: Complete policy engines with multiple validation rules

The Python CEL library is perfect for:
- **Testing Kubernetes policies locally** before deploying to clusters
- **Building admission webhook servers** that validate resources
- **Creating policy validation tools** for CI/CD pipelines
- **Developing custom operators** with CEL-based validation logic

## Why This Works

- **Readable**: Business stakeholders can understand the policy
- **Testable**: Each condition can be tested independently  
- **Flexible**: New rules can be added without code changes
- **Safe**: No risk of infinite loops or side effects
- **Auditable**: Policy changes are visible and trackable

## Best Practices

1. **Keep policies simple**: Break complex policies into smaller, composable rules
2. **Use descriptive names**: Make variable and function names self-documenting
3. **Test thoroughly**: Write unit tests for all policy scenarios
4. **Version control**: Track policy changes in version control
5. **Monitor performance**: Profile policy evaluation in production

## Related Topics

- [Business Logic & Data Transformation](business-logic-data-transformation.md) - Validate access control settings and transform user/resource data for policies
- [Production Patterns & Best Practices](production-patterns-best-practices.md) - Security and performance patterns