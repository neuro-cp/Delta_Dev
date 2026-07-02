# Runtime V1.1 Attention Score Distribution

| Concept | Score | Attention Class | Contribution | Attended | Case |
| --- | ---: | --- | --- | ---: | --- |
| `gps-multipath` | `0.5681` | `Supporting` | `Core` | `True` | gps_drift_retrieval |
| `gps-satellite-geometry` | `0.535` | `Supporting` | `Core` | `True` | gps_drift_retrieval |
| `gps-atmospheric-delay` | `0.2875` | `Supporting` | `Core` | `True` | gps_drift_retrieval |
| `snow-plow-positioning` | `0.2329` | `Peripheral` | `Noise` | `False` | gps_drift_retrieval |
| `snow-plow-positioning` | `0.797` | `Core` | `Core` | `True` | snowstorm_grounded_planning |
| `shelter-capacity` | `0.4091` | `Supporting` | `Core` | `True` | snowstorm_grounded_planning |
| `emergency-route-priority` | `0.3771` | `Supporting` | `Core` | `True` | snowstorm_grounded_planning |
| `resource-allocation-triage` | `0.1995` | `Discarded` | `Peripheral` | `False` | snowstorm_grounded_planning |
| `risk-likelihood-impact` | `0.1972` | `Discarded` | `Peripheral` | `False` | snowstorm_grounded_planning |
| `salt-traction-benefit` | `0.7583` | `Core` | `Core` | `True` | salt_tradeoff_conflict |
| `salt-environmental-cost` | `0.5503` | `Core` | `Core` | `True` | salt_tradeoff_conflict |
| `snow-plow-positioning` | `0.287` | `Peripheral` | `Noise` | `False` | salt_tradeoff_conflict |
| `shelter-capacity` | `0.2547` | `Peripheral` | `Noise` | `False` | salt_tradeoff_conflict |
| `emergency-route-priority` | `0.2331` | `Peripheral` | `Noise` | `False` | salt_tradeoff_conflict |
| `resource-allocation-triage` | `0.1987` | `Discarded` | `Noise` | `False` | salt_tradeoff_conflict |
| `resource-allocation-triage` | `0.6871` | `Core` | `Core` | `True` | resource_allocation_calibration |
| `risk-likelihood-impact` | `0.4269` | `Core` | `Core` | `True` | resource_allocation_calibration |
| `emergency-route-priority` | `0.3011` | `Supporting` | `Supporting` | `True` | resource_allocation_calibration |
| `snow-plow-positioning` | `0.2014` | `Discarded` | `Noise` | `False` | resource_allocation_calibration |
| `shelter-capacity` | `0.1955` | `Discarded` | `Peripheral` | `False` | resource_allocation_calibration |
| `salt-traction-benefit` | `0.1897` | `Discarded` | `Noise` | `False` | resource_allocation_calibration |
| `snow-plow-positioning` | `0.797` | `Core` | `Core` | `True` | repeat_snowstorm_stability |
| `shelter-capacity` | `0.4091` | `Supporting` | `Core` | `True` | repeat_snowstorm_stability |
| `emergency-route-priority` | `0.3771` | `Supporting` | `Core` | `True` | repeat_snowstorm_stability |
| `resource-allocation-triage` | `0.1995` | `Discarded` | `Peripheral` | `False` | repeat_snowstorm_stability |
| `risk-likelihood-impact` | `0.1972` | `Discarded` | `Peripheral` | `False` | repeat_snowstorm_stability |

## Summary

- scored concepts: `26`
- attended concepts: `14`
- noise concepts attended: `0`
