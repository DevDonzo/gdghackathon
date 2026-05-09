# 📞 Reverse-ASSIST: AI Bill Negotiator

> **GDG Hacks 3 — Guelph, May 9–10, 2026**
> 24-hour hackathon plan

---

## 🎯 The Pitch (memorize this exact sentence)

> **"Upload your phone bill. Our AI calls Bell, negotiates with the rep, and texts you back when it's done — without you ever picking up the phone."**

That's it. Don't open with the tech stack. Don't open with "we used Gemini." Open with that one sentence and a live demo of the call dialing out.

---

## 🏆 Why This Wins (mapped to judging criteria)

| Criterion | How this hits it |
|---|---|
| **Awesomeness** | Judges watch a phone literally dial out and negotiate live. Nobody else will have this. |
| **Impact** | Every adult in Canada has been screwed by Bell/Rogers/Telus. Universal pain point. |
| **Creativity** | Last year ASSIST won 1st making calls *for* you. We make calls *against* companies *for* you. Direct evolution of the proven winner. |
| **Design** | Clean dashboard: upload → "negotiating now" → live transcript → savings reveal. Single-page, easy on the eyes. |

**Bonus prize tracks we qualify for:**
- 🥇 Overall 1st/2nd/3rd Place
- 🤖 MLH Best Use of Gemini API (Gemini Vision for bill OCR + Gemini 2.0 Flash for live negotiation)
- 🍃 MLH Best Use of MongoDB Atlas (call history + bill storage)
- 🌐 MLH Best `.Tech` Domain Name (grab `negotiate.tech` or similar at the event)
- 🎨 Best UI (clean dashboard)

---

## ⚠️ The Legal Sandbox (READ FIRST — don't skip this)

The Mayday team last year couldn't fully demo because they hit legal restrictions on impersonating real services. Don't repeat that mistake.

**The fix:** We never call a real company during the demo. Instead:

1. We set up a **second Twilio number that plays a pre-recorded "Bell customer service" IVR script** (we record this ourselves: "Thank you for calling Bell, press 1 for billing…").
2. Our AI calls *that* number, navigates the IVR, then talks to a *third* Twilio number running a Gemini-powered "Bell rep" persona.
3. The judges see a real call happen between two real phone numbers, with our AI clearly negotiating against an AI rep.

This is **legally bulletproof, technically more impressive** (we built both ends), and **lets us tune the demo for max wow** because we control the rep's responses.

In the pitch we say: *"In production this calls real companies. For the demo, we built our own simulated customer service line so you can see exactly what happens — same code, just pointed at a sandbox number."* Judges respect that.

---

## 🧱 Tech Stack

| Layer | Tech | Why |
|---|---|---|
| Frontend | Next.js 14 + Tailwind | Fast to ship, looks polished, deploys to Vercel in 2 min |
| Backend | Python Flask + ngrok | Twilio webhooks need a public URL, ngrok handles it |
| Voice | Twilio Programmable Voice (free trial credits) | Industry standard, easier than Telnyx for first-timers |
| AI — bill OCR | Gemini 2.0 Flash (Vision) | Reads any uploaded bill PDF/image |
| AI — live negotiation | Gemini 2.0 Flash + streaming | Low latency, function calling for "make offer" / "accept" / "hang up" |
| TTS / STT | Twilio's `<Gather>` + Google Cloud Speech (or ElevenLabs if budget allows) | Twilio handles the call audio, we just send text |
| Database | MongoDB Atlas (free tier) | Stores bills, call transcripts, savings history → MLH prize |
| Hosting | Vercel (frontend) + ngrok (backend) | Zero config |
| Domain | `negotiate.tech` from .tech registry → MLH prize |

**No Kubernetes. No microservices. No Kafka. One Flask file, one Next.js app. Ship it.**

---

## 🗓 24-Hour Timeline

Hackathon hacking starts Saturday May 9 at ~10pm and ends Sunday May 10 at ~10pm. Times below are hours-elapsed from start.

### Hour 0–2 — Setup & Lock Scope (Saturday 10pm–12am)

- [ ] Form team, claim a table near a power outlet
- [ ] Everyone clones the repo, gets `npm install` and `pip install` working
- [ ] Sign up for: Twilio trial (get $15 free credits), Google AI Studio (Gemini API key), MongoDB Atlas, Vercel
- [ ] Buy `negotiate.tech` (or similar) at the .tech booth
- [ ] **Critical: agree on scope freeze.** No new features after midnight unless they replace something.
- [ ] Sketch the 3 screens: Upload, Live Call, Result
- [ ] Assign roles (see below)

### Hour 2–8 — Parallel Build Phase 1 (12am–6am)

