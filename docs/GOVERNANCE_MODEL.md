# Workspace Governance Model

> Prevent future sprawl and maintain organizational sanity

---

## The Problem We're Solving

**Current State:**
- 413 shared workspaces
- Inconsistent naming
- No clear ownership
- Duplicate collections
- Engineers can't find anything

**Target State:**
- < 50 well-organized workspaces
- Clear naming conventions
- Defined ownership
- Single source of truth per API
- Engineers find what they need in seconds

---

## Workspace Structure

### Recommended Hierarchy

```
Organization
│
├── 🏢 Platform Workspaces (shared infrastructure)
│   ├── Payment Processing
│   ├── Order Management
│   ├── Customer Identity
│   └── Notifications
│
├── 🔧 Team Workspaces (team-specific work)
│   ├── Team Alpha - Development
│   ├── Team Beta - Development
│   └── QA Automation
│
└── 📦 Archive (deprecated, read-only)
    └── [Archived workspaces]
```

### Workspace Types

| Type | Purpose | Visibility | Who Creates |
|------|---------|------------|-------------|
| **Platform** | Official API collections | Organization | Platform Team |
| **Team** | Team-specific development | Team | Team Lead |
| **Personal** | Individual experimentation | Private | Anyone |
| **Archive** | Deprecated content | Read-only | Admin |

---

## Naming Conventions

### Workspaces

```
[Domain] - [Type]

Examples:
✅ Payment Processing - Platform
✅ Order Management - Platform
✅ Team Alpha - Development
✅ QA Automation - Shared

❌ Johns workspace
❌ test
❌ api stuff
❌ Payment Processing (copy)
```

### Collections

```
[API Name] v[Version]

Examples:
✅ Payment Refund API v2.1.0
✅ Authorization Service v2.0.0
✅ Customer API v3.2.1

❌ refunds
❌ my collection
❌ test API calls
```

### Environments

```
[API Name] - [Environment]

Examples:
✅ Payment Refund API - Dev
✅ Payment Refund API - QA
✅ Payment Refund API - UAT
✅ Payment Refund API - Prod

❌ dev
❌ production
❌ my env
```

---

## Ownership Model

### Every Workspace Must Have

1. **Primary Owner** — Responsible for maintenance
2. **Backup Owner** — Covers when primary is unavailable
3. **Description** — Clear purpose documented
4. **Review Cadence** — How often it's reviewed

### Ownership Documentation

| Workspace | Primary Owner | Backup | Review Cadence |
|-----------|--------------|--------|----------------|
| Payment Processing | @jane.smith | @john.doe | Monthly |
| Order Management | @alice.wong | @bob.chen | Monthly |
| Team Alpha - Dev | @team-alpha-lead | @senior-dev | Quarterly |

### Owner Responsibilities

- Keep collections up to date
- Archive unused content
- Respond to access requests
- Enforce naming conventions
- Review quarterly

---

## Collection Management

### Source of Truth

```
OpenAPI Spec (Git) → [Automation] → Postman Collection
     ↑                                    ↓
   Source                              Generated
   of Truth                           (don't edit)
```

**Rule: Never manually edit generated collections.**

If you need to change an API:
1. Update the OpenAPI spec in Git
2. Commit and push
3. Let CI/CD regenerate the collection

### Collection Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Active    │────▶│ Deprecated  │────▶│  Archived   │
│             │     │ (30 days)   │     │ (read-only) │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Deprecation Process

1. Mark collection as deprecated (add `[DEPRECATED]` prefix)
2. Notify users via Slack/email
3. Wait 30 days
4. Move to Archive workspace
5. Delete after 90 days if no objections

---

## Access Control

### Role Definitions

| Role | Can View | Can Edit | Can Delete | Can Admin |
|------|----------|----------|------------|-----------|
| Viewer | ✅ | ❌ | ❌ | ❌ |
| Editor | ✅ | ✅ | ❌ | ❌ |
| Admin | ✅ | ✅ | ✅ | ✅ |

### Default Access by Workspace Type

| Workspace Type | Default Access |
|----------------|----------------|
| Platform | All engineers: Viewer |
| Team | Team members: Editor |
| Personal | Owner only |
| Archive | All: Viewer (read-only) |

### Requesting Access

1. Submit request via Slack #postman-access
2. Workspace owner approves/denies within 24 hours
3. Access granted at minimum required level

---

## Audit & Cleanup

### Monthly Audit

Run these checks monthly:

- [ ] Workspaces without activity in 60+ days
- [ ] Collections without owners
- [ ] Duplicate collection names
- [ ] Environments with hardcoded secrets
- [ ] Personal workspaces with shared content

### Quarterly Review

Every quarter:

1. Review workspace inventory
2. Archive unused workspaces
3. Update ownership list
4. Report metrics to leadership

### Cleanup Criteria

**Archive if:**
- No activity in 90+ days
- Owner has left the organization
- Superseded by newer version
- Marked as deprecated

**Delete if:**
- Archived for 90+ days
- Confirmed no dependencies
- Owner approves deletion

---

## Migration Plan

### From Current State (413 Workspaces)

#### Phase 1: Inventory (Week 1-2)
```bash
# Export workspace list
# Tag each as: keep, migrate, archive, delete
```

| Category | Count | Action |
|----------|-------|--------|
| Keep as-is | ~20 | Already well-organized |
| Migrate | ~50 | Move to platform workspaces |
| Archive | ~200 | Move to archive |
| Delete | ~143 | Empty or duplicate |

#### Phase 2: Migration (Week 3-6)
- Create new platform workspaces
- Move valuable collections
- Update documentation

#### Phase 3: Cleanup (Week 7-8)
- Archive old workspaces
- Delete empty workspaces
- Communicate changes

#### Phase 4: Enforce (Ongoing)
- Enable governance policies
- Train teams on new structure
- Monitor for sprawl

---

## Metrics to Track

### Workspace Health

| Metric | Target | Current |
|--------|--------|---------|
| Total workspaces | < 50 | 413 |
| Workspaces with owner | 100% | ~30% |
| Avg collections per workspace | 5-10 | 7 |
| Stale workspaces (90+ days) | 0 | ~200 |

### Collection Health

| Metric | Target | Current |
|--------|--------|---------|
| Collections from specs | 100% | ~10% |
| Collections with tests | 80%+ | 11% |
| Collections with docs | 100% | ~25% |

---

## Enforcement

### Automated Checks

```yaml
# Example: Nightly governance check
- Check for new workspaces without description
- Flag collections edited manually (should be generated)
- Alert on workspaces exceeding 30 collections
- Report stale environments
```

### Escalation Path

1. **Automated warning** — Slack notification
2. **Owner notification** — Email to workspace owner
3. **Manager escalation** — If unresolved in 7 days
4. **Forced archive** — If unresolved in 30 days

---

## Quick Reference Card

### Creating a New Workspace

1. Check if a suitable workspace exists first
2. Use naming convention: `[Domain] - [Type]`
3. Add description explaining purpose
4. Assign owner and backup owner
5. Set default access level

### Creating a New Collection

1. Don't manually create — use the sync script
2. If manual is necessary, follow naming: `[API Name] v[Version]`
3. Add to appropriate platform workspace
4. Document owner in workspace settings

### Requesting Changes

- **New workspace**: Slack #postman-governance
- **Access request**: Slack #postman-access
- **Report issue**: GitHub issue in this repo

---

*Good governance isn't bureaucracy—it's making sure engineers can find what they need without asking around.*
