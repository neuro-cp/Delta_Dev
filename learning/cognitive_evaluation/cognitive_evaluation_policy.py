class CognitiveEvaluationPolicy:
    '''
    Pure integration policy.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def integrate(
        self,
        proposals,
        bias_scores,
        selected_ids,
        promotable_ids,
        delta_surface,
    ):
        stability_index = len(promotable_ids) + sum(delta_surface.values())
        return {
            "proposal_count": len(proposals),
            "selected_count": len(selected_ids),
            "promotable_count": len(promotable_ids),
            "delta_surface": delta_surface,
            "stability_index": stability_index,
        }
