# RateDrop Controlled Live Demo

Use one company for the demo:

```text
Rogers
```

This single call shows both core capabilities:

- Price negotiation: lower the recurring monthly bill.
- Refund/dispute handling: get a one-time credit for a bad charge.

There is only one launch button:

```text
Start voice agent
```

During judging, do not call Rogers. The app places a real Twilio call to the verified demo phone number. Answer it yourself and act as the Rogers representative.

## Demo Scenario

The user has a Rogers bill at $91.50/month and a disputed $35 roaming fee. The goal is to get the bill down to $55/month and get the $35 fee credited.

## Prefilled Mission

Company:

```text
Rogers
```

Problem:

```text
The monthly bill is too high and there is a disputed $35 roaming fee that should be credited.
```

Desired outcome:

```text
Lower the monthly bill to $55 and apply a $35 credit for the disputed roaming fee.
```

Known facts:

```text
Current Rogers bill is $91.50 on Infinite Essentials 75
There is a disputed $35 roaming fee
Comparable plans are materially cheaper
```

Constraints:

```text
Do not accept a vague callback
Do not accept only a one-time credit without monthly rate relief
Ask for loyalty or retention if frontline support cannot approve it
```

Completion proof:

```text
Rep confirms the new monthly rate
Rep confirms the $35 credit
Rep confirms the effective date and account notes
```

## Rep Script

Say these naturally:

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

## What Must Work

- The agent asks for monthly rate relief.
- The agent treats the $35 fee as a credit/refund issue.
- The agent does not accept only the credit.
- The agent counters a weak $70 monthly offer.
- The agent accepts $55/month plus $35 credit.
- The agent closes only after proof is confirmed.
