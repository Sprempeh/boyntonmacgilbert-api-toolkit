# CI/CD Pipeline Setup Guide

> Automate Postman collection sync with GitHub Actions

## Overview

This guide explains how to set up automated synchronization between your OpenAPI specs and Postman collections using GitHub Actions. When you push changes to spec files, the pipeline automatically updates your Postman workspace.

---

## How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Developer      │     │  GitHub Actions  │     │  Postman        │
│  pushes spec    │────▶│  workflow runs   │────▶│  collection     │
│  change         │     │  sync script     │     │  updated        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Triggers:**
- Push to `specs/*.yaml` files
- Daily schedule (6 AM UTC)
- Manual trigger (workflow_dispatch)

---

## Step 1: Fork/Clone the Repository

If you haven't already:

```bash
git clone https://github.com/your-org/postman-adoption-kit.git
cd postman-adoption-kit
```

---

## Step 2: Add GitHub Secrets

Go to your repository on GitHub:

1. Click **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `POSTMAN_API_KEY` | Your Postman API key |
| `POSTMAN_WORKSPACE_ID` | Your workspace ID |

### How to Get These Values

**POSTMAN_API_KEY:**
1. Go to [Postman Settings](https://web.postman.co/settings/me/api-keys)
2. Generate a new API key
3. Copy the entire key (starts with `PMAK-`)

**POSTMAN_WORKSPACE_ID:**
1. Open your workspace in Postman
2. Look at the URL: `https://web.postman.co/workspace/Name~{id}/overview`
3. Copy the ID after the `~`

---

## Step 3: Review the Workflow File

The workflow is already configured in `.github/workflows/sync.yml`:

```yaml
name: Sync Postman Collections

on:
  # Trigger on spec file changes
  push:
    paths:
      - 'specs/**/*.yaml'
      - 'specs/**/*.yml'
    branches:
      - main

  # Daily sync to catch any drift
  schedule:
    - cron: '0 6 * * *'

  # Allow manual trigger
  workflow_dispatch:
    inputs:
      spec_file:
        description: 'Specific spec file to sync (or "all")'
        default: 'all'
      dry_run:
        description: 'Dry run mode (true/false)'
        default: 'false'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests pyyaml
      
      - name: Sync to Postman
        env:
          POSTMAN_API_KEY: ${{ secrets.POSTMAN_API_KEY }}
        run: |
          python scripts/postman_sync.py \
            --spec specs/payment-refund-api-openapi.yaml \
            --workspace-id ${{ secrets.POSTMAN_WORKSPACE_ID }}
```

---

## Step 4: Test the Pipeline

### Option A: Push a Spec Change

Make a small change to the spec file:

```bash
# Edit the spec (e.g., update the version)
nano specs/payment-refund-api-openapi.yaml

# Change version from 2.1.0 to 2.1.1
# Save and exit

# Commit and push
git add specs/payment-refund-api-openapi.yaml
git commit -m "Bump API version to 2.1.1"
git push origin main
```

Go to GitHub → **Actions** tab to see the workflow running.

### Option B: Manual Trigger

1. Go to GitHub → **Actions** tab
2. Click **Sync Postman Collections** in the left sidebar
3. Click **Run workflow** dropdown
4. Select options:
   - `spec_file`: "all" or specific file path
   - `dry_run`: "true" for testing, "false" for real sync
5. Click **Run workflow**

---

## Step 5: Verify the Sync

After the workflow completes:

1. Open your Postman workspace
2. Check that the collection is updated
3. Verify the API version matches your spec

---

## Advanced Configuration

### Syncing Multiple APIs

To sync multiple specs, update the workflow:

```yaml
- name: Sync all specs
  run: |
    for spec_file in specs/*.yaml; do
      echo "Syncing: $spec_file"
      python scripts/postman_sync.py \
        --spec "$spec_file" \
        --workspace-id ${{ secrets.POSTMAN_WORKSPACE_ID }}
    done
```

### Environment-Specific Workspaces

For different workspaces per environment:

```yaml
env:
  DEV_WORKSPACE_ID: "dev-workspace-id"
  PROD_WORKSPACE_ID: "prod-workspace-id"

steps:
  - name: Sync to Dev
    run: |
      python scripts/postman_sync.py \
        --spec specs/payment-refund-api-openapi.yaml \
        --workspace-id $DEV_WORKSPACE_ID
  
  - name: Sync to Prod (main branch only)
    if: github.ref == 'refs/heads/main'
    run: |
      python scripts/postman_sync.py \
        --spec specs/payment-refund-api-openapi.yaml \
        --workspace-id $PROD_WORKSPACE_ID
```

### Slack Notifications

Add a notification step:

```yaml
- name: Notify Slack
  if: always()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Postman Sync: ${{ job.status }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Postman Collection Sync*\nStatus: ${{ job.status }}\nWorkflow: ${{ github.workflow }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Troubleshooting

### Workflow doesn't trigger on push

Check that:
- You're pushing to the `main` branch
- The file path matches `specs/**/*.yaml`
- GitHub Actions is enabled for your repository

### "Secret not found" error

Ensure secrets are added at the repository level:
- Settings → Secrets and variables → Actions → Repository secrets

### Sync succeeds but Postman not updated

- Verify the workspace ID is correct
- Check if the API key has appropriate permissions
- Look at the workflow logs for error messages

### Rate limiting

If you're syncing many specs, you might hit Postman's rate limits. Add delays:

```yaml
- name: Sync with delay
  run: |
    for spec_file in specs/*.yaml; do
      python scripts/postman_sync.py --spec "$spec_file" --workspace-id $WORKSPACE_ID
      sleep 5  # Wait 5 seconds between syncs
    done
```

---

## Best Practices

1. **Always test with dry run first**
   ```bash
   python scripts/postman_sync.py --spec specs/api.yaml --workspace-id $ID --dry-run
   ```

2. **Use branch protection** — Require PR reviews before merging spec changes

3. **Version your specs** — Include version in the spec's `info.version` field

4. **Monitor workflow runs** — Set up Slack/email notifications for failures

5. **Keep secrets secure** — Never commit API keys, use GitHub secrets

---

## Next Steps

- Set up [Pull Request validation](./PR_VALIDATION.md) to test spec changes before merging
- Configure [webhooks](./WEBHOOKS.md) for real-time sync notifications
- Read the [Scaling Guide](./SCALING_GUIDE.md) to add more APIs
