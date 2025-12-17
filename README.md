# Postman API Sync Toolkit

Automatically sync OpenAPI specs to Postman collections. One command, 30 seconds, done.

```bash
python3 scripts/postman_sync.py --spec specs/your-api.yaml --workspace-id abc123
```

---

## Quick Start (5 minutes)

### 1. Prerequisites

- Python 3.8+
- Postman API key ([get one here](https://web.postman.co/settings/me/api-keys))
- Postman workspace ID (from URL: `https://web.postman.co/workspace/{workspace-id}`)

### 2. Install

```bash
git clone https://github.com/Sprempeh/boyntonmacgilbert-api-toolkit.git
cd boyntonmacgilbert-api-toolkit
pip install -r requirements.txt
```

### 3. Configure

```bash
export POSTMAN_API_KEY="PMAK-xxxxx"
```

### 4. Run

```bash
python3 scripts/postman_sync.py \
  --spec specs/payment-refund-api-openapi.yaml \
  --workspace-id YOUR_WORKSPACE_ID
```

**That's it.** Your collection is now in Postman with all environments configured.

---

## What It Does

| Input | Output |
|-------|--------|
| OpenAPI spec file | ✅ Postman collection with all endpoints |
| | ✅ Dev, QA, UAT, Prod environments |
| | ✅ JWT authentication pre-configured |
| | ✅ Request examples populated |

**Idempotent:** Run it again and it updates existing collections (no duplicates).

---

## Commands

### Basic sync
```bash
python3 scripts/postman_sync.py \
  --spec specs/your-api.yaml \
  --workspace-id abc123
```

### Dry run (preview without changes)
```bash
python3 scripts/postman_sync.py \
  --spec specs/your-api.yaml \
  --workspace-id abc123 \
  --dry-run
```

### Sync all specs in folder
```bash
for spec in specs/*.yaml; do
  python3 scripts/postman_sync.py --spec "$spec" --workspace-id abc123
done
```

---

## Adding a New API

```bash
# 1. Drop your OpenAPI spec in specs/
cp ~/my-new-api.yaml specs/

# 2. Run sync
python3 scripts/postman_sync.py --spec specs/my-new-api.yaml --workspace-id abc123

# 3. Done - check Postman
```

---

## CI/CD (Auto-sync on Git Push)

Already configured! When you push changes to `specs/*.yaml`, GitHub Actions automatically syncs to Postman.

### Setup (one-time)

Add these secrets to your GitHub repo (Settings → Secrets):

| Secret | Value |
|--------|-------|
| `POSTMAN_API_KEY` | Your API key |
| `POSTMAN_WORKSPACE_ID` | Target workspace |

### Triggers

- ✅ Push to `specs/**/*.yaml`
- ✅ Daily at 6 AM UTC
- ✅ Manual (Actions → Run workflow)

---

## Local Testing (Mock Server)

Test API calls without real credentials:

```bash
# Terminal 1: Start mock server
cd mock-api && npm install && npm start

# Terminal 2: Run sync, then test in Postman
# Select "Local" environment → base_url = http://localhost:3000/v2
```

See [mock-api/README.md](mock-api/README.md) for test scenarios.

---

## Project Structure

```
├── scripts/
│   └── postman_sync.py      # Main sync script
├── specs/                    # Your OpenAPI specs go here
│   ├── payment-refund-api-openapi.yaml
│   └── payment-authorization-api-openapi.yaml
├── environments/             # Environment templates
├── mock-api/                 # Local mock server
├── postman/
│   └── jwt-pre-request.js   # Auto-auth script
└── .github/workflows/
    └── sync.yml             # CI/CD workflow
```

---

## Troubleshooting

### "401 Unauthorized"
```bash
# Check your API key is set
echo $POSTMAN_API_KEY

# Regenerate if needed: https://web.postman.co/settings/me/api-keys
```

### "Workspace not found"
```bash
# Workspace ID is in the URL, NOT the workspace name
# https://web.postman.co/workspace/abc123-def456 → use "abc123-def456"
```

### "Collection already exists"
This is fine! The script is idempotent - it updates existing collections.

### "Rate limit exceeded"
Wait 60 seconds and try again. The Postman API has rate limits.

### Script runs but nothing in Postman?
1. Check you're looking at the right workspace
2. Hard refresh Postman (Cmd+Shift+R / Ctrl+Shift+R)
3. Check the `sync-summary.json` output file

---

## Documentation

| Doc | What it covers |
|-----|----------------|
| [Getting Started](docs/GETTING_STARTED.md) | Detailed setup guide |
| [API Guide](docs/API_GUIDE.md) | Script parameters & options |
| [CI/CD Setup](docs/CI_CD_SETUP.md) | GitHub Actions config |
| [Governance Model](docs/GOVERNANCE_MODEL.md) | Workspace organization |

---

## Support

Questions? Issues? 
- Open a GitHub issue
- Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## Why This Exists

See [BUSINESS_CASE.md](docs/BUSINESS_CASE.md) for the full story on ROI and scaling strategy.

**TL;DR:** API discovery dropped from 47 minutes to 30 seconds. That's $218K/year in recovered engineering time.
