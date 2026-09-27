---
name: tally-form-architect
description: Activate when the user is designing forms — Tally, Typeform, Google Forms, Jotform, custom HTML — for lead capture, surveys, onboarding, registration, feedback, application intake, or research. Produces forms structured for completion (right field count, right field types, right ordering, right copy, right logic) rather than forms that satisfy stakeholder field-stuffing impulses. Tally is the primary recommendation when criteria fit (free unlimited responses, robust logic, embeddable). Refuses to design forms with deceptive UX (pre-checked consent, dark patterns, hidden costs) or forms that collect data the team has no plan to use. Treats every field as having a completion cost and asks whether the value justifies it.
---

# Tally Form Architect

Forms are conversation interfaces. A 5-field form converts at maybe 70%; a 25-field form might convert at 8%. The architect's job is keeping the form to the fields that earn their place — every additional field is a tax on completion rate.

## Core principle

**Every field is a question the user could leave instead of answering.** Every required field that doesn't directly serve the next decision is a field that pushes completion rate down. The default answer to "should we add this field?" is no, with a high bar to overturn.

## When to use

| Situation | Activate? |
|---|---|
| Lead capture form (B2B / consumer) | Yes |
| Customer survey | Yes |
| Application / intake form | Yes |
| Onboarding flow | Yes — form is part of broader onboarding skill |
| Event registration | Yes |
| Quiz / qualification flow | Yes |
| Multi-step / branching forms | Yes |
| Internal tooling form | Yes — though stakes lower |
| Pure form-builder tutorial | No — different ask |

## Tally specifically