**Person A — Voice pipeline (the hard part, do this first)**
- [ ] Get Twilio trial number, run a hello-world `<Say>Hello</Say>` call to your own phone
- [ ] Set up ngrok, point a Flask `/voice` webhook at it
- [ ] Implement `<Gather input="speech">` to capture what the rep says
- [ ] Build the "fake Bell rep" Twilio number that plays a script and waits for AI response
- [ ] Wire two numbers calling each other end-to-end with hardcoded text

**Person B — Bill OCR + Gemini negotiation logic**
- [ ] Frontend file upload → POST to Flask `/upload-bill`
- [ ] Backend sends image bytes to Gemini 2.0 Flash with prompt: *"Extract account number, current monthly charge, line items, and identify 3 negotiation angles (e.g., 'data overage', 'expired promo')"*
- [ ] Build the `negotiate(transcript_so_far, bill_context) → next_response` function using Gemini with a system prompt that makes it polite, persistent, and goal-oriented
- [ ] Output structured JSON: `{ "say": "...", "action": "continue" | "accept" | "escalate" | "hangup" }`

**Person C — Frontend**
- [ ] Next.js app with three routes: `/`, `/call/[id]`, `/result/[id]`
- [ ] Upload screen: drag-drop bill, "Start negotiation" button
- [ ] Live call screen: WebSocket or polling to show transcript scrolling in real time, with two avatar bubbles (You, Bell rep)
- [ ] Result screen: big number — "Saved $32/month" — with confetti animation
- [ ] Tailwind, dark mode, monospace font for transcript

**Person D — Glue + MongoDB + the fake Bell rep persona**
- [ ] MongoDB schema: `bills`, `calls`, `transcripts`
- [ ] Write the "Bell rep" Gemini prompt — should start firm, gradually concede if pushed, have realistic objections ("I'd need to escalate to retention…")
- [ ] Set up Vercel deploy, get the live domain working

### Hour 8–10 — First End-to-End Test (6am–8am)

- [ ] **Goal:** Click "negotiate" on the frontend → real call dials out → AI talks to AI Bell rep → transcript shows up live on screen → final savings number appears.
- [ ] Expect breakage. Debug as a team.
- [ ] **Eat actual food** (this is where teams crash and burn from skipping breakfast)

### Hour 10–14 — Sleep + Polish (8am–12pm)

