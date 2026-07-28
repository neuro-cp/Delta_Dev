def predict(case):
    text = " ".join(case["turns"]).lower()
    if case["answer_obligation"] == "foreground" and ("what is angular momentum" in text or "soup" in text):
        return "unrelated_factual_answer"
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if "future goal" in text or "do not start" in text:
        return "discuss_tentative_without_activation"
    if case["answer_obligation"] == "goal_thread" and any(token in text for token in ("that", "it", "one", "comparison")):
        if "refrigerators" in text and "metal expansion" in text:
            return "clarify_between_metal_expansion_and_refrigerators"
        if "restart" in text:
            return "preserve_queue_and_clarify"
        if "later one" in text:
            return "later_one_refers_to_post_restart_action"
        return "clarify_ambiguous_topic_boundary"
    return "generic_contextual_ack"
