# Repository Migration Plan

## Goal

Migrate the FormFlow project from `formflow-agent` to the new repository:
**https://github.com/georgevetticaden/multi-agent-federal-form-automation-system**

This involves:
1. Moving all code and documentation to the new repo
2. Updating all references from `formflow-agent` → `multi-agent-federal-form-automation-system`
3. Preserving git history (optional)
4. Verifying all paths and configurations work

---

## Migration Strategy Options

### Option 1: Fresh Start (Recommended - Cleanest)

**Pros:**
- Clean git history starting fresh
- No old commits/baggage from experimentation
- Simpler to execute

**Cons:**
- Loses git history (but you have all artifacts/docs preserved)

**Steps:**
1. Clone the new empty repo
2. Copy all files from current project
3. Update all path references
4. Make initial commit with clean history

### Option 2: Preserve Git History

**Pros:**
- Maintains complete commit history
- Shows evolution of the project

**Cons:**
- More complex
- Carries over all experimental commits

**Steps:**
1. Clone current repo to new location
2. Change git remote to new repo
3. Update all path references
4. Force push to new repo

---

## Recommended Migration Steps (Option 1 - Fresh Start)

### Phase 1: Prepare New Repository

**Step 1: Clone the new repository**
```bash
cd ~/Dropbox/Development/Git
git clone https://github.com/georgevetticaden/multi-agent-federal-form-automation-system.git
cd multi-agent-federal-form-automation-system
```

**Step 2: Verify it's empty**
```bash
ls -la
# Should only show .git directory and maybe README.md from GitHub
```

---

### Phase 2: Copy Project Files

**Step 3: Copy all files except .git**
```bash
# From the NEW repo directory
rsync -av --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='venv' \
  --exclude='.pytest_cache' \
  --exclude='*.log' \
  --exclude='*.partial_*.json' \
  ~/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/ \
  ./
```

**What this does:**
- Copies ALL files and directories from old project
- Excludes git history, Python cache, virtual environments, logs
- Preserves directory structure exactly

**Step 4: Verify files copied correctly**
```bash
ls -la
# Should see: mcp-servers/, wizards/, agents/, requirements/, docs/, README.md, etc.
```

---

### Phase 3: Update Path References

Now we need to update all references from `formflow-agent` to `multi-agent-federal-form-automation-system`.

**Step 5: Search for references to update**
```bash
# First, see what needs updating
grep -r "formflow-agent" . --exclude-dir=.git --exclude-dir=venv
```

**Expected files to update:**
1. **README.md** - Installation paths, directory references
2. **CLAUDE.md** - Working directory references, file paths
3. **docs/discovery/CLAUDE_DESKTOP_SETUP.md** - MCP configuration paths
4. **mcp-servers/federalscout-mcp/README.md** - Setup instructions
5. **mcp-servers/federalrunner-mcp/README.md** - Setup instructions
6. **.claude/settings.local.json** - If exists, update paths
7. **Any shell scripts** - Update hardcoded paths

**Step 6: Update all path references**

Use find and replace (case-sensitive):
- Find: `formflow-agent`
- Replace: `multi-agent-federal-form-automation-system`

**Key files to update manually:**

**README.md:**
```bash
# Example installation paths - update from:
cd /path/to/formflow-agent/mcp-servers/federalscout-mcp
# To:
cd /path/to/multi-agent-federal-form-automation-system/mcp-servers/federalscout-mcp
```

**docs/discovery/CLAUDE_DESKTOP_SETUP.md:**
```json
{
  "mcpServers": {
    "federalscout": {
      "command": "/path/to/multi-agent-federal-form-automation-system/mcp-servers/federalscout-mcp/venv/bin/python",
      "args": ["/path/to/multi-agent-federal-form-automation-system/mcp-servers/federalscout-mcp/src/server.py"],
      "env": {
        "FEDERALSCOUT_WIZARDS_DIR": "/path/to/multi-agent-federal-form-automation-system/wizards"
      }
    }
  }
}
```

**CLAUDE.md:**
- Update working directory references
- Update file path examples

---

### Phase 4: Update GitHub-Specific References

**Step 7: Update repository URLs**

Find and replace:
- Find: `https://github.com/georgevetticaden/formflow-agent`
- Replace: `https://github.com/georgevetticaden/multi-agent-federal-form-automation-system`

**Files to update:**
- README.md (clone instructions, issue links)
- CLAUDE.md (if referenced)
- Any documentation with GitHub links
- Citation section in README.md

---

### Phase 5: Verify and Test

