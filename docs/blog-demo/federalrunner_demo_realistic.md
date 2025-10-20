# FederalRunner Voice Demo Script - Samsung Galaxy Fold 7
## Based on Actual FSA Wizard Structure (7 Pages, 17 Required Fields)

---

## Demo Setup Notes

**Device:** Samsung Galaxy Fold 7
**App:** Claude Mobile (Android)
**Connection:** FederalRunner MCP via Google Cloud Run
**Persona:** High school senior (your daughter) applying to colleges
**Context:** Using voice while doing other things (walking, driving, relaxing)

**Critical Voice Patterns for Galaxy Fold 7:**
- Speak naturally, not robotic
- Pause briefly between sentences for processing
- Use conversational filler words ("um", "like", "you know")
- Correct yourself naturally if misheard
- Reference what you're doing physically ("I'm sitting here thinking...")

---

## **RECOMMENDED DEMO FLOW: The "Three Moments" Arc**

### **Moment 1: Discovery (Casual Exploration)** 🎓
*Shows: Multi-turn conversation, data collection, natural interaction*

### **Moment 2: Decision (Family Discussion)** 💰
*Shows: What-if scenarios, quick recalculation, practical value*

### **Moment 3: Validation (Real Aid Offer)** 🎉
*Shows: Comparing to actual results, decision support, emotional payoff*

---

## **MOMENT 1: Campus Tour Discovery** 🎓

**Context:** You're role-playing as your daughter. You're sitting in the car after a Northwestern campus tour with parents. Parents are in front seats talking. You're in back seat on your phone.

**Voice Setup:**
```
[Hold Galaxy Fold 7, tap Claude app]
[Tap voice button, hold phone naturally]
```

**DEMO SCRIPT:**

**YOU (speaking naturally, providing rich context upfront):**
> "Hey Runner Agent, I just finished touring Northwestern and I need to figure out if we can afford it. Can you calculate my federal student aid? I'm 17, born May 15th, 2007, single, from Illinois, and I'll be a freshman in fall 2026. My parents are married, also in Illinois, and our family is five people - me, my parents, and my little brother and sister. My parents' income last year was $120K, and we have about $30K in savings. I didn't have any income. Northwestern costs like $85K a year."

**CLAUDE (processing rich context):**
```
[Internal: Claude extracts structured data from natural language]
✓ Birth: May 15, 2007 → birth_month="05", birth_day="15", birth_year="2007"
✓ Marital status: "single" → marital_status="unmarried"
✓ State: Illinois
✓ Grade level: Freshman
✓ Parents married: Yes
✓ Parent state: Illinois
✓ Family size: 4
✓ Income: $120,000 → parent_income="120000"
✓ Assets: $30,000 → parent_assets="30000"
✓ Student income: "didn't have any income" → student_filed_taxes="no"

MISSING (required by schema):
❌ has_dependents (not mentioned - teens don't think about "dependents")
❌ personal_circumstances_none (conditional, needs clarifying)
❌ parent_child_support (conditional on parent_filed_taxes=yes, needs value)

[Claude calls: federalrunner_get_wizard_info("fsa-estimator")]
[Analyzes schema.required[] and identifies missing fields]
```

**CLAUDE (asking 2-3 realistic clarifying questions grouped together):**
> "Perfect! I have almost everything I need. Just a couple quick questions:
>
> 1. Do you have any children or dependents you support?
> 2. Do any of these apply to you: active duty military, orphan/ward of court, in foster care, emancipated minor, or homeless? Or none of these?
> 3. Does your family receive any child support payments?"

**YOU (naturally responding):**
> "No, no, and no - none of that applies to me."

**CLAUDE:**
> "Got it! Let me run the official Federal Student Aid Estimator for you..."

```
[Internal: Claude builds complete user_data]
{
  "birth_month": "05",
  "birth_day": "15",
  "birth_year": "2007",
  "marital_status": "unmarried",
  "state": "Illinois",
  "grade_level": "freshman",
  "has_dependents": "no",
  "personal_circumstances_none": true,
  "parents_married": "yes",
  "parent_marital_status": "married",
  "parent_state": "Illinois",
  "family_size": 4,
  "parent_filed_taxes": "yes",
  "parent_income": "120000",
  "parent_assets": "30000",
  "parent_child_support": "0",
  "student_filed_taxes": "no"
}

[Calls: federalrunner_execute_wizard("fsa-estimator", user_data)]
[Execution: 8-12 seconds - Playwright runs through all 7 pages atomically]
[Returns: SAI + Screenshots]
```

