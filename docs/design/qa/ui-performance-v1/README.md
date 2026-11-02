# Uraraka UI performance and motion

Live Blender 5.2.2 / macOS Metal: changed-layout checks remain intact; unchanged author draws reuse recorded signatures, and nested rows reuse their resolved stylesheet palette. No extra GPU resources or idle timers were added.

| Warm callback | Before median / p95 | After median / p95 |
| --- | --- | --- |
| UI authoring | 1.186 / 1.385 ms | 0.948 / 1.118 ms |
| UI painting | 2.597 / 2.941 ms | 2.356 / 2.805 ms |

70 before and 72 after samples over roughly six seconds each. Sum of callback medians improved about 13%; this is not a total FPS measurement. BVT MToon rendering measured separately at 15.092 ms median / 20.683 ms p95 and remains a larger cost. No renderer or simulation settings changed.

CamKeys Appearance defaults now use speed **2.0** and strength **0.35** (half its previous 0.7). Both remain configurable, including disabling motion. Applied live without RNA re-registration or saving Uraraka.

377 unit tests and the no-focus registered-list runtime fixture pass; the focus audit recorded no activation. Source, vendor copies, and the live methods agree. Full evidence and remaining limits: [report.json](report.json).
