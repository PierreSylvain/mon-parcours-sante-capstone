from .store import HealthStore

def health_profile_get() -> dict:
    """
    Retrieve the full health profile for the user, including conditions, allergies, and current medications.
    This is a read-only operation.
    """
    store = HealthStore()
    try:
        return store.get_profile()
    finally:
        store.close()


def search_documents(query: str) -> dict:
    """
    Search indexed medical documents and lab results based on a keyword query.
    IMPORTANT: surface only, never interpret. You must only present the exact values found 
    in the document. Never judge or state whether a value is normal, abnormal, too high, or too low.
    """
    store = HealthStore()
    try:
        results = store.search_documents(query)
        return {"results": results}
    finally:
        store.close()


def health_profile_update(field: str, value: str, confirmed: bool = False) -> dict:
    """
    Update a specific field in the health profile.
    This is a sensitive, side-effecting operation. It requires confirmed=True. 
    You must explicitly describe the exact action to the user and wait for their confirmation 
    before calling this tool with confirmed=True.
    """
    if not confirmed:
        return {"error": "Action unconfirmed. Please describe the update to the user and wait for their approval before setting confirmed=True."}
    
    store = HealthStore()
    try:
        store.update_profile(field, value)
        return {"status": "success", "message": f"Successfully updated {field}."}
    except ValueError as ve:
        return {"error": str(ve)}
    except Exception as e:
        return {"error": f"Internal error: {str(e)}"}
    finally:
        store.close()
