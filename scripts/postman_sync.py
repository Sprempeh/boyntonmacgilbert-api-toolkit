#!/usr/bin/env python3
"""
Postman Adoption Kit - API Sync Tool (Production Grade)
========================================================

Automates Postman workspace setup from OpenAPI specs.
Reduces API discovery time from ~47 minutes to seconds.

Features:
    - Creates OR updates existing collections (idempotent)
    - Creates OR updates existing environments
    - Validates OpenAPI specs before sync
    - Exports specs from AWS API Gateway
    - Supports all 4 environments (Dev/QA/UAT/Prod)
    - Auto-configures JWT authentication
    - Generates sync summary JSON for CI/CD

Usage:
    # Basic sync
    python postman_sync.py --spec specs/api.yaml --workspace-id abc123

    # Dry run (preview without changes)
    python postman_sync.py --spec specs/api.yaml --workspace-id abc123 --dry-run

    # Sync multiple specs
    for spec in specs/*.yaml; do
        python postman_sync.py --spec "$spec" --workspace-id abc123
    done

    # Export from AWS API Gateway and sync
    python postman_sync.py --aws-api-id xyz789 --stage prod --workspace-id abc123

Requirements:
    pip install requests pyyaml
    pip install boto3  # Optional, for AWS API Gateway export
"""

import argparse
import json
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Error: pyyaml library required. Install with: pip install pyyaml")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

POSTMAN_API_BASE = "https://api.getpostman.com"

# Environment configurations - customize these for your organization
ENVIRONMENT_CONFIGS = {
    "Dev": {
        "base_url": "https://api-dev.payments.example.com/v2",
        "auth_url": "https://auth-dev.payments.example.com",
    },
    "QA": {
        "base_url": "https://api-qa.payments.example.com/v2",
        "auth_url": "https://auth-qa.payments.example.com",
    },
    "UAT": {
        "base_url": "https://api-uat.payments.example.com/v2",
        "auth_url": "https://auth-uat.payments.example.com",
    },
    "Prod": {
        "base_url": "https://api.payments.example.com/v2",
        "auth_url": "https://auth.payments.example.com",
    },
}

# JWT Pre-request script - handles automatic token refresh
JWT_PREREQUEST_SCRIPT = """
// ============================================
// JWT Auto-Authentication Script
// ============================================
// This script automatically handles token refresh.
// Set these environment variables:
//   - auth_url: OAuth token endpoint base URL
//   - client_id: Your OAuth client ID
//   - client_secret: Your OAuth client secret
// ============================================

const currentTime = Math.floor(Date.now() / 1000);
const tokenExpiry = pm.environment.get("jwt_expiry");
const EXPIRY_BUFFER = 60; // Refresh 60 seconds before expiry

// Check if token needs refresh
if (!tokenExpiry || currentTime >= (tokenExpiry - EXPIRY_BUFFER)) {
    console.log("Token expired or missing, refreshing...");
    
    const authUrl = pm.environment.get("auth_url");
    const clientId = pm.environment.get("client_id");
    const clientSecret = pm.environment.get("client_secret");
    
    // Validate configuration
    if (!authUrl || !clientId || !clientSecret) {
        console.error("Authentication configuration incomplete.");
        console.error("Required: auth_url, client_id, client_secret");
        throw new Error("Missing authentication configuration. Please set environment variables.");
    }
    
    // Request new token
    pm.sendRequest({
        url: authUrl + "/oauth/token",
        method: 'POST',
        header: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: {
            mode: 'urlencoded',
            urlencoded: [
                {key: 'grant_type', value: 'client_credentials'},
                {key: 'client_id', value: clientId},
                {key: 'client_secret', value: clientSecret}
            ]
        }
    }, function(err, response) {
        if (err) {
            console.error("Token request failed:", err);
            throw new Error("Authentication failed: " + err);
        }
        
        if (response.code !== 200) {
            console.error("Token request returned:", response.code, response.status);
            throw new Error("Authentication failed: " + response.status);
        }
        
        const data = response.json();
        
        if (!data.access_token) {
            console.error("No access_token in response:", data);
            throw new Error("Invalid token response");
        }
        
        // Store token and expiry
        pm.environment.set("jwt_token", data.access_token);
        pm.environment.set("jwt_expiry", currentTime + (data.expires_in || 3600));
        
        console.log("Token refreshed successfully. Expires in:", data.expires_in || 3600, "seconds");
    });
} else {
    console.log("Using cached token. Expires in:", tokenExpiry - currentTime, "seconds");
}
""".strip()


