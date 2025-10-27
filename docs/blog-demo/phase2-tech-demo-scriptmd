# Phase 2: Execution - Video Script
## Multi-Agent Federal Form Automation Demo

---

## Section 1: Creating the FederalRunner Agent (90 seconds)

### 1.1 The Platform Shift (15 seconds)

*[Transition from Claude Desktop to Claude.ai in browser]*

Discovery happens locally in Claude Desktop. But execution? That needs to work everywhere—web, mobile, voice.

That's why we're building the FederalRunner agent in Claude.ai.

*[Navigate to Claude.ai Projects page]*

### 1.2 Agent Setup (20 seconds)

*[Click "New project" button]*

Creating the FederalRunner Execution Agent.

*[Project creation modal appears with name and description fields filled]*

This agent transforms government forms into conversational, voice-accessible tools.

*[Click "Create project"]*

*[Project instructions panel opens]*

Here's what makes this agent special—detailed instructions about its identity and capabilities.

*[Scroll through instructions briefly - don't read them]*

Contract-First Form Automation. The agent never guesses—it only uses the schemas FederalScout discovered.

*[Click "Save instructions"]*

### 1.3 The Remote MCP Connection (55 seconds)

*[Click Tools → Add Connectors → Add custom connector]*

Now the critical piece—connecting to our remote MCP server.

*[Custom connector dialog appears]*

This is where Phase 2 gets interesting. The MCP server isn't local anymore—it's deployed on Google Cloud Run, protected by OAuth 2.1.

*[Switch to Google Cloud Console tab]*

Let me show you the infrastructure.

*[Navigate to Cloud Run services]*

There's our federalrunner-mcp endpoint—deployed, running, ready.

*[Click on the service name]*

*[Service details page loads showing metrics]*

The MCP server URL at the top.

*[Copy the URL]*

*[Switch back to Claude.ai tab]*

*[Paste URL into connector field]*

*[Click "Add"]*

*[Confirmation checkbox appears]*

Confirmed—this connector isn't verified by Anthropic, but we trust it.

*[Check the box, click "Add"]*

Perfect. Now the OAuth handshake begins.

---

## Section 2: OAuth 2.1 + MCP Authentication (90 seconds)

### 2.1 The Login Flow (30 seconds)

*[OAuth login page appears from Auth0]*

Watch this—Claude is discovering the OAuth endpoint through MCP's well-known URL.

*[Switch to Auth0 dashboard tab]*

Quick look at the authorization server.

*[Navigate to APIs → FederalRunner MCP Server]*

There's our API—protecting that Google Cloud Run endpoint we just saw.

*[Click on Settings tab]*

The identifier matches our Cloud Run URL exactly.

*[Click on Permissions tab]*

Two permissions: read wizards, execute wizards.

*[Navigate to Settings → Advanced Settings]*

And here's the magic—Dynamic Client Registration enabled.

This lets Claude.ai register itself as an OAuth client without pre-configuration.

### 2.2 Authentication (35 seconds)

*[Switch back to Auth0 Users section]*

*[Copy email address from user list]*

*[Switch back to OAuth login page]*

*[Fill in credentials and click "Continue"]*

*[Consent page appears]*

Claude is requesting access to our Auth0 account.

*[Click "Accept"]*

*[Loading, then returns to Claude.ai]*

Connection established.

### 2.3 The Complete Handshake (25 seconds)

*[Display OAuth 2.1 + MCP Handshake diagram - full page]*

Here's what just happened in four steps:

*[Diagram builds step by step as narrated]*

Step 1: Claude discovers the OAuth endpoint from the MCP server.

Step 2: Dynamic Client Registration—Claude registers itself with Auth0.

Step 3: User authentication and token issuance.

Step 4: Claude uses the token to fetch available tools from the MCP server.

*[Connection Established section highlights with three tools listed]*

Success—three tools now available to the agent.

---

## Section 3: Agent Introduction (30 seconds)

*[Return to FederalRunner agent chat page]*

*[Show agent instruction panel briefly]*

Let's see what this agent can do.

*[Type in chat: "What can you do?"]*

*[Agent response streams in]*

*[Highlight the two core capabilities section as it appears]*

Two core capabilities—intelligent form execution and contract-first automation.

*[Scroll to supported forms section]*

The forms it can execute—FSA Student Aid Estimator and Federal Loan Simulator.

*[Scroll to bottom of response]*

And the invitation—"Ready to get started?"

Perfect. Time to switch to voice.

---

## Section 4: Mobile Voice Interaction (3 minutes)

### 4.1 The Platform Transition (20 seconds)

*[Split screen: Narrator on left, Samsung Galaxy Z Fold 7 on right]*

Now for the real test—voice-first federal form automation.

I'm playing the persona of my 17-year-old daughter, a high school senior exploring colleges.

*[Show phone home screen]*

*[Open Claude app]*

*[Navigate to Projects → FederalRunner Execution Agent]*

*[Click "New chat"]*

### 4.2 First Query - Student Aid Estimation (60 seconds)

*[Click microphone icon]*

*[Speak clearly into phone]*

"Hey Runner Agent, can you help me figure out if I can afford Northwestern? I just toured it and it costs like $85K a year. We're from Illinois and I'll be a freshman in fall of 2026."

*[Agent begins processing - split view showing both phone and narrator]*

Watch this—the agent's listing available wizards.

*[federalrunner_list_wizards tool call visible]*

Perfect—identifies the FSA Student Aid Estimator.

*[federalrunner_get_wizard_info tool call]*

Now loading the schema—THE CONTRACT that FederalScout discovered.

*[Agent response streams with questions]*

Smart. The agent read the schema and knows exactly what data it needs.

Nine questions about me, my family, our finances.

### 4.3 Natural Conversation (45 seconds)

*[Click microphone icon again]*

"I was born May 15th, 2007. My parents are married, we're a family of five. Their income was $200K last year and we have about $100K in savings. No dependents, no child support."

*[Agent responds with follow-up questions]*

*[Click microphone]*

"Nope. Didn't work last year. And none of these special circumstances apply to me."

*[Agent confirms all information]*

"Looks good to me."

*[Agent begins execution]*

Perfect—all data validated against the schema. Now watch the atomic execution.

### 4.4 Form Automation (30 seconds)

*[federalrunner_execute_wizard tool call initiated]*

The agent's calling the MCP server with my validated data.

Behind the scenes—Playwright launches a headless browser, navigates to the FSA site, fills all seven pages sequentially, extracts the results.

Eight seconds. Start to finish.

*[Results screenshot appears in agent response]*

### 4.5 Results Analysis (25 seconds)

*[Agent displays formatted results]*

Perfect! Three critical numbers:

My estimated federal aid: $7,481 per year.

My Student Aid Index: 43,439.

The Northwestern gap: $77,500 per year I need to figure out.

Over four years, that's $310,000 beyond federal aid.

*[Agent suggests next steps]*

The agent's already thinking ahead—want to run the loan simulator?

### 4.6 Second Query - Loan Strategy (60 seconds)

*[Click microphone]*

"Yes. Let's run the simulator. My parents said they'll cover 75%. What loans should I take for the rest? I'm thinking business major, probably making like 65K a year after I graduate."

*[Agent processes - federalrunner_get_wizard_info for loan simulator]*

Now it's loading the loan simulator schema—a different contract for a different form.

*[Agent confirms understanding and begins execution]*

Watch—different government calculator, same pattern. The agent's automating the 6-page loan wizard using the structure FederalScout mapped.

*[federalrunner_execute_wizard in progress]*

Calculating the optimal loan strategy based on my post-graduation income and my parents' contribution.

*[Results screenshot appears]*

### 4.7 Loan Results Breakdown (20 seconds)

*[Agent displays loan strategy table]*

There's the three-loan strategy:

Direct Subsidized: $3,500 at 5.50% - government pays interest while I'm in school.

Direct Unsubsidized: $2,000 at 6.53% - my responsibility.

Parent PLUS: $13,875 at 9.08% - my parents' loan.

Total annual borrowing: $19,375.

*[Scroll to repayment estimates]*

The reality check: $391-$255 monthly payments for me on a $65K salary. About 6-7% of income—manageable.

But my parents owe $650/month for their portion.

---

## Section 5: Execution Transparency - Proof of Real Forms (90 seconds)

### 5.1 The Trust Question (10 seconds)

*[Switch to full screen narrator view]*

But how do we know these numbers are real? That the agent actually used the federal forms instead of hallucinating plausible results?

Let me show you the proof that these numbers came from real government forms.

*[Switch back to Claude.ai browser]*

### 5.2 First Query - FSA Estimator Verification (40 seconds)

*[Navigate to Northwestern query chat in Claude.ai]*

Let's go to the execute wizard tool call for our first query.

*[Scroll down to the "federalrunner execute wizard" tool call section]*

*[Agent response visible showing results: Total Estimated Federal Aid: $7,481/year, Student Aid Index: 43,439]*

Look at these results—$7,481 in federal aid, Student Aid Index of 43,439.

How do we know these are legitimate results from the government calculator?

*[Click to expand the "federalrunner execute wizard" tool call]*

*[Tool call expands showing the Request section with user_data JSON]*

Here's the user data—validated against the schema before execution.

*[Scroll down within expanded tool call to Response section]*

And the response from this tool call is the results screenshot.

*[Hover over screenshot thumbnail in response]*

Let's open this in a new tab.

*[Click screenshot - opens in new browser tab]*

*[Full Federal Student Aid results page visible with official branding]*

There it is. The official Federal Student Aid Estimator results page.

*[Highlight or point to key numbers on screen]*

Estimated Federal Student Aid: $7,481.

Student Aid Index (SAI): 43,439.

These exact numbers—pulled directly from the government form, not generated by the LLM.

### 5.3 Second Query - Loan Simulator Verification (30 seconds)

*[Close screenshot tab, return to chat]*

*[Navigate to loan query section or scroll down]*

Same verification for the loan strategy.

*[Scroll to second "federalrunner execute wizard" tool call]*

*[Expand the tool call]*

User data validated against the loan simulator schema.

*[Scroll to Response section]*

*[Click to open screenshot in new tab]*

*[Federal Loan Simulator results page loads]*

The Federal Loan Simulator results page.

*[Highlight the loan breakdown table]*

Three loans totaling $19,375 per year—Direct Subsidized, Direct Unsubsidized, Parent PLUS.

Interest rates, amounts, who owes what.

Every number the agent reported came from this official government page.

### 5.4 Why This Matters (10 seconds)

*[Return to agent chat view]*

This is Contract-First Form Automation. The agent can't make things up—it only reports what government calculators actually output.

Schema-driven execution means verifiable, trustworthy results every time.

---

## Section 6: Closing - The Vision (45 seconds)

*[Split screen: Mobile on left showing final results, narrator on right]*

Let's recap what just happened.

Two minutes of voice conversation on a mobile device.

Two different federal calculators—seven pages, six pages.

Zero forms manually filled. Zero confusion about what data is needed.

Just questions in natural language, answers from official government tools.

*[Switch to full screen narrator with key points appearing as text overlay]*

This is what AI-powered government services should look like:

**Conversational** - No forms, no fields, just natural language.

**Transparent** - Every result traced back to official sources.

**Intelligent** - The agent understands context and guides you through complex decisions.

**Voice-first** - Works everywhere—web, mobile, accessibility devices.

**Fast** - 30 seconds to 15 minutes maximum, instead of hours of confusion.

**Accurate** - Schema-driven validation, never guesses required fields.

*[All points remain on screen]*

That's Contract-First Form Automation for government services.

*[Fade to end card with project title]*

---

## Technical Notes for Production

### Timing Breakdown
- Section 1 (Agent Creation): 90 seconds
- Section 2 (OAuth): 90 seconds  
- Section 3 (Introduction): 30 seconds
- Section 4 (Mobile Demo): 3 minutes
- Section 5 (Verification): 90 seconds
- Section 6 (Closing): 45 seconds
- **Total Runtime: ~7.5 minutes**

### Screen Recording Requirements

**Desktop Recordings Needed:**
1. Claude.ai project creation and configuration
2. Google Cloud Console showing Cloud Run deployment
3. Auth0 dashboard showing API configuration
4. OAuth login and consent flow
5. Tool call inspection in Claude.ai chat

**Mobile Recording:**
- Samsung Galaxy Z Fold 7 screen recording with audio
- Clear microphone input for voice queries
- Visible agent responses and tool executions

**Diagram Animations:**
- OAuth 2.1 + MCP Handshake diagram (build-out animation)

### Visual Composition Guidelines

**Split Screen Segments:**
- Narrator (left) + Mobile screen (right) for Section 4
- Synchronize narrator commentary with mobile screen actions

**Picture-in-Picture:**
- Use when showing backend systems (GCP, Auth0) briefly
- Return to main screen quickly to maintain momentum

**Full Screen:**
- Use for screenshot verification in Section 5
- Diagram animation in Section 2

### Audio Guidelines

**Narrator Voice:**
- Conversational, enthusiastic without hype
- Natural pacing—not rushed but maintains momentum
- Emphasis on key technical terms: "Contract-First", "Schema", "OAuth 2.1"

**Mobile Voice Queries:**
- Clear, natural teenage voice (female)
- Authentic tone—curious, slightly concerned about cost
- Pauses where natural in conversation

**Background Music:**
- Minimal, subtle tech/corporate background track
- Lower volume during narration
- Can increase slightly during tool execution moments

### Key Visual Highlights

**Moments to Emphasize Visually:**
- Tool calls appearing in agent chat (use subtle highlight/glow)
- Schema loading confirmations
- Screenshot results populating
- Final numbers in results summaries
- Verification screenshots showing matching numbers

**Text Overlays to Add:**
- "8 seconds" when form executes
- Key numbers: "$7,481", "$77,500", "$19,375"
- Section titles as transitions
- Final recap points in Section 6

---

## Alternative Ending Options

### Option A: Technical Focus
"This system isn't just a demo—it's a blueprint for transforming how citizens interact with government services. Vision-guided discovery, contract-first execution, voice-first interfaces. The infrastructure is here. The technology works. Government forms should be this easy."

### Option B: Human Impact Focus  
"Imagine if every government service worked like this. Student aid, small business permits, tax filing, benefits enrollment. No more forms, no more confusion. Just conversation—natural, accessible, accurate. That's the future we're building."

### Option C: Call to Action
"The code is open source. The MCP specification is public. The OAuth integration pattern is reusable. This isn't just about student loans—it's about making every complex form-based system accessible through conversation. What will you automate next?"

---

## Post-Production Checklist

**Color Grading:**
- [ ] Consistent color temperature across all screen recordings
- [ ] Readable text in all UI elements
- [ ] Proper contrast for mobile screen visibility

**Audio Post:**
- [ ] Voice levels normalized across all segments
- [ ] Background music mixed appropriately
- [ ] Mobile audio cleaned of background noise

**Graphics:**
- [ ] Section title cards rendered
- [ ] OAuth diagram animation smooth
- [ ] Text overlays readable at all target resolutions

**Pacing:**
- [ ] No dead air longer than 2 seconds
- [ ] Transitions smooth between sections
- [ ] Tool execution moments feel "atomic" not rushed

**Accessibility:**
- [ ] Closed captions for all narration
- [ ] Visual descriptions of on-screen actions
- [ ] High contrast mode compatible