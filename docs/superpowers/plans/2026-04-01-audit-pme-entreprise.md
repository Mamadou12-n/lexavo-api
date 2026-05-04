# Audit PME/Entreprise — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive legal compliance audit for Belgian PME and enterprises, with a custom Claude skill, auto-updating legal checklists, and mobile UI.

**Architecture:** Extends existing compliance.py pattern with 30 domain-specific questions across 8 legal categories (RGPD, travail, fiscal, commercial, environnement, societes, gouvernance, PI). Claude generates personalized recommendations via RAG. Results persist in DB. Restricted to business/firm/enterprise plans.

**Tech Stack:** FastAPI, Anthropic Claude API, PostgreSQL, React Native, GitHub Actions

---

### Task 1: Create audit_entreprise.py feature logic

**Files:**
- Create: `api/features/audit_entreprise.py`

### Task 2: Create Pydantic models

**Files:**
- Modify: `api/models.py` — add AuditRequest, AuditResponse, AuditItem models

### Task 3: Create DB table audit_reports

**Files:**
- Modify: `api/database.py` — add audit_reports table + CRUD functions

### Task 4: Create API endpoints

**Files:**
- Modify: `api/main.py` — add /audit/questions, /audit/generate, /audit/history, /audit/{id}

### Task 5: Create mobile AuditScreen.js

**Files:**
- Create: `mobile/src/screens/AuditScreen.js`
- Modify: `mobile/src/api/client.js` — add audit API functions

### Task 6: Create lexavo-audit skill

**Files:**
- Create: `claude-skills/lexavo-audit/SKILL.md`

### Task 7: Create GitHub Actions auto-update workflow

**Files:**
- Create: `scripts/update_audit_checklist.py`
- Note: Workflow file created via GitHub UI (PAT lacks workflow scope)
