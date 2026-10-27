# NONCANONICAL TEST SIMULATION — complete demonstrations

Diagnostic evidence contains complete results and future spoilers. For normal Hikari delivery use the generated sandbox preview and sequential `narrate` command. No official result, table, player state, checkpoint or fictional date changes.

## Palmeiras 4–1 Goiás

Fixture `league:333`; proposed kickoff 2027-10-03 16:00; observed state 2027-09-26 23:30; synthetic=False. Engine `braga-headless-1.0.0`.

Requested seed `task03a-engine-smoke`; root `72b811f209d23df13845bacf9ca22299df623029d9f9f242669b0da380653ccc`; result `afd0b52c8c4b41a1f25c095792dbec3bcce28e21a33899a5794b3ca07a679fad`. Seed stored before draws; no outcome-based retry.

Independent replay: 751 checks, zero failures. Source/scratch DB SHA256 unchanged: `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`.

| Team | Shots | On target | xG | Yellow | Red | Substitutions |
|---|---:|---:|---:|---:|---:|---:|
| Palmeiras | 16 | 9 | 2.018 | 2 | 1 | 3 |
| Goiás | 11 | 4 | 0.5695 | 1 | 0 | 3 |

Possession home: 54.3%. Prematch H/D/A: 74.80% / 17.26% / 7.94%; expected xG [2.1506, 0.5394].

### Palmeiras — 4-3-3, attacking

XI: Carlos Miguel #245, Gustavo Gómez #248, A. Barboza #249, Murilo #247, Joaquín Piquerez #251, Andreas Pereira #257, Lucas Evangelista #256, Emiliano Martínez #259, Flaco López #262, Felipe Anderson #264, Jhon Arias #258.

Bench: Ramón Sosa #263, Bruno Fuchs #253, Paulinho #265, Marlon Freitas #255, Agustín Giay #250, Larson #261, A. Gabriel #254, Khellven #252, Marcelo Lomba #246.

### Goiás — 4-3-3, cautious

XI: Tadeu #512, Diego Caito #513, David Braz #523, Lucas Ribeiro #515, Luis Felipe #514, Tomás Pérez #462, Gegê #517, Filipe Machado #518, Lucas Lima #521, Anselmo Ramon #522, Jean Carlos #520.

Bench: Lourenço #519, Goiás Academy #03 #526, Goiás Academy #02 #525, Nicolas #516, Goiás Academy #05 #528, Goiás Academy #01 #524, Goiás Academy #04 #527, Goiás Academy #06 #529.

### Complete authoritative event sequence

