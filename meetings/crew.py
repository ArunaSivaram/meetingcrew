"""Define the MeetingCrew: three agents that read meeting notes, open GitHub
issues through the MCP server, and draft follow-up emails.

Public surface: ``run_meeting_crew(notes, repo, roster)``.
"""

import os
from typing import Any, Dict, List, Optional, Type

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import BaseTool
from crewai_tools import MCPServerAdapter
from pydantic import BaseModel, Field, PrivateAttr, field_validator

from .mcp_client import get_github_server_params


class NullFilteringTool(BaseTool):
    """Wrap a tool and strip None-valued kwargs before calling it.

    Needed because the GitHub MCP server's issue_write validates optional
    fields (e.g. `milestone`) strictly — it rejects `null` for a number field
    rather than treating it as "not supplied". LLMs often pass `null` for
    optional fields regardless of prompt guidance, so we drop them here.
    """

    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None
    _inner: Any = PrivateAttr()

    def __init__(self, inner_tool: BaseTool, **data: Any):
        super().__init__(
            name=inner_tool.name,
            description=inner_tool.description,
            args_schema=inner_tool.args_schema,
            **data,
        )
        self._inner = inner_tool

    def _run(self, **kwargs: Any) -> Any:
        clean = {k: v for k, v in kwargs.items() if v is not None}
        return self._inner._run(**clean)


# ---------- Structured outputs ----------------------------------------------

