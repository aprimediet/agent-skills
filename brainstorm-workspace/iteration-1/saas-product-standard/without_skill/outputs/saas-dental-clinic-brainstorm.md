# Brainstorm: SaaS for Small Dental Clinics

> **Idea**: A SaaS platform for solo practitioners and small clinics (1–5 dentists) to manage patient appointments, send automated reminders, and handle intake forms.
> **Date**: 2026-06-09
> **Depth**: Standard

---

## 1. Target Market & Positioning

### Who exactly is the customer?
- **Solo practitioner** — owns the practice, does the dentistry, manages the business. They are **time-poor** and want **set-and-forget**.
- **Small clinic** (2–5 dentists) — may have a front-desk/admin person. They need **multi-provider scheduling** and **role-based access**.
- **Dental franchise / DSO** (down the line) — not the initial target, but worth keeping architectural room for.

### What makes dental clinics different from general medical or vet clinics?
- High-volume, short appointments (cleanings 30–60 min, checkups 15 min).
- Frequent reschedules (patients no-show or cancel same-day).
- Strict HIPAA compliance needed (US) / PIPEDA (Canada) / GDPR (EU).
- Insurance verification and billing codes (CDT codes) are a key pain point.
- Recall / recare system — 6-month cleaning cycle is core to the business model.

### Current alternatives (the "replace this" market)
| Solution | Weakness |
|---|---|
| Pen & paper / Excel | Error-prone, no automation, no reminders |
| Dentrix / Eaglesoft | Expensive, overkill for 1–2 dentists, clunky UI, desktop-only |
| Open Dental | Better but still complex, steep learning curve |
| General scheduling tools (Acuity, Calendly) | No dental-specific features (CDT codes, insurance, recall) |

**Positioning**: "Simple, modern, affordable — built for the independent dentist, not the DSO."

---

## 2. Core Features (MVP)

### Must-have
1. **Multi-provider appointment scheduling**
   - Calendar per dentist + combined view
   - Appointment types (cleaning, exam, filling, etc.) with configurable durations
   - Drag-and-drop reschedule
   - Blocked time / vacation / lunch
2. **Automated patient reminders**
   - SMS + email (opt-in)
   - Configurable timing: 72h, 24h, 2h before
   - Confirmation / cancellation link (2-way)
   - No-show tracking and auto-rebook
3. **Intake forms**
   - Digital forms — patient fills before visit (link sent via reminder)
   - Medical history, consent, insurance info
   - HIPAA-compliant storage
   - Auto-populate patient record
4. **Patient records (lightweight)**
   - Name, DOB, phone, email, insurance carrier/plan
   - Appointment history
   - Notes field (free-text, dentist-facing)
5. **Dashboard & analytics**
   - Today's schedule view
   - No-show rate
   - Open time slots (revenue leakage)

### Nice-to-have (post-MVP)
- Insurance eligibility verification (integrate with dental clearinghouses)
- CDT code-based billing / claim submission
- Recare / recall automation (auto-schedule next 6-month cleaning)
- Patient portal (view history, pay bills, update info)
- Payment processing (card on file, copay collection)
- Two-way SMS chat

---

## 3. Business Model

### Pricing (monthly, per clinic)
| Tier | Price | Limit |
|---|---|---|
| Solo | $79/mo | 1 dentist, 500 patients, basic analytics |
| Growth | $149/mo | 3 dentists, 1500 patients, advanced analytics + insurance check |
| Clinic | $249/mo | 5 dentists, unlimited patients, API access, priority support |

### Free trial
- 14-day free trial, no credit card required
- Onboarding call included for Growth/Clinic tiers

### Why this works
- Open Dental charges ~$200–$400/mo for comparable features but with worse UX.
- Dentist gross revenue per chair is ~$500–$2000/day — even $249/mo is noise if it saves 1 no-show per week.
- Monthly recurring with low churn (sticky — switching costs are high once patient data is in).

---

## 4. Key Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| HIPAA compliance complexity | High | Use a BAA-covered infrastructure provider (AWS/Azure), encrypt at rest & in transit, audit log all PHI access, annual SOC2 |
| Dentists are slow tech adopters | Medium | Offer white-glove onboarding, import from existing systems (CSV import, Dentrix export), free training session |
| No-show problem is a habit, not a tool gap | Medium | Ensure reminders are actually effective — A/B test timing, message copy, channel (SMS vs email), include prepay incentives |
| Competition from entrenched players | Medium | Focus on underserved segment (solo/small), offer modern UX, API-first for integrations |
| Sales cycle is long (dentist has to evaluate) | Medium | Offer a low-risk free trial, target dental Facebook groups / forums / conferences, partner with dental supply companies |

---

## 5. Technical Architecture (High-Level)

