# RateDrop Devpost Video

Target length: 90 seconds to 2 minutes.

Format: one person records the screen and talks while using the product. No separate voiceover, no cinematic cuts required.

Live app:

```text
https://ratedrop-reezumnw5a-uc.a.run.app
```

## 0:00-0:15 Hook

On screen:

- Start on the RateDrop landing page.
- Keep your camera/audio on if you want, but the main focus should be the screen.

Say:

```text
Don’t you hate when you have to call support, sit on hold forever, explain the same problem three times, and still leave without the refund, credit, or better price you needed?

Companies already use AI to deal with us. RateDrop gives consumers an AI agent back.
```

## 0:15-0:30 What RateDrop Does

On screen:

- Scroll the landing page briefly.
- Click `Start`.
- Sign in.

Say:

```text
RateDrop is a phone agent for consumer support calls. You give it evidence, a goal, constraints, and what proof counts as done. Then it calls support and handles the conversation for you.
```

## 0:30-0:55 Setup The Demo

On screen:

- Click `Rogers demo`.
- Show the prefilled mission fields.

Say:

```text
For this demo, the customer has a Rogers bill at $91.50 a month and a disputed $35 roaming fee.

The mission is specific: lower the monthly bill to $55, get the $35 fee credited, and do not finish until the representative confirms the new rate, the credit, the effective date, and the account notes.
```

Show quickly:

- Company: Rogers
- Problem
- Desired outcome
- Target monthly: 55
- Walk-away max: 60
- Completion proof

## 0:55-1:25 Live Call

On screen:

- Click `Start voice agent`.
- Answer the phone when it rings.
- Act as the Rogers representative.

Say to the phone as the representative:

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

After the call, say:

```text
The important part is the agent loop. It did not accept a vague no, it did not accept only a one-time credit, it countered the weak offer, and it only closed after proof was confirmed.
```

## 1:25-1:45 Result

On screen:

- Show the result page.
- Show the proof trail.
- Click `Email proof`.

Say:

```text
RateDrop turns the call into a structured result: the original bill, the new monthly rate, the one-time credit, the transcript, and proof by email.
```

## 1:45-2:00 Cloud Proof

On screen:

- Open `/api/readiness`.

Say:

```text
This is running on Google Cloud Run. The same cloud service handles the frontend, backend API, Twilio webhooks, live transcript streaming, and the ConversationRelay WebSocket.

It uses Google ADK and Gemini for the agent layer, Secret Manager for credentials, Cloud Build for deployment, and Artifact Registry for the container.
```

Final line:

```text
RateDrop handles the support calls you do not want to make.
```

## Recording Notes

- Talk naturally while clicking through the product.
- Keep the video fast. Do not explain every field.
- Use the Rogers demo only.
- Do not call real Rogers. The app calls the verified demo phone number.
- If the live phone call fails while recording, show a completed Rogers result and explain the expected call flow.

