# Getting Started Guide

> How to set up and use the Postman Adoption Kit

## Prerequisites

Before you begin, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] A Postman account (free tier is sufficient)
- [ ] Git installed
- [ ] Access to your organization's API credentials

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/postman-adoption-kit.git
cd postman-adoption-kit
```

---

## Step 2: Set Up Python Environment

### macOS / Linux

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Windows

```powershell
# Create a virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3: Get Your Postman API Key

1. Log in to [Postman](https://web.postman.co/)
2. Click your **avatar** in the top right
3. Click **Settings**
4. Click **API keys** in the left sidebar
5. Click **Generate API Key**
6. Give it a name like "Adoption Kit"
7. **Copy the key** — you won't see it again!

---

## Step 4: Find Your Workspace ID

1. Go to [Postman Workspaces](https://web.postman.co/workspaces)
2. Create a new workspace or open an existing one
3. Look at the URL: `https://web.postman.co/workspace/Name~{workspace-id}/overview`
4. Copy the ID after the `~` (e.g., `8f593659-4785-4292-bb7a-2937d37e9519`)

---

## Step 5: Configure Environment Variables

### Option A: Export in Terminal (Temporary)

```bash
export POSTMAN_API_KEY="PMAK-your-key-here"
export POSTMAN_WORKSPACE_ID="your-workspace-id"
```

### Option B: Create a .env File (Recommended)

Create a `.env` file in the project root:

```bash
# .env
POSTMAN_API_KEY=PMAK-your-key-here
POSTMAN_WORKSPACE_ID=your-workspace-id
```

Then load it:

```bash
source .env
```

> ⚠️ **Important**: Never commit `.env` files to Git. The `.gitignore` already excludes it.

---

## Step 6: Run Your First Sync

### Dry Run (No Changes)

Test the script without making any changes:

```bash
python3 scripts/postman_sync.py \
  --spec specs/payment-refund-api-openapi.yaml \
  --workspace-id $POSTMAN_WORKSPACE_ID \
  --dry-run
```

You should see:
```
============================================================
POSTMAN ADOPTION KIT - API SYNC
============================================================

[DRY RUN] Would create collection: Payment Processing API - Refund Service
[DRY RUN] Would create 4 environments: Dev, QA, UAT, Prod
```

### Actual Sync

Run for real:

```bash
python3 scripts/postman_sync.py \
  --spec specs/payment-refund-api-openapi.yaml \
  --workspace-id $POSTMAN_WORKSPACE_ID
```

---

## Step 7: Verify in Postman

1. Open your Postman workspace
2. You should see:
   - **Collection**: Payment Processing API - Refund Service
   - **Environments**: Dev, QA, UAT, Prod

3. Click on the collection to explore the endpoints
4. Click on **Environments** in the sidebar to see all four environments

---

## Step 8: Configure Your Environment

1. In Postman, click **Environments** in the sidebar
2. Select **Payment Refund API - Dev**
3. Fill in your credentials:
   - `client_id`: Your OAuth client ID
   - `client_secret`: Your OAuth client secret
4. Click **Save**

The JWT pre-request script will automatically fetch tokens when you make requests.

---

## Step 9: Make Your First Request

1. In the collection, expand **Refunds**
2. Click **Create a new refund**
3. Select the **Dev** environment from the dropdown (top right)
4. Click **Send**

If everything is configured correctly, you'll get a response!

---

## Adding a New API

To add another API to your workspace:

```bash
# 1. Place the OpenAPI spec in the specs folder
cp path/to/new-api.yaml specs/

# 2. Run the sync
python3 scripts/postman_sync.py \
  --spec specs/new-api.yaml \
  --workspace-id $POSTMAN_WORKSPACE_ID
```

---

## Troubleshooting

### "POSTMAN_API_KEY environment variable is required"

Make sure you've exported the variable:
```bash
export POSTMAN_API_KEY="your-key"
```

### "401 Unauthorized" from Postman API

Your API key may be invalid or expired. Generate a new one in Postman settings.

### "Workspace not found"

Double-check your workspace ID. Make sure you copied the full ID after the `~` in the URL.

### Python command not found

Try `python3` instead of `python`, or check your Python installation.

### Virtual environment issues

```bash
# Remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Next Steps

- [ ] Set up the [CI/CD pipeline](./CI_CD_SETUP.md) for automated sync
- [ ] Read the [API Guide](./API_GUIDE.md) to understand the Payment Refund API
- [ ] Explore the [Scaling Guide](./SCALING_GUIDE.md) to add more APIs

---

## Getting Help

- **Slack**: #postman-adoption
- **Email**: platform-team@example.com
- **Issues**: Open a GitHub issue in this repository
