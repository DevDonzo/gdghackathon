# RateDrop Devpost Video

Target length: 90 seconds to 2 minutes.

Tone: make it feel like an ad, not a technical walkthrough. The video should make people immediately understand the pain, then show RateDrop fixing it.

Live app:

```text
https://ratedrop-reezumnw5a-uc.a.run.app
```

## Video Structure

### 0:00-0:15 Hook

Show: person staring at a phone on hold, support music, frustrated expression, or a screen with "Estimated wait time: 58 minutes."

Voiceover:

```text
Don’t you hate when you have to call support, sit on hold forever, explain the same problem three times, and still leave without the refund, credit, or better price you needed?
```

Beat.

```text
Companies already use AI to deal with you. RateDrop gives you an AI agent back.
```

### 0:15-0:30 Product Reveal

Show: RateDrop landing page.

Voiceover:

```text
RateDrop is a cloud-hosted phone agent for consumer support calls. You give it evidence, a goal, constraints, and what proof counts as done.
```

On screen:

- Click `Start`.
- Sign in.
- Load `Rogers demo`.

### 0:30-0:50 Mission Setup

Show the prefilled Rogers fields.

Voiceover:

```text
Here, the customer has a Rogers bill at $91.50 a month and a disputed $35 roaming fee. RateDrop’s mission is clear: lower the monthly bill to $55, get the bad charge credited, and do not finish until the rep confirms the rate, credit, effective date, and account notes.
```

Show:

- Company: Rogers
- Problem
- Desired outcome
- Target monthly: 55
- Walk-away max: 60
- Known facts
- Constraints
- Completion proof

### 0:50-1:20 Live Call

Show: click `Start voice agent`, phone rings, answer the call.

Hamza acts as the Rogers representative.

Rep lines:

```text
Thanks for calling Rogers, how can I help?
```

```text
I do not see any promotions available.
```

```text
I can apply a 35 dollar credit for the roaming fee, but the monthly plan would stay the same.
```

```text
I can reduce it to 70 dollars a month and keep the 35 dollar credit.
```

```text
I can get approval for 55 dollars a month and a 35 dollar credit.
```

```text
Confirmed, the new monthly rate is 55 dollars, the 35 dollar credit is applied, it starts next billing cycle, and it is noted on the account.
```

Voiceover:

```text
Watch what happens. The agent does not accept a vague no. It does not accept only a one-time credit. It counters the weak offer, accepts the deal that meets the goal, and only closes after proof is confirmed.
```

### 1:20-1:40 Result

Show: result page and proof email.

Voiceover:

```text
Instead of a messy call, the user gets a structured result: the original bill, the new monthly rate, the one-time credit, the transcript, and proof by email.
```

Show:

- Before: `$91.50`
- After: `$55.00`
- One-time credit: `$35`
- Email proof button

### 1:40-2:00 Cloud Proof

Show: `/api/readiness`.

Voiceover:

```text
RateDrop runs on Google Cloud Run, with Twilio ConversationRelay for phone calls, Google ADK and Gemini for the agent layer, Secret Manager for credentials, Cloud Build for deployment, and Artifact Registry for the container.
```

Final line:

```text
RateDrop handles the support calls you do not want to make.
```

## Recording Notes

- Keep the video fast. Do not explain every field.
- Use the Rogers demo only.
- Do not call real Rogers. The app calls the verified demo phone number.
- If the live phone call fails while recording, use a completed result page and narrate the expected call flow.

