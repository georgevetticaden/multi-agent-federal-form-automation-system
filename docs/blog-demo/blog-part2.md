# The Missing MCP Playbook: Deploying Custom Agents on Claude.ai and Claude Mobile

## Part 2: OAuth 2.1, Dynamic Client Registration, MCP Spec 2025-06-18, and Google Cloud Run

In [Part 1](https://medium.com/@george.vetticaden/from-pixels-to-schemas-how-claude-vision-turns-any-government-form-into-a-voice-accessible-service-602cd37b5cc1), I showed you the Vision-Guided Discovery + Contract-First Execution pattern—how Claude Vision maps government forms into automation blueprints and user data schemas, enabling voice-accessible federal form automation.

The pattern works perfectly with Claude Desktop. Local MCP server, stdio communication, full access to government forms. But when I wanted to make these custom tools accessible in Claude.ai or use them via voice on mobile? **That's when the real work began.**

> **Making custom AI agents universally accessible—Claude.ai web, Claude Mobile voice, any device, anywhere—requires deploying custom MCP server tools publicly. This reveals infrastructure challenges rarely documented together: OAuth 2.1 with Dynamic Client Registration, MCP Specification 2025-06-18 (HTTP vs stdio), Google Cloud Run deployment for serverless scaling. Get any part wrong? Claude.ai simply won't connect—silent failures with little helpful error feedback.**

Most MCP tutorials stop at local servers—stdio transport, local file access, Claude Desktop workflows. Documentation for remote MCP servers accessible from web and mobile? That gap is what this article addresses.

**Watch what happens when I add the FederalRunner MCP server as a custom connector in Claude.ai—a deceptively simple sequence that masks the complex infrastructure dance we'll unpack in the sections ahead:**

*Adding Custom MCP Connector in Claude.ai: The deceptively simple flow—click "Add custom connector," authenticate via Auth0, connect. Behind this: OAuth discovery, Dynamic Client Registration, and MCP protocol handshake*

[Embedded demo video - 2:22 minutes]

---

## Why Real-World Deployment Changes Everything

That single requirement—**making custom AI agents accessible from Claude.ai and Claude Mobile**—triggered a cascade of infrastructure decisions:

- If Claude.ai/Claude Mobile → **remote MCP server** (not local stdio)
- If remote MCP → **OAuth 2.1 authentication** (not process isolation)
- If OAuth 2.1 → **Dynamic Client Registration** (mobile can't pre-configure)
- If public HTTP → **Cloud Run deployment** (not local machine)
- If Cloud Run → **MCP Spec 2025-06-18** (latest with HTTP support)

Each requirement builds on the previous. You can't skip steps. The architecture becomes:

| Requirement | Local MCP (Claude Desktop) | Remote MCP (Claude.ai/Mobile) |
|-------------|----------------------------|-------------------------------|
| **Transport Protocol** | stdio (stdin/stdout pipes)<br/>MCP stdio spec | Streamable HTTP (POST requests with chunked transfer encoding)<br/>MCP Spec 2025-06-18 |
| **Authentication** | None (process isolation provides security) | OAuth 2.1 with PKCE<br/>Dynamic Client Registration (DCR)<br/>Token validation via JWKS or userinfo |
| **Client Discovery** | Manual config file<br/>`claude_desktop_config.json` | Automatic via `.well-known` endpoints<br/>Dynamic Client Registration with Auth0<br/>No manual configuration required |
| **Deployment** | Local machine (Python process)<br/>Single user, single session | Public HTTP endpoint (Cloud Run, Lambda, etc.)<br/>Requires: Public URL, TLS/HTTPS, 24/7 availability<br/>Multi-user, cross-device, voice-first access |
| **MCP Spec Version** | 2024-11-05 (stable stdio)<br/>Stdio transport spec | 2025-06-18 (latest with HTTP)<br/>HEAD method support<br/>Session management |
| **Access Control** | Implicit (same machine security) | OAuth token validation on every authenticated request<br/>Scope-based authorization (federalrunner:read, federalrunner:execute)<br/>JWKS validation for JWT tokens |
| **Session State** | Automatic (process memory) | Explicit session management across HTTP requests<br/>`Mcp-Session-Id` header required<br/>State persistence between requests<br/>Session validation for handshake methods |
| **Connection Setup** | Immediate (local process spawn) | Multi-phase: OAuth discovery → DCR → User auth → Token exchange → MCP handshake |
| **Selective Authentication** | Not applicable | Critical pattern:<br/>• `initialize`: NO auth (protocol requirement)<br/>• `notifications/initialized`: Session validation only<br/>• `tools/list`: Full OAuth + session validation<br/>• `tools/call`: Full OAuth + session validation |

Desktop MCP servers are local processes. Remote MCP servers are public HTTP APIs requiring enterprise-grade security, cloud infrastructure, and protocol compliance.

---

## The OAuth 2.1 + MCP Handshake: Four Steps That Must Work Together

The architecture requirements reveal WHAT must change. But understanding WHY custom connector activation fails in Claude.ai requires seeing HOW these components work together. When you click "Connect" in Claude.ai to add a custom MCP connector, here's the precise four-step sequence:

*OAuth 2.1 + MCP Connection Sequence: Four-step authentication and connection flow showing Claude.ai discovering OAuth endpoints through /.well-known/oauth-protected-resource, dynamically registering as OAuth client with Auth0 via RFC 7591, authenticating users and issuing JWT tokens in RFC 9068 format, then establishing secure MCP connection with selective authentication pattern—initialize without token, tools/list and tools/call with full OAuth validation*

![OAuth MCP Handshake](oauth-handshake-diagram.png)

The diagram shows four critical steps. Get any part wrong—wrong OAuth metadata structure, DCR configuration error, incorrect HTTP status code—and Claude.ai simply won't connect. No helpful error messages, just "Disconnected."

### Step 1: OAuth Discovery — Claude Finds Your Authorization Server

When Claude.ai connects to your MCP server URL, it first queries `/.well-known/oauth-protected-resource` expecting JSON with `authorization_servers` array pointing to Auth0. **Auth0 is an identity and access management platform that handles OAuth 2.1 authentication, stores user credentials securely, issues JWT tokens, and manages Dynamic Client Registration.** This endpoint must return exact JSON structure Claude expects, with Auth0 tenant URL correct to the character—no trailing slashes.

Without proper OAuth discovery, Claude.ai can't find your authentication server. The connection fails before it starts. This is the first silent failure point—if this JSON structure is wrong, nothing else matters.

**[View OAuth discovery implementation →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/tree/main/docs/auth0#oauth-discovery-implementation)**

```python
@app.get("/.well-known/oauth-protected-resource")
async def oauth_metadata():
    """
    OAuth Protected Resource Metadata (RFC 9728).
    Required for Claude to discover Auth0 as the authorization server
    and initiate Dynamic Client Registration (DCR).
    This is how Claude Android discovers how to authenticate.
    """
    logger.info("OAuth metadata requested (for DCR discovery)")
    logger.debug(f"Returning Auth0 domain: {config.auth0_domain}")
    return {
        "resource": config.mcp_server_url,
        "authorization_servers": [f"https://{config.auth0_domain}"],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["federalrunner:read", "federalrunner:execute"]
    }
```

> **💡 OAuth discovery is your API contract:** The `/.well-known/oauth-protected-resource` endpoint determines whether the rest of the handshake even attempts. Test this endpoint first. Verify Claude can reach it. Confirm the Auth0 tenant URL is exact. This single endpoint is the gateway to everything else.

### Step 2: Dynamic Client Registration — Claude Registers Itself Automatically

Claude (the MCP client) POSTs to Auth0's `/oidc/register` endpoint (RFC 7591), sends client metadata (redirect URIs, scopes, application type), and receives `client_id` and `client_secret` from Auth0 dynamically—no manual pre-configuration. **The client metadata Claude sends includes which redirect URIs Claude needs, what scopes it requests, and what application type it is (native mobile app vs web application).**

You must enable Dynamic Client Registration on your Auth0 API, configure allowed redirect URI patterns (Claude uses specific patterns), set appropriate scopes (`federalrunner:read`, `federalrunner:execute`), and allow token revocation (RFC 7009) for security.

**This is what makes mobile access work.** Without DCR, every device would need manual OAuth client setup—impossible for mobile. Claude.ai and Claude Mobile register themselves automatically. One Auth0 configuration works across all devices.

**[View Auth0 DCR configuration guide →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/tree/main/docs/auth0#dynamic-client-registration-setup)**

> **💡 DCR eliminates device configuration hell and enables scalability:** Without Dynamic Client Registration, supporting mobile requires pre-registering Claude Mobile as OAuth client, manually configuring redirect URIs for mobile, distributing client credentials somehow, and repeating for every user's device. With DCR: Claude.ai auto-registers when connecting, Claude Mobile auto-registers when connecting, zero manual configuration, works for unlimited devices. Beyond convenience, DCR is crucial for scalability—it's the only practical approach for multi-device, multi-user deployments where you can't know all client configurations in advance. This is the technology that makes "accessible from anywhere" actually work.

### Step 3: Authorization Code Flow + Token Issuance — Users Authenticate

Claude redirects users to Auth0 login page. Users authenticate with username/password you created in Auth0 User Management (not dashboard admin accounts). Users grant consent to requested scopes on consent screen. Auth0 redirects back with authorization code. Claude exchanges code for JWT access token in RFC 9068 format.

You must create application users in Auth0, define token expiration policies (recommend 24 hours), configure consent screen with clear scope descriptions, and enable PKCE (Proof Key for Code Exchange) for mobile security.

**The JWT token format matters critically.** Your MCP server must validate JWT signatures using JWKS (JSON Web Key Set) from Auth0. Get the token validation wrong—wrong issuer check, wrong audience validation, expired JWKS cache—and all tool calls fail with 401 errors.

**[View Auth0 user management guide →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/tree/main/docs/auth0#user-management-and-token-configuration)**

### Step 4: MCP Protocol Handshake + Tool Access — Connection Established

The MCP spec is precise about what gets authenticated when. The `initialize` method must work without tokens—clients need to discover server capabilities first. But `tools/list` and `tools/call` require full OAuth validation. This selective authentication pattern is non-negotiable.

**The MCP handshake sequence:**

1. **HEAD request** - Claude sends HEAD to `/` for protocol discovery
   - **[View HEAD endpoint implementation →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/mcp-servers/federalrunner-mcp/src/server.py#L228)**

2. **initialize method** - Claude POSTs to `/` with `initialize` method **WITHOUT** OAuth token
   - **[View initialize implementation →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/mcp-servers/federalrunner-mcp/src/server.py#L345)**

3. **notifications/initialized** - Claude POSTs to `/` with `notifications/initialized` for session validation only
   - **[View notifications/initialized implementation →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/mcp-servers/federalrunner-mcp/src/server.py#L379)**

4. **tools/list method** - Claude POSTs to `/` with `tools/list` **WITH** OAuth token for full validation
   - **[View tools/list implementation →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/mcp-servers/federalrunner-mcp/src/server.py#L409)**

5. **tools/call method** - Claude POSTs to `/` with `tools/call` for each tool execution **WITH** OAuth token
   - **[View tools/call implementation →](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/blob/main/mcp-servers/federalrunner-mcp/src/server.py#L440)**

You must implement HEAD endpoint returning `MCP-Protocol-Version: 2025-06-18` header, root path `/` endpoint (not `/sse` or custom paths—Claude assumes root), selective authentication middleware, session management with `Mcp-Session-Id` headers, and proper HTTP status codes (405 vs 501, 202 vs 204 all communicate protocol meanings).

> **💡 MCP protocol version 2025-06-18 is required:** Earlier implementations used Server-Sent Events (SSE). The latest spec uses Streamable HTTP with specific requirements: root path `/` required, HEAD method support for protocol discovery, explicit session management. Working with Anthropic Support revealed: SSE will be deprecated soon in favor of Streaming HTTP. Build for current spec (2025-06-18), architect for evolution.

> **💡 Selective authentication pattern is non-negotiable:** The MCP spec requires different authentication for different methods: `initialize` gets NO token (protocol discovery), `notifications/initialized` gets session ID only, `tools/list` gets FULL OAuth validation, `tools/call` gets FULL OAuth validation. Implement this selectively in your middleware. Don't just blanket require tokens—you'll break the protocol handshake.

Get this four-step sequence right and Claude.ai shows "Connected" with green indicator. Get any part wrong and you get "Disconnected" with zero helpful error messages.

> **💡 Comprehensive logging saves debugging time:** Without request/response logs showing exact headers, status codes, and OAuth flow progression, debugging connection failures is nearly impossible. Log every layer: OAuth discovery requests, DCR registration attempts, token validation checks, MCP protocol handshakes. Silent failures become visible patterns.

---

## Google Cloud Run: Serverless MCP Deployment

Once you've implemented the OAuth + MCP handshake, you need somewhere to deploy it. Google Cloud Run provides serverless scaling (scales to zero when idle, scales up automatically under load), HTTPS by default (SSL certificates managed automatically), pay-per-use pricing (~$15/month for hundreds of form executions), container-based packaging (Playwright, Python, and all dependencies), and regional deployment (low latency for government form access).

You deploy FastAPI application implementing MCP spec, Playwright browser automation engine, OAuth token validation middleware, session management for MCP connections, and discovered wizard structures as JSON files.

The atomic execution pattern from Part 1 enables this serverless deployment. Every form execution is independent: launch browser → execute → close browser. No persistent state between requests. Perfect fit for Cloud Run's stateless scaling model.

> **💡 Atomic execution enables serverless deployment:** Every execution is independent—launch browser, fill form, extract results, close browser. No persistent sessions. No state between runs. This atomic pattern enables 100% reproducibility (same input = same output always), Cloud Run compatibility (stateless containers scale perfectly), complete audit trails (every screenshot saved), and parallel execution (thousands of simultaneous submissions).

---

## From Pattern to Practice: Your Guide to Deploying Custom Agents

**Part 1** showed you the Vision-Guided Discovery + Contract-First Execution pattern—how Claude Vision maps government forms into automation blueprints (Wizard Structures) and data contracts (User Data Schemas), enabling conversational form automation.

**Part 2** (this post) revealed the infrastructure reality—what it actually takes to deploy custom MCP servers that successfully integrate with Claude.ai and Claude Mobile. The OAuth 2.1 handshake with Dynamic Client Registration. The MCP Specification 2025-06-18 requirements. The selective authentication pattern. The Google Cloud Run deployment architecture. And why getting any part wrong means silent failures with little helpful error feedback.

**Use this as your guide.** When you're ready to deploy your own custom MCP server, reference this working example. The patterns, configurations, and architecture decisions documented here solve the integration challenges that most MCP tutorials never address.

**For more details, check out:**
- **[Watch the complete system in action](https://www.youtube.com/watch?v=IkKKLjBCnjY)** - Vision-Guided Discovery + Contract-First Execution Demo
- **[Explore the codebase](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system)** - Complete implementation on GitHub
- **[Auth0 Implementation Guide](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/tree/main/docs/auth0)** - OAuth 2.1 + Dynamic Client Registration setup
- **[MCP Integration Details](https://github.com/georgevetticaden/multi-agent-federal-form-automation-system/tree/main/docs/mcp-integration)** - Protocol compliance and handshake sequences

**← [Read Part 1: Vision-Guided Discovery + Contract-First Execution Pattern](https://medium.com/@george.vetticaden/from-pixels-to-schemas-how-claude-vision-turns-any-government-form-into-a-voice-accessible-service-602cd37b5cc1)**

---

**George Vetticaden** builds multi-agent AI systems and writes about practical patterns in enterprise AI. Previously served as VP of Agents at Sema4.ai, where he led development of agent building tools and document intelligence solutions.

**Connect:** [LinkedIn](https://linkedin.com/in/georgevetticaden) | [Medium](https://medium.com/@george.vetticaden)

**Related Reading:**
- [From Data Graveyard to Living Intelligence: Building Multi-Agent Health Systems with Claude's Extended Context](https://medium.com/@george.vetticaden/from-data-graveyard-to-living-intelligence-building-multi-agent-health-systems-with-claudes-cb02d7df3adb)
- [The 3 Amigo Agents: The Claude Code Development Pattern I Discovered While Implementing Anthropic's Multi-Agent Architecture](https://medium.com/@george.vetticaden/the-3-amigo-agents-the-claude-code-development-pattern-i-discovered-while-implementing-18d3a2e0e4ff)