- [ ] **Two people sleep 2–3 hours each, in shifts.** A team that doesn't sleep can't pitch coherently. ASSIST won solo because the dev was rested enough to debug Xcode.
- [ ] The awake people: polish the UI, fix transcript flicker, add the savings calculation, add MongoDB call history page
- [ ] Add a "demo mode" toggle that pre-loads a sample Bell bill (so judges who don't have a bill on them can still see it work)

### Hour 14–18 — Demo-Hardening (12pm–4pm)

- [ ] Pick the **3 demo scripts** you'll run for judges:
  1. "Bill is $85/month, AI negotiates down to $52" — the happy path
  2. "Rep refuses, AI asks for retention department" — shows escalation logic
  3. "AI catches a hidden fee in the bill" — shows the Gemini Vision OCR is doing real work
- [ ] Record a 90-second demo video for Devpost (this is required for submission and matters for sponsor judging)
- [ ] Practice the pitch out loud. Three times. Time it.

### Hour 18–22 — Devpost & Final Polish (4pm–8pm)

- [ ] Write the Devpost submission:
  - **Inspiration:** Tariffs, rate hikes, the average Canadian wastes ~3 hours a year on hold with telecom. (Use real stats — judges Google-check these.)
  - **What it does:** Two-sentence version of the pitch
  - **How we built it:** Stack list with reasoning
  - **Challenges:** Be honest. Twilio webhooks fighting ngrok is always relatable.
  - **What's next:** Real partnerships with consumer-protection nonprofits, Spanish-language support, integration with Plaid for auto-detection of overcharges
- [ ] Push final code to public GitHub
- [ ] Deploy production build to `negotiate.tech`
- [ ] Test the full demo flow ONE MORE TIME on the actual judging laptop

### Hour 22–24 — Pitch (8pm–10pm)

- [ ] Be at your table 15 min before judges arrive
- [ ] Have the demo pre-loaded so the first 5 seconds of judges seeing you = phone dialing out
- [ ] Pitch order:
  1. **The hook (10 sec):** "Every Canadian wastes hours on hold fighting their phone bill. We made an AI that does it for them."
  2. **Live demo (60 sec):** Click → call dials → transcript scrolls → savings number appears
  3. **The tech (20 sec):** Gemini Vision reads the bill, Gemini 2.0 Flash drives the live negotiation, Twilio handles voice, MongoDB stores history
  4. **The why (10 sec):** "ASSIST won this hackathon last year by making calls *for* you. We make calls *against* the companies that overcharge you."
  5. **Q&A:** Smile. Don't be defensive. If a judge points out a flaw, say "great catch, that's on the roadmap."

---

## 👥 Roles (assuming team of 4)

| Person | Owns | Backup for |
|---|---|---|
| **A — Voice/Backend** | Twilio integration, Flask webhooks, ngrok | Person B's Gemini calls |
| **B — AI/Backend** | Gemini OCR, negotiation prompting, JSON contract | Person D's Mongo |
| **C — Frontend** | Next.js, Tailwind, transcript UI, deploy | Pitch delivery |
| **D — Glue & Pitch** | MongoDB, fake Bell rep, Devpost write-up, video | Anything broken at hour 20 |

**If you're a team of 2:** drop the live transcript fancy UI; just show a "Call complete — saved $X" screen. The call itself is the demo.

**If you're solo:** ASSIST won solo last year. You can do this. Skip the fake Bell rep — instead, call your own phone and play a recording of yourself as the rep, clearly labeled as a simulation in the pitch.

---

## 🚧 Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **Twilio trial restrictions** (can only call verified numbers) | Verify all team members' numbers immediately at hour 0. Use those numbers for the fake-Bell-rep line. |
| **Gemini hallucinates dollar amounts** | Validate Gemini's extracted bill numbers against a regex check before showing them. If the AI claims a saving, double-check with a deterministic calculator. |
| **Live demo fails in front of judges** | Have a pre-recorded 60-sec video of a successful call as backup. If the live demo breaks, pivot to "let me show you a recording of one we ran 10 minutes ago." This is industry-standard hackathon recovery. |
| **Latency makes the call feel awkward** | Use Gemini 2.0 Flash, not Pro. Stream responses. Cache common rep phrases. If Gemini takes >2s, play a "Mhm, let me think…" interjection first so the call feels natural. |
| **Scope creep** (the silent killer) | Anything not in this doc by hour 0 is a v2 feature. Write "v2: ___" on a sticky note and move on. |
| **Sleep deprivation kills the pitch** | Mandatory 2-hour nap each, in shifts, between hours 10–14. Set phone alarms. |

---

## 📐 Architecture (one-paragraph version)

User uploads a bill on the Next.js frontend. The bill image is sent to the Flask backend, which forwards it to Gemini 2.0 Flash Vision with a structured-output prompt that returns `{accountNumber, currentCharge, lineItems[], negotiationAngles[]}`. The backend writes this to MongoDB and triggers a Twilio outbound call to our sandbox "Bell rep" number. Twilio's voice webhook calls back to Flask on every speech turn — Flask passes the running transcript plus the bill context to Gemini, which returns the next thing to say plus an action (`continue`/`accept`/`hangup`). Twilio speaks Gemini's response back into the call. The frontend polls Mongo every 1s to show the transcript live. When the call ends, the frontend reveals the savings.

---

## 🎤 Pitch Cheat-Sheet (print this, tape it to your laptop)

**Hook:** "Every Canadian wastes hours on hold fighting their phone bill. We made an AI that does it for them."

**Demo:** *(click upload → click negotiate → narrate as transcript scrolls)* "Here it's identified an expired promo... now it's asking for retention... and we just saved $32 a month."

**The tech in 3 names:** "Gemini Vision reads the bill. Gemini Flash runs the negotiation. Twilio handles the call."

**The closer:** "ASSIST won this hackathon last year by making calls for you. We make calls against the companies overcharging you."

**If asked "is this legal?":** "Recording disclosure varies by province — in production we'd add the consent prompt at call start. For the demo, both ends are our own simulated lines."

**If asked "what's next?":** "Real telco partnerships, Plaid integration to auto-detect overcharges before they happen, and a Spanish-language version since 30% of newcomers to Canada cite phone-bill confusion as their #1 service issue."

---

## ✅ Submission Checklist (don't lose points to forgetting these)

- [ ] Public GitHub repo with commit history (judges check this — no single mega-commit at hour 23)
- [ ] 90-second demo video on Devpost
- [ ] Devpost submission with Inspiration / What it does / How / Challenges / What's next sections
- [ ] All team members added as collaborators on the Devpost project
- [ ] `.tech` domain registered and live (MLH prize)
- [ ] MongoDB Atlas used somewhere real, even if just storing call logs (MLH prize)
- [ ] Gemini API used for both OCR AND negotiation (MLH Best Gemini prize)
- [ ] In-person pitch delivered to judges (required to be considered at all)
- [ ] Slept at least 2 hours before pitching

---

## 🔥 The One Thing

If you remember nothing else from this doc: **the moment a judge sees a phone literally dial out and negotiate, you've won them.** Everything in this plan exists to make that moment happen smoothly. Protect that moment. Cut anything that threatens it.

Go win.
