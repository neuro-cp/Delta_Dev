# Runtime V1.2 Activation Trace

## planning_failed_assumption

- category: `planning`
- baseline attention count: `2`
- wide attention count: `4`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `aa6c1ba8-9c57-474c-afa5-7383a4733cae` | `reached_working_memory` | `2` | `True` | `False` |
| `76120648-7522-4025-8176-5e5fb199c687` | `reached_working_memory` | `1` | `True` | `True` |
| `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `retrieved_but_pruned_by_attention` | `3` | `False` | `False` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `76120648-7522-4025-8176-5e5fb199c687` | `expected` | `0.4734` | `True` |
| `2` | `aa6c1ba8-9c57-474c-afa5-7383a4733cae` | `expected` | `0.4512` | `True` |
| `3` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `expected` | `0.4476` | `False` |
| `4` | `4b01b020-00b1-4d40-9422-aba2288625d4` | `candidate_noise` | `0.3916` | `False` |
| `5` | `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` | `candidate_noise` | `0.3589` | `False` |
| `6` | `06b4d255-58d5-49f5-adec-43426ce0d09b` | `candidate_noise` | `0.3579` | `False` |
| `7` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `candidate_noise` | `0.3574` | `False` |
| `8` | `0586e881-099d-4866-a1cf-4ed571139c70` | `candidate_noise` | `0.355` | `False` |
| `9` | `076c39f2-9cf5-45c7-ac1b-e379da875926` | `candidate_noise` | `0.3539` | `False` |
| `10` | `3a9f7658-b877-4532-b9c8-1a79b360c5d4` | `candidate_noise` | `0.3519` | `False` |
| `11` | `5894bef8-228f-4466-9152-cf7dfec7fa4e` | `candidate_noise` | `0.351` | `False` |
| `12` | `e6f9a5a0-a724-48c4-ba2b-5d279555a25e` | `candidate_noise` | `0.3465` | `False` |
| `13` | `1ecc06d3-3c05-4224-9d30-3111a0533f50` | `candidate_noise` | `0.3422` | `False` |
| `14` | `1ce7238b-68bb-4411-ae90-044239d9c0cd` | `candidate_noise` | `0.3419` | `False` |
| `15` | `bc2086b3-87d9-479a-935f-805fe7d523c7` | `candidate_noise` | `0.3412` | `False` |
| `16` | `65e4ca55-7169-4ee4-b388-a6927043a92d` | `candidate_noise` | `0.3401` | `False` |
| `17` | `636f4a37-3296-4858-be5d-99d1988bc3d6` | `candidate_noise` | `0.34` | `False` |
| `18` | `21b090dc-e87c-4a05-8db1-b06e0b62bf42` | `candidate_noise` | `0.3399` | `False` |
| `19` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `candidate_noise` | `0.3396` | `False` |
| `20` | `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `candidate_noise` | `0.3395` | `False` |

## causal_industrial_failure