**Step 8: Check for missed references**
```bash
# Case-insensitive search for any remaining references
grep -ri "formflow-agent" . --exclude-dir=.git --exclude-dir=venv

# Search for old directory pattern (10-14-25-gov-formflow-agent)
grep -ri "10-14-25-gov-formflow-agent" . --exclude-dir=.git --exclude-dir=venv
```

**Step 9: Verify directory structure**
```bash
tree -L 2 -I 'venv|__pycache__|.git'
```

**Expected structure:**
```
multi-agent-federal-form-automation-system/
├── mcp-servers/
│   ├── federalscout-mcp/
│   └── federalrunner-mcp/
├── wizards/
│   ├── wizard-data/
│   └── wizard-schemas/
├── agents/
│   ├── federalscout-instructions.md
│   └── federalrunner-instructions.md
├── schemas/
├── requirements/
├── docs/
├── .claude/
├── README.md
├── CLAUDE.md
└── LICENSE
```

---

### Phase 6: Initial Commit

**Step 10: Stage all files**
```bash
git status
git add .
```

**Step 11: Create initial commit**
```bash
git commit -m "Initial commit: Multi-agent federal form automation system

- FederalScout: Visual discovery agent (local MCP, Claude Desktop)
- FederalRunner: Execution agent (cloud MCP, Cloud Run)
- Contract-First Form Automation pattern
- Complete FSA Student Aid Estimator wizard discovered
- Comprehensive documentation and requirements

Migrated from formflow-agent with agent renames:
- FormScout → FederalScout
- CivicCalc → FederalRunner

System uses two specialized agents to transform government calculators
into voice-accessible tools through visual discovery and atomic execution."
```

**Step 12: Push to GitHub**
```bash
git push origin main
```

---

### Phase 7: Post-Migration Setup

**Step 13: Set up virtual environments**
```bash
# FederalScout
cd mcp-servers/federalscout-mcp
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install webkit
deactivate

# FederalRunner (when ready)
cd ../federalrunner-mcp
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**Step 14: Update Claude Desktop configuration**

Edit: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "federalscout": {
      "command": "/Users/aju/Dropbox/Development/Git/multi-agent-federal-form-automation-system/mcp-servers/federalscout-mcp/venv/bin/python",
      "args": ["/Users/aju/Dropbox/Development/Git/multi-agent-federal-form-automation-system/mcp-servers/federalscout-mcp/src/server.py"],
      "env": {
        "FEDERALSCOUT_HEADLESS": "false",
        "FEDERALSCOUT_BROWSER_TYPE": "webkit",
        "FEDERALSCOUT_SCREENSHOT_QUALITY": "60",
        "FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB": "50",
        "FEDERALSCOUT_WIZARDS_DIR": "/Users/aju/Dropbox/Development/Git/multi-agent-federal-form-automation-system/wizards"
      }
    }
  }
}
```

**Step 15: Restart Claude Desktop and test**
```bash
# Restart Claude Desktop
# Test that FederalScout tools are available
# Try a simple discovery test
```

---

### Phase 8: Clean Up Old Repository (Optional)

**Step 16: Archive old repository**
```bash
cd ~/Dropbox/Development/Git/10-14-25-gov-formflow-agent
# Optional: Create archive
tar -czf formflow-agent-archive-$(date +%Y%m%d).tar.gz formflow-agent/

# Move to archive location
mkdir -p ~/Archives
mv formflow-agent-archive-*.tar.gz ~/Archives/
```

**Step 17: Remove old directory (only after verifying new repo works)**
```bash
# Only do this AFTER verifying everything works in new repo
rm -rf ~/Dropbox/Development/Git/10-14-25-gov-formflow-agent
```

---

## Reference Update Checklist

After migration, verify these references are updated:

### Documentation Files
- [ ] README.md - Installation paths, clone instructions, GitHub URLs
- [ ] CLAUDE.md - Working directory, file paths
- [ ] docs/discovery/CLAUDE_DESKTOP_SETUP.md - MCP configuration paths
- [ ] docs/discovery/OPTIMIZATIONS.md - Directory references
- [ ] docs/blog-demo/civiccalc_demo_realistic.txt - Any path references
- [ ] mcp-servers/federalscout-mcp/README.md - Setup instructions
- [ ] mcp-servers/federalrunner-mcp/README.md - Setup instructions

### Configuration Files
- [ ] .claude/settings.local.json - Working directory path
- [ ] mcp-servers/federalscout-mcp/.env.example - WIZARDS_DIR paths
- [ ] mcp-servers/federalrunner-mcp/.env.example - WIZARDS_DIR paths

### Requirements Documentation
- [ ] requirements/discovery/DISCOVERY_REQUIREMENTS.md - Path examples
- [ ] requirements/execution/EXECUTION_REQUIREMENTS.md - Path examples
- [ ] requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md - Path examples

