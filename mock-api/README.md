# Mock API Server

A fully functional mock server that simulates the Payment Refund API for demos and testing.

## Quick Start

```bash
cd mock-api
npm install
npm start
```

The server runs at `http://localhost:3000`

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v2/health` | Health check |
| POST | `/v2/refunds` | Create a refund |
| GET | `/v2/refunds` | List refunds |
| GET | `/v2/refunds/:id` | Get refund details |
| GET | `/v2/refunds/:id/status` | Get refund status history |
| POST | `/v2/refunds/:id/cancel` | Cancel a pending refund |
| POST | `/oauth/token` | Get an access token |

## Authentication

Get a token first:

```bash
curl -X POST http://localhost:3000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=test" \
  -d "client_secret=test"
```

Use the token in subsequent requests:

```bash
curl http://localhost:3000/v2/refunds \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Test Transactions

| Transaction ID | Scenario |
|----------------|----------|
| `txn_1234567890abcdef` | Normal captured transaction ($50) |
| `txn_test_success_full` | Full refund succeeds ($75) |
| `txn_test_not_captured` | Returns "not captured" error |
| `txn_test_max_refunds` | Returns "max refunds exceeded" |

## Example: Create a Refund

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:3000/oauth/token \
  -d "grant_type=client_credentials&client_id=test&client_secret=test" | jq -r '.access_token')

# Create refund
curl -X POST http://localhost:3000/v2/refunds \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transactionId": "txn_1234567890abcdef",
    "amount": 2500,
    "reason": "Customer requested refund"
  }'
```

## Using with Postman

1. Start the mock server: `npm start`
2. In Postman, create a "Local" environment with:
   - `base_url`: `http://localhost:3000/v2`
   - `auth_url`: `http://localhost:3000`
   - `client_id`: `test`
   - `client_secret`: `test`
3. Select the Local environment and make requests!

## Simulating Refund Completion

To simulate a refund completing (for demo purposes):

```bash
curl -X POST http://localhost:3000/v2/refunds/REFUND_ID/simulate-complete \
  -H "Authorization: Bearer $TOKEN"
```
