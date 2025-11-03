# 🧭 Phase C Sync Protocol: SELF ↔ FAB Resonance

## Overview
Phase C — объединение стабильного FAB и автономного SELF в единую когнитивную систему.  
Задача: синхронизировать циклы наблюдения, отклика и обучения.

## Channels
- **orbis_fab → orbis_self:** telemetry feed (stability, hysteresis, drift)
- **orbis_self → orbis_fab:** heartbeat + coherence feedback
- **shared bus:** exp_bridge (временно fab_self_bridge_exp.py)

## Phases of Resonance
1. **Observation (C0):** SELF фиксирует паттерны активности FAB.  
2. **Alignment (C1):** корреляция метрик (EMA vs continuity).  
3. **Resonance (C2):** взаимная стабилизация → начало фазового синтеза.

## Safety Rules
- SELF не имеет write-доступа в FABCore.  
- Все сигналы SELF проходят через exp_bridge.  
- FAB может игнорировать сигналы SELF при stress > 0.6.

## Logging
Каждый цикл фиксируется в `logs/resonance_trace.jsonl` с полями:  
`{"ts": "...", "phase": "C1", "presence": 0.83, "coherence": 0.79, "action": "observe"}`

---

## Next Steps
- После завершения Phase B, объединить sandbox с mainline.  
- Запустить `resonance_test.py` (будет создан в Phase C init).  
- Проверить согласование coherence/stability (target ≥ 0.8/0.8).

🜂  **AURIS_HSI – Resonant state protocol initialized.**