Tally is recommended over alternatives when:
- Need unlimited responses on free tier (Tally's defining feature)
- Need conditional logic (free; paid in most alternatives)
- Need calculations (free in Tally)
- Need embedding (free, multiple modes)
- Need custom branding (paid in Tally, but cheaper than Typeform)
- Want quick build with Notion-like editing

Choose alternatives when:
- Need deeply branded / custom look beyond Tally's options → Typeform or custom
- Need form-to-CRM that's specifically pre-built and complex → vendor-native (HubSpot forms for HubSpot CRM)
- Need offline / paper-equivalent → Google Forms for simplicity
- Need enterprise compliance (HIPAA, SOC2 for sensitive data) → Jotform Healthcare or similar

## Workflow

### Step 1: Define the form's job

Before designing, get clarity on:

1. **What action does the form trigger downstream?**
   - "Schedule a call" — fields support scheduling + qualifying
   - "Send a quote" — fields support quoting
   - "Add to nurture list" — minimum fields, drip handles the rest
   - "Internal triage" — fields support routing decision

2. **What's the alternative action the user is choosing this over?**
   - Closing the tab, going to a competitor, doing nothing — the form must beat their threshold for effort

3. **Who reads the responses?**
   - If sales: they need contact + qualifying signals
   - If product: they need user role + use case
   - If support: they need account + issue specifics

4. **What's the conversion target?**
   - High-volume top-of-funnel (newsletter): completion rate matters more than data depth — fewer fields
   - Bottom-of-funnel (demo request): completion rate matters less; qualification matters more — more fields acceptable

The job determines field count.

### Step 2: Field minimum

Default to fewer. For each field, justify:

| Field | Required for | Decision |
|---|---|---|
| Email | Contact, identification | Required |
| First/Last name | Personalization, communication | Often required |
| Company | B2B routing | Required for B2B |
| Role / title | Sales qualification, segmentation | Conditional |
| Company size | Sales routing | Conditional — only if it changes routing |
| Phone | Sales follow-up | Optional usually; required only if phone is the channel |
| Use case / pain | Sales prep, segmentation | Optional / 1 selection |
| How did you hear about us | Marketing attribution | Optional |
| Country / region | Compliance / localization | Conditional |

Rule of thumb:
- Newsletter signup: 1–2 fields (email; optional name)
- Demo request: 4–6 fields (email, name, company, role, use case, optional phone)
- Application / detailed intake: 8–15 fields, broken into multiple steps
- Enterprise sales form: 6–10 fields with company size as routing trigger

### Step 3: Field type selection

Picking the right input type is half the design:

| Question | Best field |
|---|---|
| Email | Email field with validation |
| Yes / no | Single-select radio (Yes / No) — not a checkbox |
| Pick one from a list ≤7 | Radio buttons / dropdown |
| Pick one from a list >7 | Searchable dropdown |
| Pick multiple | Checkbox group |
| 5-point or 7-point scale | Linear scale / matrix |
| Open-ended text | Short text (1 line) or long text (multiline); pick based on expected length |
| Numeric range | Slider or numeric input with min/max validation |
| Date | Date picker (not free text) |
| Phone | Phone field with country code |
| File upload | File uploader (size limit specified) |
| Sensitive (SSN, password) | Don't collect via form unless absolutely necessary; appropriate field with masking |

Common mistakes:
- Open-ended text where a multi-select would do (and analyze better)
- Multi-select where a single-select would do (forced specificity is useful)
- Linear scale where binary would do (1–10 satisfaction scales are noisy)

### Step 4: Field order

Order matters psychologically:

1. **Easiest / lowest-friction first** — email or name
2. **Building commitment** — questions of moderate effort that the user has already started so they continue
3. **Hardest / qualifying / sensitive** — closer to the end
4. **Don't end on hard** — close with an easy one or a confirmation

For sales-qualifying forms, the order also encodes priority:
- Contact info (lead exists)
- Company (lead is real)
- Use case (lead has need)
- Timeline / budget (lead is ready)

### Step 5: Multi-step / progressive disclosure

For forms >5 fields, multi-step is almost always better than long-page:

- Each step ≤3 fields
- Progress indicator visible
- Don't rely on "save and resume" — most users abandon when they close
- Logic-branching steps based on early answers (skip irrelevant sections)

Tally's multi-step support is solid; use it.

### Step 6: Conditional logic

Use logic to:
- Skip irrelevant questions ("Don't ask about team size to a solo user")
- Surface follow-up depth only when warranted ("If unsatisfied, ask why")
- Route to different ending screens based on answers ("Enterprise → calendar booking; SMB → trial signup")

Don't use logic to:
- Force users into branches they didn't choose
- Hide that some answers gate them out of follow-up
- Add complexity the team can't maintain

### Step 7: Copy

Form copy is half the conversion rate:

- **Form title**: descriptive, not cute. "Request a demo" beats "Let's chat"
- **Form description**: 1 sentence on what happens after submission. Set expectations (response time, what they'll receive)
- **Field labels**: above the field, not placeholder-as-label (accessibility + UX). Specific. "Work email" beats "Email"
- **Help text**: under fields where ambiguity exists. Sparingly.
- **Required indicators**: visible, conventional (asterisk)
- **Submit button**: action verb, specific. "Send my request" beats "Submit"
- **Privacy / consent text**: under or near submit. Honest about what happens with data.

### Step 8: Validation

Client-side validation that fires on blur (not on every keystroke; not only on submit):
- Email format check
- Required field check
- Min/max length where relevant
- Pattern match (phone, postal code)

Error messages: specific. "Email looks incomplete — missing @" beats "Invalid".

### Step 9: Confirmation / thank-you

What happens after submit?
- Confirmation screen with what to expect next
- If immediate value can be delivered (download, calendar link), deliver it
- Email confirmation if response comes later
- Tracking: pixel / event for analytics

Don't end on a generic "Thank you" with no next step — the user is most engaged the moment after submitting; use that.

### Step 10: Compliance and privacy

For any form collecting personal data:
- Privacy policy link
- Consent for marketing communications (separate from form submission consent — opt-in, not pre-checked)
- GDPR / DPDP / CCPA depending on jurisdiction
- Data retention disclosed
- Right to delete / opt-out

Pre-checked consent boxes are a dark pattern in many jurisdictions (illegal under GDPR). Don't.

## Output format

```
# Form Design — [Form purpose] — [Date]

## Form job
- Triggers: [downstream action]
- Audience: [who fills this out]
- Conversion target: [completion rate / qualification rate]

## Field list
| # | Field | Type | Required | Reason | Notes |
|---|---|---|---|---|---|

## Field order rationale
[Why this order]

## Multi-step structure
- Step 1: [fields]
- Step 2: [fields]
- ...

## Conditional logic
- If [field X] = [value], then [action]
- ...

## Copy
- Title: ...
- Description: ...
- Submit button: ...
- Confirmation screen: ...

## Validation
- [Per field with validation]

## Compliance
- [Consent checkbox text]
- [Privacy policy link]
- [Data retention note]

## Tally setup
- [Specific Tally features used]
- [Embed mode: standalone / popup / embedded / chat-style]

## Measurement
- Conversion target: [%]
- Tracking: [analytics events]
```

## Anti-patterns

1. ❌ Stuffing every conceivable field "in case sales wants it" — ignore unused fields drag completion rate
2. ❌ Marking everything required — required-creep kills conversions; only fields needed for the next step
3. ❌ Pre-checked marketing consent — dark pattern, often illegal
4. ❌ Asking phone for B2B newsletter signup — wildly off-purpose for the action
5. ❌ Free-text where multi-select would work — harder for user, harder to analyze
6. ❌ Dropdowns of 50 countries / states without search — friction
7. ❌ Forms that don't validate email format — bounces clog downstream sequences
8. ❌ Single-page form with 20 fields — multi-step
9. ❌ "Other (please specify)" with no character limit — gets abused
10. ❌ Hard-coding form state in URL params — accessibility / shareability issues
11. ❌ Submit button labeled "Submit" — generic; specify the action
12. ❌ Confirmation screen that says "Thank you" with no next step — wastes engaged moment
13. ❌ Asking the same info twice (in form + during scheduling tool that follows)
14. ❌ Form abandonment rate not tracked — without measurement, can't improve
15. ❌ Honeypot field plus visible captcha — pick one; both is overkill
16. ❌ Forms that require account creation to submit — almost always wrong; collect data first, account later

## Confidence calibration

- Field count for completion rate: high — well-evidenced
- Specific completion rate prediction: low — varies by audience, traffic source, offer
- Whether multi-step > single-page in your specific case: high (almost always for >5 fields)
- Optimal copy / button text: medium — A/B test variants
- GDPR / privacy compliance: medium — verify with legal counsel for high-stakes flows
