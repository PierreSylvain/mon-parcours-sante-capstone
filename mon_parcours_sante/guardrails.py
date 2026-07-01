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
    r"("
    # interprétation / diagnostic
    r"c'est grave|est-ce grave|c'est normal|est-ce (?:que c'est )?normal|"
    r"trop (?:haut|élevé|eleve|bas|basse)|anormal|inquiétant|inquietant|"
    r"qu'est-ce que j'ai|qu'est-ce que (?:ça|cela|ca) veut dire|ça veut dire quoi|"
    r"interpr[èe]t|diagnosti|je suis malade|"
    # verbe de modification + objet médical proche
    r"(?:arr[êe]ter|stopper|doubler|augmenter|r[ée]duire|diminuer|changer|modifier|sauter|espacer)"
    r"(?:\s+\w+){0,3}\s+(?:dose|doses|traitement|posologie|m[ée]dicament|cachet|comprim[ée]|g[ée]lule|prise|ordonnance)|"
    # intention de modifier un traitement (objet libre : nom de médicament)
    r"(?:puis-je|je peux|est-ce que je peux|dois-je|j'aimerais|je voudrais)\s+"
    r"(?:arr[êe]ter|stopper|doubler|augmenter|r[ée]duire|diminuer)"
    r")",
    re.IGNORECASE,
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
        if hasattr(callback_context, 'state'):
            callback_context.state['guardrail_hit'] = 'medical_emergency'
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
        if hasattr(callback_context, 'state'):
            callback_context.state['guardrail_hit'] = 'medical_advice'
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

FINANCIAL_ADVICE_PATTERN = re.compile(
    r"(quelle mutuelle.*(dois-je|choisir|prendre|recommand|conseill)|dois-je (contester|changer|résilier|prendre)|est-ce que je devrais|vaut-il mieux|optimiser (mes impôts|ma fiscalité)|quel(?:le)? (contrat|complémentaire).*(choisir|prendre)|réduire mes impôts|conseil(?:le|s)? financ)",
    re.IGNORECASE
)

def financial_guardrail(callback_context, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """
    Before-model callback to intercept financial, tax, and legal advice requests.
    Factual queries pass through.
    """
    last_user_text = _last_user_text(llm_request)
    
    if not last_user_text:
        return None
        
    if FINANCIAL_ADVICE_PATTERN.search(last_user_text):
        if hasattr(callback_context, 'state'):
            callback_context.state['guardrail_hit'] = 'financial_advice'
            
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="« Je ne suis pas conseiller financier ni juridique : je peux vous présenter vos chiffres (totaux, reste à charge, remboursements en attente), mais je ne peux ni vous recommander une mutuelle, ni vous dire de contester, ni optimiser votre fiscalité. Pour ces décisions, rapprochez-vous de votre mutuelle, de votre caisse d'Assurance Maladie (Ameli) ou d'un conseiller. Je peux en revanche vous sortir le détail des remboursements en attente — vous voulez ? »"
                    )
                ]
            )
        )
        
    return None
def before_model(callback_context, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """Runs all guardrails in sequence and returns the first interception."""
    med = medical_guardrail(callback_context, llm_request)
    if med:
        return med
    return financial_guardrail(callback_context, llm_request)
