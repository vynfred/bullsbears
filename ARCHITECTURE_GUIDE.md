BULLSBEARS_ARCHITECTURE = {
    "Google_Cloud_SQL": "Prime DB + 30-day candidate tracking + learning history",
    "RunPod": "qwen2.5:32b prescreen + Learner/BrainAgent (single RTX 4090 serverless endpoint)",
    "Cloud_APIs": "Groq Vision + Grok Social + Rotating Arbitrator",
    "Firebase": "Real-time picks & user experience",
    "Integration": "Each does ONE job perfectly"
}

HOW THEY WORK TOGETHER

GOOGLE_CLOUD_SQL_HANDLES = {
    "Prime_DB": "90-day OHLCV + 127 pre-computed features for all ~3,800 NASDAQ tickers",
    "Candidate_Tracking": "All 75 SHORT_LIST candidates + vision flags + social context + final picks",
    "Learning_Data": "30-day performance of every candidate → BrainAgent fuel",
    "History": "Git-style learning_history/ folder with every nightly change",
    "Bulk_Storage": "FMP Premium data (300 calls/min, 20 GB/month cap)",
    "Complex_Queries": "Retrospective analysis, pattern mining, arbitrator leaderboard"
}

RUNPOD_HANDLES = {
    "Endpoint": "qwen2.5:32b (RTX 4090 serverless, 1 worker, 120 GB volume)",
    "Data_Source": "Reads/writes Prime DB from Google Cloud SQL",
    "Models": "qwen2.5:32b",
    "Output": "75 SHORT_LIST → SQL + triggers cloud phases; nightly hot-reloads 3 files",
    
    "Workflow": [
        "1. Read ACTIVE tickers + 127 features from Prime DB",
        "2. ONE FinMA-7b call → exactly 75 ranked candidates",
        "3. Store 75 candidates in SQL for tracking",
        "4. Trigger Cloud Vision + Social phases",
        "5. 4:01 AM: LearnerAgent + BrainAgent → hot-reload prompts/weights/bias"
    ]
}

CLOUD_APIS_HANDLE = {
    "Vision": "Groq Llama-3.2-11B-Vision → 75 charts → 6 boolean flags",
    "Social_Context": "Grok API → -5 to +5 score + top 3 headlines + events + Polymarket prob",
    "Arbitrator": "7-day rotating frontier model (DeepSeek-V3 / Gemini 2.5 Pro / Grok 4 / Claude Sonnet 4 / GPT-5)",
}

FIREBASE_HANDLES = {
    "Real_Time_Updates": "Latest 3–6 picks pushed instantly",
    "User_Experience": "Live feed, notifications, performance stats",
    "User_Auth": "Secure login/logout",
    "Simple_Data": "Current picks, hit rate, moon/rug count",
    "Scalability": "Handles 10,000+ concurrent users",
    
    "Data_Structure": {
        "/picks/latest": "Current AI picks + targets + reasoning",
        "/stats/performance": "30-day hit rate, best arbitrator, top patterns",
        "/watchlist/{user}": "User-specific tracking",
        "/notifications/{user}": "Push alerts"
    }
}

DAILY_WORKFLOW = {
    "PRIME_DB_BOOTSTRAP": "One-time: FMP Premium → 90-day OHLCV + metadata (7-week rolling batch, ~7.8 GB total)",
    "3:00 AM ET": "FMP Premium → daily delta update (1-day bars only) → Prime DB always fresh",
    "3:05 AM ET": "Logic filter → ACTIVE (~1,700)",
    "3:10 AM ET": "RunPod (finma-learner-v3) → FinMA-7b → exactly 75 SHORT_LIST",
    "3:15 AM ET": "Matplotlib → 75 charts",
    "3:16 AM ET": "Groq Vision → 6 flags per ticker",
    "3:17 AM ET": "Grok API → social score + news + Polymarket",
    "3:20 AM ET": "Rotating Arbitrator → 3–6 final picks + targets",
    "3:25 AM ET": "Picks → Firebase → users see instantly",
    "4:01 AM ET": "RunPod (same endpoint) → BrainAgent + LearnerAgent (deepseek) → hot-reloads 3 files",
    
    "Result": "Users get real-time picks. Bot gets smarter every single night."
}