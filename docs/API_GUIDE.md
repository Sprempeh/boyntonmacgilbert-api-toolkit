# Payment Refund API - Developer Guide

> Complete guide for integrating with the Payment Refund API

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Environments](#environments)
4. [Endpoints](#endpoints)
5. [Error Handling](#error-handling)
6. [Code Examples](#code-examples)
7. [Testing](#testing)
8. [FAQ](#faq)

---

## Overview

The Payment Refund API enables you to process refunds for captured payment transactions. It supports full and partial refunds, status tracking, and cancellation of pending refunds.

### Base URLs

| Environment | URL |
|-------------|-----|
| Production | `https://api.payments.example.com/v2` |
| UAT | `https://api-uat.payments.example.com/v2` |
| QA | `https://api-qa.payments.example.com/v2` |
| Development | `https://api-dev.payments.example.com/v2` |

### Rate Limits

| Tier | Limit |
|------|-------|
| Standard | 100 requests/minute |
| Enterprise | 1,000 requests/minute |

Rate limit headers are included in every response:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

---

## Authentication

The API supports two authentication methods:

### OAuth 2.0 (External Partners)

Use OAuth 2.0 for external partner integrations.

```bash
# Request an access token
curl -X POST https://auth.payments.example.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=refunds:read refunds:write"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "refunds:read refunds:write"
}
```

### JWT (Internal Services)

Use JWT for service-to-service authentication within the organization.

```bash
# Include the JWT in the Authorization header
curl -X GET https://api.payments.example.com/v2/refunds \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Token Refresh

Tokens expire after 1 hour. Implement token refresh logic:

```python
import time

class TokenManager:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.expiry = 0
    
    def get_token(self):
        # Refresh if expired or expiring within 60 seconds
        if time.time() >= self.expiry - 60:
            self._refresh_token()
        return self.token
    
    def _refresh_token(self):
        response = requests.post(
            "https://auth.payments.example.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        data = response.json()
        self.token = data["access_token"]
        self.expiry = time.time() + data["expires_in"]
```

---

## Environments

### Setting Up Your Environment

1. **Get credentials** from the Payment Platform team
2. **Choose the right environment** for your use case:
   - **Dev**: For local development and experimentation
   - **QA**: For automated testing and CI/CD
   - **UAT**: For user acceptance testing and demos
   - **Prod**: For production traffic only

### Environment Variables

Set these environment variables in your application:

```bash
# Development
export PAYMENT_API_BASE_URL="https://api-dev.payments.example.com/v2"
export PAYMENT_AUTH_URL="https://auth-dev.payments.example.com"
export PAYMENT_CLIENT_ID="dev_client_id"
export PAYMENT_CLIENT_SECRET="dev_client_secret"

# Production
export PAYMENT_API_BASE_URL="https://api.payments.example.com/v2"
export PAYMENT_AUTH_URL="https://auth.payments.example.com"
export PAYMENT_CLIENT_ID="prod_client_id"
export PAYMENT_CLIENT_SECRET="prod_client_secret"
```

---

## Endpoints

### Create Refund

**POST** `/refunds`

Creates a new refund for a captured transaction.

#### Request

```bash
curl -X POST https://api.payments.example.com/v2/refunds \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transactionId": "txn_1234567890abcdef",
    "amount": 2500,
    "currency": "USD",
    "reason": "Customer requested refund",
    "notifyCustomer": true,
    "metadata": {
      "ticketNumber": "TKT-12345",
      "initiatedBy": "support@example.com"
    }
  }'
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transactionId` | string | Yes | Original transaction ID (format: `txn_*`) |
| `amount` | integer | No | Refund amount in cents. Omit for full refund |
| `currency` | string | No | ISO 4217 currency code. Defaults to original transaction currency |
| `reason` | string | Yes | Human-readable reason for the refund |
| `notifyCustomer` | boolean | No | Send email notification to customer. Default: `false` |
| `metadata` | object | No | Key-value pairs for tracking (max 10 keys, 500 chars each) |

#### Response (201 Created)

```json
{
  "refundId": "rfnd_abc123def456",
  "transactionId": "txn_1234567890abcdef",
  "status": "pending",
  "amount": 5000,
  "currency": "USD",
  "refundAmount": 2500,
  "refundCurrency": "USD",
  "reason": "Customer requested refund",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:30:00Z",
  "estimatedCompletionTime": "2024-01-15T14:30:00Z",
  "metadata": {
    "ticketNumber": "TKT-12345",
    "initiatedBy": "support@example.com"
  },
  "links": {
    "self": "/refunds/rfnd_abc123def456",
    "status": "/refunds/rfnd_abc123def456/status",
    "cancel": "/refunds/rfnd_abc123def456/cancel"
  }
}
```

#### Business Rules

- Refunds can only be issued for transactions in `captured` status
- Partial refunds must not exceed the original transaction amount
- Refunds cannot be created more than 180 days after the original transaction
- Maximum of 5 refunds per transaction

---

### List Refunds

**GET** `/refunds`

Retrieves a paginated list of refunds with optional filtering.

#### Request

```bash
curl -X GET "https://api.payments.example.com/v2/refunds?status=pending&page=1&pageSize=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `pending`, `processing`, `completed`, `failed`, `cancelled` |
| `transactionId` | string | Filter by original transaction ID |
| `startDate` | string | Filter refunds created after this date (ISO 8601) |
| `endDate` | string | Filter refunds created before this date (ISO 8601) |
| `page` | integer | Page number (default: 1) |
| `pageSize` | integer | Results per page (default: 20, max: 100) |

#### Response (200 OK)

```json
{
  "refunds": [
    {
      "refundId": "rfnd_abc123def456",
      "transactionId": "txn_1234567890abcdef",
      "status": "pending",
      "amount": 5000,
      "refundAmount": 2500,
      "currency": "USD",
      "createdAt": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 20,
    "totalPages": 3,
    "totalItems": 47,
    "hasNext": true,
    "hasPrevious": false
  }
}
```

---

### Get Refund Details

**GET** `/refunds/{refundId}`

Retrieves detailed information about a specific refund.

#### Request

```bash
curl -X GET https://api.payments.example.com/v2/refunds/rfnd_abc123def456 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Response (200 OK)

```json
{
  "refundId": "rfnd_abc123def456",
  "transactionId": "txn_1234567890abcdef",
  "status": "completed",
  "amount": 5000,
  "currency": "USD",
  "refundAmount": 2500,
  "refundCurrency": "USD",
  "reason": "Customer requested refund",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T14:25:00Z",
  "completedAt": "2024-01-15T14:25:00Z",
  "metadata": {
    "ticketNumber": "TKT-12345"
  },
  "links": {
    "self": "/refunds/rfnd_abc123def456",
    "transaction": "/transactions/txn_1234567890abcdef"
  }
}
```

---

### Get Refund Status

**GET** `/refunds/{refundId}/status`

Retrieves the current status and status history of a refund.

#### Request

```bash
curl -X GET https://api.payments.example.com/v2/refunds/rfnd_abc123def456/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Response (200 OK)

```json
{
  "refundId": "rfnd_abc123def456",
  "status": "completed",
  "updatedAt": "2024-01-15T14:25:00Z",
  "completedAt": "2024-01-15T14:25:00Z",
  "statusHistory": [
    {
      "status": "pending",
      "timestamp": "2024-01-15T10:30:00Z",
      "message": "Refund request created"
    },
    {
      "status": "processing",
      "timestamp": "2024-01-15T12:00:00Z",
      "message": "Refund is being processed"
    },
    {
      "status": "completed",
      "timestamp": "2024-01-15T14:25:00Z",
      "message": "Refund completed successfully"
    }
  ]
}
```

---

### Cancel Refund

**POST** `/refunds/{refundId}/cancel`

Cancels a pending refund. Only refunds in `pending` status can be cancelled.

#### Request

```bash
curl -X POST https://api.payments.example.com/v2/refunds/rfnd_abc123def456/cancel \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Customer changed their mind"
  }'
```

#### Response (200 OK)

```json
{
  "refundId": "rfnd_abc123def456",
  "status": "cancelled",
  "cancelledAt": "2024-01-15T11:00:00Z",
  "cancellationReason": "Customer changed their mind"
}
```

---

### Health Check

**GET** `/health`

Check if the API is healthy and available.

#### Request

```bash
curl -X GET https://api.payments.example.com/v2/health
```

#### Response (200 OK)

```json
{
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "dependencies": {
    "database": "healthy",
    "paymentGateway": "healthy",
    "notificationService": "healthy"
  }
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "transactionId",
    "issue": "Invalid format"
  },
  "code": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request parameters |
| 400 | `BUSINESS_RULE_VIOLATION` | Request violates business rules |
| 401 | `AUTHENTICATION_ERROR` | Invalid or missing authentication |
| 403 | `AUTHORIZATION_ERROR` | Insufficient permissions |
| 404 | `RESOURCE_NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Resource state conflict |
| 429 | `RATE_LIMIT_ERROR` | Too many requests |
| 500 | `SERVER_ERROR` | Internal server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

### Common Errors

#### Invalid Refund Amount
```json
{
  "error": "INVALID_REFUND_AMOUNT",
  "message": "Refund amount exceeds the original transaction amount",
  "details": {
    "transactionId": "txn_1234567890abcdef",
    "originalAmount": 5000,
    "requestedRefundAmount": 6000,
    "currency": "USD"
  },
  "code": "VALIDATION_ERROR"
}
```

#### Transaction Not Eligible
```json
{
  "error": "TRANSACTION_NOT_ELIGIBLE",
  "message": "Refunds can only be issued for transactions in 'captured' status",
  "details": {
    "transactionId": "txn_1234567890abcdef",
    "currentStatus": "authorized",
    "eligibleStatuses": ["captured"]
  },
  "code": "BUSINESS_RULE_VIOLATION"
}
```

### Retry Strategy

For transient errors (5xx), implement exponential backoff:

```python
import time
import random

def make_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code < 500:
            return response
        
        # Exponential backoff with jitter
        wait_time = (2 ** attempt) + random.uniform(0, 1)
        time.sleep(wait_time)
    
    raise Exception("Max retries exceeded")
```

---

## Code Examples

### Python

```python
import requests
import os

class RefundClient:
    def __init__(self):
        self.base_url = os.environ.get("PAYMENT_API_BASE_URL")
        self.token = os.environ.get("PAYMENT_API_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def create_refund(self, transaction_id, amount=None, reason=""):
        payload = {
            "transactionId": transaction_id,
            "reason": reason,
            "notifyCustomer": True
        }
        if amount:
            payload["amount"] = amount
        
        response = requests.post(
            f"{self.base_url}/refunds",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_refund(self, refund_id):
        response = requests.get(
            f"{self.base_url}/refunds/{refund_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def cancel_refund(self, refund_id, reason):
        response = requests.post(
            f"{self.base_url}/refunds/{refund_id}/cancel",
            headers=self.headers,
            json={"reason": reason}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = RefundClient()

# Create a full refund
refund = client.create_refund(
    transaction_id="txn_1234567890abcdef",
    reason="Customer requested refund"
)
print(f"Created refund: {refund['refundId']}")

# Check status
details = client.get_refund(refund['refundId'])
print(f"Status: {details['status']}")
```

### Node.js

```javascript
const axios = require('axios');

class RefundClient {
  constructor() {
    this.baseUrl = process.env.PAYMENT_API_BASE_URL;
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: {
        'Authorization': `Bearer ${process.env.PAYMENT_API_TOKEN}`,
        'Content-Type': 'application/json'
      }
    });
  }

  async createRefund(transactionId, amount = null, reason = '') {
    const payload = {
      transactionId,
      reason,
      notifyCustomer: true
    };
    if (amount) payload.amount = amount;

    const response = await this.client.post('/refunds', payload);
    return response.data;
  }

  async getRefund(refundId) {
    const response = await this.client.get(`/refunds/${refundId}`);
    return response.data;
  }

  async cancelRefund(refundId, reason) {
    const response = await this.client.post(`/refunds/${refundId}/cancel`, { reason });
    return response.data;
  }
}

// Usage
const client = new RefundClient();

async function main() {
  // Create a partial refund
  const refund = await client.createRefund(
    'txn_1234567890abcdef',
    2500, // $25.00
    'Partial refund for damaged item'
  );
  console.log(`Created refund: ${refund.refundId}`);

  // Check status
  const details = await client.getRefund(refund.refundId);
  console.log(`Status: ${details.status}`);
}

main().catch(console.error);
```

### cURL

```bash
# Set your token
export TOKEN="your_jwt_token"
export BASE_URL="https://api-dev.payments.example.com/v2"

# Create a refund
curl -X POST "$BASE_URL/refunds" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transactionId": "txn_1234567890abcdef",
    "amount": 2500,
    "reason": "Customer requested refund"
  }'

# Get refund details
curl -X GET "$BASE_URL/refunds/rfnd_abc123def456" \
  -H "Authorization: Bearer $TOKEN"

# Cancel a refund
curl -X POST "$BASE_URL/refunds/rfnd_abc123def456/cancel" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer changed mind"}'
```

---

## Testing

### Using Postman

1. Import the collection from the Postman workspace
2. Select the appropriate environment (Dev/QA/UAT/Prod)
3. Set your `client_id` and `client_secret` in the environment
4. The pre-request script will automatically handle authentication

### Test Transaction IDs

Use these test transaction IDs in non-production environments:

| Transaction ID | Scenario |
|----------------|----------|
| `txn_test_success_full` | Successful full refund |
| `txn_test_success_partial` | Successful partial refund |
| `txn_test_not_captured` | Returns "not captured" error |
| `txn_test_max_refunds` | Returns "max refunds exceeded" error |
| `txn_test_expired` | Returns "transaction expired" error |
| `txn_test_slow` | Simulates slow processing (5 second delay) |
| `txn_test_fail` | Simulates refund failure |

---

## FAQ

### How long does a refund take to process?

Refunds typically complete within 3-5 business days. The `estimatedCompletionTime` field provides a more accurate estimate.

### Can I refund a transaction multiple times?

Yes, up to 5 refunds per transaction, as long as the total refunded amount doesn't exceed the original transaction amount.

### What happens if a refund fails?

The refund status will change to `failed` with a `failureReason`. You can retry by creating a new refund request.

### How do I handle webhooks for refund status changes?

Subscribe to the `refund.updated` webhook event. See the Webhooks documentation for setup instructions.

### What's the difference between "pending" and "processing"?

- **Pending**: Refund created, awaiting processing
- **Processing**: Refund is actively being processed by the payment gateway

---

## Support

- **Documentation**: https://docs.example.com/payment-apis
- **Support Portal**: https://support.example.com
- **Email**: payment-platform@example.com
- **Slack**: #payment-platform-support