```
Frontend: React/Next.js (responsive web — dentists use desktop, patients use mobile)
Backend: Node.js / Python (FastAPI) — REST + WebSockets for real-time calendar
Database: PostgreSQL — relational, good for scheduling
Queue: Redis / Bull — for reminder scheduling (cron + delayed jobs)
File Storage: S3-compatible — encrypted intake forms, patient docs
Auth: Clerk or Auth0 — social login optional, email+password for clinic staff
SMS: Twilio
Email: SendGrid / SES
Infra: AWS or DigitalOcean — HIPAA BAA required
```

### Reminder scheduling flow
```
Patient books appointment via phone (staff enters) OR patient portal
  → Backend creates appt in DB
  → Schedules 3 reminder jobs in Redis (72h, 24h, 2h before)
  → At each interval, worker sends SMS/email with confirmation link
  → If patient confirms → mark confirmed
  → If patient cancels → free slot, notify clinic
  → If no response → mark as "not confirmed" (clinic sees amber flag)
  → If appointment passes without action → mark as "no-show" or "attended"
```

---

## 6. Onboarding & User Experience

### Clinic setup flow (first time)
1. Create account (email, password, clinic name, address)
2. Add dentist(s) — name, color-code, hours, lunch break
3. Import patients — CSV upload or manual entry
4. Configure reminder templates and timing
5. Go live — start scheduling

### Patient experience
1. Receives SMS reminder with link → opens on phone
2. Fills intake form before visit (once, then just confirms updates)
3. Shows up → dentist sees completed form
4. After visit → auto-reminder for next 6-month cleaning (recare)

---

## 7. Open Questions to Investigate

1. **HIPAA**: What exact technical and process controls are needed for a BAA? Do we need a dedicated compliance officer?
2. **Insurance integration**: Which clearinghouses (Change Healthcare, ZirMed, etc.) provide APIs? What's the cost to integrate?
3. **Recall / recare**: How do dentists currently track 6-month cycles? Is it manual calendar entry or do they use dedicated recall software?
4. **EHR vs PM**: Is this a practice management (PM) system only, or do we eventually add clinical notes / charting? (PM is simpler, larger TAM for PM, but EHR is stickier.)
5. **Desktop vs mobile**: Dentists often use desktop (Windows) in-clinic — do we need an offline-capable desktop app or is PWA enough?
6. **Patient acquisition**: What's the most cost-effective channel to reach solo dentists? (Facebook groups? Dental conferences? Partnerships with dental supply distributors?)
7. **Legacy data migration**: How painful is importing from Dentrix / Eaglesoft / Open Dental? Do we build importers or use a service like DENTRIX export CSV?
8. **Payment processing**: Stripe for basic card payments, or do we need dental-specific (claim submission, insurance adjudication)?

---

## 8. Success Metrics (for the product)

| Metric | Target (Year 1) |
|---|---|
| Paying clinics | 50 |
| Monthly churn | < 5% |
| Avg reminder confirmation rate | > 60% |
| No-show reduction vs baseline | > 30% |
| NPS score | > 50 |
| Avg onboarding time (clinic) | < 15 min |
| Forms completion rate (before visit) | > 80% |

---

## 9. Competitive Landscape Summary

| Product | Price (approx) | Strengths | Weaknesses |
|---|---|---|---|
| **Dentrix** | $500–$1000/mo | Market leader, full EHR | Expensive, Windows-only, terrible UX |
| **Eaglesoft** | $400–$800/mo | Full PM+EHR | Same as Dentrix, older tech |
| **Open Dental** | $200–$400/mo+hosting | Modular, flexible | Complex setup, dated UI, requires IT savvy |
| **Curve Dental** | $200–$500/mo | Cloud-based, modern-ish | Still expensive for solo, feature-bloated |
| **Zocdoc** | Pay-per-booking | Patient acquisition | High cost, not a full PM system |
| **YAPI** | Free / low-cost | Modern, simple | Limited features, new |

**Our angle**: Simpler, cheaper, and purpose-built for the solo/small clinic — no 12-month contracts, no implementation fees, modern UX, mobile-first for patients.

---

## 10. Next Steps

1. **Validation**: Interview 5–10 solo/small dental clinic owners to confirm pain points and willingness to pay.
2. **HIPAA groundwork**: Get legal guidance on BAA, policies, and required technical controls.
3. **Prototype**: Build a clickable prototype (Figma) of the scheduling + reminder flow — test with 3 clinics.
4. **Build MVP**: 8–12 weeks of dev — scheduling, reminders, intake forms, basic patient records.
5. **Launch**: Recruit 10 beta clinics (free first 3 months) in exchange for feedback and case studies.
6. **Iterate**: Focus on no-show reduction data and import/migration ease.