**CLAUDE (15 seconds later):**
> "Your official Student Aid Index is **$24,789**.
>
> At Northwestern with $85,000 total cost, your expected family contribution is $24,789, leaving about $60,211 to cover through aid, grants, and loans. You are eligible for federal student aid.
>
> Would you like me to compare this with other schools?"

**YOU (impressed):**
> "Wow, that was fast! Yeah, can you do University of Illinois? That's like $32,000 a year."

**CLAUDE:**
> "Since your SAI stays the same, at U of I's $32,000 cost, you'd need about $7,211 after your expected family contribution of $24,789. Much more affordable - and you're still eligible for federal aid!"

---

### **Why This Moment Works:**

✅ **Fast-paced** - One rich query, one grouped clarification, done! (~1 minute)
✅ **Shows natural language processing** - Claude extracts 10+ data points from conversational speech
✅ **Shows intelligence** - Claude knows what's missing, asks only that
✅ **Shows actual FSA execution** - Real federalrunner_execute_wizard() in 8-12 seconds
✅ **Shows immediate comparison** - Instant recalculation for second school
✅ **Emotional beat** - Relief when seeing U of I is more affordable
✅ **Demo-friendly** - Keeps audience engaged, no tedious Q&A
✅ **Realistic teen language** - Full birth date provided naturally, awkward questions (child support) asked by Claude

**Timing:** ~1 minute total (down from 3-4 minutes!)

---

## **MOMENT 2: The "What-If" Scenario** 💰

**Context:** Later that evening, at dinner table. Mom mentions potentially taking a new job.

**Voice Setup:**
```
[At dinner table, pick up phone casually]
[Tap Claude, tap voice]
```

**DEMO SCRIPT:**

**YOU (providing context upfront):**
> "Hey Claude, quick question about my financial aid. My mom might get a new job making more money. Can you recalculate my Student Aid Index if our family income goes from $120,000 to $145,000? Everything else stays the same - same family size, same savings, same state."

**CLAUDE (ZERO clarifying questions needed - has context from before):**
> "Let me recalculate with the higher income..."

```
[Internal: Claude calls federalrunner_execute_wizard() with updated income]
[Fast execution: 8 seconds]
```

**CLAUDE (8 seconds later):**
> "With income at $145,000 instead of $120,000, your Student Aid Index would be **$31,089** - that's about $6,300 higher.
>
> Here's what that means: The extra $25,000 in income would reduce your aid eligibility by roughly $6,300 per year. Net benefit to your family: about $18,700 per year.
>
> Bottom line: Your mom should take the job - you'll still come out ahead even with less aid."

**YOU (to parents, phone down):**
> "See Mom? Claude says you should take it!"

---

### **Why This Moment Works:**

✅ **Ultra-fast** - 30 seconds total, zero back-and-forth
✅ **Shows memory** - Claude remembers previous data
✅ **Shows rapid recalculation** - 8 seconds for new result
✅ **Shows analysis** - Claude does the math comparison automatically
✅ **Shows practical value** - Actionable family decision
✅ **Natural setting** - Real dinner table moment

**Timing:** ~30 seconds (down from 1-2 minutes!)

---

## **MOMENT 3: Validating the Aid Offer** 🎉

**Context:** Two months later. You just got your acceptance letter from DePaul University with financial aid package. You're excited but confused.

**Voice Setup:**
```
[Sitting on bed, holding acceptance letter]
[Pick up phone, excited energy]
```

**DEMO SCRIPT:**

**YOU (excited, providing full context):**
> "Claude! I just got my acceptance letter from DePaul and I need you to check if their financial aid offer is fair! They're offering me $18,000 in grants plus $5,500 in federal loans, and the total cost is $58,000 per year. Is that reasonable based on my family's finances? We make $120,000, family of four, $30,000 in savings."

