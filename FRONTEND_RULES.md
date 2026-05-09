# FRONTEND_RULES

This document is for frontend work on RateDrop.

The active frontend is plain HTML, CSS, and JavaScript in [`frontend/static/`](/Users/hparacha/Projects/gdghackathon/frontend/static).

## What Frontend Owns

- landing page design
- upload flow UX
- demo bill selection UX
- extracted bill summary presentation
- live transcript presentation
- result page presentation
- loading states
- empty states
- error states
- responsive behavior

## What Frontend Does Not Own

Do not change these unless the backend owner explicitly asks for it:

- API routes
- API response shapes
- negotiation logic
- savings math
- Mongo document structure
- Twilio callback behavior

## Main Files To Work In

- [`frontend/static/index.html`](/Users/hparacha/Projects/gdghackathon/frontend/static/index.html)
- [`frontend/static/styles.css`](/Users/hparacha/Projects/gdghackathon/frontend/static/styles.css)
- [`frontend/static/app.js`](/Users/hparacha/Projects/gdghackathon/frontend/static/app.js)

Reference only:

- [`frontend/next-legacy/`](/Users/hparacha/Projects/gdghackathon/frontend/next-legacy)

## Current Frontend Flow

1. Home page loads
2. User uploads a file or picks a demo bill
3. UI renders extracted bill details
4. User starts negotiation
5. App routes to `/call/[id]`
6. Transcript updates via SSE
7. App routes to `/result/[id]`

## Design Direction

The UI should feel like a focused consumer product, not an internal dashboard or hackathon demo site.

Priorities:

- clear hierarchy
- restraint
- strong typography
- fast comprehension
- visible trust signals
- readable transcript progression
- clean mobile layout

Avoid:

- card overload
- dashboard grids everywhere
- loud gradients for no reason
- cluttered feature marketing
- making the homepage feel like a technical demo checklist

## Product Copy Rules

- Brand only as `RateDrop`
- Do not mention ASSIST
- Do not mention internal demos or prior prototypes
- Speak like a consumer product
- Make the sandbox nature clear where relevant, but do not make the product sound fake

## Integration Rules

The active frontend calls backend endpoints directly from `frontend/static/app.js`.

Do not invent new response shapes in the frontend.

If an API field is unclear, resolve it in the backend contract rather than patching around it cosmetically.

## Error Handling Rules

The UI should handle:

- upload failure
- extraction failure
- negotiation start failure
- SSE disconnects
- missing result data
- sandbox call fallback or call error states

The UI should explain the issue in plain language.

## Loading Rules

Always provide a useful loading state for:

- homepage initial data
- bill extraction
- negotiation start
- transcript loading
- result loading

Do not leave blank white states while requests are in flight.

## Safe Refactor Rules

Safe:

- restructuring the HTML
- simplifying sections
- improving semantic markup
- improving accessibility
- tightening spacing, motion, and typography

Unsafe without backend coordination:

- changing endpoint assumptions
- changing event payload assumptions
- changing negotiation status expectations

## Visual Emphasis

The three moments that matter most:

1. Uploading or choosing a bill
2. Watching the negotiation unfold
3. Seeing the savings outcome clearly

If the frontend has to prioritize, make those three moments excellent first.

## Local Run

Run backend:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Required Checks Before Shipping Frontend Changes

```bash
node --check frontend/static/app.js
```

Then manually verify:

1. Home page loads
2. Demo bill selection works
3. Start negotiation routes to call page
4. Call page renders transcript updates
5. Result page renders savings correctly

## Handoff Summary

If you are the frontend owner:

- make it feel like a real product
- remove unnecessary visual noise
- do not rewrite backend behavior
- keep RateDrop branding intact
