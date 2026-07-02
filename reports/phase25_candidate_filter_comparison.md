# Phase 25 Candidate Filter Comparison

## Current Rejection Reasons

- `missing_predicate_signal`: `32`
- `prompt_artifact`: `20`
- `missing_reusable_signal`: `18`
- `prompt_scaffolding`: `18`
- `missing_referent`: `8`
- `incomplete_proposition`: `6`
- `too_long`: `4`

## Legacy-Accepted Candidates Now Rejected

- `Evidence that would revise the belief could include a confirmation of supplier issues or a significant change in the production schedule` reasons `['missing_predicate_signal', 'prompt_artifact']`
- `Evidence that would revise the belief could include a confirmation of supplier issues or a significant change in the production schedule.` reasons `['missing_predicate_signal', 'prompt_artifact']`
- `If the initial orders fail to materialize, the next operational risk could be a supply chain disruption` reasons `['missing_predicate_signal']`
- `If the initial orders fail to materialize, the next operational risk could be a supply chain disruption.` reasons `['missing_predicate_signal']`
- `Evidence that would require reallocation includes a significant increase in the number of individuals in the new priority group seeking shelter, or a decrease in the availability of resources for existing groups` reasons `['prompt_artifact']`
- `Evidence that would require reallocation includes a significant increase in the number of individuals in the new priority group seeking shelter, or a decrease in the availability of resources for existing groups.` reasons `['prompt_artifact']`
- `Predicting the failure mode, if the capacity is not adjusted, it could lead to a shortfall in resources for the new priority group, potentially exacerbating the crisis` reasons `['prompt_scaffolding']`
- `Predicting the failure mode, if the capacity is not adjusted, it could lead to a shortfall in resources for the new priority group, potentially exacerbating the crisis.` reasons `['prompt_scaffolding']`
- `This process should be continuously monitored, and reallocation decisions should be based on updated capacity reports and real-time data to ensure the most effective use of resources` reasons `['missing_referent']`
- `This process should be continuously monitored, and reallocation decisions should be based on updated capacity reports and real-time data to ensure the most effective use of resources.` reasons `['missing_referent']`
- `Uncertainty remains, as external factors such as economic conditions and additional emergencies could impact the availability and distribution of resources, necessitating ongoing adjustments and reallocations` reasons `['missing_predicate_signal']`
- `Uncertainty remains, as external factors such as economic conditions and additional emergencies could impact the availability and distribution of resources, necessitating ongoing adjustments and reallocations.` reasons `['missing_predicate_signal']`
- `Evidence that would confirm this prediction includes reports of snow accumulation or lack of snow removal in the downstream area, as well as traffic congestion or delays in the alternative route` reasons `['prompt_scaffolding', 'prompt_artifact']`
- `Evidence that would confirm this prediction includes reports of snow accumulation or lack of snow removal in the downstream area, as well as traffic congestion or delays in the alternative route.` reasons `['prompt_scaffolding', 'prompt_artifact']`
- `Evidence that would falsify this prediction would be if the snow removal efforts were successful in the downstream area, despite the bridge closure, or if there was no significant traffic congestion or delays in the alternative route` reasons `['prompt_scaffolding', 'prompt_artifact']`
- `Evidence that would falsify this prediction would be if the snow removal efforts were successful in the downstream area, despite the bridge closure, or if there was no significant traffic congestion or delays in the alternative route.` reasons `['prompt_scaffolding', 'prompt_artifact']`
- `This prediction is based on the assumption that the snow removal trucks will have to find an alternative route, which may lead to increased traffic and delays, potentially causing the snow removal efforts to fail in the area downstream` reasons `['prompt_scaffolding']`
- `This prediction is based on the assumption that the snow removal trucks will have to find an alternative route, which may lead to increased traffic and delays, potentially causing the snow removal efforts to fail in the area downstream.` reasons `['prompt_scaffolding']`
- `This prediction is uncertain due to the unpredictability of traffic patterns and the potential for alternative routes to be found or used` reasons `['prompt_scaffolding']`
- `This prediction is uncertain due to the unpredictability of traffic patterns and the potential for alternative routes to be found or used.` reasons `['prompt_scaffolding']`
- `The uncertainty in this scenario lies in the accuracy of the predictive model and the potential for unanticipated events to impact the homeless population` reasons `['missing_predicate_signal']`
- `The uncertainty in this scenario lies in the accuracy of the predictive model and the potential for unanticipated events to impact the homeless population.` reasons `['missing_predicate_signal']`
- `Evidence that would break the chain includes the supplier resolving the delay or the work being completed before the inspection window expires` reasons `['prompt_artifact']`
- `Evidence that would break the chain includes the supplier resolving the delay or the work being completed before the inspection window expires.` reasons `['prompt_artifact']`
- `The cycle can be completed by predicting that if the supplier consistently delivers on time, the need for resequencing and inspection window expirations will decrease, thus reducing project delays` reasons `['prompt_scaffolding']`
- `The cycle can be completed by predicting that if the supplier consistently delivers on time, the need for resequencing and inspection window expirations will decrease, thus reducing project delays.` reasons `['prompt_scaffolding']`
- `This prediction can be tested by monitoring the supplier's delivery performance over time` reasons `['prompt_scaffolding']`
- `This prediction can be tested by monitoring the supplier's delivery performance over time.` reasons `['prompt_scaffolding']`
- `Uncertainty in the answer arises from unpredictable supplier performance and the complexity of project scheduling` reasons `['missing_predicate_signal']`
- `Uncertainty in the answer arises from unpredictable supplier performance and the complexity of project scheduling.` reasons `['missing_predicate_signal']`
