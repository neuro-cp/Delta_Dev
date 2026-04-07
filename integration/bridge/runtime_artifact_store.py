class RuntimeArtifactStore:

    def __init__(self):
        self._store = {}

    def put(self, semantic_id: str, artifact: dict):
        self._store[semantic_id] = artifact

    def get(self, semantic_id: str):
        return self._store.get(semantic_id)

    def all(self):
        return dict(self._store)
