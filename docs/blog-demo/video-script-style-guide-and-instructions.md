# Video Script Style Guide & Project Instructions
## Multi-Agent Federal Form Automation Demo

---

## Project Overview

This is a technical demo video script for a multi-agent federal form automation system. The video is divided into two phases:
- **Phase 1: Discovery** - FederalScout agent mapping government forms
- **Phase 2: Execution** - FederalRunner agent automating forms via voice

The script is designed for voiceover narration with simultaneous screen recording showing live demos.

---

## Core Philosophy: Guide, Don't Read

**CRITICAL PRINCIPLE**: The script guides viewers' attention through the visual experience—it does NOT transcribe what appears on screen.

### What This Means in Practice:

❌ **AVOID**: Listing everything visible on screen
```
The agent identifies:
- Page title: "Federal Student Aid Estimator"
- This is a MULTI-PAGE WIZARD (Type B)
- Prominent blue "Start Estimate" button
- Information sections explaining the process
- Estimated time: 5-10 minutes
```

✅ **DO**: Guide attention to key moments and concepts
```
There's the Federal Student Aid Estimator landing page.

The agent analyzes it with vision and identifies this as a multi-page wizard.

Perfect—clicking into the wizard now.
```

**Rationale**: Viewers can see the screen. Your job is to help them understand WHAT they're seeing and WHY it matters, not to enumerate every element.

---

## Voice & Tone

### Conversational Authority
- Natural, flowing narration (like explaining to a colleague)
- Technically precise without being academic
- Enthusiasm for the technology without hype
- First-person perspective ("Let me show you", "Watch what happens")

### Examples of Good Voice:

✅ "This is where the magic happens—the MCP provides browser automation tools using Playwright."

✅ "Watch this—I didn't even provide a URL this time."

✅ "Smart reasoning about context."

❌ "The system then proceeds to initialize the discovery protocol by instantiating..."

❌ "As previously mentioned in the architectural overview section..."

### Pacing Language
Use natural transition phrases that maintain momentum:
- "Now watch this happen..."
- "Perfect—clicking into the wizard now"
- "Let's move through this a bit faster"
- "And finally, the results page"

---

## Handling On-Screen Content

### Agent Conversations
When the agent is processing or responding:

❌ **DON'T**: Read the agent's entire response verbatim
```
The agent responds: "I'm FederalScout, a specialized discovery agent for mapping government form wizards into machine-readable structures. I transform multi-step government calculators and forms into automated, voice-accessible tools..."
```

✅ **DO**: Summarize key points and guide to important sections
```
Look at this—the agent explains it generates two critical artifacts for each government form.

The Wizard Structure for Playwright execution, and the User Data Schema—the contract defining required inputs.
```

### Tool Calls & Technical Details

❌ **DON'T**: Enumerate every tool and its description
```
Available tools:
- start_discovery - Initiates wizard mapping
- get_page_info - Analyzes current page with vision
- click_element - Navigates through the wizard
- execute_actions - Fills fields with test data
- save_page_metadata - Captures page structure
- complete_discovery - Finalizes the mapping
```

✅ **DO**: Summarize the capability
```
The FederalScout MCP Server provides specialized tools—starting discovery, analyzing pages with vision, navigating wizards, capturing structures.
```

**When to show more detail**: Only when it's pedagogically important for understanding the pattern.

### Form Fields

❌ **DON'T**: List every field
```
Fields discovered:
- Birth date (month/day/year) - Text/dropdown fields
- Marital status - Radio buttons
- State of residence - Dropdown with all US states
- Grade level for 2026-27 school year - Radio buttons
```

✅ **DO**: Use visual highlighting with brief narration
```
Watch the systematic approach—the agent reviews the page screenshot and analyzes the page element data.

*[Highlight fields as they're analyzed - don't list them]*

For each field, it extracts the selector information, data type, validation rules.
```

---

## User Queries

### Don't Read Queries Verbatim

❌ **DON'T**:
```
*[Query appears in chat]*

> "Yes. My daughter is a senior in high school looking at colleges. So, discover the FSA Student Aid Estimator wizard at https://studentaid.gov/aid-estimator/"

*[Agent starts processing]*
```

✅ **DO**: Summarize the action
```
*[Type the query into chat]*

I provide the FSA Student Aid Estimator URL and the context—my daughter's a high school senior looking at colleges.

*[Agent starts processing]*
```

**Why**: The query is visible on screen. Summarizing maintains pacing and avoids redundancy.

---

## Structural Patterns

### Page-by-Page Navigation

For repetitive processes (like going through multiple wizard pages), use this pattern:

1. **Show first page in detail** (educational - teach the pattern)
2. **Accelerate through remaining pages** (they understand the pattern now)
3. **Call out page names** as narration to maintain orientation

