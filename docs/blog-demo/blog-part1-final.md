# From Pixels to Schemas: How Claude Vision Turns Any Government Form Into a Voice-Accessible Service

## Part 1: The Vision-Guided Discovery + Contract-First Execution Design Pattern

A few Saturdays ago, my 17-year-old daughter and I spent an entire afternoon filling out federal student aid forms. The [FSA Estimator](https://studentaid.gov/aid-estimator/). The [Loan Simulator](https://studentaid.gov/loan-simulator/). The infamous [FAFSA](https://studentaid.gov/h/apply-for-aid/fafsa).

Seven pages into the Student Aid Estimator, navigating nested dropdowns and radio buttons that spawned new fields with every click, she looked up: "Dad, these forms are so annoying. Why can't I just describe my situation in a few sentences and get the number I need? And use my phone to do this—like I do everything else?"

That question led me to build a [multi-agent federal form automation system](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system). But more importantly, it led to something broader—formalizing a pattern I've used successfully across [complex FHIR Apple Health PDFs](https://medium.com/@george.vetticaden/from-data-graveyard-to-living-intelligence-building-multi-agent-health-systems-with-claudes-d4eb74f60c35), invoices, and now federal forms. A pattern I'm calling **Vision-Guided Discovery + Contract-First Execution**, for automating any complex application that lacks APIs.

This two-part series covers the complete journey. **Part 1** (this post) focuses on the design pattern—how Claude Vision and Playwright work together to map any government form into automation blueprints and data contracts. **Part 2** covers what it actually takes to deploy these custom agents for real-world use: OAuth 2.1 authentication, MCP Spec 2025-06-18, Dynamic Client Registration, and Google Cloud Run deployment.

The demo below shows the result: me playing my daughter's persona using a Samsung Galaxy Z Fold to query federal student aid eligibility through natural conversation. No web forms. No clicking. Just voice to official government results in under two minutes.

*[Voice-First Federal Form Automation: Using Samsung Galaxy Z Fold to query federal student aid eligibility for Northwestern and University of Chicago through natural conversation with Claude Mobile]*

[Embedded demo video - 4:16 minutes]

---

## When Conversational AI Meets Traditional Forms: A New Interface Expectation

My daughter's frustration reflects a broader shift in user expectations. **A generation raised on ChatGPT, Claude.ai, and Gemini is asking: why can't traditional services work like this?**

They're not asking for better forms. They're questioning why forms exist at all.

We've seen this pattern before. When the iPhone launched in 2007, people who experienced the touch interface started asking why every phone couldn't work that way. Conversational AI is triggering the same expectation reset—except now it's not just phones, it's every service that requires filling out forms.

The federal student aid system captures this tension perfectly:
- **FSA Student Aid Estimator** → 7 pages, 47 fields, 15-20 minutes of clicking
- **Federal Loan Simulator** → 6 pages, repetitive data entry across multiple screens  
- **FAFSA** → Multi-hour ordeal with dedicated support infrastructure

But federal forms are just one example. Think about legacy systems across every industry that lack modern APIs:
- **Insurance portals** where claims processors click through dozens of forms
- **EHR systems** with no programmatic access to patient data
- **Legacy enterprise tools** built before APIs existed
- **Government systems** with Byzantine web interfaces

This isn't about making forms easier. It's about making complex services conversationally accessible—from anywhere, on any device.

---

## The Pattern: Two Phases, Two Agents, Two Automation Contracts

The solution required two specialized agents working in concert:

**Phase 1: Discovery** — How do you map complex multi-page forms without writing custom integration code for each one?

**Phase 2: Execution** — How do you make those automations work universally across any form and accessible from anywhere—web, mobile, voice—through natural conversation?

*[Multi-Agent Federal Form Automation Architecture: Two specialized agents working in concert—FederalScout discovering form structures locally using Claude Vision and Playwright, FederalRunner executing them remotely via OAuth-secured MCP server accessible from Claude.ai web and Claude Mobile voice]*

![System Architecture](architecture-diagram.png)

FederalScout runs locally in Claude Desktop, using Claude Vision to map forms. FederalRunner runs on Claude.ai and Claude Mobile, executing forms from natural conversation. **Between them sit two automation contracts**—the Wizard Structure (automation blueprint) and User Data Schema (the data contract)—that bridge visual discovery and conversational execution.

Let's break down each phase.

---

## Phase 1: Introducing FederalScout — Vision-Guided Discovery

The discovery phase solves a fundamental problem: how do you automate forms that were designed for human eyes, not programmatic access?

Traditional approaches require:
- Inspecting HTML source code
- Writing custom selectors for each form
- Maintaining brittle code when forms change
- Repeating this process for every new form

**[FederalScout](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/agents/federalscout-instructions.md) uses a hybrid approach instead.** It combines Claude Vision (understanding page structure like humans do) with structured HTML analysis (extracting precise selectors and element data). This dual-mode discovery makes automation both intelligent and reliable.

*FederalScout Introduction: Specialized discovery agent explaining its capabilities—visual form mapping, dual-mode analysis, and two-contract output following the Contract-First pattern*

---

### Visual-First Automation: How It Works

The discovery process combines three capabilities working in concert:

**1. Playwright's browser automation** → Navigate forms, trigger interactions, capture screenshots

**2. Claude Vision + HTML analysis** → Dual-mode understanding:
   - **Visual layer**: Screenshots show the rendered page as humans see it—conditional fields, validation messages, layout
   - **Structural layer**: HTML data provides precise element IDs, types, attributes, and selectors

**3. Self-correcting loops** → After each interaction, the agent captures a new screenshot and HTML state, compares it with the previous state to detect changes (new fields appearing, validation errors), generates appropriate test data to progress through conditional branches, and documents discovered patterns in both automation contracts.

Here's the sequence FederalScout follows when mapping a new form:

```
1. Navigate to form URL (Playwright)
2. Capture full-page screenshot + extract HTML elements (Playwright)
3. Dual-mode analysis (Claude):
   → Vision: Understand page layout, field relationships, visual cues
   → Structure: Extract precise selectors, element IDs, types from HTML data
4. Generate realistic test data for each field type
5. Execute actions: Fill fields with test data to trigger conditional logic
6. Capture new screenshot + extract updated HTML elements
7. Dual-mode comparison (Claude):
   → Vision: Detect what changed visually (new fields, error messages)
   → Structure: Identify exact new elements that appeared in HTML
8. Click "Continue" to advance to next page
9. Repeat steps 2-7 until reaching final results page
10. Generate two automation contracts:
    → Wizard Structure (automation blueprint)
    → User Data Schema (data contract)
```

**Why the dual-mode approach works:**

- **Vision handles ambiguity** → When fields appear dynamically or layouts shift, Claude Vision sees the changes as humans would
- **Structure provides precision** → HTML data gives exact CSS selectors that never fail
- **Together they adapt** → Forms change their UI frequently, but the combination of visual understanding + structural extraction remains reliable

> **💡 MCP ImageContent optimization:** Discovery agents take 20-40 screenshots during multi-page wizard mapping. Each screenshot consumes context window space. By returning MCP's ImageContent structure instead of base64 text strings, we reduced screenshot size from 115KB to 50KB per image—a 57% reduction enabling discovery of 15+ page wizards within Claude Desktop's limits.

> **💡 Claude Desktop economics:** With 20-40 screenshots per discovery session, cost matters. Running FederalScout on Claude Desktop with a Claude Max subscription ($200/month fixed cost) versus the Claude API (pay-per-token, ~$15-30 per discovery session) makes the economics work for iterative development.

> **💡 Non-headless mode for visual validation:** Claude Desktop lets us run Playwright in non-headless mode—meaning you see the browser automation happening live. This visual validation was invaluable during development. You watch the agent reason about what it sees, click elements, detect conditional fields, and self-correct errors in real-time. The video below captures this split-screen experience—agent reasoning on the left, browser automation on the right. This visibility made debugging and refining the discovery patterns dramatically faster than working blind with headless automation.

*Discovery in Action: Split-screen view showing FederalScout agent performing dual-mode analysis (left) while Playwright browser automation navigates the FSA Student Aid Estimator in real-time (right)*

[Embedded YouTube video - 1:35 minutes]

---

### Discovery Output: Two Automation Contracts

FederalScout generates two automation contracts—JSON specifications that define everything FederalRunner needs to execute the form:

**1. Wizard Structure (Automation Blueprint)**

This contract specifies **HOW** to execute the form—every interaction Playwright must perform: page-by-page navigation, precise CSS selectors for each field, interaction types (fill, click, select), conditional logic for dynamic fields, and continue button locations.

This automation blueprint tells the execution engine exactly what to do at each step. Without this blueprint, execution engines would need hardcoded page logic for every government form. With it, one universal execution engine works for FSA Estimator, Loan Simulator, FAFSA, IRS forms—any multi-page wizard.

[View the complete FSA Estimator Wizard Structure →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/wizards/wizard-structures/fsa-estimator.json)

**2. User Data Schema (The Data Contract)**

This contract specifies **WHAT** data is needed—the inputs required from the user: required properties (birth_date, family_size, parent_income), validation rules (pattern for dates, minimum for income, enum for states), data types, field descriptions for conversational collection, and dependencies between fields.

[View the complete FSA Estimator User Data Schema →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/wizards/data-schemas/fsa-estimator-schema.json)

> **💡 Contract-first automation:** The execution agent doesn't need custom field mapping code—Claude reads the JSON Schema naturally and understands what data to collect, how to validate responses, and how fields relate. With the schema as single source of truth, you never write transformation logic. The execution agent collects data matching the schema during conversation, validates it, then maps directly to form fields using the Wizard Structure. No mapping bugs, no data loss.

> **💡 Version-controlled form definitions:** Both contracts are JSON files stored in Git. When government forms change, diff the Wizard Structures to see exactly what changed, re-discover only the affected pages, and track form evolution over time. No need to audit entire codebases—just compare two JSON files.

---

*Discovery Complete: Both automation contracts generated in Claude Desktop as artifacts—User Data Schema (JSON Schema defining required user data) and Wizard Structure (Playwright execution blueprint for 7 pages, 47 fields). Switch between artifacts to view complete contracts. Total discovery time: 5 minutes*

![Artifacts Generated](artifacts-complete.png)

---

## Phase 2: Introducing FederalRunner — Contract-Driven Execution

The execution phase solves a fundamental challenge: how do you build ONE execution agent that works for ANY form—government, enterprise, legacy—and make it accessible from anywhere: Claude.ai web, Claude Mobile voice, Samsung Galaxy Z Fold? Federal forms (FSA Estimator, Federal Loan Simulator, FAFSA) demonstrate the pattern because their multi-page wizards, conditional logic, and validation rules represent the full complexity spectrum.

Traditional automation approaches require:
- Custom mapping code for every form (birth_month → selector, income → selector)
- Separate integrations for web vs mobile vs voice
- Hardcoded transformations ("May" → "05", "$120k" → 120000)
- Redeploying code whenever forms change

**[FederalRunner](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/agents/federalrunner-instructions.md) uses the contract-first pattern instead.** It reads both automation contracts that FederalScout discovered—the User Data Schema (what data to collect) and Wizard Structure (how to execute)—understands requirements naturally, collects user input conversationally, and executes forms atomically. This contract-driven approach makes one execution engine work universally across any discovered form.

*FederalRunner Introduction: Specialized execution agent explaining its capabilities—contract-driven data collection, natural language transformations, atomic execution via remote MCP server, and voice-first mobile access*

---

### Contract-Driven Data Collection: Schema-Guided Transformations

When my daughter asks via voice: "Can you help me figure out if I can afford Northwestern?", FederalRunner doesn't execute hardcoded logic. Instead, it reads the FSA Estimator User Data Schema—the data contract FederalScout discovered—and understands three critical things:

**1. What data to collect** → Required fields (birth_date, dependency_status, parent_income), optional fields, conditional dependencies (if dependent → parent fields required)

**2. How to validate inputs** → Data types (string, integer, enum), patterns (dates as "MM/DD/YYYY"), constraints (income ≥ 0), allowed values (marital_status: unmarried/married/separated)

**3. How to transform natural language** → User says "May 15th, 2007" → Schema shows birth_month needs pattern "^(0[1-9]|1[0-2])$" → Claude transforms to "05". User says "$120k income" → Schema expects integer → Claude transforms to 120000. User says "single" → Schema enum shows "unmarried" → Claude maps correctly.

> **💡 Schema as transformation guide:** Claude doesn't need hardcoded transformation rules. The JSON Schema's type, pattern, and enum fields tell Claude exactly how to convert natural language into form-ready data. "May" → "05" happens because the schema shows `pattern: "^(0[1-9]|1[0-2])$"`. "$120k" → 120000 happens because the schema shows `type: "integer"`. One universal agent, unlimited forms—no custom mapping code.

The agent collects data conversationally across multiple turns, validates each input against schema rules in real-time, identifies missing required fields before execution, and asks clarifying questions when inputs don't match expected patterns.

---

### Atomic Execution: From Conversation to Official Results

Once all data validates against the User Data Schema, FederalRunner reads the second contract—the Wizard Structure automation blueprint—and executes the form atomically. This blueprint tells the execution engine exactly how to navigate the form, which selectors to use, and how to handle conditional logic.

The execution flow follows this sequence:

**1. Map field_id → selector** → The Wizard Structure maps each schema field to its CSS selector: birth_month (schema field_id) → #fsa_Input_DateOfBirthMonth (selector)

**2. Launch browser via MCP** → Remote Playwright server on Google Cloud Run starts headless Chrome

**3. Execute atomically** → The Wizard Structure guides every step: Navigate to form URL → Fill all pages in sequence using mapped selectors → Handle conditional fields based on blueprint rules → Capture screenshots at each step → Extract results from final page → Close browser

**4. Return results** → Complete execution trace with screenshots, extracted data, execution time

> **💡 Atomic execution enables serverless deployment:** Every execution is independent—launch browser, fill form, extract results, close browser. No persistent sessions. No state between runs. This atomic pattern enables 100% reproducibility (same input = same output always), Cloud Run compatibility (stateless containers scale perfectly), complete audit trails (every screenshot saved), and parallel execution (thousands of simultaneous submissions).

Thirty seconds after the voice query: official government results delivered conversationally.

*"Your Student Aid Index (SAI) is $8,200. Northwestern's estimated cost is $89,000/year. Expected federal aid eligibility: $18,700/year (Pell Grant + subsidized loans). Remaining gap: $62,100/year."*

No web form filled. No laptop opened. Just voice to official result.

> **💡 Universal execution architecture:** The FederalRunner MCP server running on Google Cloud Run executes any government form discovered by FederalScout. One deployment, unlimited forms. Add a new form? Drop two JSON files (Wizard Structure + User Data Schema) into the repo, and it's immediately voice-accessible from mobile. No code changes. No redeployment.

---

## Making It Real: From Proof-of-Concept to Production

The Vision-Guided Discovery + Contract-First Execution pattern works across government and enterprise forms—tax filing, benefits enrollment, insurance claims, HR onboarding. The technology exists. The pattern proves itself. 

FederalScout runs successfully on Claude Desktop with locally running MCP tools (stdio protocol, private to your machine). But FederalRunner's true value comes from universal accessibility—Claude.ai web, Claude Mobile voice, any device, anywhere. This requires deploying custom MCP server tools publicly, adhering to specific specifications that enable successful integration with Claude.ai. That reveals infrastructure challenges rarely documented together: OAuth 2.1 with Dynamic Client Registration, MCP Specification 2025-06-18 (HTTP vs stdio), Google Cloud Run deployment for serverless scaling, and why getting any part wrong means silent failures with zero error messages.

**Part 2** (coming soon) covers this production infrastructure gap—what actually happens when you click "Add custom connector" in Claude.ai, the four-step OAuth handshake, and why most MCP tutorials stop at local stdio servers.

---

**George Vetticaden** builds multi-agent AI systems and writes about practical patterns in enterprise AI. Previously served as VP of Agents at a leading AI startup, where he led development of agent building tools and document intelligence solutions.

**Watch the complete system in action:** [Vision-Guided Discovery + Contract-First Execution Demo](https://www.youtube.com/watch?v=IkKKLjBCnjY) | **Explore the codebase:** [GitHub Repository](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system)

**Connect:** [LinkedIn](https://linkedin.com/in/georgevetticaden) | [Medium](https://medium.com/@george.vetticaden)

**Related Reading:**
- [From Data Graveyard to Living Intelligence: Building Multi-Agent Health Systems with Claude's Extended Context](https://medium.com/@george.vetticaden/from-data-graveyard-to-living-intelligence-building-multi-agent-health-systems-with-claudes-d4eb74f60c35)
- [The 3 Amigo Agents: The Claude Code Development Pattern I Discovered While Implementing Anthropic's Multi-Agent Architecture](https://medium.com/@george.vetticaden/the-3-amigo-agents-the-claude-code-development-pattern-i-discovered-while-implementing-95d023df7882)
