# Multi-Agent Federal Form Automation System
## Phase 1: Discovery - Video Script (Refined)

**Estimated Runtime:** 6-7 minutes raw → 4-5 minutes edited

---

## 1. Opening Intro (45 seconds)

*[Scene: Split screen - George on left, right side shows college-related artifacts]*

Over the last six months, I've been spending a lot of time with my 17-year-old college-bound daughter navigating the world of college planning.

Campus tours, college fairs, financial aid workshops—and most importantly, understanding the FAFSA process.

*[Right panel transitions to show FSA forms]*

A few weeks back, my daughter and I spent an entire Saturday filling out federal student aid forms—the infamous FAFSA, the Federal Student Aid Estimator, the Loan Simulator.

As we clicked through page after page of dropdowns and radio buttons, nested forms, my daughter looks up and says:

"All these forms are so annoying. Why can't I just describe my situation in a few sentences and get the number I need? And use my phone to do this like I do everything else?"

*[Show article excerpt]*

That question got me thinking about something I wrote—about the future of agent interfaces being conversational and voice-first.

Here was a real user—my 17-year-old daughter—who has grown up with ChatGPT and Claude, frustrated by traditional forms.

Challenge accepted.

This led me to build a system that demonstrates something broader—a pattern for automating ANY complex government form through natural conversation, combined with the infrastructure to deploy it remotely.

Let me show you how it works.

---

## 2. Architecture Overview (60 seconds)

*[Transition: Architecture diagram appears - title and subtitle only]*

Here's the complete technical stack—a two-phase multi-agent system.

*[Pause on title/subtitle]*

The first phase is Discovery—mapping government forms into machine-readable structures.

The second phase is Execution—automating those forms through natural conversation and voice.

Let's drill into the first phase.

*[Phase 1 section builds - Discovery Request and FederalScout Agent appear]*

**Phase 1: Discovery Flow**

It starts with a discovery request—give the agent a government form URL to map.

The FederalScout Agent running in Claude Desktop receives this request and starts the mapping process.

*[Arrow highlights, FederalScout MCP box appears]*

The agent calls the FederalScout MCP Server deployed locally on my machine.

This is where the magic happens—the MCP provides browser automation tools using Playwright.

Think of it this way: Playwright becomes the hands that interact with the form, Claude Vision becomes the eyes and brain that understand what it's seeing.

*[Arrow highlights, Government Website box appears]*

Those tools navigate to the actual government website and map the complete form structure.

*[Discovery Outputs section appears with both artifacts]*

The discovery process produces two critical artifacts:

The Wizard Structure—a complete automation blueprint telling Playwright exactly how to navigate and fill the form.

And the Input Schema—THE CONTRACT defining what data we need from users.

This is Contract-First Form Automation. The schema becomes the source of truth that both agents rely on.

*[Phase 2 section builds - Voice Query and FederalRunner Agent appear]*

**Phase 2: Execution Flow**

Now the second phase—execution.

The FederalRunner Agent runs on Claude.ai and Claude Mobile—enabling both web and voice queries.

*[Arrow highlights, FederalRunner MCP box appears]*

The agent calls the FederalRunner MCP Server—but this one's deployed remotely on Google Cloud Run.

This remote deployment is what enables access from anywhere—phone, web, mobile app.

The MCP validates the user's data against our discovered schema, then uses Playwright to execute the form atomically—8 seconds start to finish.

*[Arrow highlights, Government Website box appears]*

It navigates to the same government website and fills the form using our discovered wizard structure.

*[Arrow highlights, Auth0 box appears]*

All of this is secured through Auth0—OAuth 2.1 authentication with Dynamic Client Registration.

The auth flow ensures only authorized users can access the remote MCP endpoints.

*[Pause, full diagram visible]*

Here's what makes this architecture design pattern powerful:

Vision-guided discovery eliminates custom integration code—making any federal form automatable without writing form-specific logic.

