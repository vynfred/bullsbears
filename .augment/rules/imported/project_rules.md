---
type: "always_apply"
---

# BullsBears.xyz - AI Agent Build Rules

## MANDATORY AI AGENT WORKFLOW RULES


### Rule    : Confirmation Questions Before New Tasks ⚠️ REQUIRED
Before starting new work, AI agent MUST ask clarifying questions:
- Priority confirmation based on updated roadmap
- Approach options for upcoming features
- Technical constraint clarifications
- Requirement refinements or changes

### Rule 2: NO WORK WITHOUT CONFIRMATION – REQUIRED
Before writing a single line of new code, you MUST ask:

"Is this the highest priority right now?"
"Do you want Option A (fast/dirty) or Option B (clean/scalable)?"
"Any hard deadlines or constraints I should know?"
"Confirm: delete old code or keep for reference?"



### Architecture Requirements

BULLSBEARS_ARCHITECTURE = {
    "Render.com": "FastAPI web service + Background Workers + Postgres + Redis + Cron Jobs",
    "Fireworks.ai": "qwen2.5-72b-instruct → prescreen (75) + arbitrator (3–6 picks) + nightly learner",
    "Groq": "Llama-3.2-11B-Vision → 75 charts → 6 boolean flags (instant, <1 min total)",
    "xAI Grok API": "Grok-4 → social score –5 to +5 + headlines + Polymarket odds",
    "Firebase Hosting": "Next.js 15 frontend (edge global CDN)",
    "Firebase Realtime Database / Firestore": "Instant picks push + user watchlists + live stats",
    "Integration": "Each service does ONE job perfectly – no local code, no Dockerfiles, no .env"

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

If you didn’t ask → you don’t build.