**Example**:
```markdown
### The Discovery Pattern (30 seconds)

*[Page 1 visible on right, agent working on left]*

Watch the systematic approach—the agent reviews the page screenshot and analyzes the page element data.

For each field, it extracts the selector information, data type, validation rules.

Then it generates the test data and calls execute_actions to fill this data in the form via Playwright.

This is Playwright "being the hands."

All fields filled. Now it saves the complete page metadata.

And advances to Page 2.

This is the pattern: analyze, extract, fill, save, advance.

### The Seven-Page Journey (35 seconds)

Now watch this happen across all seven pages.

Page 2: Student Personal Circumstances
*[Fields fill → Continue]*

Page 3: Parent Marital Status
*[Fields fill → Continue]*

[... etc ...]
```

### Timing Compression

When content needs to be shorter than originally estimated:

1. **Identify what can be visual-only** (no narration needed)
2. **Combine related concepts** into single statements
3. **Remove redundant explanations** of things shown multiple times
4. **Use narration to call out page names** instead of describing what's on them

**Example Compression**:
- Original: 4 minutes for FSA discovery
- Refined: 90 seconds
- How: Detailed Page 1, quick cuts for Pages 2-7 with just page names

---

## Architecture & Technical Explanations

### Build-Out Animations

When explaining architecture with animated diagrams:

1. **Introduce the overall system** first
2. **Follow the visual build order** exactly
3. **Explain relationships between components** (arrows matter!)
4. **Use concrete metaphors** when helpful

**Example Pattern**:
```markdown
*[Phase 1 section builds - Discovery Request and FederalScout Agent appear]*

**Phase 1: Discovery Flow**

It starts with a discovery request—give the agent a government form URL to map.

The FederalScout Agent running in Claude Desktop receives this request.

*[Arrow highlights, FederalScout MCP box appears]*

The agent calls the FederalScout MCP Server deployed locally on my machine.

This is where the magic happens—the MCP provides browser automation tools using Playwright.

Think of it this way: Playwright becomes the hands that interact with the form, Claude Vision becomes the eyes and brain that understand what it's seeing.
```

**Key Points**:
- Narrate as each component appears
- Explain the arrows/connections
- Use metaphors strategically
- Don't get ahead of the visual build

### Technical Accuracy Without Jargon Overload

Balance technical precision with accessibility:

✅ "The MCP validates the user's data against our discovered schema, then uses Playwright to execute the form atomically—8 seconds start to finish."

✅ "OAuth 2.1 authentication with Dynamic Client Registration"

✅ "Contract-First Form Automation"

But immediately ground technical terms in what they enable:

✅ "Contract-first execution enables the same discovered structure to work across web, mobile, and voice interfaces."

---

## Transitions

### Between Sections

Create natural bridges between sections:

❌ **ABRUPT**:
```
Discovery complete.

## Next Section

Now let's look at the artifacts.
```

✅ **SMOOTH**:
```
Discovery complete. Seven pages mapped, 47 fields documented.

*[Highlight artifact generation in agent chat]*

Two more artifacts generated—both the Wizard Structure and User Data Schema ready for FederalRunner.
```

### From Architecture to Demo

Use clear signposting:

✅ "That's the architecture. Now let's see Phase 1 in action—the discovery process."

### Between Related Tasks

Show progression and purpose:

✅ "Let's discover one more federal form—the Loan Simulator. These two forms together create a realistic example for execution—first estimate your aid, then simulate borrowing to cover the gap."

---

## Stage Directions

### Format

Use `*[bracketed italics]*` for stage directions that tell the editor/presenter what to do:

```markdown
*[Type the query into chat]*
*[Agent starts processing]*
*[Browser opens on right, navigates to FSA site]*
*[Highlight "Start Estimate" button as agent clicks it]*
*[Fields start filling with test data]*
```

### What to Include

Stage directions should specify:
1. **Camera/screen actions** ("Split screen", "Full screen", "Picture-in-picture")
2. **Visual highlights** ("Highlight fields as they're analyzed")
3. **Timing cues** ("Quick cuts", "Pause")
4. **What appears when** ("Browser opens on right")

### What NOT to Include

Don't put narration text in stage directions:

❌ `*[Say: "This is the discovery process"]*`
✅ Just write: `This is the discovery process`

---

## Common Refinement Patterns

### Pattern 1: Removing Enumeration

**Before**:
```
The agent discovers:
- 6 pages
- 47 fields  
- Multiple field types
- Conditional logic
- Validation rules
```

**After**:
```
The agent systematically maps every page, every field, every interaction.
```

Or even simpler:
```
The agent maps the complete form structure.
```

### Pattern 2: Explaining Relationships

**Before**:
```
The FederalScout MCP Server running locally.
```

