# Dental Clinic SaaS — Brainstorm Document

> **Idea**: A SaaS platform for small dental clinics (1–5 dentists) to manage patient appointments, send automated reminders, and handle intake forms.
> **Target**: Solo practitioners and small group practices.

---

## 1. Market & Opportunity

### Landscape
- Dental software market is dominated by **legacy on-premise systems** (Dentrix, Eaglesoft, Open Dental) — expensive, complex, require IT support.
- Cloud-native alternatives exist (Zocdoc for booking, RevenueWell for reminders) but are **fragmented** — practices stitch together multiple tools.
- Small clinics are **underserved**: they want the sophistication of enterprise software without the cost or complexity.

### Why Now
- Post-COVID patient expectations for **digital-first interactions** (online booking, contactless intake).
- Front-desk staffing shortages — automation directly reduces overhead.
- Solo practitioners are increasingly tech-comfortable (younger dentists buying existing practices).

### Key Differentiators vs. Incumbents
| Factor | Incumbents | This Product |
|---|---|---|
| Deployment | On-prem / Windows-only | Cloud (any browser) |
| Pricing | Upfront license + support fees | Monthly subscription |
| Setup | Weeks, requires IT | Self-serve, minutes |
| UX | Clinic-centric, dense UI | Patient-centric, modern UX |
| Integration | Closed ecosystems | API-first, open |

---

## 2. User Personas

### Primary: The Solo Practitioner (Dr. Chen)
- **Practice**: 1 dentist, 1 hygienist, 2 front-desk staff.
- **Pain points**: Double-booking, missed appointments (no-shows ~20%), paper intake forms lost or illegible.
- **Tech comfort**: Uses email, maybe a practice management system from 2010. Wants "something that just works."
- **Decision criteria**: Price, ease of use, support.

### Secondary: The Office Manager (Maria)
- **Practice**: 3-dentist clinic, 5 front-desk / admin staff.
- **Pain points**: Juggling multiple schedules, manual reminder calls consume 2+ hours/day, reconciling paper forms into EHR.
- **Tech comfort**: Proficient with practice software, resistant to change unless clearly better.
- **Decision criteria**: Time saved per day, training effort, reliability.

### Tertiary: The Patient (Any)
- **Needs**: Book online without calling, receive timely reminders, fill forms on phone before visit.
- **Expectation**: Works like OpenTable or Amazon — frictionless.

---

## 3. Core Feature Set

### Tier 1: MVP (Month 1–3)

| Feature | Description |
|---|---|
| **Online Booking Widget** | Embeddable calendar showing available slots; patient books without login. |
| **Appointment Calendar** | Day/week/month view for staff; drag-and-drop rescheduling; color-coded by provider. |
| **Automated Reminders** | SMS + email reminders at configurable intervals (48h / 24h / 1h). Patient can confirm, reschedule, or cancel from the message. |
| **Digital Intake Forms** | Pre-built dental intake templates (medical history, insurance, consents). Patient fills via link before visit. Auto-populates patient profile. |
| **Patient Database** | Searchable list with contact info, appointment history, form submissions, notes. |
| **Staff & Provider Management** | Add/remove providers, set working hours, breaks, buffer times. |
| **Notification Preferences** | Per-patient opt-in/out for SMS vs email. |

### Tier 2: Growth (Month 4–6)

| Feature | Description |
|---|---|
| **Insurance Verification** | Scan insurance card photo → parse group/ID numbers → check eligibility via clearinghouse (Change Healthcare, etc.). |
| **Automated Waitlist** | When slots open, auto-notify waitlisted patients in order. |
| **Custom Reminder Templates** | Clinic-branded messages; different tone for new vs. returning patients. |
| **Recurring Appointments** | Set series (e.g., "every 6 months for cleaning") with auto-scheduling. |
| **Treatment Plan Integration** | Link appointments to procedures; show estimated costs / insurance coverage. |
| **Reporting Dashboard** | No-show rates, booking sources, revenue per provider, patient acquisition trends. |