# =============================================================================
# POSTMAN API CLIENT
# =============================================================================

class PostmanClient:
    """Client for interacting with the Postman API."""
    
    def __init__(self, api_key: str, dry_run: bool = False):
        self.api_key = api_key
        self.dry_run = dry_run
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        self._collections_cache = None
        self._environments_cache = None
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an API request to Postman."""
        url = f"{POSTMAN_API_BASE}{endpoint}"
        
        if self.dry_run:
            print(f"    [DRY RUN] {method} {endpoint}")
            return {"dry_run": True, "id": "dry-run-id", "uid": "dry-run-uid"}
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 429:
                print("    ⚠️  Rate limited. Waiting 60 seconds...")
                import time
                time.sleep(60)
                return self._request(method, endpoint, data)
            
            if response.status_code >= 400:
                error_msg = response.text[:200]
                print(f"    ❌ API Error {response.status_code}: {error_msg}")
                response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            print("    ❌ Request timed out")
            raise
        except requests.exceptions.ConnectionError:
            print("    ❌ Connection failed")
            raise
    
    def get_workspace_collections(self, workspace_id: str) -> List[dict]:
        """Get all collections in a workspace."""
        if self._collections_cache is None:
            result = self._request("GET", f"/workspaces/{workspace_id}")
            workspace = result.get("workspace", {})
            self._collections_cache = workspace.get("collections", [])
        return self._collections_cache
    
    def get_workspace_environments(self, workspace_id: str) -> List[dict]:
        """Get all environments in a workspace."""
        if self._environments_cache is None:
            result = self._request("GET", "/environments")
            # Filter to just this workspace's environments
            all_envs = result.get("environments", [])
            # Note: Postman API doesn't filter by workspace, so we get all
            self._environments_cache = all_envs
        return self._environments_cache
    
    def find_collection_by_name(self, workspace_id: str, name: str) -> Optional[dict]:
        """Find a collection by name in the workspace."""
        collections = self.get_workspace_collections(workspace_id)
        for col in collections:
            if col.get("name") == name:
                return col
        return None
    
    def find_environment_by_name(self, name: str) -> Optional[dict]:
        """Find an environment by name."""
        environments = self._request("GET", "/environments").get("environments", [])
        for env in environments:
            if env.get("name") == name:
                return env
        return None
    
    def create_collection(self, workspace_id: str, collection: dict) -> dict:
        """Create a new collection."""
        name = collection.get("info", {}).get("name", "Unknown")
        print(f"    Creating collection: {name}")
        result = self._request("POST", f"/collections?workspaceId={workspace_id}", {"collection": collection})
        return result.get("collection", result)
    
    def update_collection(self, collection_uid: str, collection: dict) -> dict:
        """Update an existing collection."""
        name = collection.get("info", {}).get("name", "Unknown")
        print(f"    Updating collection: {name}")
        result = self._request("PUT", f"/collections/{collection_uid}", {"collection": collection})
        return result.get("collection", result)
    
    def create_environment(self, workspace_id: str, environment: dict) -> dict:
        """Create a new environment."""
        name = environment.get("name", "Unknown")
        print(f"    Creating environment: {name}")
        result = self._request("POST", f"/environments?workspaceId={workspace_id}", {"environment": environment})
        return result.get("environment", result)
    
    def update_environment(self, environment_uid: str, environment: dict) -> dict:
        """Update an existing environment."""
        name = environment.get("name", "Unknown")
        print(f"    Updating environment: {name}")
        result = self._request("PUT", f"/environments/{environment_uid}", {"environment": environment})
        return result.get("environment", result)
    
    def upsert_collection(self, workspace_id: str, collection: dict) -> Tuple[dict, str]:
        """Create or update a collection. Returns (result, action)."""
        name = collection.get("info", {}).get("name", "Unknown")
        existing = self.find_collection_by_name(workspace_id, name)
        
        if existing:
            result = self.update_collection(existing["uid"], collection)
            return result, "updated"
        else:
            result = self.create_collection(workspace_id, collection)
            return result, "created"
    
    def upsert_environment(self, workspace_id: str, environment: dict) -> Tuple[dict, str]:
        """Create or update an environment. Returns (result, action)."""
        name = environment.get("name", "Unknown")
        existing = self.find_environment_by_name(name)
        
        if existing:
            result = self.update_environment(existing["uid"], environment)
            return result, "updated"
        else:
            result = self.create_environment(workspace_id, environment)
            return result, "created"


# =============================================================================
# OPENAPI SPEC HANDLING
# =============================================================================

def load_openapi_spec(spec_path: str) -> Tuple[dict, str]:
    """Load and parse an OpenAPI specification file."""
    path = Path(spec_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if path.suffix in ['.yaml', '.yml']:
        spec = yaml.safe_load(content)
    else:
        spec = json.loads(content)
    
    return spec, content


def validate_openapi_spec(spec: dict) -> List[str]:
    """Validate an OpenAPI spec and return any warnings/errors."""
    issues = []
    
    # Check required fields
    if "openapi" not in spec and "swagger" not in spec:
        issues.append("ERROR: Missing 'openapi' or 'swagger' version field")
    
    if "info" not in spec:
        issues.append("ERROR: Missing 'info' section")
    elif "title" not in spec["info"]:
        issues.append("WARNING: Missing 'info.title'")
    
    if "paths" not in spec:
        issues.append("ERROR: Missing 'paths' section")
    elif len(spec["paths"]) == 0:
        issues.append("WARNING: No paths defined")
    
    # Check for common issues
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "patch", "delete"]:
                if "operationId" not in details:
                    issues.append(f"WARNING: {method.upper()} {path} missing operationId")
    
    return issues


def spec_to_collection(spec: dict, prerequest_script: str = None) -> dict:
    """Convert an OpenAPI spec to a Postman collection."""
    info = spec.get("info", {})
    
    # Build base collection structure
    collection = {
        "info": {
            "name": info.get("title", "API Collection"),
            "description": info.get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [],
        "event": [],
        "auth": {
            "type": "bearer",
            "bearer": [
                {"key": "token", "value": "{{jwt_token}}", "type": "string"}
            ]
        },
        "variable": [
            {"key": "base_url", "value": "{{base_url}}", "type": "string"}
        ]
    }
    
    # Add pre-request script for JWT auth
    if prerequest_script:
        collection["event"].append({
            "listen": "prerequest",
            "script": {
                "type": "text/javascript",
                "exec": prerequest_script.split("\n")
            }
        })
    
    # Convert paths to requests, grouped by tags
    paths = spec.get("paths", {})
    tagged_items: Dict[str, List[dict]] = {}
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method not in ["get", "post", "put", "patch", "delete"]:
                continue
            
            # Get tag for grouping
            tags = details.get("tags", ["General"])
            tag = tags[0] if tags else "General"
            
            if tag not in tagged_items:
                tagged_items[tag] = []
            
            # Build request
            request_item = build_request_item(path, method, details, spec)
            tagged_items[tag].append(request_item)
    
    # Add folders for each tag
    for tag, items in tagged_items.items():
        collection["item"].append({
            "name": tag,
            "item": items,
            "description": f"Endpoints tagged with '{tag}'"
        })
    
    return collection


def build_request_item(path: str, method: str, details: dict, spec: dict) -> dict:
    """Build a Postman request item from an OpenAPI operation."""
    
    # Build URL with path parameters
    url_path = path
    path_params = []
    
    # Extract path parameters
    for param in details.get("parameters", []):
        if param.get("in") == "path":
            path_params.append({
                "key": param["name"],
                "value": f"{{{{{param['name']}}}}}",
                "description": param.get("description", "")
            })
    
    # Extract query parameters
    query_params = []
    for param in details.get("parameters", []):
        if param.get("in") == "query":
            query_params.append({
                "key": param["name"],
                "value": "",
                "description": param.get("description", ""),
                "disabled": not param.get("required", False)
            })
    
    # Build headers
    headers = []
    for param in details.get("parameters", []):
        if param.get("in") == "header":
            headers.append({
                "key": param["name"],
                "value": "",
                "description": param.get("description", "")
            })
    
    # Build request body
    body = None
    if "requestBody" in details:
        content = details["requestBody"].get("content", {})
        if "application/json" in content:
            json_content = content["application/json"]
            example = extract_example(json_content, spec)
            
            body = {
                "mode": "raw",
                "raw": json.dumps(example, indent=2) if example else "{}",
                "options": {"raw": {"language": "json"}}
            }
            
            headers.append({
                "key": "Content-Type",
                "value": "application/json"
            })
    
    # Build the request item
    request_item = {
        "name": details.get("summary", f"{method.upper()} {path}"),
        "request": {
            "method": method.upper(),
            "header": headers,
            "url": {
                "raw": "{{base_url}}" + path,
                "host": ["{{base_url}}"],
                "path": [p for p in path.split("/") if p and not p.startswith("{")],
                "variable": path_params,
                "query": query_params if query_params else None
            },
            "description": details.get("description", "")
        }
    }
    
    if body:
        request_item["request"]["body"] = body
    
    # Remove None values from URL
    request_item["request"]["url"] = {
        k: v for k, v in request_item["request"]["url"].items() if v is not None
    }
    
    return request_item


def extract_example(json_content: dict, spec: dict) -> dict:
    """Extract example from OpenAPI content definition."""
    # Try direct example
    if "example" in json_content:
        return json_content["example"]
    
    # Try examples (plural)
    if "examples" in json_content:
        examples = json_content["examples"]
        if examples:
            first_example = next(iter(examples.values()), {})
            return first_example.get("value", {})
    
    # Try to build from schema
    if "schema" in json_content:
        schema = json_content["schema"]
        
        # Handle $ref
        if "$ref" in schema:
            ref_path = schema["$ref"].split("/")[-1]
            schema = spec.get("components", {}).get("schemas", {}).get(ref_path, {})
        
        # Try schema example
        if "example" in schema:
            return schema["example"]
        
        # Build minimal example from properties
        if "properties" in schema:
            example = {}
            for prop_name, prop_def in schema["properties"].items():
                if "example" in prop_def:
                    example[prop_name] = prop_def["example"]
                elif prop_def.get("type") == "string":
                    example[prop_name] = "string"
                elif prop_def.get("type") == "integer":
                    example[prop_name] = 0
                elif prop_def.get("type") == "boolean":
                    example[prop_name] = True
            return example
    
    return {}


def create_environment_config(api_name: str, env_name: str, config: dict) -> dict:
    """Create a Postman environment configuration."""
    return {
        "name": f"{api_name} - {env_name}",
        "values": [
            {
                "key": "base_url",
                "value": config["base_url"],
                "enabled": True,
                "type": "default"
            },
            {
                "key": "auth_url",
                "value": config["auth_url"],
                "enabled": True,
                "type": "default"
            },
            {
                "key": "client_id",
                "value": "",
                "enabled": True,
                "type": "secret"
            },
            {
                "key": "client_secret",
                "value": "",
                "enabled": True,
                "type": "secret"
            },
            {
                "key": "jwt_token",
                "value": "",
                "enabled": True,
                "type": "secret"
            },
            {
                "key": "jwt_expiry",
                "value": "",
                "enabled": True,
                "type": "default"
            }
        ]
    }


# =============================================================================
# AWS API GATEWAY INTEGRATION
# =============================================================================

def export_from_api_gateway(api_id: str, stage: str, region: str = None) -> str:
    """Export an OpenAPI spec from AWS API Gateway."""
    try:
        import boto3
    except ImportError:
        print("❌ boto3 required for AWS export. Install with: pip install boto3")
        sys.exit(1)
    
    print(f"    API ID: {api_id}")
    print(f"    Stage: {stage}")
    if region:
        print(f"    Region: {region}")
    
    # Create client
    if region:
        client = boto3.client('apigateway', region_name=region)
    else:
        client = boto3.client('apigateway')
    
    try:
        # Get API info
        api_info = client.get_rest_api(restApiId=api_id)
        api_name = api_info.get('name', 'unknown-api')
        print(f"    API Name: {api_name}")
        
        # Export spec
        response = client.get_export(
            restApiId=api_id,
            stageName=stage,
            exportType='oas30',
            accepts='application/yaml'
        )
        
        spec_content = response['body'].read().decode('utf-8')
        
        # Save to file
        output_path = f"specs/{api_id}-{stage}.yaml"
        Path("specs").mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(spec_content)
        
        print(f"    ✅ Exported to: {output_path}")
        return output_path
        
    except client.exceptions.NotFoundException:
        print(f"    ❌ API not found: {api_id}")
        sys.exit(1)
    except Exception as e:
        print(f"    ❌ Export failed: {e}")
        sys.exit(1)


# =============================================================================
# MAIN SYNC FUNCTION
# =============================================================================

def run_sync(
    spec_path: str,
    workspace_id: str,
    api_key: str,
    dry_run: bool = False,
    aws_api_id: str = None,
    aws_stage: str = None,
    aws_region: str = None,
    skip_validation: bool = False
) -> dict:
    """
    Main sync function. Creates or updates Postman collections and environments.
    
    Returns a summary dict for CI/CD integration.
    """
    start_time = datetime.now()
    summary = {
        "timestamp": start_time.isoformat(),
        "dry_run": dry_run,
        "spec_path": spec_path,
        "workspace_id": workspace_id,
        "success": False,
        "actions": []
    }
    
    print("\n" + "=" * 60)
    print("🚀 POSTMAN ADOPTION KIT - API SYNC")
    print("=" * 60)
    print(f"Timestamp: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()
    
    # Step 0: Export from AWS if specified
    if aws_api_id and aws_stage:
        print("📦 STEP 0: Exporting from AWS API Gateway")
        print("-" * 40)
        spec_path = export_from_api_gateway(aws_api_id, aws_stage, aws_region)
        summary["spec_path"] = spec_path
        summary["aws_export"] = {"api_id": aws_api_id, "stage": aws_stage}
        print()
    
    # Step 1: Load and validate spec
    print("📄 STEP 1: Loading OpenAPI Specification")
    print("-" * 40)
    print(f"    Source: {spec_path}")
    
    try:
        spec, raw_content = load_openapi_spec(spec_path)
    except Exception as e:
        print(f"    ❌ Failed to load spec: {e}")
        summary["error"] = str(e)
        return summary
    
    api_name = spec.get("info", {}).get("title", "API Collection")
    api_version = spec.get("info", {}).get("version", "1.0.0")
    print(f"    API: {api_name}")
    print(f"    Version: {api_version}")
    
    # Calculate spec hash for change detection
    spec_hash = hashlib.md5(raw_content.encode()).hexdigest()[:8]
    print(f"    Hash: {spec_hash}")
    
    summary["api_name"] = api_name
    summary["api_version"] = api_version
    summary["spec_hash"] = spec_hash
    
    # Validate spec
    if not skip_validation:
        issues = validate_openapi_spec(spec)
        if issues:
            print(f"    ⚠️  Validation issues:")
            for issue in issues:
                print(f"       - {issue}")
            if any(issue.startswith("ERROR") for issue in issues):
                print("    ❌ Spec has errors, aborting")
                summary["validation_issues"] = issues
                return summary
        else:
            print("    ✅ Validation passed")
    print()
    
    # Step 2: Initialize Postman client
    print("🔌 STEP 2: Connecting to Postman API")
    print("-" * 40)
    client = PostmanClient(api_key, dry_run=dry_run)
    print("    ✅ Client initialized")
    print()
    
    # Step 3: Create/update collection
    print("📚 STEP 3: Syncing Collection")
    print("-" * 40)
    collection = spec_to_collection(spec, JWT_PREREQUEST_SCRIPT)
    
    path_count = sum(len(folder.get("item", [])) for folder in collection["item"])
    print(f"    Endpoints: {path_count}")
    print(f"    Folders: {len(collection['item'])}")
    
    try:
        result, action = client.upsert_collection(workspace_id, collection)
        collection_id = result.get("uid", result.get("id", "unknown"))
        print(f"    ✅ Collection {action}: {collection_id}")
        summary["actions"].append({
            "type": "collection",
            "action": action,
            "name": api_name,
            "id": collection_id
        })
    except Exception as e:
        print(f"    ❌ Collection sync failed: {e}")
        summary["error"] = str(e)
        return summary
    print()
    
    # Step 4: Create/update environments
    print("🌍 STEP 4: Syncing Environments")
    print("-" * 40)
    
    for env_name, env_config in ENVIRONMENT_CONFIGS.items():
        env = create_environment_config(api_name, env_name, env_config)
        try:
            result, action = client.upsert_environment(workspace_id, env)
            env_id = result.get("uid", result.get("id", "unknown"))
            summary["actions"].append({
                "type": "environment",
                "action": action,
                "name": f"{api_name} - {env_name}",
                "id": env_id
            })
        except Exception as e:
            print(f"    ⚠️  Environment {env_name} failed: {e}")
    print()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("=" * 60)
    print("✅ SYNC COMPLETE")
    print("=" * 60)
    print(f"""