class ActionItemOut(BaseModel):
    """One action item extracted from the meeting notes."""

    task: str = Field(..., description="The action to perform.")
    owner_name: Optional[str] = Field(
        None, description="Human-readable name of the owner from the roster."
    )
    github_username: Optional[str] = Field(
        None,
        description=(
            "Bare GitHub login (no '@' prefix) of the owner from the roster, "
            "or None if no clear match."
        ),
    )
    due_date: Optional[str] = Field(
        None, description="Due date mentioned in the notes, in YYYY-MM-DD if possible."
    )
    context: str = Field(
        "",
        description="One or two sentences of context from the notes supporting this item.",
    )

    @field_validator("github_username")
    @classmethod
    def strip_at_prefix(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.lstrip("@") or None


class ActionItemList(BaseModel):
    """Container returned by the Notes Analyst."""

    items: List[ActionItemOut]


class OwnerEmail(BaseModel):
    """A single email draft for one owner."""

    github_username: str
    owner_name: str
    subject: str
    body: str

    @field_validator("github_username")
    @classmethod
    def strip_at_prefix(cls, v: str) -> str:
        return v.lstrip("@")


class CommsOutput(BaseModel):
    """Container returned by the Comms Writer."""

    emails: List[OwnerEmail] = Field(
        ..., description="One email per owner. github_username is on each OwnerEmail."
    )
    summary: str = Field(..., description="A 3-line meeting summary.")


# ---------- Helpers ---------------------------------------------------------

ISSUE_TOOL_NAME = "issue_write"


def _format_roster(roster: List[Dict[str, Any]]) -> str:
    """Turn the roster list into a readable block for the LLM prompt."""
    lines = []
    for p in roster:
        aliases = p.get("aliases") or ""
        lines.append(
            f"- {p['name']} (aliases: {aliases or 'none'}; github: @{p['github_username']}; email: {p.get('email', '')})"
        )
    return "\n".join(lines) if lines else "(empty roster)"


# ---------- Public entrypoint ----------------------------------------------

def run_meeting_crew(
    notes: str, repo: str, roster: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Run the full three-agent crew end-to-end.

    Args:
        notes: Raw meeting notes pasted by the user.
        repo: GitHub repository in "owner/repo" form.
        roster: List of participant dicts with keys name, email, github_username, aliases.

    Returns:
        A dict with the structured outputs of each task plus the final kickoff result.
    """
    llm = LLM(model=os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini"))
    roster_block = _format_roster(roster)
    params = get_github_server_params()

    with MCPServerAdapter(params) as mcp_tools:
        # Give the Issue Creator ONLY the tool it needs — nothing else.
        raw_issue_tools = [t for t in mcp_tools if t.name == ISSUE_TOOL_NAME]
        if not raw_issue_tools:
            raise RuntimeError(
                f"MCP server did not expose a '{ISSUE_TOOL_NAME}' tool; "
                f"saw: {[t.name for t in mcp_tools]}"
            )
        # Wrap so null-valued optional fields are stripped before the MCP call.
        issue_tools = [NullFilteringTool(t) for t in raw_issue_tools]

        analyst = Agent(
            role="Notes Analyst",
            goal=(
                "Extract every action item from the meeting notes and match each one "
                "to a person in the provided roster — strictly, never inventing people."
            ),
            backstory=(
                "You are a meticulous chief of staff. You read raw meeting notes and "
                "produce a clean, structured list of commitments. You match owners only "
                "against a known roster using names and aliases; when the notes are "
                "ambiguous or the person isn't on the roster, you leave github_username empty "
                "rather than guess."
            ),
            tools=[],
            llm=llm,
            allow_delegation=False,
            verbose=True,
        )

        issue_creator = Agent(
            role="Issue Creator",
            goal=(
                "Create one GitHub issue per action item in the target repository, "
                "assigning it to the right person when a github username is known."
            ),
            backstory=(
                "You are a disciplined engineering coordinator. You translate action "
                "items into well-formed GitHub issues: a clear title, a body that "
                "preserves the context and due date, and the correct assignee. "
                "You use only the issue-creation tool and don't invent fields."
            ),
            tools=issue_tools,
            llm=llm,
            allow_delegation=False,
            verbose=True,
        )

        comms = Agent(
            role="Comms Writer",
            goal=(
                "Draft one short, friendly email per owner listing only their action "
                "items with GitHub issue links, plus a short meeting summary."
            ),
            backstory=(
                "You are a communications lead who writes crisp follow-up emails. "
                "You group tasks by owner, cite the GitHub issue URL for each task, "
                "and keep the tone warm and brief."
            ),
            tools=[],
            llm=llm,
            allow_delegation=False,
            verbose=True,
        )

        task_extract = Task(
            description=(
                "Read the meeting notes below and extract every action item.\n\n"
                "=== NOTES ===\n{notes}\n=== END NOTES ===\n\n"
                "Match each action item's owner strictly against this roster. "
                "Use the person's name OR any of their aliases. "
                "If no roster entry clearly matches, set github_username to null. "
                "Never invent a person who is not on the roster.\n\n"
                "=== ROSTER ===\n{roster}\n=== END ROSTER ===\n\n"
                "For each action item, capture: the task, the owner_name (if matched), "
                "the github_username (if matched; the BARE login WITHOUT a leading '@'), "
                "the due_date (YYYY-MM-DD if possible, else null), and a one-to-two-sentence "
                "context quote from the notes."
            ),
            expected_output=(
                "A JSON object matching the ActionItemList schema: "
                '{"items": [{"task": "...", "owner_name": "...", "github_username": "...", '
                '"due_date": "...", "context": "..."}, ...]}'
            ),
            agent=analyst,
            output_pydantic=ActionItemList,
        )

        task_issues = Task(
            description=(
                "For each action item from the previous task, create exactly ONE "
                "GitHub issue in the repository '{repo}'. Call the issue_write tool "
                "once per action item, passing ONLY these fields:\n"
                "- method: the literal string \"create\"\n"
                "- owner: the part before '/' in '{repo}'\n"
                "- repo: the part after '/' in '{repo}'\n"
                "- title: a concise summary of the task\n"
                "- body: include the task text, context, and due date (if any)\n"
                "- assignees: [github_username] if github_username is not null, else an empty list []\n"
                "  (pass the bare login as-is — DO NOT prepend '@'. GitHub rejects '@login'.)\n\n"
                "DO NOT include milestone, labels, issue_number, duplicate_of, issue_fields, "
                "or any other field. Omit them entirely — do not send them as null.\n\n"
                "Record each result's issue number and html_url."
            ),
            expected_output=(
                "A JSON list, one entry per action item, each with: task, owner_name, "
                "github_username, issue_number, issue_url."
            ),
            agent=issue_creator,
            context=[task_extract],
        )

        task_comms = Task(
            description=(
                "Using the action items from task 1 and the issues created in task 2, "
                "produce:\n"
                "1. One email per owner. Each email lists ONLY that owner's action "
                "   items, with the GitHub issue URL next to each. Keep it short and friendly.\n"
                "2. A 3-line meeting summary suitable for a team channel.\n\n"
                "Return a JSON object matching this shape:\n"
                "{\"emails\": [{\"github_username\": \"...\", \"owner_name\": \"...\", "
                "\"subject\": \"...\", \"body\": \"...\"}, ...], \"summary\": \"...\"}\n\n"
                "Omit action items that have no github_username (they cannot be emailed)."
            ),
            expected_output=(
                "A JSON object matching the CommsOutput schema with keys 'emails' "
                "(a list of email objects) and 'summary' (3 short lines)."
            ),
            agent=comms,
            context=[task_extract, task_issues],
            output_pydantic=CommsOutput,
        )

        crew = Crew(
            agents=[analyst, issue_creator, comms],
            tasks=[task_extract, task_issues, task_comms],
            process=Process.sequential,
            verbose=True,
        )

        kickoff_result = crew.kickoff(
            inputs={"notes": notes, "repo": repo, "roster": roster_block}
        )

        return {
            "action_items": task_extract.output.pydantic if task_extract.output else None,
            "issues_raw": task_issues.output.raw if task_issues.output else None,
            "comms": task_comms.output.pydantic if task_comms.output else None,
            "final": str(kickoff_result),
        }