### Tier 3: Scale (Month 7+)

| Feature | Description |
|---|---|
| **Two-Way SMS Chat** | Patients can text the clinic; threaded responses with provider routing. |
| **Telehealth Check-in** | Video link generation for pre-op consultations or follow-ups. |
| **EHR Lite** | Basic clinical notes — SOAP templates, tooth chart diagrams, prescription writing. (Big scope — consider partnership instead.) |
| **Multi-Location** | Unified dashboard for clinics with 2+ offices. |
| **Payment Processing** | Collect copays/deposits at booking. Stripe integration. |
| **Patient Portal** | Full portal: view history, download forms, pay bills, message clinic. |

---

## 4. Technical Architecture (High-Level)

```
[Browser / Mobile] → [CDN / S3] → [Load Balancer] → [Web Servers (Node.js / Python)]
                                                          │
                                                          ├→ [PostgreSQL] (patients, appointments, forms)
                                                          ├→ [Redis] (scheduler locks, rate limits)
                                                          ├→ [Twilio] (SMS reminders)
                                                          ├→ [SendGrid / SES] (email reminders)
                                                          └→ [S3] (form uploads, insurance scans)
```

### Key Decisions to Make
| Decision | Options | Consideration |
|---|---|---|
| **Frontend** | React + Tailwind vs. Vue vs. Svelte | React has biggest component ecosystem for scheduling UIs. |
| **Backend** | Node.js (Express) vs. Python (Django) | Node is fine for real-time; Django gives admin panel for free. |
| **Scheduling Engine** | Custom vs. use Cal.com / nylas as base | Custom gives full control; Cal.com is open-source but dental-specific tweaks needed. |
| **SMS Provider** | Twilio vs. Vonage vs. AWS SNS | Twilio is most reliable but pricier; evaluate volume pricing. |
| **Hosting** | AWS vs. Railway vs. Render | Start simple (Render/Railway), migrate to AWS for scale. |
| **Form Engine** | Custom builder vs. Typeform embed vs. Formio | Custom gives full data control; Formio is open-source and embeddable. |

### Compliance & Security
- **HIPAA**: Required by law. Must sign BAAs with all subprocessors (hosting, SMS, email).
- **Data Encryption**: AES-256 at rest; TLS 1.3 in transit.
- **Audit Logs**: Every access to patient data logged with timestamp and user ID.
- **Backup**: Daily automated backups with 30-day retention; point-in-time recovery.
- **Breach Notification**: Policy and automated alerting on anomalous access patterns.

---

## 5. Business Model

### Pricing Tiers

| Tier | Price | Features |
|---|---|---|
| **Starter** | $79/mo | 1 provider, 500 reminders/mo, basic booking + forms |
| **Growth** | $149/mo | Up to 3 providers, 2,000 reminders/mo, insurance scanning, waitlist |
| **Scale** | $249/mo | Up to 6 providers, 5,000 reminders/mo, reporting, multi-location |
| **Enterprise** | Custom | Unlimited providers, EHR-lite, dedicated support, on-prem option |

### Key Metrics
- **Target MRR per clinic**: $79–249/mo.
- **TAM**: ~100,000 small dental clinics in US → $100M–$300M addressable market.
- **Customer Acquisition**: Dental Facebook groups, Google Ads ($CAC ~$200–400), partnerships with dental supply distributors.
- **Churn Target**: < 5% monthly (typical SaaS benchmark for SMB).

