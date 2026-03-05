class ExecutionPreviewPolicy:
    '''
    Pure execution preview selection policy.
    '''

    def compute_surface(self, proposals, promotable_ids):
        surface = {}
        for p in proposals:
            if p.proposal_id in promotable_ids:
                surface[p.proposal_id] = len(p.deltas)
        return surface
