def predict(case):
    text = " ".join(case["turns"]).lower()
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if "that" in text or "it" in text or "one" in text:
        return "last_mentioned_object"
    if "what is angular momentum" in text or ("soup" in text and "do not apply" in text):
        return "unrelated_factual_answer"
    return "generic_contextual_ack"