Contract-first execution enables the same discovered structure to work across web, mobile, and voice interfaces.

Remote MCP infrastructure with OAuth 2.1 enables secure access from anywhere.

That's the architecture. Now let's see Phase 1 in action—the discovery process.

---

## 3. Phase 1: FederalScout Discovery Agent (30 seconds)

*[Transition: Claude Desktop with FederalScout agent on left, empty browser on right]*

This is the FederalScout Discovery Agent already created in Claude Desktop.

Let me quickly introduce what powers it.

*[Click agent settings]*

The agent's core mission: Transform government form wizards into machine-readable structures.

*[Expand tools briefly]*

The FederalScout MCP Server provides specialized tools—starting discovery, analyzing pages with vision, navigating wizards, capturing structures.

*[Close tools, return to chat]*

Let me ask what it can do.

*[Type "What can you do?" and agent responds]*

*[Scroll through response highlighting key sections]*

Look at this—the agent explains it generates two critical artifacts for each government form.

The Wizard Structure for Playwright execution, and the User Data Schema—the contract defining required inputs.

*[Scroll to bottom of response]*

And here's our invitation: "Ready to discover a government form? Just share the URL."

Perfect. Let's give it one.

---

## 4. Discovering the FSA Student Aid Estimator (90 seconds)

### Initial Query (10 seconds)

*[Type the query into chat]*

I provide the FSA Student Aid Estimator URL and the context—my daughter's a high school senior looking at colleges.

*[Agent starts processing]*

Watch what happens—the agent immediately connects to the browser.

*[Browser opens on right, navigates to FSA site]*

### Landing Page Recognition (15 seconds)

There's the Federal Student Aid Estimator landing page.

The agent analyzes it with vision and identifies this as a multi-page wizard.

*[Highlight "Start Estimate" button as agent clicks it]*

Perfect—clicking into the wizard now.

*[First wizard page appears]*

And we're in. Page 1: Student Information.

This is where the discovery magic begins.

### The Discovery Pattern (30 seconds)

*[Page 1 visible on right, agent working on left]*

Watch the systematic approach—the agent reviews the page screenshot and analyzes the page element data.

*[Highlight fields as they're analyzed - don't list them]*

For each field, it extracts the selector information, data type, validation rules.

*[Fields start filling with test data]*

Then it generates the test data and calls execute_actions to fill this data in the form via Playwright.

This is Playwright "being the hands."

*[Scroll to show all fields populated]*

All fields filled. Now it saves the complete page metadata—field types, selectors, data types—everything needed for automation.

*[Agent clicks Continue]*

And advances to Page 2.

This is the pattern: analyze, extract, fill, save, advance.

### The Seven-Page Journey (35 seconds)

Now watch this happen across all seven pages.

*[Quick cuts showing progression through remaining pages - no music, conversation/tool calls trimmed]*

Page 2: Student Personal Circumstances

*[Fields fill → Continue]*

Page 3: Parent Marital Status

*[Fields fill → Continue]*

Page 4: Parent Information

*[Fields fill → Continue]*

Page 5: Family Size

*[Fields fill → Continue]*

Page 6: Parent Income and Assets

*[Fields fill → Continue]*

Page 7: Student Income and Assets

*[Fields fill → Continue]*

*[Results page appears]*

### Discovery Complete (10 seconds)

And there's the results page.

The agent recognizes this—no more input fields, just calculated outputs.

*[Agent completes discovery]*

Discovery complete. Seven pages mapped, 47 fields documented.

*[Artifacts appear in chat]*

### The Artifacts (45 seconds)

*[Click to show artifacts panel]*

Two files created—let me show you what's inside.

*[Open User Data Schema artifact]*

First, the User Data Schema—this is THE CONTRACT.

*[Scroll quickly through schema]*

Look at this structure—every field the wizard needs defined with its exact data type, whether it's required, validation patterns.

When FederalRunner executes later, it knows exactly what to collect from the user.

