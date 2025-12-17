# Troubleshooting Guide

Quick fixes for common issues.

---

## Authentication Errors

### "401 Unauthorized" or "Invalid API Key"

**Check your API key is set:**
```bash
echo $POSTMAN_API_KEY
# Should output: PMAK-xxxxx
```

**If empty, set it:**
```bash
export POSTMAN_API_KEY="PMAK-your-key-here"
```

**If still failing:**
1. Go to [Postman API Keys](https://web.postman.co/settings/me/api-keys)
2. Revoke old key
3. Generate new key
4. Update your environment variable

---

## Workspace Errors

### "Workspace not found" or "Invalid workspace ID"

**Common mistake:** Using workspace *name* instead of *ID*

**Find your workspace ID:**
1. Open Postman
2. Go to your workspace
3. Look at the URL: `https://web.postman.co/workspace/abc123-def456-...`
4. The ID is `abc123-def456-...` (NOT the workspace name)

**Verify it works:**
```bash
curl -s "https://api.getpostman.com/workspaces/YOUR_WORKSPACE_ID" \
  -H "X-Api-Key: $POSTMAN_API_KEY" | head -20
```

---

## Collection Issues

### "Collection already exists"

**This is normal!** The script is idempotent - it updates existing collections instead of creating duplicates.

Check the output:
- `Collection created: ...` = New collection
- `Collection updated: ...` = Existing collection updated

### Collection not appearing in Postman

1. **Check the right workspace** - Are you looking at the correct one?
2. **Hard refresh Postman:**
   - Mac: `Cmd + Shift + R`
   - Windows: `Ctrl + Shift + R`
3. **Check sync-summary.json:**
   ```bash
   cat sync-summary.json
   ```
   Look for `collection_id` - you can search for this in Postman

### Collection appears but endpoints missing

Your OpenAPI spec might have issues:
```bash
# Validate spec syntax
python3 -c "import yaml; yaml.safe_load(open('specs/your-api.yaml'))"
```

Check for:
- Missing `paths` section
- Invalid YAML syntax
- Empty endpoint definitions

---

## Environment Issues

### Environments not created

The script creates environments based on the spec. Check:

1. **Spec has servers defined:**
   ```yaml
   servers:
     - url: https://api-dev.example.com/v2
       description: Development
   ```

2. **Run with verbose output:**
   ```bash
   python3 scripts/postman_sync.py --spec your-spec.yaml --workspace-id abc123 2>&1 | tee output.log
   ```

### Wrong base_url in environment

Edit the environment in Postman, or modify `environments/*.json` and re-import.

---

## CI/CD Issues

### GitHub Action not triggering

**Check triggers in `.github/workflows/sync.yml`:**
```yaml
on:
  push:
    paths:
      - 'specs/**/*.yaml'  # Only triggers on spec changes
```

**Force trigger manually:**
1. Go to Actions tab
2. Select "Sync Postman Collections"
3. Click "Run workflow"

### GitHub Action fails with auth error

**Add secrets to your repo:**
1. Settings → Secrets → Actions
2. Add `POSTMAN_API_KEY`
3. Add `POSTMAN_WORKSPACE_ID`

**Verify secrets are set:**
- Secrets show as `***` in logs if set correctly
- If you see the actual key in logs, it's NOT set as a secret

---

## Rate Limiting

### "429 Too Many Requests" or "Rate limit exceeded"

The Postman API has rate limits. Solutions:

1. **Wait and retry:**
   ```bash
   sleep 60 && python3 scripts/postman_sync.py ...
   ```

2. **For bulk operations, add delays:**
   ```bash
   for spec in specs/*.yaml; do
     python3 scripts/postman_sync.py --spec "$spec" --workspace-id abc123
     sleep 5  # 5 second delay between syncs
   done
   ```

---

## Mock Server Issues

### Mock server won't start

```bash
cd mock-api
npm install  # Make sure dependencies are installed
npm start
```

**Port already in use:**
```bash
# Find what's using port 3000
lsof -i :3000

# Kill it or use different port
PORT=3001 npm start
```

### Postman can't reach localhost

**Most common cause: Wrong agent selected!**

1. **Use Desktop Agent** (not Cloud Agent)
   - Look at bottom-right of Postman
   - Click the agent icon
   - Select **"Desktop Agent"**
   - Without this, Postman CAN'T reach localhost!

2. **Enable local network access** in browser (if using web version)
3. **Check firewall** isn't blocking port 3000

### Pre-request script errors with mock server

The collection's pre-request script is built for production JWT auth. For mock testing:

1. **Option A: Comment out the script**
   - Open collection → Pre-request Script tab
   - Select all → Comment out (Cmd+/ or Ctrl+/)
   - The mock server uses simpler auth

2. **Option B: Just get a token manually**
   ```bash
   curl -X POST http://localhost:3000/oauth/token \
     -d "grant_type=client_credentials&client_id=test&client_secret=test"
   ```
   - Copy the `access_token`
   - Paste into your environment's `jwt_token` variable

---

## Script Errors

### "ModuleNotFoundError: No module named 'requests'"

```bash
pip install -r requirements.txt
# or
pip install requests pyyaml
```

### "FileNotFoundError: specs/..."

Make sure you're in the repo root directory:
```bash
pwd  # Should show /path/to/boyntonmacgilbert-api-toolkit
ls specs/  # Should show your .yaml files
```

---

## Getting Help

### Collect debug info

```bash
# 1. Python version
python3 --version

# 2. Installed packages
pip list | grep -E "requests|pyyaml"

# 3. Environment variables (redacted)
echo "API Key set: $([ -n "$POSTMAN_API_KEY" ] && echo 'YES' || echo 'NO')"

# 4. Run with full output
python3 scripts/postman_sync.py --spec specs/your-api.yaml --workspace-id abc123 2>&1 | tee debug.log
```

### Open an issue

Include:
- What you ran (command)
- What you expected
- What happened (full error)
- Output of debug commands above

---

## Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| 401 error | Check `POSTMAN_API_KEY` is set |
| Workspace not found | Use ID from URL, not name |
| Collection exists | Normal - it updates existing |
| Not appearing | Hard refresh Postman |
| Rate limit | Wait 60 seconds |
| CI/CD fails | Check GitHub secrets |
