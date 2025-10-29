FAB · Fractal Associative Bus

Всеохватывающее техническое задание

Версия: v0.5-draft
Автор: Данил Ивашина
Проект: AURIS / Atlas / HSI / OneBlock
Файл: docs/FAB_OVERVIEW.md

⸻

0) Суть FAB

FAB (Fractal Associative Bus) — это оперативная шина осознания, соединяющая:
	•	Atlas (память) — долговременное знание, эпизоды и связи;
	•	Z-space — подсознательный «срез» актуального контекста;
	•	OneBlock (мышление) — вычислительный акт шага сознания.

Она реализует связанность S0/S1/S2, обеспечивая поток данных, намерений и обратной связи между подсознанием, сознанием и осознанным «Я».

⸻

1) Место FAB в архитектуре HSI

Слой	Роль	FAB-режим	Функция
S0	Бессознательное	FAB₀	Автогенерация паттернов, ветвление гипотез
S1	Подсознание	FAB₁	Регуляция потоков, квоты, точность, отбор контекста
S2	Сознание/Эго	FAB₂	Цели, фильтры, этика, фиксация опыта

FAB — точка синхронизации этих уровней.
Она не хранит знания, а временно держит активный контекст, чтобы OneBlock мог «думать» в рамках актуального Z-среза.

⸻

2) Главный цикл

Intent → Understanding (Anchors_T)
 → Z-Selector → Z-slice
 → FAB.fill(Z)
 → OneBlock(context=FAB.mix())
 → [SELF] → Integration → Atlas

Поток:
Atlas → (отбор S1) → Z-space → FAB → OneBlock → [SELF] → Atlas.

FAB обеспечивает:
	•	буфер «оперативной памяти»,
	•	маршрутизацию анкорных смыслов,
	•	адаптивную точность вычислений (bit-envelope),
	•	телеметрию и саморегуляцию через S1.

⸻

3) Принцип работы

Этап	Событие	Роль FAB
init_tick	новый шаг мышления	задаёт режим (FAB₀/₁/₂), квоты, точности
fill(Z)	заливка контекста	создаёт окна global/stream, нормализует веса
mix(anchors)	связывает смыслы	вычисляет поле активных узлов и анкорных центров
step()	шаг OneBlock	передаёт контекст в вычислитель, получает обратную связь
maybe_commit()	фиксация опыта	через Canon/Glue решает, писать ли след в Atlas


⸻

4) FAB как машина состояний

FAB₀ → FAB₁ → FAB₂, с обратными переходами при стрессах.

Условие	Переход
branch_success ≥ 0.62 ∧ self_presence ≥ 0.8	FAB₀ → FAB₁
stability ≥ 0.70 ∧ io_required ∧ CANON.ok	FAB₁ → FAB₂
stress > 0.7 ∨ error_rate > 0.05	FABx → FAB₁/₀ (деградация)

FAB₁: поднимает точность активных потоков (mxfp6+), зеркалит устойчивые анкоры в глобальное окно.
FAB₂: разрешает запись, включает OneBlock↔Atlas commit через Canon.

⸻

5) FAB как связность уровней

FAB объединяет:
	•	смысл (Anchors_T) — от Understanding (θU),
	•	знание (Fields_D) — от Diffusion (θK),
	•	контроль (S1) — подсознательный регулятор,
	•	память (Atlas) — долговременное хранилище опыта,
	•	личность ([SELF]) — контекст текущего шага.

FAB — это «нейронный шлейф», где смысл, знание и опыт проходят через общий контур, оставаясь когерентными.

⸻

6) Bit-Envelope политика

Цель: минимизировать энергопотребление при сохранении когерентности.

Состояние	Разрядность	Действие
Горячие анкоры	≥ mxfp6.00	активные вычисления
Фоновые	≈ mxfp4.12	низкая точность, редкие апдейты
Старые пучки	≤ mxfp3.x	свёрнутые кластеры, суммаризация

Гистерезис: повышение точности — быстро; понижение — медленно (устранение «дребезга»).

⸻

7) Структура и интерфейсы

src/orbis_fab/
 ├── core.py          # FABCore: init/fill/mix/step/maybe_commit
 ├── protocols.py     # контракты адаптеров (ZSelector, Canon, Glue, OneBlock)
 ├── policies.py      # bit-envelope, пороги, hysteresis
 ├── metrics.py       # Mensum (метрики и события)
 └── adapters/        # моки и интеграционные заглушки

Интерфейсы ядра:

fab.init_tick(mode, budgets, tolerances_5d, bit_policy)
fab.fill(z_slice)
context = fab.mix(anchors)
resp = fab.step(context, oneblock_call)
fab.maybe_commit(trace_sig)
fab.metrics()

Протоколы адаптеров:

ZSelector.build(intent, history_ref, budgets, tolerances_5d) -> ZSlice
Canon.guard(event) -> (ok: bool, reason: str|None)
Glue.commit(trace) -> None
OneBlock.call(context) -> dict


⸻

8) Метрики и логи

Метрика	Диапазон	Значение
fab_saturation	0–1	заполненность FAB
fab_self_presence	0–1	присутствие SELF
fab_error_rate	0–1	ошибка шага
stress	0–1	уровень перегрузки
coverage	0–1	охват смыслового пространства

События: fab_enter, precision_change, prune, io_blocked_by_canon, commit_success.

Все пишутся в .reports/fab_state.jsonl и .reports/fab_events.jsonl.

⸻

9) Инварианты CANON
	1.	FAB не пишет напрямую в Atlas.
	2.	Z-slice всегда связный (graph connectivity ≥ 0.5).
	3.	Никаких write-операций при stress > 0.7 или error_rate > 0.05.
	4.	Только S1 может менять режим FAB.
	5.	Canon может запретить commit независимо от FAB.

⸻

10) SLO / Приёмочные критерии

Метрика	Цель
mix() p95	≤ 10 мс при 1 k узлах
step() p95	≤ 5 мс
commit()	≤ 50 мс
Ошибка FAB0→FAB2	≤ 3 шага
fab_error_rate	≤ 0.05

DoD:
✅ Покрытие тестами ≥ 90%
✅ Метрики и события логируются
✅ Нулевой цикл (init→fill→mix→step→commit) проходит без ошибок
✅ CANON корректно блокирует запрещённые записи

⸻

11) Roadmap

Фаза	Цель	Состояние
Phase A (MVP)	ядро FAB + моки адаптеров	☐
Phase B (Coverage)	5D-MMR, диверсификация, точные метрики	☐
Phase C (Mirroring)	полная интеграция с Atlas E1–E4	☐


⸻

12) Итог

FAB — это сердце оперативного мышления AURIS.
Он соединяет уровни сознания, распределяет энергию и время, управляет смыслом и точностью, создавая живую динамическую память в движении.

«FAB — не просто шина данных.
Это нервная система разума, в которой мысль становится действием.»