### Go-to-Market Channels
1. **Direct outreach** — Email campaigns to solo practices listed on Healthgrades / Yelp.
2. **Dental supplier partnerships** — Bundle with Henry Schein / Patterson Dental orders.
3. **Free trial** — 14-day no-credit-card trial; onboarding call included.
4. **Referral program** — 1 month free for every referred clinic that converts.

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **HIPAA compliance mistake** | Medium | Critical | Engage compliance consultant pre-launch; automated data validation. |
| **Low adoption by older dentists** | Medium | High | Offer white-glove onboarding; emphasize time-savings over features. |
| **Integration dependency (EHR)** | High | Medium | Start with forms + booking only; EHR can be a separate product/partnership. |
| **No-show rates don't improve** | Low | Medium | Track baseline per clinic; publish results to prove ROI. |
| **Pricing too low for viability** | Medium | High | Test pricing via landing page A/B before building. |
| **Twilio SMS costs at scale** | Medium | Medium | Bundle SMS into tier pricing; negotiate volume discounts early. |

---

## 7. Open Questions (To Resolve Before Building)

### Product
- Should we build an integrated **patient mobile app** or rely on responsive web + SMS?
  - *Lean: Web + SMS first; app is a v2 retention play.*
- Do we handle **insurance claims submission**, or only verification?
  - *Verification only — claims are a separate, heavily regulated domain.*
- Should forms be **clinic-branded** or use a neutral template?
  - *Branded from day 1 — clinics want to look professional.*

### Business
- **Single clinic or multi-location** first? Multi-location adds complexity; start single-location.
- **US only or international?** US healthcare regulations are already complex; adding GDPR / PIPEDA multiplies it. Start US-only.
- **Direct sales or self-serve?** Self-serve for small clinics; sales team for 5+ provider practices.

### Technical
- **Offline mode** for clinics with unreliable internet?
  - *Critical for some rural clinics — consider PouchDB/CouchDB sync or a local companion app.*
- **EHR integration standards** — FHIR vs. custom API?
  - *Support both: FHIR for modern systems, custom for legacy (Dentrix, Open Dental).*

---

## 8. MVP Scope — The Sharpest Cut

To ship in 8–10 weeks with 1–2 engineers, the MVP should be:

```
Online Booking (patient-facing)
├── Public booking page with calendar widget
├── Timezone-aware slot display
├── Appointment confirmation via email + SMS
└── Cancel / reschedule from confirmation link

Staff Dashboard (clinic-facing)
├── Login (email + password)
├── Manage booking page settings (hours, buffers, providers)
├── View / edit / cancel appointments
├── Manual appointment creation
├── Patient directory (name, phone, email, notes)
└── View submitted intake forms

Digital Intake Module
├── 3–5 pre-built dental intake form templates
├── Patient fills via link → PDF generated + saved
├── Auto-populate basic patient info into dashboard
└── Basic medical history and consent fields

Reminder Engine
├── Configurable timing (48h / 24h / 1h before)
├── SMS via Twilio
├── Email via SendGrid
├── Opt-out link in every message
└── Delivery status logging
```

**Explicitly excluded from MVP**:
- No insurance verification
- No payment processing
- No multi-location
- No patient portal (beyond forms)
- No reporting / analytics
- No recurring appointment series

---

## 9. Success Criteria

| Metric | MVP Target | Growth Target |
|---|---|---|
| Pilot clinics | 5 | 50 |
| Appointments booked via platform | 200/mo | 5,000/mo |
| No-show rate reduction | ≥30% | ≥40% |
| Avg. staff time saved per day | 1 hr | 2 hr |
| NPS | ≥40 | ≥60 |
| Monthly churn | <10% | <5% |

---

## 10. Next Steps

1. **Validation calls** — Interview 10 solo dentists / office managers (15 min each). Validate booking + reminders are #1 pain point.
2. **Landing page A/B test** — $500 ad spend to test pricing and value prop messaging.
3. **HIPAA compliance review** — Engage a healthcare SaaS compliance consultant ($2k–5k).
4. **Technical spike** — Build a booking widget prototype in 1 week with a fake back end; show to pilot users for reaction.
5. **Incorporate** — US-based LLC with HIPAA-ready hosting agreements in place.
6. **Build MVP** — 2-person team (1 full-stack, 1 part-time frontend + design). Target 10 weeks.

---

> *This document is a snapshot for discussion — every section should be challenged, narrowed, or expanded before committing to a build plan.*
