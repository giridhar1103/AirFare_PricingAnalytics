# Claim and source ledger

Research checked on 2026-09-02. Primary sources are preferred for data contracts and implementation choices.

| Claim | Source | Evidence strength | Implementation consequence |
| --- | --- | --- | --- |
| DB1B used a quarterly 10% ticket sample before July 2025. | [BTS Origin and Destination Survey Data](https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data) | High, official | Use DB1B as a historical quarterly model source. |
| DB1C uses a monthly 40% sample effective July 2025. | [BTS Origin and Destination Survey Data](https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data) | High, official | Keep a separate post-transition monitoring layer and do not naively concatenate. |
| The DB1C market file contains direction, service carriers, fare, origin, and destination. | [BTS DB1C Market](https://www.bts.gov/topics/airlines-and-airports/origin-and-destination-survey-data-market) | High, official | Add current monthly market monitoring after the historical product is stable. |
| T-100 contains monthly traffic and capacity and does not contain carrier financial information. | [BTS T-100 database profile](https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EEE) | High, official | Use it for passengers, seats, and load factor, not profit or reported revenue. |
| DOT ticket fares include ticket value and taxes but exclude optional services such as baggage. | [BTS Air Fares](https://www.bts.gov/air-fares) | High, official | Label fare and revenue proxy precisely and exclude ancillary claims. |
| DOT identifiers are more stable than display codes over long periods. | [BTS T-100 terms](https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EEE) | High, official | Use airport ID and airline ID for canonical joins. |
| Two-way panel fixed effects can absorb entity and time effects. | [linearmodels PanelOLS](https://bashtage.github.io/linearmodels/panel/panel/linearmodels.panel.model.PanelOLS.html) | High, implementation documentation | Use route-carrier and calendar effects in the interpretive model. |
| Airline fare is endogenous to demand and ignoring it can bias elasticity. | [Mumbower, Garrow, and Higgins, 2014](https://doi.org/10.1016/j.tra.2014.05.003) | High, peer-reviewed study | Use observational language and reserve causal claims for a defensible identification design. |
| Time-ordered validation prevents training on future observations and evaluating on the past. | [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | High, implementation documentation | Use expanding-window model evaluation. |
| Histogram gradient boosting is appropriate for larger tabular datasets and supports missing values. | [scikit-learn HistGradientBoostingRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html) | High, implementation documentation | Use it as the ML challenger after a transparent baseline. |
| Claude tool definitions can enforce a JSON schema and force a named tool call. | [Anthropic tool-use documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) | High, official | Restrict the AI brief to approved fields and evidence keys. |
| LLM evaluation criteria should be specific, measurable, and tested against representative edge cases. | [Anthropic evaluation documentation](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) | High, official | Grade recommendation policy, grounding, prohibited claims, schema, and latency. |
| A useful dashboard provides a quick overview and coordinated drill-down without overwhelming the user. | [Observable dashboard guidance](https://observablehq.com/blog/seven-ways-design-better-dashboards) | Medium, expert guidance | Lead with an action queue and keep filters compact. |
| Dashboard hierarchy should put important content first and use linked views and whitespace. | [IBM Carbon dashboard guidance](https://carbondesignsystem.com/data-visualization/dashboards/) | Medium, design-system guidance | Use sparse KPIs, strong hierarchy, consistent colors, and linked evidence. |

## Open evidence gaps

| Gap | Current status | Release impact |
| --- | --- | --- |
| Stable T-100 download mechanism | Resolved through the official field-selection form | The pipeline replays official form tokens and records the selected field contract. |
| Join coverage between DB1B and T-100 | 99.78% passenger-weighted in the 2024 Q4 direct-route spike when using operating carrier | V1 further restricts to aligned reporting, ticketing, and operating carrier records. |
| Defensible instrument for causal fare elasticity | Not established | All initial elasticity language remains observational. |
| Route-level cost and ancillary revenue | Not available in selected public sources | No historical profit optimization. Optional cost stays user supplied. |
| Prediction interval calibration across thin markets | Nominal 80% interval achieved 74.82% coverage on the untouched 2025 H1 evaluation period | Report the miss, keep the interval descriptive, and add segment-level calibration before operational use. |