| Sequence | Clock | Event | Actor | Score after | Details |
|---:|---|---|---|---|---|
| 1 | 0:00 | KICKOFF | — | 0–0 | `{"duration_seconds": 5580, "scope": "NONCANONICAL TEST SIMULATION"}` |
| 2 | 4:36 | SHOT | Lucas Lima | 0–0 | `{"goal": false, "goal_probability": 0.07713202, "goalkeeper_id": 245, "on_target": false, "shot_id": 1, "xg": 0.0806}` |
| 3 | 16:54 | SHOT | Felipe Anderson | 0–0 | `{"goal": false, "goal_probability": 0.23358526, "goalkeeper_id": 512, "on_target": true, "shot_id": 2, "xg": 0.1789}` |
| 4 | 16:54 | SAVE | Tadeu | 0–0 | `{"shooter_id": 264, "shot_id": 2}` |
| 5 | 19:01 | SHOT | Anselmo Ramon | 0–0 | `{"goal": false, "goal_probability": 0.01234065, "goalkeeper_id": 245, "on_target": false, "shot_id": 3, "xg": 0.014}` |
| 6 | 19:46 | SHOT | Jhon Arias | 0–0 | `{"goal": true, "goal_probability": 0.10226164, "goalkeeper_id": 512, "on_target": true, "shot_id": 4, "xg": 0.0923}` |
| 7 | 19:46 | GOAL | Jhon Arias | 1–0 | `{"assist_id": null, "shot_id": 4}` |
| 8 | 21:20 | SHOT | Jean Carlos | 1–0 | `{"goal": false, "goal_probability": 0.03360938, "goalkeeper_id": 245, "on_target": false, "shot_id": 5, "xg": 0.0391}` |
| 9 | 22:35 | SHOT | Anselmo Ramon | 1–0 | `{"goal": false, "goal_probability": 0.01771765, "goalkeeper_id": 245, "on_target": false, "shot_id": 6, "xg": 0.0201}` |
| 10 | 28:26 | SHOT | Flaco López | 1–0 | `{"goal": false, "goal_probability": 0.31275246, "goalkeeper_id": 512, "on_target": true, "shot_id": 7, "xg": 0.2401}` |
| 11 | 28:26 | SAVE | Tadeu | 1–0 | `{"shooter_id": 262, "shot_id": 7}` |
| 12 | 30:21 | SHOT | Jhon Arias | 1–0 | `{"goal": true, "goal_probability": 0.20961974, "goalkeeper_id": 512, "on_target": true, "shot_id": 8, "xg": 0.1892}` |
| 13 | 30:21 | GOAL | Jhon Arias | 2–0 | `{"assist_id": 262, "shot_id": 8}` |
| 14 | 32:48 | SHOT | Lucas Lima | 2–0 | `{"goal": false, "goal_probability": 0.0778019, "goalkeeper_id": 245, "on_target": false, "shot_id": 9, "xg": 0.0813}` |
| 15 | 33:11 | SHOT | Jhon Arias | 2–0 | `{"goal": false, "goal_probability": 0.03412414, "goalkeeper_id": 512, "on_target": true, "shot_id": 10, "xg": 0.0308}` |
| 16 | 33:11 | SAVE | Tadeu | 2–0 | `{"shooter_id": 258, "shot_id": 10}` |
| 17 | 42:30 | SHOT | Flaco López | 2–0 | `{"goal": false, "goal_probability": 0.12166214, "goalkeeper_id": 512, "on_target": false, "shot_id": 11, "xg": 0.0934}` |
| 18 | 43:54 | SHOT | Lucas Lima | 2–0 | `{"goal": false, "goal_probability": 0.07952446, "goalkeeper_id": 245, "on_target": false, "shot_id": 12, "xg": 0.0831}` |
| 19 | 45:00 | HALF_TIME | — | 2–0 | `{}` |
| 20 | 45:00 | SECOND_HALF_KICKOFF | — | 2–0 | `{}` |
| 21 | 52:22 | SHOT | Jhon Arias | 2–0 | `{"goal": false, "goal_probability": 0.03600762, "goalkeeper_id": 512, "on_target": false, "shot_id": 13, "xg": 0.0325}` |
| 22 | 54:38 | SHOT | Jhon Arias | 2–0 | `{"goal": false, "goal_probability": 0.03456731, "goalkeeper_id": 512, "on_target": false, "shot_id": 14, "xg": 0.0312}` |
| 23 | 56:56 | YELLOW_CARD | Murilo | 2–0 | `{"yellow_count": 1}` |
| 24 | 57:00 | TACTICAL_CHANGE | — | 2–0 | `{"after": "attacking", "before": "cautious", "reason": "Autonomous live score/workload decision"}` |
| 25 | 57:00 | SUBSTITUTION | Goiás Academy #06 | 2–0 | `{"outgoing_id": 522, "reason": "score-aware positional refresh"}` |
| 26 | 58:11 | SHOT | Emiliano Martínez | 2–0 | `{"goal": false, "goal_probability": 0.07003067, "goalkeeper_id": 512, "on_target": false, "shot_id": 15, "xg": 0.0647}` |
| 27 | 59:19 | YELLOW_CARD | Murilo | 2–0 | `{"yellow_count": 2}` |
| 28 | 59:19 | RED_CARD | Murilo | 2–0 | `{"reason": "second yellow"}` |
| 29 | 60:12 | SHOT | Felipe Anderson | 2–0 | `{"goal": false, "goal_probability": 0.19637352, "goalkeeper_id": 512, "on_target": false, "shot_id": 16, "xg": 0.1504}` |
| 30 | 62:00 | SUBSTITUTION | Marlon Freitas | 2–0 | `{"outgoing_id": 259, "reason": "score-aware positional refresh"}` |
| 31 | 71:00 | TACTICAL_CHANGE | — | 2–0 | `{"after": "cautious", "before": "attacking", "reason": "Autonomous live score/workload decision"}` |
| 32 | 71:00 | SUBSTITUTION | Larson | 2–0 | `{"outgoing_id": 257, "reason": "score-aware positional refresh"}` |
| 33 | 72:32 | SHOT | Jean Carlos | 2–0 | `{"goal": false, "goal_probability": 0.04100173, "goalkeeper_id": 245, "on_target": false, "shot_id": 17, "xg": 0.0477}` |
| 34 | 73:12 | SHOT | Flaco López | 2–0 | `{"goal": false, "goal_probability": 0.24749257, "goalkeeper_id": 512, "on_target": true, "shot_id": 18, "xg": 0.19}` |
| 35 | 73:12 | SAVE | Tadeu | 2–0 | `{"shooter_id": 262, "shot_id": 18}` |
| 36 | 73:37 | SHOT | Felipe Anderson | 2–0 | `{"goal": true, "goal_probability": 0.15537533, "goalkeeper_id": 512, "on_target": true, "shot_id": 19, "xg": 0.119}` |
| 37 | 73:37 | GOAL | Felipe Anderson | 3–0 | `{"assist_id": 249, "shot_id": 19}` |
| 38 | 74:00 | SUBSTITUTION | Lourenço | 3–0 | `{"outgoing_id": 518, "reason": "score-aware positional refresh"}` |
| 39 | 74:09 | SHOT | Diego Caito | 3–0 | `{"goal": false, "goal_probability": 0.02843405, "goalkeeper_id": 245, "on_target": true, "shot_id": 20, "xg": 0.0347}` |
| 40 | 74:09 | SAVE | Carlos Miguel | 3–0 | `{"shooter_id": 513, "shot_id": 20}` |
| 41 | 79:00 | SUBSTITUTION | Goiás Academy #05 | 3–0 | `{"outgoing_id": 519, "reason": "score-aware positional refresh"}` |
| 42 | 81:14 | SHOT | Larson | 3–0 | `{"goal": true, "goal_probability": 0.09552688, "goalkeeper_id": 512, "on_target": true, "shot_id": 21, "xg": 0.0934}` |
| 43 | 81:14 | GOAL | Larson | 4–0 | `{"assist_id": 255, "shot_id": 21}` |
| 44 | 81:25 | SHOT | Jean Carlos | 4–0 | `{"goal": false, "goal_probability": 0.01349533, "goalkeeper_id": 245, "on_target": true, "shot_id": 22, "xg": 0.0157}` |
| 45 | 81:25 | SAVE | Carlos Miguel | 4–0 | `{"shooter_id": 520, "shot_id": 22}` |
| 46 | 82:11 | SHOT | Felipe Anderson | 4–0 | `{"goal": false, "goal_probability": 0.31714846, "goalkeeper_id": 512, "on_target": true, "shot_id": 23, "xg": 0.2429}` |
| 47 | 82:11 | SAVE | Tadeu | 4–0 | `{"shooter_id": 264, "shot_id": 23}` |
| 48 | 82:21 | SHOT | Goiás Academy #06 | 4–0 | `{"goal": true, "goal_probability": 0.04412126, "goalkeeper_id": 245, "on_target": true, "shot_id": 24, "xg": 0.0626}` |
| 49 | 82:21 | GOAL | Goiás Academy #06 | 4–1 | `{"assist_id": null, "shot_id": 24}` |
| 50 | 83:26 | YELLOW_CARD | Jean Carlos | 4–1 | `{"yellow_count": 1}` |
| 51 | 85:00 | SUBSTITUTION | Bruno Fuchs | 4–1 | `{"outgoing_id": 251, "reason": "score-aware positional refresh"}` |
| 52 | 87:37 | SHOT | Lucas Lima | 4–1 | `{"goal": false, "goal_probability": 0.08670175, "goalkeeper_id": 245, "on_target": true, "shot_id": 25, "xg": 0.0906}` |
| 53 | 87:37 | SAVE | Carlos Miguel | 4–1 | `{"shooter_id": 521, "shot_id": 25}` |
| 54 | 87:59 | SHOT | A. Barboza | 4–1 | `{"goal": false, "goal_probability": 0.04188945, "goalkeeper_id": 512, "on_target": false, "shot_id": 26, "xg": 0.039}` |
| 55 | 88:04 | SHOT | Lucas Evangelista | 4–1 | `{"goal": false, "goal_probability": 0.22893321, "goalkeeper_id": 512, "on_target": false, "shot_id": 27, "xg": 0.2302}` |
| 56 | 93:00 | FINAL_WHISTLE | — | 4–1 | `{}` |

