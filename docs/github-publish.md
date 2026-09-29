# SENTINEL — GitHub Publishing Guide

This guide covers publishing SENTINEL to a public GitHub repository for the Qualcomm Snapdragon AI Lab competition submission.

---

## Before You Push

Complete these checks first:

- [ ] `python scripts/verify_installation.py` → ALL SYSTEMS READY
- [ ] `pytest backend/tests -q` → 145 passed, 0 failed
- [ ] `cd frontend && npx tsc --noEmit` → 0 errors
- [ ] `cd frontend && npm run lint` → 0 warnings / errors
- [ ] Screenshots captured to `submission/assets/`
- [ ] `submission/form-data.md` updated with the actual GitHub URL

---

## Step 1 — Create GitHub Repository

1. Go to **https://github.com/new**
2. Set repository name: `sentinel-ai` (or your preferred name)
3. Set visibility: **Public** (required for competition submission)
4. **Do NOT** initialize with README, .gitignore, or license — the project already has these
5. Click **Create repository**
6. Copy the repository URL (e.g. `https://github.com/YOUR_USERNAME/sentinel-ai.git`)

---

## Step 2 — Initialize Local Git Repository

Open **PowerShell** (or Command Prompt) in the project root (`C:\Users\shrey\Desktop\Snapdragon`):

```powershell
git init
git add .
git status
```

Review `git status` output carefully before committing. Verify that:
- Source files are staged (backend/, frontend/, docs/, scripts/, etc.)
- `.env` is **NOT** staged
- `*.db` files are **NOT** staged
- `node_modules/`, `.venv/`, `.next/` are **NOT** staged
- Model binaries (`*.onnx`) are **NOT** staged
- `data/uploads/*` files are **NOT** staged

> [!CAUTION]
> If `git status` shows `.env`, `sentinel.db`, or model `.onnx` files as staged, stop immediately and run `git rm --cached <file>` to unstage them before committing.

---

## Step 3 — Commit

```powershell
git commit -m "SENTINEL: final competition submission build"
```

---

## Step 4 — Set Main Branch and Remote

```powershell
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
```

Replace `<YOUR_GITHUB_REPO_URL>` with your actual repository URL from Step 1.

---

## Step 5 — Push to GitHub

```powershell
git push -u origin main
```

If you have 2FA enabled and push fails, you may need to:
1. Create a **Personal Access Token** at https://github.com/settings/tokens
2. Use the token as your password when prompted

---

## Step 6 — Verify Published Repository

After pushing, open the repository URL in a browser and verify:

- [ ] README.md renders correctly with all sections
- [ ] `submission/SENTINEL_Brief_Description.pdf` is visible
- [ ] `submission/SENTINEL_Short_Pitch.pptx` is visible
- [ ] `submission/SENTINEL_Short_Pitch.pdf` is visible
- [ ] `.env` is **NOT** present
- [ ] `sentinel.db` is **NOT** present
- [ ] `models/vision/yolox_s.onnx` is **NOT** present (only `models/vision/README.md`)
- [ ] `data/uploads/` shows only `.gitkeep`

---

## Step 7 — Update Submission Form Data

Open `submission/form-data.md` and replace:

```
<INSERT_FINAL_PUBLIC_GITHUB_URL>
```

with your actual public GitHub URL, for example:

```
https://github.com/YOUR_USERNAME/sentinel-ai
```

Then commit this update:

```powershell
git add submission/form-data.md
git commit -m "chore: add final GitHub repository URL"
git push
```

---

## Files That WILL Be Committed

```
backend/                          (FastAPI application source)
frontend/app/                     (Next.js pages)
frontend/components/              (React components)
frontend/lib/                     (TypeScript utilities)
frontend/public/                  (Static assets)
frontend/eslint.config.mjs
frontend/next-env.d.ts
frontend/package.json
frontend/postcss.config.mjs
frontend/tsconfig.json
docs/                             (All documentation)
  architecture.md
  ai-models.md
  benchmarking.md
  demo.md
  demo-script.md
  documents.md
  final-project-description.md
  final-truth-table.md
  memory.md
  multimodal.md
  privacy.md
  screenshot-checklist.md
  snapdragon.md
  submission-readiness.md
  voice.md
  workspace-tracking.md
  vision_baseline_report.md
scripts/
  benchmark_vision_baseline.py
  benchmark_voice.py
  generate_pitch_deck.py
  reset_demo_data.py
  verify_installation.py
  README.md
models/
  .gitkeep
  README.md
  vision/README.md               (download instructions, no binaries)
submission/
  SENTINEL_Brief_Description.pdf
  SENTINEL_Short_Pitch.pdf
  SENTINEL_Short_Pitch.pptx
  form-data.md
  assets/.gitkeep               (screenshots if captured)
data/
  uploads/.gitkeep
  audio/.gitkeep
benchmarks/
  results/.gitkeep
.env.example
.gitignore
LICENSE
THIRD_PARTY_NOTICES.md
README.md
run_sentinel.bat
config/target_profile.json      (if present)
```

---

## Files That Will NOT Be Committed (gitignored)

```
.env                            (local secrets — use .env.example)
sentinel.db                     (local SQLite database)
backend/sentinel.db             (local SQLite database)
.venv/                          (Python virtual environment)
frontend/node_modules/          (Node.js packages)
frontend/.next/                 (Next.js build output)
models/vision/*.onnx            (model binaries — download separately)
data/uploads/*                  (user-uploaded files — privacy)
*.log                           (log files)
*.wav / *.mp3                   (audio recordings — privacy)
opencode-windows-x64/           (third-party binary)
frontend/AGENTS.md              (AI tooling instructions)
frontend/CLAUDE.md              (AI tooling instructions)
frontend/tsconfig.tsbuildinfo   (TS build cache)
docs/development-plan.md        (internal dev doc)
docs/product-spec.md            (internal product spec)
docs/project-description-draft.md (superseded draft)
docs/vision_baseline_report.json   (benchmark artifact)
```

---

## Suggested Commit Messages

| Commit | Message |
|---|---|
| Initial submission | `SENTINEL: final competition submission build` |
| Add GitHub URL | `chore: add final GitHub repository URL` |
| Add screenshots | `docs: add application screenshots for submission` |
| Any last fix | `fix: <specific issue description>` |

---

## Important Reminders

> [!IMPORTANT]
> The repository **must be PUBLIC** to be accessible to competition judges for evaluation.

> [!CAUTION]
> Never commit `.env`, `*.db`, or model binary files (`.onnx`, `.pt`, `.bin`). These are covered by `.gitignore` but always verify with `git status` before `git push`.

> [!NOTE]
> After pushing, copy the final GitHub URL and paste it into both `submission/form-data.md` (Field 3: GitHub Repository Link) and the actual competition submission form.
