from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from observer.observer import BrainObserver

# --------------------------------------------------
# Resolve repo root (directory containing this file)
# --------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent

loader = NeuralFrameworkLoader(REPO_ROOT)

loader.load_neuron_bases()
loader.load_regions()
loader.load_profiles()

brain = loader.compile(
    expression_profile="human_default",
    state_profile="awake",
    compound_profile="experimental_compound",
)

observer = BrainObserver(brain)
observer.summary()
observer.region_details()
observer.connectivity_summary()
observer.validate_references()