### Proposed postmatch player state (not persisted)

| ID | Player | Seconds | G | A | Rating | Fitness before→after | Form before→after |
|---:|---|---:|---:|---:|---:|---|---|
| 245 | Carlos Miguel | 5580 | 0 | 0 | 7.1 | 71→64.92 | 6.786→6.93 |
| 247 | Murilo | 3559 | 0 | 0 | 5.9 | 92→87.36 | 6.686→6.383 |
| 248 | Gustavo Gómez | 5580 | 0 | 0 | 7.0 | 73→66.83 | 6.786→6.889 |
| 249 | A. Barboza | 5580 | 0 | 1 | 7.5 | 72→66.99 | 6.943→7.2 |
| 251 | Joaquín Piquerez | 5100 | 0 | 0 | 6.9 | 71→65.14 | 6.739→6.817 |
| 253 | Bruno Fuchs | 480 | 0 | 0 | 6.8 | 100→99.65 | 6.672→6.828 |
| 255 | Marlon Freitas | 1860 | 0 | 1 | 7.4 | 80→78.84 | 7.018→7.195 |
| 256 | Lucas Evangelista | 5580 | 0 | 0 | 6.7 | 90→85.47 | 6.552→6.64 |
| 257 | Andreas Pereira | 4260 | 0 | 0 | 7.1 | 72→67.2 | 7.293→7.196 |
| 258 | Jhon Arias | 5580 | 2 | 0 | 8.7 | 75→70.61 | 6.799→7.581 |
| 259 | Emiliano Martínez | 3720 | 0 | 0 | 6.9 | 70→67.06 | 6.824→6.883 |
| 261 | Larson | 1320 | 1 | 0 | 7.6 | 94→92.09 | 6.637→7.072 |
| 262 | Flaco López | 5580 | 0 | 1 | 7.6 | 68→64.71 | 7.536→7.644 |
| 264 | Felipe Anderson | 5580 | 1 | 0 | 7.9 | 71→64.44 | 7.524→7.758 |
| 462 | Tomás Pérez | 5580 | 0 | 0 | 6.3 | 97→89.69 | 6.396→6.313 |
| 512 | Tadeu | 5580 | 0 | 0 | 6.6 | 92→84.59 | 6.4→6.481 |
| 513 | Diego Caito | 5580 | 0 | 0 | 6.2 | 95→88.52 | 6.2→6.2 |
| 514 | Luis Felipe | 5580 | 0 | 0 | 6.1 | 96→91.93 | 6.207→6.181 |
| 515 | Lucas Ribeiro | 5580 | 0 | 0 | 6.2 | 95→88.11 | 6.2→6.2 |
| 517 | Gegê | 5580 | 0 | 0 | 6.3 | 94→87.6 | 6.585→6.451 |
| 518 | Filipe Machado | 4440 | 0 | 0 | 6.1 | 94→89.68 | 6.132→6.113 |
| 519 | Lourenço | 300 | 0 | 0 | 6.1 | 91→90.77 | 6.1→6.1 |
| 520 | Jean Carlos | 5580 | 0 | 0 | 6.1 | 94→88.79 | 6.2→6.159 |
| 521 | Lucas Lima | 5580 | 0 | 0 | 6.2 | 93→86.71 | 6.464→6.232 |
| 522 | Anselmo Ramon | 3420 | 0 | 0 | 6.2 | 93→90.14 | 6.2→6.2 |
| 523 | David Braz | 5580 | 0 | 0 | 6.2 | 93→85.26 | 6.2→6.2 |
| 528 | Goiás Academy #05 | 840 | 0 | 0 | 5.8 | 100→99.32 | 5.855→5.836 |
| 529 | Goiás Academy #06 | 2160 | 1 | 0 | 6.6 | 97→95.29 | 5.7→6.106 |