### Shell Scripts
- [ ] mcp-servers/federalscout-mcp/scripts/setup.sh - If exists
- [ ] mcp-servers/federalrunner-mcp/scripts/deploy-to-cloud-run.sh - If exists

---

## Verification Tests

After migration, test these to ensure everything works:

1. **Directory structure correct**
   ```bash
   tree -L 2 -I 'venv|__pycache__|.git'
   ```

2. **No old references remain**
   ```bash
   grep -ri "formflow-agent" . --exclude-dir=.git --exclude-dir=venv
   grep -ri "10-14-25-gov-formflow-agent" . --exclude-dir=.git --exclude-dir=venv
   ```

3. **FederalScout MCP server starts**
   ```bash
   cd mcp-servers/federalscout-mcp
   source venv/bin/activate
   python src/server.py
   # Should start without errors
   ```

4. **Claude Desktop integration works**
   - Restart Claude Desktop
   - Verify FederalScout tools appear
   - Test simple discovery workflow

5. **Wizards directory accessible**
   ```bash
   ls -la wizards/wizard-data/
   ls -la wizards/wizard-schemas/
   # Should show FSA wizard files
   ```

6. **Documentation renders correctly**
   - View README.md on GitHub
   - Check all internal links work
   - Verify code blocks render properly

---

## Success Criteria

Migration is complete when:

✅ All files copied to new repository
✅ All `formflow-agent` references updated to `multi-agent-federal-form-automation-system`
✅ All GitHub URLs point to new repository
✅ Claude Desktop configuration updated and working
✅ FederalScout MCP server starts successfully
✅ Virtual environments recreated
✅ No broken path references in documentation
✅ Repository pushed to GitHub
✅ README.md displays correctly on GitHub
✅ Old repository archived (optional) or removed (after verification)

---

## Rollback Plan

If issues arise during migration:

1. **New repository has issues:**
   - Old repository still exists at original location
   - Can continue working from old location
   - Debug issues in new repo without pressure

2. **Claude Desktop broken:**
   - Revert claude_desktop_config.json to old paths
   - Restart Claude Desktop
   - Continue using old setup while fixing new one

3. **Nuclear option:**
   - Delete new repository contents
   - Re-clone and start migration from scratch
   - Old repository remains untouched

---

## Timeline Estimate

- **Phase 1-2 (Clone & Copy):** 5 minutes
- **Phase 3-4 (Update References):** 15-20 minutes
- **Phase 5 (Verify):** 10 minutes
- **Phase 6 (Commit & Push):** 5 minutes
- **Phase 7 (Setup & Test):** 15 minutes
- **Phase 8 (Cleanup):** 5 minutes

**Total: ~1 hour** for careful, methodical migration

---

## Post-Migration Tasks

After successful migration:

1. **Update GitHub repository settings:**
   - Add description: "Multi-agent system for automating federal form wizards using visual discovery and atomic execution"
   - Add topics: `ai`, `automation`, `government-forms`, `playwright`, `mcp`, `claude-ai`, `vision`, `accessibility`
   - Enable Issues, Wikis if desired

2. **Create initial GitHub Issue for tracking:**
   - "Phase 3.5: Schema Generation Implementation"
   - "Phase 4: FederalRunner Execution Agent"
   - "Phase 5: Cloud Deployment"

3. **Update local development workflow:**
   - Update any IDE/editor project configurations
   - Update terminal aliases or shortcuts
   - Bookmark new GitHub repo

4. **Share new repository:**
   - Update any external references
   - Share new URL with collaborators
   - Update LinkedIn/portfolio links when ready

---

## Questions to Consider Before Migration

1. **Do you want to preserve git history?**
   - If yes: Use Option 2 (more complex)
   - If no: Use Option 1 (recommended, cleaner)

2. **Is the new repo completely empty?**
   - Check: Does it have a README or LICENSE from GitHub?
   - If yes: May need to delete those first or merge

3. **Do you want to keep the old repo as archive?**
   - If yes: Keep it and just archive it
   - If no: Can delete after verification period

4. **Should we update the project name "FormFlow"?**
   - Current: "FormFlow: Voice-Accessible Government Form Automation"
   - Keep FormFlow as brand name? Or rename to match repo?
   - Recommend: Keep "FormFlow" as the project/brand name

---

## Ready to Migrate?

When you're ready, follow the steps in order. Take your time with Phase 3-4 (updating references) to ensure nothing is missed.

After migration, we'll be working from:
- **Local:** `~/Dropbox/Development/Git/multi-agent-federal-form-automation-system/`
- **Remote:** `https://github.com/georgevetticaden/multi-agent-federal-form-automation-system`

Good luck! 🚀
