from pathlib import Path
from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

def build_runtime(repo_root: Path):
    loader = NeuralFrameworkLoader(repo_root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain, dt=0.01)
    return runtime