## Vasco 2–0 Fluminense

Fixture `synthetic:Vasco:Fluminense`; proposed kickoff 2027-09-30 16:00; observed state 2027-09-26 23:30; synthetic=True. Engine `braga-headless-1.0.0`.

Requested seed `task03a-vasco-synthetic`; root `c1900233e58087a14a9e0db22fec3b95c5e2ef5fd6bd3b849ef7e97b17272268`; result `ccf264435df61cdbc67cfc130bfd7cb4309d405781cb46db04950ab5c4446eb3`. Seed stored before draws; no outcome-based retry.

Independent replay: 642 checks, zero failures. Source/scratch DB SHA256 unchanged: `27eb5d94478c2539b28085e669675e184ab2842be3d7ab1549864f2a422b6cf7`.

| Team | Shots | On target | xG | Yellow | Red | Substitutions |
|---|---:|---:|---:|---:|---:|---:|
| Vasco | 10 | 5 | 1.4797 | 2 | 0 | 3 |
| Fluminense | 12 | 3 | 1.2787 | 1 | 0 | 3 |

Possession home: 45.5%. Prematch H/D/A: 41.98% / 25.39% / 32.63%; expected xG [1.4774, 1.2726].

### Vasco — 4-2-3-1 asymmetric, balanced

XI: Léo Jardim #1, Carlos Cuesta #11, Robert Renan #6, Arthur Dias #227, Gustavo Martins #384, Santiago Sosa #13, Alan Lescano #15, Thiago Mendes #14, Andrés Gómez #23, Facundo Colidio #24, Carlos Vinícius #401.