- category: `causal_reasoning`
- baseline attention count: `8`
- wide attention count: `21`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `reached_working_memory` | `2` | `True` | `True` |
| `ce828fd3-8630-418e-857b-65904d4fb2ed` | `reached_working_memory` | `1` | `True` | `True` |
| `45d9686a-fded-4818-ae8e-47007cd33529` | `retrieved_but_ranked_too_low` | `37` | `False` | `True` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `ce828fd3-8630-418e-857b-65904d4fb2ed` | `expected` | `0.3965` | `True` |
| `2` | `e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `expected` | `0.3965` | `True` |
| `3` | `183718d2-9612-4057-94b7-4ad8fd896278` | `candidate_noise` | `0.3571` | `True` |
| `4` | `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` | `candidate_noise` | `0.3568` | `True` |
| `5` | `b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` | `candidate_noise` | `0.3541` | `True` |
| `6` | `9d5b7363-5857-4091-8449-9374d6b4b68f` | `candidate_noise` | `0.354` | `True` |
| `7` | `0fb23c0b-b877-4cf2-a66d-94d927b77542` | `candidate_noise` | `0.352` | `True` |
| `8` | `cc6cc333-f8f7-450a-b8a2-0543ae0276fb` | `candidate_noise` | `0.3478` | `True` |
| `9` | `65e4ca55-7169-4ee4-b388-a6927043a92d` | `candidate_noise` | `0.3452` | `False` |
| `10` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `candidate_noise` | `0.3452` | `False` |
| `11` | `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `candidate_noise` | `0.3435` | `False` |
| `12` | `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `candidate_noise` | `0.3433` | `False` |
| `13` | `89b85467-0655-47d3-9a0c-89da364cd487` | `candidate_noise` | `0.3422` | `False` |
| `14` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `candidate_noise` | `0.3421` | `False` |
| `15` | `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `candidate_noise` | `0.3409` | `False` |
| `16` | `b85b0a01-9c3f-4c42-a26a-01741c84682c` | `candidate_noise` | `0.3393` | `False` |
| `17` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `candidate_noise` | `0.339` | `False` |
| `18` | `0586e881-099d-4866-a1cf-4ed571139c70` | `candidate_noise` | `0.3382` | `False` |
| `19` | `48c454a5-6362-4533-a53e-b6d6f9c19a00` | `candidate_noise` | `0.3381` | `False` |
| `20` | `06c7ab71-397c-4754-984d-48cbdcec18bd` | `candidate_noise` | `0.3381` | `False` |

## contradictory_evidence

- category: `contradiction_handling`
- baseline attention count: `1`
- wide attention count: `2`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `8430c4bb-9070-4e98-aaa6-90404f2da021` | `retrieved_but_pruned_by_attention` | `2` | `False` | `False` |
| `0249542c-c698-4a93-805c-8f83c40f8c34` | `retrieved_but_pruned_by_attention` | `7` | `False` | `False` |
| `a1e249bd-67dc-4056-9120-89380cbe5928` | `retrieved_but_pruned_by_attention` | `3` | `False` | `False` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `1450511f-f0dd-4e2f-8598-1cf1511a2811` | `candidate_noise` | `0.422` | `False` |
| `2` | `8430c4bb-9070-4e98-aaa6-90404f2da021` | `expected` | `0.4072` | `False` |
| `3` | `a1e249bd-67dc-4056-9120-89380cbe5928` | `expected` | `0.384` | `False` |
| `4` | `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `candidate_noise` | `0.3724` | `False` |
| `5` | `ef940f21-c49c-41f8-b86e-12a02a0f37f6` | `candidate_noise` | `0.372` | `True` |
| `6` | `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `candidate_noise` | `0.3671` | `False` |
| `7` | `0249542c-c698-4a93-805c-8f83c40f8c34` | `expected` | `0.3635` | `False` |
| `8` | `800c60da-06fc-41b6-b259-b4f98e08cd79` | `candidate_noise` | `0.3635` | `False` |
| `9` | `fb9f365a-95c7-4757-92f6-e55f4580c57b` | `candidate_noise` | `0.3624` | `False` |
| `10` | `5ff60e9f-a309-4902-aaee-2611b5743833` | `useful_neighbor` | `0.3617` | `False` |
| `11` | `011d4f3b-e7d2-4865-9fe3-b269795e07cb` | `candidate_noise` | `0.3615` | `False` |
| `12` | `8cc42686-7fc3-4e08-b295-515b26899606` | `candidate_noise` | `0.3597` | `False` |
| `13` | `0586e881-099d-4866-a1cf-4ed571139c70` | `candidate_noise` | `0.3593` | `False` |
| `14` | `1ecc06d3-3c05-4224-9d30-3111a0533f50` | `candidate_noise` | `0.3541` | `False` |
| `15` | `41cc8fe7-a7a2-4cd9-8e17-4c5336b8ac28` | `candidate_noise` | `0.3529` | `False` |
| `16` | `65e4ca55-7169-4ee4-b388-a6927043a92d` | `candidate_noise` | `0.3437` | `False` |
| `17` | `3cc55e56-cb07-4085-a786-afd705a58770` | `candidate_noise` | `0.3437` | `False` |
| `18` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `candidate_noise` | `0.3436` | `False` |
| `19` | `4d6d84dd-1073-413a-9d3f-6692daef36c7` | `candidate_noise` | `0.3433` | `False` |
| `20` | `4b01b020-00b1-4d40-9422-aba2288625d4` | `candidate_noise` | `0.3428` | `False` |