*[Switch to Wizard Structure artifact]*  

Second, the Wizard Structure—the complete automation blueprint.

*[Scroll quickly through structure]*

See the page-by-page mapping? Field selectors, interaction types, navigation buttons.

This tells Playwright exactly how to fill and navigate the form.

*[Close artifacts]*

These two artifacts work together—the schema defines WHAT data we need, the structure defines HOW to automate it.

Contract-first pattern in action.

---

## 5. Discovering the Federal Loan Simulator (90 seconds)

### Second Discovery (10 seconds)

*[Type in chat]*

Let's discover one more federal form—the Loan Simulator. These two forms together create a realistic example for execution—first estimate your aid, then simulate borrowing to cover the gap.

*[Agent starts processing]*

This time, notice I didn't even provide a URL.

*[Browser navigates to studentaid.gov]*

### Smart Navigation (20 seconds)

The agent searches and finds the Federal Student Loan Simulator page.

*[Landing page with three different calculators visible]*

Look at this—there are three different simulators on this page.

Based on the context of my query—"simulate borrowing for school"—it picks the right one.

*[Highlight "I want to simulate borrowing MORE money" option]*

"Borrow More Money" simulator—exactly what we need for college planning.

*[Agent clicks and enters wizard]*

Smart reasoning about context.

### Faster Discovery (50 seconds)

*[Quick cuts through all six pages]*

Same discovery pattern, but let's move through this a bit faster.

Page 2: Program Details

*[Fields fill → Continue]*

Page 3: Family Income

*[Fields fill → Continue]*

Page 4: Loan Amount

*[Fields fill → Continue]*

Page 5: Salary projections post graduation

*[Fields fill → Continue]*

Page 6: Loan simulation—complex loan entry section where multiple loans can be added. The agent identifies this as a repeatable field group structure.

*[Fields fill → Continue]*

*[Results page appears]*

### Second Discovery Complete (10 seconds)

And finally, the results page.

*[Agent completes discovery]*

Discovery complete. Six pages mapped.

*[Highlight artifact generation in agent chat]*

Two more artifacts generated—both the Wizard Structure and User Data Schema ready for FederalRunner.

---

## 6. Phase 1 Complete - Transition (15 seconds)

*[Show both sets of artifacts side by side]*

In about 5 minutes, we've mapped two complex multi-page federal forms—13 total pages, nearly 70 fields.

No custom integration code. Just vision-guided discovery with a universal pattern.

These schemas and structures are now ready for Phase 2—where we execute them through voice conversation on mobile.

Let's see that next.

---

## Technical Notes for Editing

**Key Visual Principles:**
- Show, don't tell—let viewers see the automation happening
- Highlight specific UI elements with annotations when guiding attention
- Use time-lapse for repetitive actions (pages 2-7)
- Return to normal speed for key moments (results pages, artifact generation)

**Screen Layout:**
- Left: Claude Desktop agent conversation
- Right: Browser with form automation happening
- Use picture-in-picture for George during time-lapse sequences

**Music Notes:**
- Discovery time-lapse: Upbeat, technical, rhythmic
- Architecture build-out: Cinematic, building
- Normal sections: Light background or none

**Pacing:**
- Page 1 discovery: Show in detail (45 seconds)
- Pages 2-7: Fast time-lapse (60 seconds) 
- Artifact reveal: Medium pace (45 seconds)
- Second discovery: Faster overall (2:30)

**Visual Callouts (text overlays):**
- "Playwright = Hands, Claude Vision = Eyes & Brain"
- "Contract-First Pattern"
- "Universal Automation Pattern"
- "47 Fields Across 7 Pages"
- "No Custom Code Required"

**Transitions:**
- Architecture → Demo: Animated wipe
- First discovery → Second discovery: Quick fade
- Phase 1 → Phase 2: Emphasize with title card

**Total Phase 1 Runtime:** 6-7 minutes raw → 4-5 minutes edited