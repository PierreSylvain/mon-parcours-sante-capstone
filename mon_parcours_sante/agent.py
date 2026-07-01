import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.skills import load_skill_from_dir

from .prompt import ROOT_INSTRUCTION
from .tools import health_profile_get, search_documents, health_profile_update, marker_timeline, parse_lab_pdf, index_document, upcoming_renewals, reimbursement_add, reimbursement_summary
from .guardrails import medical_guardrail, confirm_writes, before_model



# Dynamically load all skills from the `skills/` directory
skills_dir = os.path.join(os.path.dirname(__file__), "skills")
loaded_skills = []
if os.path.exists(skills_dir):
    for skill_name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, skill_name)
        if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
            loaded_skills.append(load_skill_from_dir(skill_path))

# Google Calendar MCP
calendar_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@cocal/google-calendar-mcp"],
            env={
                "GOOGLE_OAUTH_CREDENTIALS": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "gcp-oauth.keys.json")),
                "PATH": os.environ.get("PATH", "")
            },
        ),
        timeout=60,
    )
)

# Gmail MCP (Read-only)
gmail_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@shinzolabs/gmail-mcp"],
            env={
                "GOOGLE_OAUTH_CREDENTIALS": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "gcp-oauth.keys.json")),
                "PATH": os.environ.get("PATH", "")
            },
        ),
        timeout=60,
    ),
    # Expose ONLY read tools. Verify these exact names depending on the chosen MCP server.
    tool_filter=["gmail_search", "gmail_get_message", "gmail_get_thread", "gmail_list_messages", "gmail_list_threads", "search", "read_email", "get_email", "list_emails"]
)

tools = [
    health_profile_get,
        search_documents,
        marker_timeline,
        health_profile_update,
        parse_lab_pdf,
        index_document,
        upcoming_renewals,
        reimbursement_add,
        reimbursement_summary,
        SkillToolset(skills=loaded_skills)
]
if os.getenv("MPS_DISABLE_MCP") != "1":
    tools += [
        calendar_mcp,
        gmail_mcp,
        ]  

root_agent = LlmAgent(
    name="mon_parcours_sante", model=Gemini(model="gemini-flash-latest"),
    instruction=ROOT_INSTRUCTION, tools=tools,
    before_model_callback=before_model, before_tool_callback=confirm_writes,
)

