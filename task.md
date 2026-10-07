# Current task — WP-012 exact-SHA CI release gate
Date: 2026-10-07 Europe/Rome.
Status: NO EXECUTOR TASK; OWNER CI NOTIFICATION PENDING. OWNER ECONOMIC PLAN INACTIVE.

Technical findings are closed in [Director review](delivery/WP-012-CORRECTION-DIRECTOR-REVIEW.md) on product e3a5afa6e355363cd2df93871c68ad8cb4de3626.

The Owner watches CI and supplies green/red for that SHA; the Director verifies the exact-SHA checks/compose-smoke outcome once notified. No polling, monitoring shell or repeat tests. If red, diagnose the reported failure under a bounded task; no blind retry.

No implementation, acquisition, Owner data inspection, replay, Deep or economic run active. Only after release acceptance will the Director activate the registered app comparison and provide Owner commands/configuration. Old v0.3 series and October evidence remain preserved.