**CLAUDE (ONE clarifying question):**
> "Congratulations! Just to confirm - is this still the same student aid situation we calculated before, or has anything changed with your family's income or size?"

**YOU:**
> "Yeah, same everything!"

**CLAUDE:**
> "Perfect, let me verify your aid eligibility..."

```
[Internal: Claude calls federalrunner_execute_wizard() to confirm current SAI]
[Execution: 8 seconds]
```

**CLAUDE (10 seconds later):**
> "Your aid package is **fair and reasonable**. Here's the breakdown:
>
> - Your Student Aid Index: **$24,789**
> - DePaul's total cost: **$58,000**
> - Their aid offered: **$23,500** ($18k grants + $5.5k loans)
> - What you'd actually pay: **$34,500** per year
>
> This aligns with your expected family contribution. The $5,500 in federal loans will need to be repaid, so over 4 years that's $22,000 in debt.
>
> If you have other offers with more grant money and less loans, those might be worth comparing. You could also try negotiating with DePaul if you have competing offers."

**YOU:**
> "Okay, so I'm not getting ripped off? This is normal?"

**CLAUDE:**
> "Exactly. This is a standard aid package for your family's financial situation. You're not getting ripped off - this is what the government says you can afford."

---

### **Why This Moment Works:**

✅ **Shows memory/context** - Claude references previous calculations
✅ **Shows validation use case** - Checking aid offers (huge real value)
✅ **Shows advisory role** - Strategic advice about negotiation
✅ **Emotional support** - Reduces anxiety about finances
✅ **Authentic voice** - "Am I getting ripped off?" is how teens talk
✅ **Fast-paced** - One question, quick confirmation, done

**Timing:** ~45 seconds (down from 2 minutes!)

---

## **BONUS MOMENT: The Voice Correction** 🎤
*(Include this to show natural voice interaction)*

**Context:** During initial data collection

**YOU:**
> "Our family income is, um... wait, I said that wrong. It's 120,000, not 112,000. One hundred twenty thousand."

**CLAUDE:**
> "No problem, I've updated that to $120,000. Let me continue..."

**Why This Works:** Shows that voice interactions can be corrected naturally, just like human conversation.

---

## **COMPLETE DEMO SCRIPT: Fast & Compelling Flow**

### **SETUP (20 seconds)**
*Explain what you're about to show*

> "Let me show you how a high school senior would use FederalRunner on her phone to figure out college financial aid. I'll role-play as my daughter. Watch how she provides context naturally and Claude just *gets it* without tedious back-and-forth..."

### **MOMENT 1 (1 minute) - Discovery**
*Execute full scenario: Campus tour, initial calculation*
```
Rich context upfront (10+ data points)
→ One grouped clarification (3 questions teens wouldn't naturally mention)
→ 8-second execution
→ Results + quick comparison
```
**Impact:** Shows natural language understanding + speed

### **MOMENT 2 (30 seconds) - What-If**
*Execute scenario: Mom's job offer impact*
```
Rich context upfront with what-if scenario
→ Zero clarifying questions (Claude has memory)
→ 8-second recalculation
→ Comparison analysis
```
**Impact:** Shows memory + instant analysis

### **MOMENT 3 (45 seconds) - Validation**
*Execute scenario: Validating aid offer*
```
Rich context with aid package details
→ One confirmation question
→ 8-second validation
→ Advisory feedback
```
**Impact:** Shows real-world value + advisory intelligence

### **CLOSE (20 seconds)**
*Bring it home*

> "That's it. Three scenarios in under 3 minutes total. No forms, no laptop, no tedious Q&A. Just rich context, smart understanding, and instant official government results. On her phone. With her voice. While doing other things.
>
> This is how government services should work in the AI age."

**TOTAL TIME: 3 minutes 15 seconds** (down from 7-8 minutes!)

---

## **KEY DEMO PRINCIPLE: Rich Context Upfront**

### **Instead of:**
```
❌ Claude: "What's your income?"
❌ You: "$120,000"
❌ Claude: "How many in family?"
❌ You: "Four"
❌ Claude: "Any savings?"
❌ You: "$30,000"
[12 tedious exchanges...]
```

