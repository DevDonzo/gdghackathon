# FRONTEND_RULES

This document is for frontend work on RateDrop.

The frontend should make the product feel polished and clear without changing how the backend works.

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
- `lib/types.ts`
- negotiation logic
- savings math
- Mongo document structure
- Twilio callback behavior

## Main Files To Work In

- `app/page.tsx`
- `app/call/[id]/page.tsx`
- `app/result/[id]/page.tsx`
- `components/upload-panel.tsx`
- `components/call-dashboard.tsx`
- `components/result-summary.tsx`
- `app/globals.css`

Read for context:

- `lib/api.ts`
- `lib/types.ts`

## Current Frontend Flow

1. Home page loads demo bills and recent negotiations
2. User uploads a file or picks a demo bill
3. UI renders extracted bill details
4. User starts negotiation
5. App routes to `/call/[id]`
6. Transcript updates via SSE
7. App routes to `/result/[id]`

## Design Direction

The UI should feel like a focused consumer product, not an internal dashboard.

Priorities:

- clear hierarchy
- fast comprehension
- strong before/after storytelling
- visible trust signals
- readable transcript progression
- clean mobile layout

Avoid:

- generic enterprise dashboard styling
- cluttered cards everywhere
- excessive labels with weak hierarchy
- overdesigned gradients with poor contrast
- making the call page feel like a developer console

## Product Copy Rules

- Brand only as `RateDrop`
- Do not mention ASSIST
- Do not mention internal demos or prior prototypes
- Speak like a consumer product
- Make the sandbox nature clear where relevant, but do not make the product sound fake

## Integration Rules

Use the existing helpers in `lib/api.ts`.

Do not scatter raw fetch logic across components unless there is a strong reason.

Use the existing types in `lib/types.ts`.

If a backend field is unclear, ask the backend owner before changing the type locally.

## Error Handling Rules

The UI should handle:

- upload failure
- extraction failure
- negotiation start failure
- SSE disconnects
- missing result data
- sandbox call fallback or call error states

The UI should explain the issue in plain language, not dump raw JSON unless nothing else is available.

## Loading Rules

Always provide a useful loading state for:

- homepage initial data
- bill extraction
- negotiation start
- transcript loading
- result loading

Do not leave empty white states while requests are in flight.

## Safe Refactor Rules

Safe:

- split large components
- create shared presentational components
- improve semantic HTML
- improve accessibility
- improve spacing, motion, and typography

Unsafe without backend coordination:

- renaming fields from the API
- assuming new status values
- changing event stream payload handling

## Visual Emphasis

The three moments that matter most:

1. Uploading or choosing a bill
2. Watching the negotiation unfold
3. Seeing the savings outcome clearly

If the frontend has to prioritize, make those three moments excellent first.

## Local Run

Run frontend:

```bash
npm run dev
```

Run backend separately:

```bash
npm run dev:api
```

Open:

```text
http://127.0.0.1:3000
```

## Required Checks Before Shipping Frontend Changes

```bash
npm run build
```

Then manually verify:

1. Home page loads
2. Demo bill selection works
3. Start negotiation routes to call page
4. Call page renders transcript updates
5. Result page renders savings correctly

## Handoff Summary

If you are the frontend owner:

- make it look strong
- make it read clearly
- do not rewrite backend behavior
- keep RateDrop branding intact