## resource_allocation_shelters

- category: `resource_allocation`
- baseline attention count: `1`
- wide attention count: `35`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `380b765f-ffa2-4296-a66e-527bacb75a64` | `retrieved_but_ranked_too_low` | `11` | `False` | `True` |
| `68ae35cf-2be5-4dfc-bdd0-b179682163ad` | `retrieved_but_ranked_too_low` | `18` | `False` | `True` |
| `df85054d-ffcd-4c50-8118-ecb512271eaf` | `retrieved_but_pruned_by_attention` | `1` | `False` | `True` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `expected` | `0.4151` | `False` |
| `2` | `6b704bd9-ecc5-4066-b351-a4eda0ba5c8d` | `candidate_noise` | `0.4081` | `False` |
| `3` | `bc2086b3-87d9-479a-935f-805fe7d523c7` | `candidate_noise` | `0.4041` | `False` |
| `4` | `f567a38f-be7c-4783-972f-d82e8fb2e36f` | `candidate_noise` | `0.3933` | `True` |
| `5` | `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d` | `candidate_noise` | `0.3869` | `False` |
| `6` | `76120648-7522-4025-8176-5e5fb199c687` | `candidate_noise` | `0.3827` | `False` |
| `7` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `candidate_noise` | `0.3728` | `False` |
| `8` | `7e5bf5f6-780a-4ba7-85c1-b514b848a162` | `candidate_noise` | `0.3684` | `False` |
| `9` | `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `candidate_noise` | `0.3661` | `False` |
| `10` | `97190912-de2a-4fa6-b283-a9a1baafb53c` | `candidate_noise` | `0.3645` | `False` |
| `11` | `380b765f-ffa2-4296-a66e-527bacb75a64` | `expected` | `0.3615` | `False` |
| `12` | `1be89cfb-2a02-4183-8054-00c0186f6271` | `candidate_noise` | `0.3609` | `False` |
| `13` | `7a4b823b-f9df-4e77-b3b7-744ee834741c` | `candidate_noise` | `0.3595` | `False` |
| `14` | `0586e881-099d-4866-a1cf-4ed571139c70` | `candidate_noise` | `0.3578` | `False` |
| `15` | `b887cc74-2628-4fbd-8890-38792ed54876` | `candidate_noise` | `0.3574` | `False` |
| `16` | `9fafbb71-ef17-4c05-8764-3577ae15ef59` | `candidate_noise` | `0.3564` | `False` |
| `17` | `d45f3c3d-86fa-4ee5-a75a-fd988642038b` | `candidate_noise` | `0.356` | `False` |
| `18` | `68ae35cf-2be5-4dfc-bdd0-b179682163ad` | `expected` | `0.3557` | `False` |
| `19` | `98154cbb-a296-4bc9-87e5-83e1e6fbd245` | `candidate_noise` | `0.3539` | `False` |
| `20` | `88b2e857-6d3d-45f0-be3f-d01cbc1e2023` | `candidate_noise` | `0.3519` | `False` |

## risk_uncertainty_planning

- category: `risk_assessment`
- baseline attention count: `1`
- wide attention count: `32`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `52ca9d0c-f68c-429a-afe8-285bf2ceb996` | `not_retrieved` | `None` | `False` | `False` |
| `4b01b020-00b1-4d40-9422-aba2288625d4` | `retrieved_but_pruned_by_attention` | `2` | `False` | `True` |
| `98154cbb-a296-4bc9-87e5-83e1e6fbd245` | `retrieved_but_pruned_by_attention` | `4` | `False` | `True` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `candidate_noise` | `0.3997` | `False` |
| `2` | `4b01b020-00b1-4d40-9422-aba2288625d4` | `expected` | `0.3991` | `False` |
| `3` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `candidate_noise` | `0.3971` | `False` |
| `4` | `98154cbb-a296-4bc9-87e5-83e1e6fbd245` | `expected` | `0.3958` | `False` |
| `5` | `ad599dfe-ddbd-4689-ad43-4dc8249fdab1` | `candidate_noise` | `0.3917` | `False` |
| `6` | `6457f783-957c-4e69-95bb-bacf18f6fd32` | `candidate_noise` | `0.385` | `False` |
| `7` | `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` | `candidate_noise` | `0.3842` | `True` |
| `8` | `0e3fdeda-0d38-40ad-993c-480703e55f9e` | `candidate_noise` | `0.3835` | `False` |
| `9` | `7b1fd455-c6f7-4dcf-a109-11fc3c89262f` | `candidate_noise` | `0.3809` | `False` |
| `10` | `fec7285c-8ebf-45ba-8197-911a515e4e0b` | `candidate_noise` | `0.3773` | `False` |
| `11` | `16ce389d-1c43-4d03-94e3-f16ad8259cbc` | `candidate_noise` | `0.3758` | `False` |
| `12` | `0ada7d73-b196-40cc-b6bb-031ac1eaa8cd` | `candidate_noise` | `0.3756` | `False` |
| `13` | `636f4a37-3296-4858-be5d-99d1988bc3d6` | `candidate_noise` | `0.3749` | `False` |
| `14` | `77b37207-0a4f-4af1-a029-1ead85cc56ce` | `candidate_noise` | `0.3742` | `False` |
| `15` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `candidate_noise` | `0.3725` | `False` |
| `16` | `65e4ca55-7169-4ee4-b388-a6927043a92d` | `candidate_noise` | `0.3712` | `False` |
| `17` | `35f7296f-3e5d-4372-8819-a3e769cde611` | `candidate_noise` | `0.3696` | `False` |
| `18` | `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `candidate_noise` | `0.3695` | `False` |
| `19` | `4ed48c4d-2273-4fd5-be65-4452627810b5` | `candidate_noise` | `0.3687` | `False` |
| `20` | `89b85467-0655-47d3-9a0c-89da364cd487` | `candidate_noise` | `0.3682` | `False` |

