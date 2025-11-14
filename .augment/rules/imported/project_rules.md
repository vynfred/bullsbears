---
type: "always_apply"
---

# BullsBears.xyz - AI Agent Build Rules

## MANDATORY AI AGENT WORKFLOW RULES

### Rule 1: AGENT_TASKS.MD Update After Each Task ⚠️ REQUIRED
At the end of every AI agent task:
- Mark completed tasks as ✅ COMPLETED with timestamps
- Update progress percentages and current phase status
- Add new tasks discovered during development
- Document blockers, dependencies, or technical discoveries
- Update success metrics and milestone completion

### Rule 2: Confirmation Questions Before New Tasks ⚠️ REQUIRED
Before starting new work, AI agent MUST ask clarifying questions:
- Priority confirmation based on updated roadmap
- Approach options for upcoming features
- Timeline adjustments based on discoveries
- Technical constraint clarifications
- Requirement refinements or changes

### Rule 3: NO WORK WITHOUT CONFIRMATION – REQUIRED
Before writing a single line of new code, you MUST ask:

"Is this the highest priority right now?"
"Do you want Option A (fast/dirty) or Option B (clean/scalable)?"
"Any hard deadlines or constraints I should know?"
"Confirm: delete old code or keep for reference?"

## PROJECT BUILD RULES



### Architecture Requirements

**Backend**: Python/FastAPI with async endpoints, PostgreSQL, Redis caching, Celery for background tasks
**Frontend**: Next.js 15 with App Router, Tailwind CSS, mobile-first design
**AI Integration**: 8-Agent Multi-AI System with RunPod GPU infrastructure
**Data Sources**: FMP, AI Agents
**Deployment**: Serverless RunPod GPUs, Firebase hosting, Google SQL, Firebase RealTime db. 
**Libraries**: TA-Lib for technical indicators, scikit-learn for ML, NLTK/VADER as sentiment fallback

DOs and DON'Ts – NON-NEGOTIABLE

DO keep all API keys in .env only
DO use os.getenv() – never hardcode
DO hot-reload prompts/*.txt and weights.json nightly
DO run everything on one RunPod worker (zero extra cost)
DO ask before touching frontend styles
DO delete dead code immediately
DON'T add new endpoints, models, or agents
DON'T make code unnecessarily complex.
DON'T use local vision models
DON'T parse unstructured text – JSON only
DON'T assume paths – ask
DON'T say "yes" to anything that breaks the lean pipeline
DON'T update without confirming priority

If it’s not in AGENT_TASKS.MD → it doesn’t exist.
If you didn’t ask → you don’t build.
If it’s not on the RunPod worker → it’s not running.