**After**:
```
The agent calls the FederalScout MCP Server deployed locally on my machine.
```

**Why**: The arrow/relationship matters more than just listing components.

### Pattern 3: Using Agent's Own Words as Transitions

**Before**:
```
Let's start the discovery.

*[Type query]*
```

**After**:
```
*[Scroll to bottom of response]*

And here's our invitation: "Ready to discover a government form? Just share the URL."

Perfect. Let's give it one.

*[Type query]*
```

**Why**: Uses the natural flow of the demo itself to create transitions.

### Pattern 4: Explaining "Why" with "What"

**Before**:
```
The User Data Schema—a JSON file defining required fields.
```

**After**:
```
The Input Schema—THE CONTRACT defining what data we need from users.

This is Contract-First Form Automation. The schema becomes the source of truth that both agents rely on.
```

**Why**: Explains the architectural significance, not just what the file contains.

---

## Timing Guidelines

### Per-Section Targets

These are rough guidelines based on Phase 1 refinement:

- **Intro sections**: 30-60 seconds
- **Architecture overviews**: 50-90 seconds  
- **First detailed demo**: 60-90 seconds (teach the pattern)
- **Subsequent demos**: 60-90 seconds (faster, pattern is known)
- **Results/artifacts sections**: 30-45 seconds

### Compression Techniques

When sections run long:

1. **Visual-only segments**: Let screen action speak (with just page names called out)
2. **Combine related steps**: "analyzes, extracts, fills" instead of three separate sentences
3. **Remove meta-commentary**: Cut "Now let me show you" type phrases
4. **Trust the visual**: If it's clearly visible, don't narrate it

---

## Quality Checklist

Before finalizing any section, verify:

### Content
- [ ] Does narration guide attention vs. reading the screen?
- [ ] Are technical terms explained through what they enable?
- [ ] Are transitions smooth and purposeful?
- [ ] Is the "why this matters" clear?

### Voice
- [ ] Conversational and natural?
- [ ] Enthusiastic without hype?
- [ ] First-person where appropriate?
- [ ] Technically accurate but accessible?

### Structure
- [ ] Follows visual build order for animations?
- [ ] Page 1 detailed, subsequent pages faster?
- [ ] Stage directions clear and actionable?
- [ ] Timing realistic for actual delivery?

### Efficiency
- [ ] No redundant explanations?
- [ ] No reading visible text verbatim?
- [ ] Compressed where appropriate?
- [ ] Visual-only segments identified?

---

## Reference Examples

### Excellent Section (Section 4 - FSA Discovery)

What makes it good:
- Clear structure (Landing → Pattern → Journey → Complete)
- Page 1 detailed to teach pattern
- Pages 2-7 just names with visual flow
- Natural transitions between subsections
- Timing realistic (90 seconds)
- Stage directions specific and actionable

### Key Moment Example (Architecture Overview)

What makes it good:
- Introduces two phases upfront
- Follows animated build order exactly
- Explains arrows/relationships
- Uses Playwright metaphor at right moment
- Smooth transition to breakthrough section
- "What makes this powerful" framing

---

## Applying to Phase 2

When working on Phase 2 (Execution), apply these same principles:

1. **Don't read voice queries verbatim** - summarize the interaction
2. **Show mobile screen actions** without excessive narration
3. **Explain what's happening** (schema validation, form execution) not just that it's happening
4. **Use results as teaching moments** - "This proves it's not hallucinated"
5. **Maintain momentum** - Phase 2 should feel faster since the pattern is established

---

## Collaboration Notes

### Iteration Style

The refinement process follows this pattern:

1. **Identify specific issues** ("This section reads the screen too much")
2. **Show concrete examples** (screenshots of what's actually shown)
3. **Suggest specific changes** (not just "make it better")
4. **Review updated section** before moving to next
5. **Update artifact incrementally** (section by section)

### What Works Well

- Concrete "before/after" examples
- Reference to actual screenshots/recordings
- Specific timing targets
- Clear rationale for changes

### Update Pattern

Always update the script artifact after each section is finalized:
```
"great. lets update the script artifact with the complete updated section X"
```

This ensures no changes are lost and provides a clean reference point.

---

## Final Notes

**Remember**: This is a technical demo video, not a tutorial or documentation. The goal is to show the system working impressively while explaining the key innovations—vision-guided discovery, contract-first execution, remote MCP infrastructure, voice-first interaction.

Every sentence should either:
1. Guide attention to something visually happening
2. Explain a concept that makes the visual meaningful
3. Transition between ideas/sections
4. Emphasize what makes this approach powerful

If a sentence doesn't do one of these things, consider cutting it.

---

**Document Version**: 1.0 (Based on Phase 1 Refinement - January 2025)
