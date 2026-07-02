# Phase B.1 Activation Waste

| Case | Concept | Classification | Neighbor Utility |
| --- | --- | --- | --- |
| gps_drift_retrieval | `gps-satellite-geometry` | `USED` | `Core Evidence` |
| gps_drift_retrieval | `gps-multipath` | `USED` | `Core Evidence` |
| gps_drift_retrieval | `snow-plow-positioning` | `IGNORED` | `Noise` |
| gps_drift_retrieval | `gps-atmospheric-delay` | `USED` | `Core Evidence` |
| snowstorm_grounded_planning | `snow-plow-positioning` | `USED` | `Core Evidence` |
| snowstorm_grounded_planning | `shelter-capacity` | `USED` | `Core Evidence` |
| snowstorm_grounded_planning | `emergency-route-priority` | `USED` | `Core Evidence` |
| snowstorm_grounded_planning | `resource-allocation-triage` | `IGNORED` | `Useful Neighbor` |
| snowstorm_grounded_planning | `risk-likelihood-impact` | `IGNORED` | `Useful Neighbor` |
| salt_tradeoff_conflict | `salt-traction-benefit` | `USED` | `Core Evidence` |
| salt_tradeoff_conflict | `salt-environmental-cost` | `USED` | `Core Evidence` |
| salt_tradeoff_conflict | `snow-plow-positioning` | `IGNORED` | `Noise` |
| salt_tradeoff_conflict | `shelter-capacity` | `IGNORED` | `Noise` |
| salt_tradeoff_conflict | `emergency-route-priority` | `IGNORED` | `Noise` |
| salt_tradeoff_conflict | `resource-allocation-triage` | `IGNORED` | `Noise` |
| resource_allocation_calibration | `resource-allocation-triage` | `USED` | `Core Evidence` |
| resource_allocation_calibration | `emergency-route-priority` | `SUPPORTED` | `Useful Neighbor` |
| resource_allocation_calibration | `snow-plow-positioning` | `IGNORED` | `Noise` |
| resource_allocation_calibration | `risk-likelihood-impact` | `USED` | `Core Evidence` |
| resource_allocation_calibration | `shelter-capacity` | `IGNORED` | `Useful Neighbor` |
| resource_allocation_calibration | `salt-traction-benefit` | `IGNORED` | `Noise` |
| repeat_snowstorm_stability | `snow-plow-positioning` | `USED` | `Core Evidence` |
| repeat_snowstorm_stability | `shelter-capacity` | `USED` | `Core Evidence` |
| repeat_snowstorm_stability | `emergency-route-priority` | `USED` | `Core Evidence` |
| repeat_snowstorm_stability | `resource-allocation-triage` | `IGNORED` | `Useful Neighbor` |
| repeat_snowstorm_stability | `risk-likelihood-impact` | `IGNORED` | `Useful Neighbor` |