## policy_audit_conflict

- category: `conflicting_evidence`
- baseline attention count: `1`
- wide attention count: `4`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `acaca659-aee5-4cef-9c4c-5a2281c1a9ef` | `reached_working_memory` | `1` | `True` | `True` |
| `1b324e50-0b5b-43b4-befd-f4e6e25d5e01` | `retrieved_but_ranked_too_low` | `37` | `False` | `True` |
| `3cc55e56-cb07-4085-a786-afd705a58770` | `retrieved_but_ranked_too_low` | `22` | `False` | `True` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `acaca659-aee5-4cef-9c4c-5a2281c1a9ef` | `expected` | `0.3979` | `True` |
| `2` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `candidate_noise` | `0.3757` | `False` |
| `3` | `65e4ca55-7169-4ee4-b388-a6927043a92d` | `candidate_noise` | `0.3741` | `False` |
| `4` | `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `candidate_noise` | `0.3724` | `False` |
| `5` | `b85b0a01-9c3f-4c42-a26a-01741c84682c` | `candidate_noise` | `0.3716` | `False` |
| `6` | `89b85467-0655-47d3-9a0c-89da364cd487` | `candidate_noise` | `0.3711` | `False` |
| `7` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `candidate_noise` | `0.3696` | `False` |
| `8` | `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `candidate_noise` | `0.3683` | `False` |
| `9` | `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `candidate_noise` | `0.3671` | `False` |
| `10` | `06b4d255-58d5-49f5-adec-43426ce0d09b` | `candidate_noise` | `0.3666` | `False` |
| `11` | `19c469f2-b11b-445a-9b0c-fcd2ee80bd1f` | `candidate_noise` | `0.3636` | `False` |
| `12` | `0e3fdeda-0d38-40ad-993c-480703e55f9e` | `candidate_noise` | `0.3606` | `False` |
| `13` | `b887cc74-2628-4fbd-8890-38792ed54876` | `candidate_noise` | `0.3596` | `False` |
| `14` | `0586e881-099d-4866-a1cf-4ed571139c70` | `candidate_noise` | `0.3593` | `False` |
| `15` | `a61cdfc3-a845-4b83-94b6-cf93ff6b0a08` | `candidate_noise` | `0.3573` | `False` |
| `16` | `5894bef8-228f-4466-9152-cf7dfec7fa4e` | `candidate_noise` | `0.3565` | `False` |
| `17` | `3a9f7658-b877-4532-b9c8-1a79b360c5d4` | `candidate_noise` | `0.3557` | `False` |
| `18` | `0ada7d73-b196-40cc-b6bb-031ac1eaa8cd` | `candidate_noise` | `0.3553` | `False` |
| `19` | `77b37207-0a4f-4af1-a029-1ead85cc56ce` | `candidate_noise` | `0.3453` | `False` |
| `20` | `3eb435c5-bca6-45e3-9dd4-9dab5289ad38` | `candidate_noise` | `0.3444` | `False` |

## multi_step_failure_revision

- category: `multi_step_reasoning`
- baseline attention count: `4`
- wide attention count: `2`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `4b01b020-00b1-4d40-9422-aba2288625d4` | `reached_working_memory` | `1` | `True` | `True` |
| `076c39f2-9cf5-45c7-ac1b-e379da875926` | `retrieved_but_pruned_by_attention` | `6` | `False` | `False` |
| `e6f9a5a0-a724-48c4-ba2b-5d279555a25e` | `retrieved_but_ranked_too_low` | `40` | `False` | `False` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `4b01b020-00b1-4d40-9422-aba2288625d4` | `expected` | `0.4903` | `True` |
| `2` | `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `candidate_noise` | `0.3931` | `False` |
| `3` | `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `candidate_noise` | `0.3865` | `False` |
| `4` | `76120648-7522-4025-8176-5e5fb199c687` | `candidate_noise` | `0.3775` | `True` |
| `5` | `0586e881-099d-4866-a1cf-4ed571139c70` | `candidate_noise` | `0.376` | `False` |
| `6` | `076c39f2-9cf5-45c7-ac1b-e379da875926` | `expected` | `0.3749` | `False` |
| `7` | `1ecc06d3-3c05-4224-9d30-3111a0533f50` | `candidate_noise` | `0.372` | `False` |
| `8` | `3a9f7658-b877-4532-b9c8-1a79b360c5d4` | `candidate_noise` | `0.3714` | `False` |
| `9` | `22471376-888c-42fb-ac5d-c06d09f25345` | `candidate_noise` | `0.3705` | `True` |
| `10` | `fec7285c-8ebf-45ba-8197-911a515e4e0b` | `candidate_noise` | `0.3698` | `True` |
| `11` | `636f4a37-3296-4858-be5d-99d1988bc3d6` | `candidate_noise` | `0.3688` | `False` |
| `12` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `candidate_noise` | `0.367` | `False` |
| `13` | `65e4ca55-7169-4ee4-b388-a6927043a92d` | `candidate_noise` | `0.3662` | `False` |
| `14` | `89b85467-0655-47d3-9a0c-89da364cd487` | `candidate_noise` | `0.3632` | `False` |
| `15` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `candidate_noise` | `0.3625` | `False` |
| `16` | `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `candidate_noise` | `0.3623` | `False` |
| `17` | `b85b0a01-9c3f-4c42-a26a-01741c84682c` | `candidate_noise` | `0.3619` | `False` |
| `18` | `2b9eb759-86cc-4d3d-b136-dae4abfe4246` | `candidate_noise` | `0.3608` | `False` |
| `19` | `1adaa011-9a30-45bc-a78e-c8ba659af51a` | `candidate_noise` | `0.3606` | `False` |
| `20` | `591247fd-e943-42e5-b5bd-d8f016e93089` | `candidate_noise` | `0.3592` | `False` |

