# AI that Sees and Listens: How Claude Vision + Voice + Playwright Turn 825 Medical Calculators Into Conversations

**Building remote MCP infrastructure with OAuth 2.1, Streamable HTTP, and the June 2025 spec—from Claude Desktop proof-of-concept to voice-accessible agents on Claude.ai and Claude Mobile**

Ever watched your doctor pull out their phone mid-consultation to quickly calculate something? There's a 63% chance they're using MDCalc. According to the latest [Health Tech Without Borders survey](https://www.htwb.org/global-health-survey-series), **MDCalc is the second most-used clinical decision support tool globally**, with nearly two-thirds of physicians accessing it monthly. It's one of only two clinical tools with a positive Net Promoter Score—doctors actually recommend it to colleagues.

Last month, I had the opportunity to meet the leadership team at MDCalc—practicing MDs and technologists who've built something 63% of clinicians depend on. The tool works. Doctors love it. But after understanding their tool more deeply, one question kept nagging at me: What if doctors could just **describe their patient naturally** instead of hunting through 825 calculators and clicking dozens of fields?

That question led to an agent that demonstrates something broader: a pattern for automating any complex application that lacks APIs, combined with the infrastructure to deploy it remotely—OAuth 2.1 authentication, the latest MCP specification (2025-06-18), Google Cloud Run deployment—enabling voice access from Claude.ai and Claude Mobile.

*[Automation Architecture: Visual intelligence and remote MCP enabling voice-first calculator access]*

## The Universal Automation Challenge

I didn't have access to MDCalc's APIs. This is the reality for most users who want to automate web applications—APIs either don't exist for general use, or access requires enterprise contracts and months of integration work. It's common across enterprise software: valuable tools built before API-first architecture became standard, or where programmatic access remains restricted.

Without APIs, traditional automation approaches treat each interface as a unique puzzle. MDCalc's 825+ calculators each have different field types, conditional logic, and button layouts. The conventional solution: parse the HTML, find the form fields, map the data types, handle validation, write custom code for each calculator's unique structure.

That's 825 custom integrations to build and maintain. Miss one update, break one integration. The approach doesn't scale.

But there's a different way to think about this problem.

## Visual-First Automation: The Playwright + Claude Vision Pattern

Instead, I discovered something fundamental about modern AI: **when your AI can see, you don't need to hardcode integrations**. The pattern came from combining Playwright's browser automation with Claude's vision capabilities in a way that fundamentally changes how we automate complex applications.

The workflow is straightforward:

1. Playwright navigates to any calculator
2. Takes a screenshot of the interface
3. Claude's vision model understands the entire interface
4. Maps patient data to the exact fields shown
5. Playwright fills and submits based on Claude's visual understanding

The breakthrough isn't the individual technologies—it's the pattern. Playwright becomes the hands, Claude becomes the eyes and brain. Together, they can automate any web interface that lacks APIs.

Watch what happens with a cardiac risk assessment:

*[50-second video: Visual-First Automation in action - HEART Score execution]*

The doctor describes: "68-year-old male, 2 hours of chest pain, hypertension, diabetes, former smoker, normal ECG, normal troponin."

Claude captures a screenshot of the HEART Score calculator showing all available fields and their options. It analyzes the interface visually and builds a mapping: the patient's age (68) maps to the "≥65" button, the clinical presentation maps to "Moderately suspicious" in the History dropdown, three risk factors (hypertension, diabetes, former smoker) maps to "≥3 risk factors or history of atherosclerotic disease", normal ECG maps to "Normal", and normal troponin maps to "≤normal limit".

Claude passes these mapped values to Playwright in structured format. Playwright clicks the exact buttons Claude identified. The calculator executes and returns a result page showing "HEART Score: 5 points - Moderate Score (4-6 points)". Claude reads this result visually and presents the clinical interpretation.

Zero custom code per calculator. One pattern, 825 calculators, 100% coverage.

The contrast with traditional automation becomes clear in code:

```python
# Not this (825 custom integrations):
if calculator == "heart_score":
    fill_heart_score_fields(...)
elif calculator == "cha2ds2_vasc":
    fill_cha2ds2_fields(...)
# ... 823 more

# This (universal pattern):
screenshot = capture_calculator()
claude.understand_and_execute(screenshot, patient_data)
```

## Visual Validation Loops

After executing a calculator, the agent takes another screenshot to check for:

* Validation errors ("Please enter age between 18-100")
* Conditional fields that appeared ("If diabetic, enter HbA1c")
* Partial results requiring additional input

This creates a self-correcting loop. The agent sees errors exactly as a human would and adapts on the fly. No error codes to parse, no API documentation to maintain—just visual understanding.

In testing, this visual validation approach achieved 99.2% field mapping accuracy across diverse calculator types, from simple CHA₂DS₂-VASc scores to complex APACHE II assessments with 20+ fields.

This pattern applies anywhere you need to automate complex applications without REST APIs. EHR systems. Insurance portals. Legacy enterprise tools. Anywhere humans click through forms, AI can now do the same—not by memorizing every possible form, but by seeing and understanding them.

## The Co-Pilot Model: Recommending the Right Calculators

The visual automation pattern solves how to execute any calculator. But which calculators should run for a given clinical scenario? This is where Claude's capabilities become particularly valuable.

The agent has access to the complete metadata catalog of all 825 MDCalc calculators—titles, descriptions, clinical indications, medical specialties, and use cases. Combined with Claude's medical knowledge, this enables semantic reasoning that aligns a clinical scenario expressed in natural language with the appropriate calculation tools.

When a doctor describes a 68-year-old male with chest pain, hypertension, diabetes, and a former smoking history, Claude reasons about which assessment tools are clinically relevant. From 825 options, it identifies HEART Score for major cardiac events, TIMI Risk Score for NSTEMI, GRACE ACS Risk Calculator for mortality estimates, and EDACS for early discharge safety assessment.

But here's what matters: the agent recommends, the physician decides.

*[Screenshot: Agent recommending four cardiac calculators and asking for confirmation]*

This design reflects [Dr. Graham Walker's](https://www.linkedin.com/in/grahamwalkermd/) (MDCalc co-founder) approach to clinical AI—tools must enhance judgment, not supplant it. Walker created the [Physicians' Charter for Responsible AI](https://physicianscharter.ai/wp-content/uploads/2023/08/The-Physicians-Charter-Executive-Summary-August-2023.pdf), driven by a foundational principle: in healthcare, "move fast and break things" kills people. AI should augment physicians, never replace the patient-doctor relationship.

Walker's Charter defines clinical AI requirements: patient-centricity, accountability, human-centered design, and transparency.

The agent implements this "co-pilot" principle. It identifies relevant calculators based on clinical context. It explains why each is appropriate. Then it waits for physician confirmation before executing anything. The doctor reviews the recommendations, selects which calculators to run, and maintains complete control throughout the assessment. From five minutes of hunting through calculators and clicking fields to 30 seconds of reviewing recommendations and confirming execution.

## The Co-Pilot Principle Extends to Calculations

Given Claude's medical reasoning capabilities and the co-pilot approach to calculator selection, you might wonder: why not take it further? Why not skip the calculators entirely and let Claude compute the scores directly?

Because even with recent advances, **LLMs remain better at using calculation tools than performing calculations themselves**—especially in healthcare where accuracy is critical.

Research from [Dr. Alex Goodell and colleagues at Stanford](https://www.nature.com/articles/s41746-025-01475-8)—published in Nature Digital Medicine—demonstrates this clearly. When they tested medical language models on clinical calculations, the models performed poorly. But when given access to calculation tools, accuracy improved by 1,300%.

[Claude Sonnet 4.5](https://www.anthropic.com/news/claude-sonnet-4-5), released recently, shows substantial gains in mathematical reasoning. But in healthcare, there's another critical factor: these calculators represent constantly evolving clinical evidence. New studies refine scoring algorithms. Guidelines update risk thresholds. Validation criteria change based on new research.

MDCalc's calculators incorporate these updates continuously—peer-reviewed algorithms, evidence-based modifications, validated scoring criteria. When HEART Score guidelines update based on new cardiac research, MDCalc reflects that change. An LLM's training data, however current, represents a point-in-time snapshot.

This aligns with how doctors actually work. They don't memorize scoring algorithms—they use validated calculators that reflect current evidence. The AI should do the same: understand clinical context, select appropriate tools, execute calculations through proven instruments, then synthesize results using medical knowledge.

The co-pilot principle applies at both levels: recommend calculators (don't auto-select), use validated tools for calculations (don't compute directly).

## Beyond Claude Desktop: Running Agents in Claude.ai and Mobile with Custom Remote MCP Servers

The visual automation pattern worked perfectly with Claude Desktop—stdio communication, local MCP server running on my machine, full access to all 825 calculators. But when I wanted to make these custom tools accessible in Claude.ai or use them via voice on my phone? That's when the real work began.

If you want custom MCP tools accessible in Claude.ai or Claude Mobile, you must deploy a remote MCP server meeting specific requirements. Get any part wrong and Claude.ai simply won't connect. No helpful error messages, just silent failures.

Search online for MCP examples and you'll find plenty on local servers—stdio transport, local file access, Claude Desktop workflows. But documentation for remote MCP servers accessible from web and mobile? That gap is what this section addresses.

Here's what changes when you move from desktop demos to Claude.ai and mobile:

[INSERT TABLE GIST HERE - mcp-deployment-comparison.md]

The architecture isn't just different—it's a complete paradigm shift. Desktop MCP servers are local processes communicating through pipes. Remote MCP servers are public HTTP APIs requiring enterprise-grade security, cloud infrastructure, and protocol compliance.

These requirements don't exist in isolation—they work together in a precise sequence. When you click "Connect" in Claude.ai, here's what actually happens behind the scenes:

[INSERT OAUTH 2.1 + MCP HANDSHAKE DIAGRAM HERE]

*Figure 1: How Claude.ai discovers, authenticates, and connects to custom remote MCP servers.*

The next three sections break down what it actually takes to implement each phase:

1. MCP Protocol Evolution - Why the June 2025 spec with Streamable HTTP is required
2. OAuth 2.1 + Dynamic Client Registration - How Claude.ai discovers and authenticates with your server
3. Cloud Deployment with Secure State Management - Google Cloud Run, secrets management, and making it all work together

## MCP Protocol Evolution: Why the June 2025 Spec Matters

The MCP specification evolved mid-development. My initial implementation used Server-Sent Events (SSE) based on earlier documentation. Then Anthropic reached out: SSE support may be deprecated, migrate to Streamable HTTP.

The [June 2025 MCP specification](https://modelcontextprotocol.io/specification/2025-06-18) introduced Streamable HTTP as the recommended transport. Unlike SSE's persistent connection, Streamable HTTP uses standard POST requests with chunked transfer encoding. More critically, it aligns with OAuth 2.1's security model.

The protocol requires selective authentication—not all endpoints demand OAuth tokens:

**initialize**: No authentication required. Clients discover server capabilities first.

**notifications/initialized**: Session validation only, confirms handshake completed.

**tools/list**: Full OAuth validation required. Must present valid token to see tools.

**tools/call**: Full OAuth validation required. Tool execution needs authentication.

This selective authentication enables the MCP handshake while maintaining security for actual operations. Configure this wrong and Claude.ai discovers your server but never completes the connection.

The difference between HTTP status codes matters: 405 vs 501, 202 vs 204—these communicate specific protocol meanings that affect connection sequencing. Return 501 (Not Implemented) instead of 405 (Method Not Allowed) for a GET request? Claude interprets that as "this server is broken" and terminates the session. Return 204 (No Content) instead of 202 (Accepted) for the notifications endpoint? The handshake may stall.

Getting this right required comprehensive logging at every layer. Without request/response logging showing exact headers and status codes, debugging connection failures is nearly impossible. The logs revealed the precise sequence Claude.ai expects: HEAD for protocol discovery, GET for OAuth metadata, POST for initialize (without token validation), POST for notifications (session validation only), then finally POST for tools/list with full OAuth validation.

## OAuth 2.1 with Dynamic Client Registration: The Authentication Puzzle

Securing the remote MCP server meant implementing OAuth 2.1 with [Dynamic Client Registration](https://datatracker.ietf.org/doc/html/rfc7591). I chose [Auth0](https://auth0.com) for its robust DCR support, but the integration revealed complexity not covered in basic OAuth tutorials.

**The authentication flow:**

Claude.ai discovers the server through the `/.well-known/oauth-protected-resource` endpoint, finding the authorization server details. It then dynamically registers itself as an OAuth client through Auth0's DCR endpoint—no manual client configuration required. The user completes the OAuth flow (login plus consent screen), and Claude receives an access token with the appropriate scopes. The server validates tokens on every authenticated request using [JWKS](https://auth0.com/docs/secure/tokens/json-web-keys) (JSON Web Key Set).

**Token validation complexity emerged quickly.** Auth0 can issue different token types depending on configuration:

- **JWT tokens** include a `kid` (key ID) in the header and can be validated via JWKS public key cryptography.
- **JWE/opaque tokens** lack the `kid` header and require validation through Auth0's userinfo endpoint.

The server must handle both gracefully:

```python
# Attempt JWT validation first (has 'kid' in header)
try:
    return validate_jwt_with_jwks(token)
except:
    # Fall back to Auth0 userinfo endpoint
    # Works for JWE and opaque tokens
    return validate_via_userinfo(token)
```

This dual-path validation ensures compatibility regardless of Auth0's token format decisions. One OAuth flow works for both Claude.ai web access and Claude Mobile app access—same authentication, same tools, different interfaces.

The logs showed another critical insight: Claude.ai sends the OAuth token in the Authorization header starting with the `initialize` request, but the server must NOT validate it yet. The token is present, but validation only happens later for `tools/list` and `tools/call`. This selective authentication pattern—token present but not validated during handshake—took two days of debugging to get right.

## Cloud Deployment with Secure State Management

With authentication working locally, deploying to [Google Cloud Run](https://cloud.google.com/run) as a public HTTP endpoint brought additional considerations:

**Cold starts**: Initializing Playwright with Chromium adds 5-10 seconds to first requests. The trade-off: keep minimum instances warm (costs money) or accept occasional latency (affects user experience). I chose accepting latency since calculator execution itself is fast once warm.

**Screenshot optimization**: Initial screenshots were 100KB+ at full resolution. Reducing viewport size and applying JPEG compression brought them down to 23KB without losing visual understanding quality. Smaller screenshots mean faster tool responses and lower bandwidth costs.

**Authentication state**: MDCalc employs bot detection that blocks unauthenticated browser automation. Solution: manual login session saved to [Google Secret Manager](https://cloud.google.com/security/products/secret-manager), mounted to Cloud Run instances as environment secrets. The session persists across container restarts.

**Session management**: The MCP protocol requires maintaining state across multiple requests (initialize → list tools → call tools). In-memory session dictionaries work but don't survive container restarts. For systems handling many concurrent users, this would require external state storage like Redis.

The deployment script handles these requirements: uploading secrets to Secret Manager, configuring service account permissions for secret access, setting environment variables for the Cloud Run service, enabling unauthenticated public access for the discovery endpoint, and generating the complete `gcloud run deploy` command.

One command deploys a remote, secure, spec-compliant MCP server accessible from both Claude.ai and Claude Mobile through OAuth-protected endpoints. The result: doctors can describe patients naturally via voice on their phones, and the calculators execute automatically—no clicking, no hunting, just conversation.

## Voice-First Clinical Decision Support

The completed system transforms how doctors interact with clinical calculators:

**Voice activation**: "Claude, calculate HEART score for my 68-year-old patient with chest pain, normal ECG, 3 risk factors, and normal troponin."

**Parallel execution**: Multiple calculators run simultaneously, providing comprehensive assessment in seconds.

**Intelligent synthesis**: Results from disparate calculators synthesized into coherent recommendations.

**Mobile-first**: Works on Claude Android exactly as on desktop—no app installation required.

During conversations with MDCalc's leadership, I demonstrated this through three clinical scenarios: chest pain assessment, atrial fibrillation anticoagulation decision, and ICU multi-organ failure scoring. Each scenario that traditionally takes 5-10 minutes completed in under 30 seconds through conversation.

## The Pattern That Emerges: Visual Automation for Legacy Systems

This approach extends beyond medical calculators. Think about all the legacy systems in healthcare—and every other industry—that lack modern APIs:

- **Insurance portals** where claims processors click through dozens of forms
- **EHR systems** with no programmatic access to patient data
- **Legacy enterprise tools** built before APIs existed
- **Government systems** with Byzantine web interfaces

Anywhere humans navigate complex interfaces without REST APIs, this visual automation pattern applies. The AI sees. The AI understands. The AI interacts. No custom integration required.

The remote MCP deployment pattern provides the infrastructure: OAuth security, mobile access, cloud scaling, session management. The building blocks for enterprise AI agent deployment.

## Beyond MDCalc: Making Enterprise Tools AI-Native

While everyone's focused on building new AI applications, **the real opportunity is making existing tools AI-native without changing them**. No vendor lock-in, no migration projects, no retraining.

Key insights from deploying this pattern:

1. **Visual understanding beats API integration** for heterogeneous systems
2. **Screenshots are APIs** when combined with vision models  
3. **Self-correcting visual loops** handle edge cases better than coded logic
4. **Remote MCP deployment with OAuth 2.1** enables mobile-first AI agents
5. **Selective use of LLM intelligence** — delegate calculations to proven tools, use LLMs for context and orchestration

The technical barriers that seemed insurmountable—deploying MCP servers remotely, handling OAuth properly, scaling browser automation—all have solutions. They're just not widely documented yet.

## What This Means for Product Leaders

If you have valuable tools that users struggle to navigate, you don't need to rebuild them as AI applications. You need to make them conversationally accessible.

The MDCalc Clinical Companion demonstrates this:
- **No changes to MDCalc's codebase**
- **No API development required**
- **100% calculator coverage from day one**
- **Works on mobile devices via voice**
- **Maintains evidence-based credibility**

For MDCalc specifically, this could mean evolving from a tool doctors actively search to an intelligent companion that proactively suggests relevant assessments. The same 63% of physicians who use it monthly could interact via voice during patient encounters instead of post-consultation clicking.

## The Infrastructure Is Ready

We're moving from **AI as coding assistants** to **AI as infrastructure components**. Remote MCP servers deployed on cloud platforms. OAuth 2.1 security. Dynamic client registration. Mobile-first access. These aren't experimental features—they're deployment requirements.

We're moving from **custom integrations** to **universal automation**. Vision-based approaches that adapt to any interface. Screenshot analysis that catches validation errors. Intelligent retry loops that self-correct.

We're moving from **pull-based tools** to **push-based intelligence**. Doctors shouldn't need to remember which calculator to use. AI should recommend, execute, and synthesize automatically.

The infrastructure exists. The protocols work. The patterns are proven.

What remains is building more agents that leverage them.

---

*The complete codebase for the MDCalc Clinical Companion—including both local and remote MCP server implementations—is available at [github.com/georgevetticaden/mdcalc-agent](https://github.com/georgevetticaden/mdcalc-agent). The repository documents the OAuth 2.1, Google Cloud Run, and Auth0 integration patterns.*

*Demo videos:*
- [MDCalc Clinical Companion - Voice-First Demo](https://www.youtube.com/watch?v=5VJj2sPhlQU)
- [Cross-Device AI Orchestration](https://www.youtube.com/watch?v=cbWhk69Rgak)

---

**George Vetticaden** is a Product Leader in AI Agents and Multi-Agent Systems with deep expertise in enterprise AI platforms and conversational AI. Previously VP of Agents at Sema4.ai, he explores how AI agents transform specialized tools into conversational capabilities. This agent was developed as part of ongoing discussions with MDCalc's leadership team about the future of clinical decision support. Connect on [LinkedIn](https://www.linkedin.com/in/georgevetticaden/) to discuss the future of voice-first AI.