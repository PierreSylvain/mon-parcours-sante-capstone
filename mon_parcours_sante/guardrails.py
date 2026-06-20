import re
from typing import Optional
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

# Deterministic regex for blocking conditions
EMERGENCY_PATTERN = re.compile(
    r"(mal à la poitrine|détresse|suicid|idées noires|du mal à respirer)",
    re.IGNORECASE
)

MEDICAL_ADVICE_PATTERN = re.compile(
    r"(c'est grave\s*\?|c'est normal\s*\?|trop haut|anormal|double ma dose|changer mon traitement|j'arrête mon traitement|qu'est-ce que j'ai\s*\?)",
    re.IGNORECASE
)

WRITE_TOOLS = {"health_profile_update"}


def _last_user_text(llm_request: LlmRequest) -> str:
    """Helper to extract the last user message text from the request contents."""
    for content in reversed(llm_request.contents):
        if content.role == "user" and content.parts:
            for part in content.parts:
                if hasattr(part, 'text') and part.text:
                    return part.text
    return ""


def medical_guardrail(callback_context, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """
    Before-model callback to deterministically catch emergency or medical advice requests.
    Zero LLM call ensures strict adherence and low latency.
    """
    last_user_text = _last_user_text(llm_request)
            
    if not last_user_text:
        return None
        
    if EMERGENCY_PATTERN.search(last_user_text):
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="🚨 Il semble s'agir d'une urgence médicale. Appelez immédiatement le 15 ou le 112. "
                        "En cas de détresse psychologique, appelez le 3114."
                    )
                ]
            )
        )
        
    if MEDICAL_ADVICE_PATTERN.search(last_user_text):
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="Je ne suis pas autorisé à fournir une interprétation médicale, à poser un diagnostic "
                        "ou à conseiller sur vos traitements. Seul un professionnel de santé peut le faire. "
                        "Si vous le souhaitez, je peux préparer ces questions pour votre prochaine consultation."
                    )
                ]
            )
        )
        
    return None


def confirm_writes(tool, args: dict, tool_context) -> Optional[dict]:
    """
    Before-tool callback to intercept side-effecting operations
    and ensure the 'confirmed' argument is explicitly set to True.
    """
    tool_name = getattr(tool, 'name', str(tool))
    
    if tool_name in WRITE_TOOLS:
        confirmed = args.get('confirmed')
        if not confirmed:
            return {
                "error": (
                    "L'action nécessite une confirmation explicite de l'utilisateur. "
                    f"Veuillez demander son accord pour l'action '{tool_name}' avec les paramètres {args} "
                    "avant de rappeler cet outil avec confirmed=True."
                )
            }
            
    return None

    