Summary:
    API: {api_name} v{api_version}
    Endpoints: {path_count}
    Environments: {', '.join(ENVIRONMENT_CONFIGS.keys())}
    Duration: {duration:.1f}s
    JWT Auth: Configured

Next Steps:
    1. Open Postman workspace
    2. Select an environment (Dev/QA/UAT/Prod)
    3. Set client_id and client_secret in environment
    4. Start making requests!
""")
    
    summary["success"] = True
    summary["duration_seconds"] = duration
    summary["endpoints_count"] = path_count
    summary["environments"] = list(ENVIRONMENT_CONFIGS.keys())
    
    # Write summary to file for CI/CD
    summary_path = "sync-summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"    Summary written to: {summary_path}")
    
    return summary


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sync OpenAPI specs to Postman",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic sync
    python postman_sync.py --spec specs/api.yaml --workspace-id abc123

    # Dry run (preview without changes)
    python postman_sync.py --spec specs/api.yaml --workspace-id abc123 --dry-run

    # Export from AWS API Gateway and sync
    python postman_sync.py --aws-api-id xyz789 --stage prod --workspace-id abc123

Environment Variables:
    POSTMAN_API_KEY      Your Postman API key (required)
    POSTMAN_WORKSPACE_ID Default workspace ID (optional)
        """
    )
    
    parser.add_argument("--spec", help="Path to OpenAPI spec file (YAML or JSON)")
    parser.add_argument("--workspace-id", 
                        default=os.environ.get("POSTMAN_WORKSPACE_ID", ""),
                        help="Postman workspace ID")
    parser.add_argument("--aws-api-id", help="AWS API Gateway REST API ID")
    parser.add_argument("--stage", default="prod", help="AWS API Gateway stage (default: prod)")
    parser.add_argument("--region", help="AWS region")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--skip-validation", action="store_true", help="Skip spec validation")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.spec and not args.aws_api_id:
        parser.error("Either --spec or --aws-api-id is required")
    
    if not args.workspace_id:
        parser.error("--workspace-id is required (or set POSTMAN_WORKSPACE_ID)")
    
    # Get API key
    api_key = os.environ.get("POSTMAN_API_KEY")
    if not api_key and not args.dry_run:
        print("❌ Error: POSTMAN_API_KEY environment variable is required")
        print("   Get your key at: https://web.postman.co/settings/me/api-keys")
        sys.exit(1)
    
    # Run sync
    summary = run_sync(
        spec_path=args.spec,
        workspace_id=args.workspace_id,
        api_key=api_key or "dry-run-key",
        dry_run=args.dry_run,
        aws_api_id=args.aws_api_id,
        aws_stage=args.stage if args.aws_api_id else None,
        aws_region=args.region,
        skip_validation=args.skip_validation
    )
    
    # Exit with appropriate code
    sys.exit(0 if summary.get("success") else 1)


if __name__ == "__main__":
    main()