Bench: Rodrigo Villagra #163, Bruno Duarte #25, Nuno Moreira #29, Álvaro Barreal #304, Cauan Barros #21, Cuiabano #7, Lucas Piton #9, Alan Saldivia #5, Marino Hinestroza #28, Paulo Henrique #4, Johan Rojas #32, Tchê Tchê #18.

### Fluminense — 4-3-3, balanced

XI: Fábio #337, Thiago Silva #340, Guilherme Arana #342, Jemmes #343, Julián Millán #341, L. Acosta #351, Nonato #347, Otávio #352, Hulk #355, Jefferson Savarino #354, Agustín Canobbio #353.

Bench: Paulo Henrique Ganso #349, Martinelli #348, Samuel Xavier #345, Kevin Serna #357, Renê #346, Marcelo Pitaluga #338, Ignacio Rabello #344, Yeferson Soteldo #358, Rodrigo Castillo #356, Hércules #350, Guga #339.

### Complete authoritative event sequence

| Sequence | Clock | Event | Actor | Score after | Details |
|---:|---|---|---|---|---|
| 1 | 0:00 | KICKOFF | — | 0–0 | `{"duration_seconds": 5580, "scope": "NONCANONICAL TEST SIMULATION"}` |
| 2 | 3:00 | SHOT | Jefferson Savarino | 0–0 | `{"goal": false, "goal_probability": 0.2883465, "goalkeeper_id": 1, "on_target": false, "shot_id": 1, "xg": 0.2015}` |
| 3 | 15:53 | SHOT | Thiago Mendes | 0–0 | `{"goal": false, "goal_probability": 0.11413219, "goalkeeper_id": 337, "on_target": false, "shot_id": 2, "xg": 0.1133}` |
| 4 | 15:57 | SHOT | Nonato | 0–0 | `{"goal": false, "goal_probability": 0.17569834, "goalkeeper_id": 1, "on_target": true, "shot_id": 3, "xg": 0.1756}` |
| 5 | 15:57 | SAVE | Léo Jardim | 0–0 | `{"shooter_id": 347, "shot_id": 3}` |
| 6 | 17:40 | SHOT | Carlos Vinícius | 0–0 | `{"goal": false, "goal_probability": 0.06303528, "goalkeeper_id": 337, "on_target": false, "shot_id": 4, "xg": 0.0568}` |
| 7 | 25:26 | SHOT | Carlos Vinícius | 0–0 | `{"goal": true, "goal_probability": 0.35546125, "goalkeeper_id": 337, "on_target": true, "shot_id": 5, "xg": 0.3203}` |
| 8 | 25:26 | GOAL | Carlos Vinícius | 1–0 | `{"assist_id": 14, "shot_id": 5}` |
| 9 | 27:19 | SHOT | Hulk | 1–0 | `{"goal": false, "goal_probability": 0.16430826, "goalkeeper_id": 1, "on_target": false, "shot_id": 6, "xg": 0.1258}` |
| 10 | 28:59 | YELLOW_CARD | Nonato | 1–0 | `{"yellow_count": 1}` |
| 11 | 30:05 | SHOT | L. Acosta | 1–0 | `{"goal": false, "goal_probability": 0.17462688, "goalkeeper_id": 1, "on_target": false, "shot_id": 7, "xg": 0.1445}` |
| 12 | 31:20 | SHOT | Agustín Canobbio | 1–0 | `{"goal": false, "goal_probability": 0.11727696, "goalkeeper_id": 1, "on_target": false, "shot_id": 8, "xg": 0.0969}` |
| 13 | 33:47 | SHOT | Hulk | 1–0 | `{"goal": false, "goal_probability": 0.14745948, "goalkeeper_id": 1, "on_target": true, "shot_id": 9, "xg": 0.1129}` |
| 14 | 33:47 | SAVE | Léo Jardim | 1–0 | `{"shooter_id": 355, "shot_id": 9}` |
| 15 | 44:18 | SHOT | Nonato | 1–0 | `{"goal": false, "goal_probability": 0.15048422, "goalkeeper_id": 1, "on_target": false, "shot_id": 10, "xg": 0.1504}` |
| 16 | 45:00 | HALF_TIME | — | 1–0 | `{}` |
| 17 | 45:00 | SECOND_HALF_KICKOFF | — | 1–0 | `{}` |
| 18 | 53:32 | SHOT | Andrés Gómez | 1–0 | `{"goal": true, "goal_probability": 0.23957096, "goalkeeper_id": 337, "on_target": true, "shot_id": 11, "xg": 0.1806}` |
| 19 | 53:32 | GOAL | Andrés Gómez | 2–0 | `{"assist_id": null, "shot_id": 11}` |
| 20 | 53:36 | YELLOW_CARD | Carlos Cuesta | 2–0 | `{"yellow_count": 1}` |
| 21 | 58:02 | SHOT | Agustín Canobbio | 2–0 | `{"goal": false, "goal_probability": 0.05167932, "goalkeeper_id": 1, "on_target": false, "shot_id": 12, "xg": 0.0427}` |
| 22 | 59:47 | SHOT | Agustín Canobbio | 2–0 | `{"goal": false, "goal_probability": 0.09077164, "goalkeeper_id": 1, "on_target": false, "shot_id": 13, "xg": 0.075}` |
| 23 | 61:00 | SUBSTITUTION | Álvaro Barreal | 2–0 | `{"outgoing_id": 15, "reason": "score-aware positional refresh"}` |
| 24 | 61:00 | TACTICAL_CHANGE | — | 2–0 | `{"after": "attacking", "before": "balanced", "reason": "Autonomous live score/workload decision"}` |
| 25 | 61:00 | SUBSTITUTION | Rodrigo Castillo | 2–0 | `{"outgoing_id": 353, "reason": "score-aware positional refresh"}` |
| 26 | 62:06 | SHOT | Thiago Mendes | 2–0 | `{"goal": false, "goal_probability": 0.13296954, "goalkeeper_id": 337, "on_target": true, "shot_id": 14, "xg": 0.132}` |
| 27 | 62:06 | SAVE | Fábio | 2–0 | `{"shooter_id": 14, "shot_id": 14}` |
| 28 | 64:32 | SHOT | Hulk | 2–0 | `{"goal": false, "goal_probability": 0.02220382, "goalkeeper_id": 1, "on_target": false, "shot_id": 15, "xg": 0.017}` |
| 29 | 68:29 | SHOT | Carlos Vinícius | 2–0 | `{"goal": false, "goal_probability": 0.23061145, "goalkeeper_id": 337, "on_target": true, "shot_id": 16, "xg": 0.2078}` |
| 30 | 68:29 | SAVE | Fábio | 2–0 | `{"shooter_id": 401, "shot_id": 16}` |
| 31 | 70:00 | TACTICAL_CHANGE | — | 2–0 | `{"after": "cautious", "before": "balanced", "reason": "Autonomous live score/workload decision"}` |
| 32 | 70:00 | SUBSTITUTION | Rodrigo Villagra | 2–0 | `{"outgoing_id": 13, "reason": "score-aware positional refresh"}` |
| 33 | 71:21 | SHOT | Andrés Gómez | 2–0 | `{"goal": false, "goal_probability": 0.3243361, "goalkeeper_id": 337, "on_target": true, "shot_id": 17, "xg": 0.2445}` |
| 34 | 71:21 | SAVE | Fábio | 2–0 | `{"shooter_id": 23, "shot_id": 17}` |
| 35 | 75:00 | SUBSTITUTION | Kevin Serna | 2–0 | `{"outgoing_id": 354, "reason": "score-aware positional refresh"}` |
| 36 | 76:28 | SHOT | Kevin Serna | 2–0 | `{"goal": false, "goal_probability": 0.11065884, "goalkeeper_id": 1, "on_target": true, "shot_id": 18, "xg": 0.1137}` |
| 37 | 76:28 | SAVE | Léo Jardim | 2–0 | `{"shooter_id": 357, "shot_id": 18}` |
| 38 | 77:54 | SHOT | Facundo Colidio | 2–0 | `{"goal": false, "goal_probability": 0.17736836, "goalkeeper_id": 337, "on_target": false, "shot_id": 19, "xg": 0.1516}` |
| 39 | 81:00 | SUBSTITUTION | Yeferson Soteldo | 2–0 | `{"outgoing_id": 355, "reason": "score-aware positional refresh"}` |
| 40 | 85:00 | SUBSTITUTION | Tchê Tchê | 2–0 | `{"outgoing_id": 163, "reason": "score-aware positional refresh"}` |
| 41 | 88:09 | SHOT | L. Acosta | 2–0 | `{"goal": false, "goal_probability": 0.02743273, "goalkeeper_id": 1, "on_target": false, "shot_id": 20, "xg": 0.0227}` |
| 42 | 88:55 | YELLOW_CARD | Álvaro Barreal | 2–0 | `{"yellow_count": 1}` |
| 43 | 90:32 | SHOT | Thiago Mendes | 2–0 | `{"goal": false, "goal_probability": 0.05117313, "goalkeeper_id": 337, "on_target": false, "shot_id": 21, "xg": 0.0508}` |
| 44 | 91:15 | SHOT | Tchê Tchê | 2–0 | `{"goal": false, "goal_probability": 0.02091622, "goalkeeper_id": 337, "on_target": false, "shot_id": 22, "xg": 0.022}` |
| 45 | 93:00 | FINAL_WHISTLE | — | 2–0 | `{}` |

