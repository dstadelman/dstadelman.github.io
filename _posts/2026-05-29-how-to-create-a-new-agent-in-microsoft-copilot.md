---
layout: "post"
title: "How to Create a New Agent in Microsoft Copilot"
date: 2026-05-29
---

Microsoft 365 Copilot includes a built-in Agent Builder that lets you create custom agents without coding. There are two methods: building from a natural-language prompt or using a template. Both paths go through the same interface -- Agent Builder -- and produce the same result.

## Requirements

- A Microsoft 365 subscription that includes Copilot (Copilot Pro, Copilot for Microsoft 365, or Copilot for Business).
- Access to the Microsoft 365 Copilot app at https://www.microsoft365.com.
- Copilot agents must be enabled by your organization's admin for business/enterprise tenants.

## Method 1: Create from a Prompt (Recommended)

This is the fastest path. You describe what you want, and Agent Builder writes your agent for you.

1. Open the Microsoft 365 Copilot app at https://www.microsoft365.com and sign in.

2. In the left navigation pane, under **Agents**, select **New Agent**.

3. Describe what the agent should do in plain language. For example:
   - "Help me create a detailed career development plan based on my current role and future goals."
   - "Analyze my weekly calendar and suggest time-blocking strategies."
   - "Summarize my unread emails and surface action items."

4. Click **Send**.

5. Agent Builder will respond conversationally, refining your agent's name, description, and system instructions as you go. Each prompt you send updates the agent definition.

6. When the agent is ready, click **Send** to test it. You can chat with your agent immediately and adjust the instructions at any time afterward.

7. If you want to edit the agent's configuration, select **Configure** to review and modify its name, description, and instructions.

8. When satisfied, select **Create** to finalize the agent.

## Method 2: Create from a Template

Templates provide pre-built starting points for common agent types.

1. Open the Microsoft 365 Copilot app at https://www.microsoft365.com and sign in.

2. In the left navigation pane, under **Agents**, select **New Agent**.

3. Select a template from the list of available options on the right side of the screen.

4. Choose one of the suggested prompts to test or chat with your agent and press **Send**.

5. If you want to customize the agent, select **Configure**. Here you can edit:
   - Agent name
   - Agent description
   - Agent instructions (the system prompt that controls behavior)
   - Knowledge sources (documents, files, links the agent can reference)
   - Suggested prompts (starter questions users can ask)

6. When finished, select **Create**.

## After You Create an Agent

Once created, you can further customize the agent at any time:

- **Edit instructions**: Open the agent and select Configure to modify the system instructions. Clear, specific instructions produce better results. Define the agent's role, the scope of work it should handle, and any constraints on its behavior.
- **Add knowledge sources**: Connect the agent to your files, folders, or web pages so it can reference specific content in its responses.
- **Add tools**: Enable the agent to interact with Microsoft 365 apps like Outlook, Word, or Excel if your subscription supports it.
- **Share with others**: In the agent settings, use Share to give colleagues access. Shared agents appear in the recipient's Agents list under the same name.

## Writing Effective Agent Instructions

The quality of an agent's output depends entirely on the instructions you provide. Follow these practices:

- **Be specific about the role**: Define who the agent is and what it does. "You are a project management assistant that helps track deliverables and timelines."
- **Define scope and boundaries**: Tell the agent what it should NOT do. "Do not make scheduling decisions. Present options and ask the user to choose."
- **Specify output format**: If you want structured responses, state it explicitly. "Present findings in a bulleted list with action items and deadlines."
- **Iterate**: Agent Builder is conversational. You can adjust instructions at any time. Test the agent and refine based on its output.

The Microsoft Support article provides a printable visual walkthrough: [PDF guide](https://res.publiconecdn.static.microsoft/s01-prod/pdf/Buid-an-agent-with-Agent-Builder.pdf).

## References

[1] Microsoft Support, "Build your own agent with Microsoft 365 Copilot," 2025. https://support.microsoft.com/en-us/Microsoft-365-Copilot/build-your-own-agent-with-microsoft-365-copilot

[2] Microsoft Learn, "Build Agents with Agent Builder in Microsoft 365 Copilot." https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/agent-builder-build-agents