### **Do this:**
```
✅ You: "I'm 17, born May 15th, 2007, single, from Illinois, starting
        college as a freshman in 2026. My parents are married,
        we're four people, family income $120k, $30k in savings,
        I didn't have any income. Northwestern costs $85k."

✅ Claude: "Perfect! Just a couple quick questions:
           1. Do you have any children or dependents?
           2. Any of these apply: military, orphan, foster care, etc?
           3. Does your family receive child support?"

✅ You: "No, no, and no."

✅ Claude: [8 seconds] "Your SAI is $24,789. At Northwestern..."
```

**Difference:** 1 minute vs. 4 minutes. Audience stays engaged!

---

## **REALISTIC DATA EXTRACTION PATTERNS**

### **What 17-Year-Olds Naturally Say:**
✅ Full birth date: "May 15th, 2007"
✅ Marital status: "single" / "I'm not married"
✅ Location: "Illinois" / "from Chicago"
✅ College plans: "freshman in fall 2026"
✅ Family composition: "me, my parents, and my little brother" → 4 people
✅ Parent finances: "$120,000 income, $30,000 in savings"
✅ Student work: "I didn't have any income" / "I didn't work"

### **What They DON'T Naturally Say (Claude Must Ask):**
❌ "I have no dependents" - Teens don't think in these terms
❌ "None of the special circumstances apply" - Too formal/technical
❌ "We don't receive child support" - Awkward topic, requires prompting

### **Realistic Clarifying Questions (Grouped):**
```
Instead of 3 separate back-and-forths, ask together:

"Perfect! Just a couple quick questions:
1. Do you have any children or dependents you support?
2. Do any of these apply: active duty military, orphan/ward of court,
   in foster care, emancipated minor, or homeless? Or none of these?
3. Does your family receive any child support payments?"

Expected answer: "No, no, and no" / "None of that applies"
```

This feels natural and saves time!

---

## **TECHNICAL NOTES FOR SMOOTH DEMO**

### **Before Demo:**
1. ✅ Deploy FederalRunner to Google Cloud Run with production env vars
2. ✅ Test OAuth flow works from Claude.ai mobile app
3. ✅ Verify `fsa-estimator.json` + schema in wizards/ directory
4. ✅ Test voice recognition on Galaxy Fold 7 in demo environment
5. ✅ Have backup: type instead of voice if WiFi/recognition issues
6. ✅ Run local test: `pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_non_headless -v`

### **During Demo:**
1. **Speak clearly** but naturally (not robotic)
2. **Hold phone 6-8 inches** from mouth (Fold 7 has good mics)
3. **Pause between questions** - Let Claude process
4. **Don't worry about "um" and "like"** - Makes it more authentic
5. **If Claude misunderstands** - Correct naturally (shows resilience)
6. **Show the screen** when Claude responds (visual confirmation)

### **Props to Have Ready:**
- 📱 Galaxy Fold 7 (obviously)
- 📄 Fake DePaul acceptance letter (for Moment 3)
- 💺 Chair near WiFi (for stable connection)

### **Fallback Plan:**
If voice fails:
- Switch to typing: "Let me type this since the WiFi is acting up..."
- Shows product still works without voice
- Actually makes it more impressive when voice works

---

## **EXPECTED FSA CALCULATION RESULTS**

### **Scenario 1: $120K Income, $30K Assets, Family of 4**
- **SAI:** ~$24,789
- **Northwestern ($85K/yr):** $60,211 need-based aid gap
- **U of Illinois ($32K/yr):** $7,211 need-based aid gap

### **Scenario 2: $145K Income (Mom's New Job)**
- **SAI:** ~$31,089 (increase of ~$6,300)
- **Net benefit:** $18,700/year ($25K raise - $6.3K aid reduction)

### **Scenario 3: DePaul Validation ($120K Income)**
- **SAI:** $24,789
- **DePaul Cost:** $58,000
- **Aid Offered:** $23,500 ($18K grants + $5.5K loans)
- **Family Pays:** $34,500/year
- **Verdict:** Fair and reasonable ✓

---

## **TALKING POINTS FOR AFTER DEMO**

**"Here's what you just saw happening behind the scenes..."**

