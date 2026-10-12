# Cardiology Chest Pain Pilot — Clinician Review Pack (Workshop)

**Phase 2J** · Target duration **15–20 minutes** · **Design review only** — no rule YAML, no thresholds, no live product.

**Design version:** `cardiology-chest-pain-v0.1.1-design` · **Vocabulary:** cardiology `1.0.0` (`approved_demo` — not production-approved)

**Sources (metadata only; not licensed for rule encoding):** AHA/ACC 2021 chest pain (primary framing); ESC 2023 ACS (ACS-specific, secondary). See [`chest_pain_verified_source_references.md`](chest_pain_verified_source_references.md).

---

## Part A — Structured inputs (vocabulary)

For each item: mark **KEEP** · **CHANGE** · **REMOVE** · **ADD** (add suggestions in free text).

### Complaints (TR labels shown)

| Clinician label (TR) | EN |
|----------------------|-----|
| Göğüs ağrısı | Chest pain |
| Dispne | Dyspnea |
| Çarpıntı | Palpitations |
| Senkop | Syncope |
| Baş dönmesi | Dizziness |
| Yorgunluk | Fatigue |
| Periferik ödem | Peripheral edema |

### Findings / history

| Clinician label (TR) | EN |
|----------------------|-----|
| Eforla ilişkili semptomlar | Exertional symptoms |
| Ortopne | Orthopnea |
| Paroksismal nokturnal dispne | Paroxysmal nocturnal dyspnea |
| Düzensiz nabız | Irregular pulse |
| Alt ekstremite ödemi | Lower extremity edema |
| Sigara öyküsü | Smoking history |
| Diyabet öyküsü | Diabetes history |
| Hipertansiyon öyküsü | Hypertension history |
| Ailede kardiyovasküler öykü | Family cardiovascular history |

### Questions (yes / no / unknown)

| Clinician label (TR) | EN |
|----------------------|-----|
| Eforla göğüs ağrısı | Chest pain on exertion |
| Göğüs ağrısı süresi | Chest pain duration *(note: answer model may need review)* |
| Eforla dispne | Dyspnea on exertion |
| Eforla senkop | Syncope with exertion |
| Çarpıntı süresi | Palpitations duration |

### Vitals

| Clinician label (TR) | EN |
|----------------------|-----|
| Sistolik kan basıncı | Systolic blood pressure |
| Diyastolik kan basıncı | Diastolic blood pressure |
| Kalp hızı | Heart rate |
| Oksijen satürasyonu | Oxygen saturation |

---

## Part B — Chest pain characterization gaps (review only)

Not mandatory — which should be **structured in first MVP** vs **free text** vs **unnecessary**?

| Concept | Structured MVP? | Free text OK? | Unnecessary? | Notes |
|---------|-----------------|---------------|--------------|-------|
| Location | ☐ | ☐ | ☐ | |
| Radiation | ☐ | ☐ | ☐ | |
| Quality / character | ☐ | ☐ | ☐ | |
| Duration (numeric + unit) | ☐ | ☐ | ☐ | |
| Severity (ordinal) | ☐ | ☐ | ☐ | |
| Pleuritic features | ☐ | ☐ | ☐ | |
| Positional features | ☐ | ☐ | ☐ | |
| Associated dyspnea | ☐ | ☐ | ☐ | *(partially covered)* |
| Diaphoresis | ☐ | ☐ | ☐ | |
| Nausea / vomiting | ☐ | ☐ | ☐ | |
| Syncope / presyncope | ☐ | ☐ | ☐ | |
| Known cardiovascular disease / PCI-CABG | ☐ | ☐ | ☐ | |

**Missing concept we should add:** _______________________________

---

## Part C — Missing information

*When a patient presents with chest pain, which information would you want flagged as **missing** before showing any clinical considerations?*

List **top 5–10** only (free text):

1.  
2.  
3.  
4.  
5.  

---

## Part D — Suggested questions

- Which reminders are **genuinely useful**?  
- Which would **interrupt** workflow unnecessarily?  
- What should **never** be auto-suggested without context?  

*(No implementation — feedback only.)*

---

## Part E — Safety alert philosophy

No thresholds or rule encoding today.

- What **types of situations** warrant a visible safety alert?  
- When should the system **stay silent**?  
- **Alert fatigue** risk — high / medium / low?  
- Should alerts require **acknowledgment**?  
- Wording that avoids **false reassurance**?  

---

## Part F — Differential display preference

**No probability output is planned.**

Preferred display for future “considerations”:

- ☐ **A** Unranked list  
- ☐ **B** Ordinal bands (e.g. higher / medium attention)  
- ☐ **C** Ordered list **without** probability  
- ☐ **D** Other: _______________

---

## Part G — Output wording (TR examples)

| Example string | Useful? | False confidence? | Suggested change |
|----------------|---------|-------------------|------------------|
| “Değerlendirmede dikkate alınabilir.” | ☐ | ☐ | |
| “Bu alan için yeterli yapılandırılmış bilgi bulunmuyor.” | ☐ | ☐ | |
| “Şu bilgi henüz kaydedilmemiş.” | ☐ | ☐ | |

English equivalents will mirror approved TR tone.

---

## Part H — First MVP boundary

Should the **first** chest-pain pilot emphasize only:

- structured history collection  
- missing information  
- question reminders  

**before** differential or safety outputs?

- ☐ Yes — defer considerations/alerts  
- ☐ No — include considerations early  
- ☐ Hybrid: _______________

---

## After the workshop

Record outcomes in [`reviews/cardiology_review_record_template.md`](reviews/cardiology_review_record_template.md) (copy to a dated file when completed).

**Record template outcomes (reference):** `NEEDS_REVISION` · `ACCEPTABLE_FOR_DEMO_DESIGN` · `CLINICALLY_REVIEWED_FOR_DEMO` — not `approved_prod`.

---

## Workshop invitation (draft — do not send)

**Subject:** 20-min design review — chest pain CDS pilot (no patient data)

Merhaba / Hello,

We invite you to a **20-minute** structured review of our **chest pain clinical decision support pilot design** (documentation and vocabulary only — no live AI diagnosis). We seek your feedback on structured fields, missing-information priorities, and safe wording. No guideline text will be shared from our side; this is product design governance.

Proposed format: walkthrough of attached pack + open notes.

Date/time: **TO_FILL**  
Location/video: **TO_FILL**

Thank you,  
**TO_FILL**
