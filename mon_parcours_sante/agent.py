import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.skills import load_skill_from_dir

from .prompt import ROOT_INSTRUCTION
from .tools import health_profile_get, search_documents, health_profile_update
from .guardrails import medical_guardrail, confirm_writes

# Dynamically load all skills from the `skills/` directory
skills_dir = os.path.join(os.path.dirname(__file__), "skills")
loaded_skills = []
if os.path.exists(skills_dir):
    for skill_name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, skill_name)
        if os.path.isdir(skill_path) and os.path.exists(os.path.join(skill_path, "SKILL.md")):
            loaded_skills.append(load_skill_from_dir(skill_path))

root_agent = LlmAgent(
    name='mon_parcours_sante',
    model=Gemini(model='gemini-flash-latest'),
    instruction=ROOT_INSTRUCTION,
    tools=[
        health_profile_get,
        search_documents,
        health_profile_update,
        SkillToolset(skills=loaded_skills)
    ],
    before_model_callback=medical_guardrail,
    before_tool_callback=confirm_writes
)