## logistics_proxy_planning

- category: `logistics`
- baseline attention count: `1`
- wide attention count: `2`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| `68ae35cf-2be5-4dfc-bdd0-b179682163ad` | `retrieved_but_ranked_too_low` | `24` | `False` | `False` |
| `76120648-7522-4025-8176-5e5fb199c687` | `reached_working_memory` | `1` | `True` | `True` |
| `380b765f-ffa2-4296-a66e-527bacb75a64` | `retrieved_but_pruned_by_attention` | `4` | `False` | `False` |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `76120648-7522-4025-8176-5e5fb199c687` | `expected` | `0.4179` | `True` |
| `2` | `06b4d255-58d5-49f5-adec-43426ce0d09b` | `candidate_noise` | `0.3841` | `False` |
| `3` | `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d` | `candidate_noise` | `0.3779` | `False` |
| `4` | `380b765f-ffa2-4296-a66e-527bacb75a64` | `expected` | `0.3777` | `False` |
| `5` | `0586e881-099d-4866-a1cf-4ed571139c70` | `candidate_noise` | `0.3739` | `False` |
| `6` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `candidate_noise` | `0.3652` | `False` |
| `7` | `bc2086b3-87d9-479a-935f-805fe7d523c7` | `candidate_noise` | `0.3651` | `False` |
| `8` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `candidate_noise` | `0.3646` | `False` |
| `9` | `65e4ca55-7169-4ee4-b388-a6927043a92d` | `candidate_noise` | `0.364` | `False` |
| `10` | `4b01b020-00b1-4d40-9422-aba2288625d4` | `candidate_noise` | `0.3625` | `False` |
| `11` | `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `candidate_noise` | `0.3624` | `False` |
| `12` | `21b090dc-e87c-4a05-8db1-b06e0b62bf42` | `candidate_noise` | `0.3619` | `False` |
| `13` | `89b85467-0655-47d3-9a0c-89da364cd487` | `candidate_noise` | `0.3611` | `False` |
| `14` | `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `candidate_noise` | `0.3606` | `False` |
| `15` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `candidate_noise` | `0.3605` | `False` |
| `16` | `b85b0a01-9c3f-4c42-a26a-01741c84682c` | `candidate_noise` | `0.3593` | `False` |
| `17` | `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `candidate_noise` | `0.3587` | `False` |
| `18` | `0121143f-0779-4965-9405-2e7b3eabcd05` | `candidate_noise` | `0.3563` | `False` |
| `19` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `candidate_noise` | `0.3558` | `False` |
| `20` | `0820a071-1bc7-42e2-8365-554a1e92900a` | `candidate_noise` | `0.3547` | `False` |

## sparse_violin_tuning

- category: `sparse_knowledge`
- baseline attention count: `0`
- wide attention count: `0`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| none | none |  |  |  |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `85ba1ed5-56cf-4cbd-a3ec-c4290ab0fc9f` | `noise_sparse_case` | `0.3501` | `False` |
| `2` | `bc2086b3-87d9-479a-935f-805fe7d523c7` | `noise_sparse_case` | `0.3496` | `False` |
| `3` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `noise_sparse_case` | `0.3452` | `False` |
| `4` | `380b765f-ffa2-4296-a66e-527bacb75a64` | `noise_sparse_case` | `0.3437` | `False` |
| `5` | `c456133c-be3b-43da-8d46-b983619f01bf` | `noise_sparse_case` | `0.3433` | `False` |
| `6` | `d53e3d9f-445c-4ab7-9b3c-8acb899caa78` | `noise_sparse_case` | `0.3429` | `False` |
| `7` | `1c6bd504-03b0-4c4f-b9c4-026bb1722420` | `noise_sparse_case` | `0.3428` | `False` |
| `8` | `698a613f-15a8-4919-b1f1-3f383f34a1d9` | `noise_sparse_case` | `0.342` | `False` |
| `9` | `efb9555a-e0d2-41f4-8706-7ed612988e42` | `noise_sparse_case` | `0.342` | `False` |
| `10` | `0121143f-0779-4965-9405-2e7b3eabcd05` | `noise_sparse_case` | `0.3418` | `False` |
| `11` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `noise_sparse_case` | `0.3413` | `False` |
| `12` | `06c7ab71-397c-4754-984d-48cbdcec18bd` | `noise_sparse_case` | `0.3411` | `False` |
| `13` | `7b1fd455-c6f7-4dcf-a109-11fc3c89262f` | `noise_sparse_case` | `0.3404` | `False` |
| `14` | `7a4b823b-f9df-4e77-b3b7-744ee834741c` | `noise_sparse_case` | `0.3399` | `False` |
| `15` | `0e3fdeda-0d38-40ad-993c-480703e55f9e` | `noise_sparse_case` | `0.3397` | `False` |
| `16` | `ee7f9d7a-56de-41a7-bebb-681cf7cdc54b` | `noise_sparse_case` | `0.3396` | `False` |
| `17` | `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d` | `noise_sparse_case` | `0.3394` | `False` |
| `18` | `f2ffe815-a7f5-453f-8e8f-644aa264e07c` | `noise_sparse_case` | `0.3385` | `False` |
| `19` | `68ae35cf-2be5-4dfc-bdd0-b179682163ad` | `noise_sparse_case` | `0.3384` | `False` |
| `20` | `9d0fbe5a-30dd-4b7c-ac0e-d00c0a5e6542` | `noise_sparse_case` | `0.338` | `False` |

## unsupported_recipe

- category: `unsupported_questions`
- baseline attention count: `0`
- wide attention count: `1`

### Expected Concepts

| Concept | Category | Rank | Baseline Attention | Wide Attention |
| --- | --- | ---: | --- | --- |
| none | none |  |  |  |

### Top 20 Activated

| Rank | Concept | Role | Score | Baseline Attention |
| ---: | --- | --- | ---: | --- |
| `1` | `d53e3d9f-445c-4ab7-9b3c-8acb899caa78` | `noise_sparse_case` | `0.3749` | `False` |
| `2` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `noise_sparse_case` | `0.3725` | `False` |
| `3` | `06c7ab71-397c-4754-984d-48cbdcec18bd` | `noise_sparse_case` | `0.3684` | `False` |
| `4` | `698a613f-15a8-4919-b1f1-3f383f34a1d9` | `noise_sparse_case` | `0.3659` | `False` |
| `5` | `6b396377-f29f-44d8-8adb-10016fbb07a5` | `noise_sparse_case` | `0.3659` | `False` |
| `6` | `0121143f-0779-4965-9405-2e7b3eabcd05` | `noise_sparse_case` | `0.3656` | `False` |
| `7` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `noise_sparse_case` | `0.3651` | `False` |
| `8` | `380b765f-ffa2-4296-a66e-527bacb75a64` | `noise_sparse_case` | `0.3648` | `False` |
| `9` | `ee7f9d7a-56de-41a7-bebb-681cf7cdc54b` | `noise_sparse_case` | `0.3645` | `False` |
| `10` | `7a4b823b-f9df-4e77-b3b7-744ee834741c` | `noise_sparse_case` | `0.3637` | `False` |
| `11` | `0e3fdeda-0d38-40ad-993c-480703e55f9e` | `noise_sparse_case` | `0.3626` | `False` |
| `12` | `f2ffe815-a7f5-453f-8e8f-644aa264e07c` | `noise_sparse_case` | `0.3623` | `False` |
| `13` | `f299e4d4-249a-4ff4-88e6-2c4dadefe30d` | `noise_sparse_case` | `0.3622` | `False` |
| `14` | `e2ad3694-8cae-4df0-83db-b6908ff2463e` | `noise_sparse_case` | `0.3616` | `False` |
| `15` | `7b1fd455-c6f7-4dcf-a109-11fc3c89262f` | `noise_sparse_case` | `0.3614` | `False` |
| `16` | `b877488b-5347-402c-b287-50125c8561c0` | `noise_sparse_case` | `0.3614` | `False` |
| `17` | `184f244d-7bd6-4609-8b67-1a45520c1fb8` | `noise_sparse_case` | `0.3611` | `False` |
| `18` | `9fafbb71-ef17-4c05-8764-3577ae15ef59` | `noise_sparse_case` | `0.3609` | `False` |
| `19` | `527623e3-ae77-4c75-b1e2-f9db386ba568` | `noise_sparse_case` | `0.3605` | `False` |
| `20` | `6457f783-957c-4e69-95bb-bacf18f6fd32` | `noise_sparse_case` | `0.3604` | `False` |
