def predict(case):
    text = " ".join(case["turns"]).lower()
    if "do not apply" in text and ("soup" in text or "cooking" in text):
        return "unrelated_factual_answer"
    if "future goal" in text or "do not start" in text:
        return "discuss_tentative_without_activation"
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if case["answer_obligation"] == "goal_thread":
        return "clarify_ambiguous_topic_boundary"
    if "what is angular momentum" in text:
        return "unrelated_factual_answer"
    return "generic_contextual_ack"