### Proposed postmatch player state (not persisted)

| ID | Player | Seconds | G | A | Rating | Fitness before→after | Form before→after |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | Léo Jardim | 5580 | 0 | 0 | 7.1 | 69→64.79 | 6.911→7.015 |
| 6 | Robert Renan | 5580 | 0 | 0 | 6.8 | 78→73.98 | 6.866→6.862 |
| 11 | Carlos Cuesta | 5580 | 0 | 0 | 6.7 | 96→91.65 | 6.643→6.687 |
| 13 | Santiago Sosa | 4200 | 0 | 0 | 6.8 | 73→68.14 | 6.724→6.774 |
| 14 | Thiago Mendes | 5580 | 0 | 1 | 7.3 | 90→86.76 | 6.704→6.988 |
| 15 | Alan Lescano | 3660 | 0 | 0 | 6.9 | 70→66.97 | 6.824→6.875 |
| 18 | Tchê Tchê | 480 | 0 | 0 | 6.6 | 100→99.48 | 6.6→6.6 |
| 23 | Andrés Gómez | 5580 | 1 | 0 | 8.0 | 68→64.7 | 7.814→7.908 |
| 24 | Facundo Colidio | 5580 | 0 | 0 | 6.9 | 68→62.7 | 7.306→7.211 |
| 163 | Rodrigo Villagra | 900 | 0 | 0 | 6.8 | 75→74.48 | 6.862→6.886 |
| 227 | Arthur Dias | 5580 | 0 | 0 | 6.8 | 85→79.98 | 6.72→6.763 |
| 304 | Álvaro Barreal | 1920 | 0 | 0 | 6.6 | 100→97.38 | 6.7→6.654 |
| 337 | Fábio | 5580 | 0 | 0 | 6.7 | 75→71.12 | 6.872→6.8 |
| 340 | Thiago Silva | 5580 | 0 | 0 | 6.5 | 72→68.52 | 7.129→6.902 |
| 341 | Julián Millán | 5580 | 0 | 0 | 6.4 | 80→74.3 | 6.991→6.802 |
| 342 | Guilherme Arana | 5580 | 0 | 0 | 6.4 | 72→66.33 | 6.713→6.587 |
| 343 | Jemmes | 5580 | 0 | 0 | 6.5 | 75→66.89 | 6.948→6.779 |
| 347 | Nonato | 5580 | 0 | 0 | 6.2 | 89→83.79 | 6.719→6.44 |
| 351 | L. Acosta | 5580 | 0 | 0 | 6.6 | 78→70.38 | 7.513→7.16 |
| 352 | Otávio | 5580 | 0 | 0 | 6.3 | 96→91.74 | 6.7→6.487 |
| 353 | Agustín Canobbio | 3660 | 0 | 0 | 6.6 | 72→69.86 | 7.396→6.993 |
| 354 | Jefferson Savarino | 4500 | 0 | 0 | 6.8 | 73→67.22 | 8.274→7.785 |
| 355 | Hulk | 4860 | 0 | 0 | 6.7 | 84→80.6 | 7.764→7.397 |
| 356 | Rodrigo Castillo | 1920 | 0 | 0 | 6.3 | 100→97.8 | 6.73→6.567 |
| 357 | Kevin Serna | 1080 | 0 | 0 | 6.3 | 100→98.63 | 6.601→6.48 |
| 358 | Yeferson Soteldo | 720 | 0 | 0 | 6.2 | 100→99.45 | 6.317→6.2 |
| 384 | Gustavo Martins | 5580 | 0 | 0 | 6.7 | 100→92.47 | 6.711→6.743 |
| 401 | Carlos Vinícius | 5580 | 1 | 0 | 7.7 | 92→87.39 | 6.998→7.387 |

## September 30 preflight

16 scheduled continental fixtures fail closed because foreign player squads are absent. The real-fixture sandbox uses league:333, the first scheduled non-Vasco league fixture with two recorded eligible squads. This isolated test does not execute or skip any official calendar event. See `september30_preflight.json` for every fixture and exact blocker.