1. **FederalScout discovered the FSA wizard structure** (7 pages, 17 required fields)
   - Saved as JSON file with all selectors and interaction patterns
   - One-time discovery, infinite reuse

2. **FederalRunner loaded that structure** from the JSON file
   - Read the User Data Schema (THE CONTRACT)
   - Knew exactly what data to collect and how to validate it
   - Knew exactly how to navigate each page

3. **Playwright executed the wizard atomically**
   - Filled all 7 pages in one atomic operation
   - Took 8-12 seconds total (vs 10-15 minutes manually)
   - Returned official government results with screenshot audit trail

4. **All of this ran on Google Cloud Run**
   - Accessible from anywhere (web, mobile, voice)
   - OAuth 2.1 authenticated for security
   - WebKit browser in headless mode for reliability
   - Scales to millions of users

5. **The pattern works for ANY government calculator**
   - Social Security benefits
   - Medicare costs
   - Tax withholding estimates
   - Loan repayment simulators
   - Literally any multi-page government form

**"This isn't just about student aid. It's about making government accessible through conversation."**

---

## **VOICE COMMAND REFERENCE SHEET**

### **How to Activate Voice on Galaxy Fold 7:**
1. Open Claude app
2. Tap microphone icon in input field
3. Phone shows "Listening..."
4. Speak naturally
5. Phone auto-submits after pause, OR tap checkmark to submit

### **Voice Tips for Demo Success:**
- ✅ "Hey Claude" works as wake phrase
- ✅ Speak at normal conversation volume
- ✅ Brief pauses between sentences are good
- ✅ You can interrupt Claude by tapping mic again
- ❌ Don't shout (mics are sensitive)
- ❌ Don't speak too slowly (sounds unnatural)
- ❌ Don't over-articulate (not a robot)

### **If Voice Fails:**
> "Let me try that again..." [Re-tap mic]
> OR
> "Let me just type that..." [Switch to keyboard]

Both show product resilience!

---

## **THE MONEY QUOTE FOR YOUR DEMO**

End with this:

> "Think about what just happened. A 17-year-old girl, lying in bed at 11 PM, worried about college costs, picks up her phone and has a natural conversation that gives her official government financial aid calculations in under a minute. No forms. No confusion. No anxiety. Just answers.
>
> That's the promise of AI + government services. And we just made it real."

🎤 *Drop mic* 🎤

---

## **DEPLOYMENT VERIFICATION CHECKLIST**

Before recording the demo, verify:

- [ ] **Cloud Run Deployment**
  - [ ] Service URL: `https://federalrunner-mcp-[PROJECT_NUMBER].us-central1.run.app`
  - [ ] Health check passes: `curl https://[URL]/health`
  - [ ] OAuth metadata: `curl https://[URL]/.well-known/oauth-protected-resource`

- [ ] **Environment Variables (Production)**
  - [ ] `FEDERALRUNNER_BROWSER_TYPE=webkit`
  - [ ] `FEDERALRUNNER_HEADLESS=true`
  - [ ] `FEDERALRUNNER_SAVE_SCREENSHOTS=false`
  - [ ] `FEDERALRUNNER_EXECUTION_TIMEOUT=60`
  - [ ] `FEDERALRUNNER_WIZARDS_DIR=/app/wizards`

- [ ] **Auth0 Configuration**
  - [ ] API Identifier matches service URL
  - [ ] Dynamic Client Registration enabled
  - [ ] Permissions configured

- [ ] **Claude.ai Connector**
  - [ ] MCP connector added in Settings → Connectors
  - [ ] OAuth flow tested on web
  - [ ] Sync to mobile verified (wait 2 minutes)

- [ ] **Wizard Files**
  - [ ] `fsa-estimator.json` in `wizards/wizard-structures/`
  - [ ] `fsa-estimator-schema.json` in `wizards/data-schemas/`
  - [ ] Both files validated and tested locally

- [ ] **Test Execution**
  - [ ] Local test passed: `pytest tests/test_execution_local.py -v`
  - [ ] Cloud Run logs show successful executions
  - [ ] Screenshots captured correctly
  - [ ] SAI results accurate

**All green? You're ready to demo! 🚀**
