import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { CalendarPlus, ChevronLeft, ChevronRight, Clock3, Copy, Users } from 'lucide-react';

import { Avatar, RoleBadge } from '../common.jsx';
import {
  AVAILABLE_CARD_STYLE,
  EVENT_STYLES,
  buildDayEventMap,
  previewNote,
} from '../../scheduleConfig.js';

function shiftWeek(weekStart, offsetDays) {
  const [year, month, day] = weekStart.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

function WeekSwitcher({ selectedWeekStart, weekRangeLabel, canGoPreviousWeek, onWeekChange }) {
  return (
    <div className="inline-grid grid-cols-[44px_minmax(150px,1fr)_44px] items-center overflow-hidden rounded-xl border border-bf-cream/10 bg-[#101826]/90 shadow-[0_10px_26px_rgba(0,0,0,0.18)]">
      <button
        className="grid h-11 place-items-center border-r border-bf-cream/10 text-bf-cream/72 transition hover:bg-bf-orange/12 hover:text-bf-orange disabled:cursor-not-allowed disabled:text-bf-cream/22 disabled:hover:bg-transparent"
        type="button"
        onClick={() => onWeekChange(shiftWeek(selectedWeekStart, -7))}
        disabled={!canGoPreviousWeek}
        aria-label="Предыдущая неделя"
      >
        <ChevronLeft size={18} />
      </button>
      <div className="px-4 text-center text-sm font-black tabular-nums text-slate-100">
        {weekRangeLabel}
      </div>
      <button
        className="grid h-11 place-items-center border-l border-bf-cream/10 text-bf-cream/72 transition hover:bg-bf-orange/12 hover:text-bf-orange"
        type="button"
        onClick={() => onWeekChange(shiftWeek(selectedWeekStart, 7))}
        aria-label="Следующая неделя"
      >
        <ChevronRight size={18} />
      </button>
    </div>
  );
}

function HeroBanner({ hasPlayerProfile, canAdd, canEditSelectedWeek, onAdd, onCopy }) {
  return (
    <section className="glass-panel hero-banner relative mt-4 overflow-hidden rounded-xl border-bf-orange/45 px-6 py-6 lg:px-8">
      <div className="relative z-10 grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="grid gap-3 lg:max-w-[440px]">
          <div className="text-sm font-black uppercase text-bf-orange">Black Flock team</div>
          <h1 className="text-5xl font-black uppercase leading-none text-slate-100 max-md:text-4xl">
            Weekly roster
          </h1>
        </div>

        <div className="relative z-10 flex flex-wrap justify-self-start gap-3 lg:justify-self-end">
          {hasPlayerProfile ? (
            <>
              {canAdd ? (
                <button
                  className="inline-flex min-h-11 items-center gap-3 rounded-xl bg-[#f4f7fb] px-6 font-black text-[#151b26] shadow-[0_8px_18px_rgba(0,0,0,0.14)] transition hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_10px_22px_rgba(0,0,0,0.18)]"
                  type="button"
                  onClick={() => onAdd(null)}
                >
                  <CalendarPlus size={20} />
                  Добавить время
                </button>
              ) : !canEditSelectedWeek ? (
                <span className="rounded-full border border-bf-cream/10 bg-black/30 px-4 py-3 font-bold text-bf-cream/70">
                  Архивная неделя
                </span>
              ) : null}
              <button
                className="inline-flex min-h-11 items-center gap-3 rounded-xl bg-[#f4f7fb] px-6 font-black text-[#151b26] shadow-[0_8px_18px_rgba(0,0,0,0.14)] transition hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_10px_22px_rgba(0,0,0,0.18)]"
                type="button"
                onClick={onCopy}
              >
                <Copy size={19} />
                Скопировать расписание
              </button>
            </>
          ) : (
            <span className="rounded-full border border-bf-cream/10 bg-black/30 px-4 py-3 font-bold text-bf-cream/70">
              Аккаунт не привязан к игроку
            </span>
          )}
        </div>
      </div>
    </section>
  );
}

function PlayerRow({ player }) {
  return (
    <div className="flex h-full min-w-0 items-center gap-2.5 px-4 py-2">
      <Avatar src={player.avatarUrl} alt={player.name} fallbackLabel={player.name} className="h-10 w-10 object-cover" />
      <div className="min-w-0">
        <div className="truncate text-sm font-black text-slate-100">{player.name}</div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          <RoleBadge role={player.role} color={player.roleColor} className="max-w-28 truncate" />
          {player.canEdit ? (
            <span className="rounded-full border border-bf-orange/30 bg-bf-orange/10 px-2 py-0.5 text-xs font-bold text-bf-orange">
              Вы
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function EventCard({ event, onEdit, onNoteHoverStart, onNoteHoverEnd }) {
  const eventStyle = EVENT_STYLES[event.eventType] || EVENT_STYLES.fallback;
  const isUnavailable = event.slotType === 'unavailable';
  const isFullDayAvailable = event.slotType === 'full_day_available';
  const isTentative = event.slotType === 'tentative';
  const isAllDayStatus = isUnavailable || isFullDayAvailable || isTentative;
  const style = isUnavailable
    ? EVENT_STYLES.unavailable
    : isFullDayAvailable
      ? EVENT_STYLES.full_day_available
      : isTentative
        ? EVENT_STYLES.tentative
      : AVAILABLE_CARD_STYLE;
  const Icon = isUnavailable
    ? EVENT_STYLES.unavailable.icon
    : isFullDayAvailable
      ? EVENT_STYLES.full_day_available.icon
      : isTentative
        ? EVENT_STYLES.tentative.icon
      : eventStyle.icon;
  const editableProps = event.canEdit
    ? {
        role: 'button',
        tabIndex: 0,
        'aria-label': 'Редактировать событие',
        onClick: () => onEdit(event),
        onKeyDown: (keyboardEvent) => {
          if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') {
            keyboardEvent.preventDefault();
            onEdit(event);
          }
        },
      }
    : {};

  return (
    <motion.article
      whileHover={{ scale: 1.015 }}
      className={`group relative z-0 max-w-full rounded-xl border ${style.border} ${style.bg} ${style.glow} p-2 transition hover:z-30 ${
        event.canEdit ? 'cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bf-orange' : ''
      }`}
      onMouseEnter={(mouseEvent) => {
        if (event.note) {
          onNoteHoverStart(event.note, mouseEvent.currentTarget.getBoundingClientRect());
        }
      }}
      onMouseLeave={() => {
        if (event.note) {
          onNoteHoverEnd();
        }
      }}
      {...editableProps}
    >
      <div className="flex min-w-0 items-center gap-2">
        <Icon className={`${style.text} shrink-0`} size={isAllDayStatus ? 16 : 17} />
        <div className="min-w-0 flex-1">
          {isAllDayStatus ? (
            <>
              <div className={`whitespace-normal break-words text-[11px] font-black uppercase leading-tight ${style.text}`}>
                {isFullDayAvailable ? 'Свободен весь день' : isTentative ? 'Не уверен' : 'Не могу в этот день'}
              </div>
              {event.note ? (
                <div className="relative mt-1">
                  <p className="line-clamp-1 text-[11px] font-medium leading-tight text-bf-cream/60">
                    {previewNote(event.note)}
                  </p>
                </div>
              ) : null}
            </>
          ) : (
            <>
              <div className={`text-[11px] font-black leading-tight ${style.text}`}>{event.timeRange}</div>
              {event.note ? (
                <div className="relative mt-1">
                  <p className="line-clamp-1 text-[11px] font-medium leading-tight text-bf-cream/60">
                    {previewNote(event.note)}
                  </p>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </motion.article>
  );
}

function Legend({ eventTypes }) {
  return (
    <section className="glass-panel mt-4 rounded-xl p-4">
      <div className="mb-4 text-sm font-black uppercase text-bf-orange">Event legend</div>
      <div className="grid grid-cols-4 gap-3 border-t border-bf-cream/10 pt-4 max-lg:grid-cols-2 max-sm:grid-cols-1">
      {eventTypes.map((eventType) => {
        const style = EVENT_STYLES[eventType.value] || EVENT_STYLES.fallback;
        const Icon = style.icon;
        return (
          <div key={eventType.value} className="flex items-center gap-3 border-r border-bf-cream/10 pr-3 last:border-r-0 last:pr-0 max-sm:border-r-0 max-sm:pr-0">
            <div className={`grid h-9 w-9 place-items-center rounded-xl border ${style.border} ${style.bg}`}>
              <Icon className={style.text} size={17} />
            </div>
            <div>
              <div className={`text-xs font-black ${style.text}`}>{eventType.label}</div>
              <div className="text-[11px] text-bf-cream/52">{eventType.description}</div>
            </div>
          </div>
        );
      })}
      </div>
    </section>
  );
}

function RosterTable({
  days,
  players,
  slots,
  dayEventTypes,
  selectedWeekStart,
  weekRangeLabel,
  canGoPreviousWeek,
  canEditSelectedWeek,
  onWeekChange,
  onAdd,
  onEdit,
  onNoteHoverStart,
  onNoteHoverEnd,
  lastUpdated,
}) {
  const dayEventMap = useMemo(() => buildDayEventMap(dayEventTypes), [dayEventTypes]);

  const slotsByCell = useMemo(() => {
    const grouped = new Map();
    slots.forEach((slot) => {
      const key = `${slot.playerId}:${slot.dayOfWeek}`;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(slot);
    });
    return grouped;
  }, [slots]);

  return (
    <section className="glass-panel mt-4 rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between gap-4 max-md:flex-col max-md:items-stretch">
        <div className="flex items-center gap-3 text-lg font-black uppercase text-slate-100">
          <Users className="text-bf-orange" size={22} />
          Расписание на неделю
        </div>
        <WeekSwitcher
          selectedWeekStart={selectedWeekStart}
          weekRangeLabel={weekRangeLabel}
          canGoPreviousWeek={canGoPreviousWeek}
          onWeekChange={onWeekChange}
        />
      </div>

      <div className="roster-scroll overflow-x-auto">
        <div className="grid min-w-[1180px] grid-cols-[180px_repeat(7,minmax(134px,1fr))] overflow-visible rounded-xl border border-bf-cream/10 bg-[#182231]/75">
          <div className="grid min-h-[84px] content-center border-b border-r border-bf-cream/10 bg-[#151f2e]/78 px-4 py-4">
            <div className="flex items-center gap-2 font-black uppercase text-slate-100">
              <Users size={19} className="text-bf-orange" />
              Игроки
            </div>
          </div>
          {days.map((day) => {
            const dayEvent = dayEventMap.get(day.value);
            const hasDayType = Boolean(dayEvent?.eventType);
            const style = EVENT_STYLES[dayEvent?.eventType] || EVENT_STYLES.fallback;
            const Icon = style.icon;

            return (
              <div
                key={day.value}
                className={`grid min-h-[84px] place-items-center border-b border-r border-bf-cream/10 bg-[#151f2e]/78 px-2.5 pt-4 pb-3 text-center last:border-r-0 ${
                  day.isToday ? 'day-header-today' : ''
                }`}
              >
                <div className="grid justify-items-center gap-1.5">
                  <div className="text-sm font-black text-slate-100">{day.label}</div>
                  <div className="text-xs font-semibold text-bf-cream/52">{day.date}</div>
                  <div
                    className={`mt-1 inline-flex max-w-full items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-black ${
                      hasDayType
                        ? `${style.border} ${style.bg} ${style.text}`
                        : 'border-bf-cream/10 bg-[#202b40]/70 text-bf-cream/35'
                    }`}
                    title={hasDayType ? 'Тип события задан админом для всего дня' : 'Админ не выбрал тип события для этого дня'}
                  >
                    {hasDayType ? <Icon size={12} /> : <Clock3 size={12} />}
                    <span className="truncate">{hasDayType ? dayEvent.eventLabel : 'No type'}</span>
                  </div>
                </div>
              </div>
            );
          })}

          {players.map((player) => (
            <div key={player.id} className="contents">
              <div className="min-h-[60px] border-b border-r border-bf-cream/10 bg-[#151f2e]/78">
                <PlayerRow player={player} />
              </div>
              {days.map((day) => {
                const cellSlots = slotsByCell.get(`${player.id}:${day.value}`) || [];
                const isUnavailable = cellSlots.some((slot) => slot.slotType === 'unavailable');
                const isFullDayAvailable = cellSlots.some((slot) => slot.slotType === 'full_day_available');
                const isTentative = cellSlots.some((slot) => slot.slotType === 'tentative');
                return (
                  <div
                    key={`${player.id}-${day.value}`}
                    className={`relative flex min-h-[60px] items-center border-b border-r border-bf-cream/10 p-1.5 last:border-r-0 ${
                      isUnavailable ? 'bg-[#4d202d]/78' : isFullDayAvailable ? 'bg-[#17382f]/78' : isTentative ? 'bg-[#3f2c22]/78' : 'bg-[#151f2e]/82'
                    }`}
                  >
                    {cellSlots.length ? (
                      <div className="grid w-full gap-1.5">
                        {cellSlots.map((slot) => (
                          <EventCard
                            key={slot.id}
                            event={slot}
                            onEdit={onEdit}
                            onNoteHoverStart={onNoteHoverStart}
                            onNoteHoverEnd={onNoteHoverEnd}
                          />
                        ))}
                        {player.canEdit && canEditSelectedWeek ? (
                          <button
                            className="justify-self-end text-[11px] font-black text-bf-cream/45 transition hover:text-bf-orange"
                            type="button"
                            onClick={() => onAdd(day.value)}
                          >
                            + запись
                          </button>
                        ) : null}
                      </div>
                    ) : player.canEdit && canEditSelectedWeek ? (
                      <button
                        className="grid min-h-9 w-full place-items-center text-2xl font-light text-bf-cream/28 transition hover:scale-105 hover:text-bf-orange"
                        type="button"
                        onClick={() => onAdd(day.value)}
                        aria-label={`Добавить запись на ${day.label}`}
                      >
                        +
                      </button>
                    ) : (
                      <span className="grid min-h-9 w-full place-items-center text-2xl font-light text-bf-cream/18">+</span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <footer className="mt-4 flex justify-end gap-4 border-t border-bf-cream/10 pt-4 text-sm text-bf-cream/35">
        <span>Дата последнего обновления: {lastUpdated}</span>
      </footer>
    </section>
  );
}

export default function RosterPage({
  hasPlayerProfile,
  canAdd,
  canEditSelectedWeek,
  selectedWeekStart,
  weekRangeLabel,
  canGoPreviousWeek,
  days,
  players,
  slots,
  dayEventTypes,
  eventTypes,
  lastUpdated,
  onAdd,
  onEdit,
  onCopy,
  onWeekChange,
  onNoteHoverStart,
  onNoteHoverEnd,
}) {
  return (
    <>
      <HeroBanner
        hasPlayerProfile={hasPlayerProfile}
        canAdd={canAdd}
        canEditSelectedWeek={canEditSelectedWeek}
        onAdd={onAdd}
        onCopy={onCopy}
      />
      <RosterTable
        days={days}
        players={players}
        slots={slots}
        dayEventTypes={dayEventTypes}
        selectedWeekStart={selectedWeekStart}
        weekRangeLabel={weekRangeLabel}
        canGoPreviousWeek={canGoPreviousWeek}
        canEditSelectedWeek={canEditSelectedWeek}
        onWeekChange={onWeekChange}
        onAdd={onAdd}
        onEdit={onEdit}
        onNoteHoverStart={onNoteHoverStart}
        onNoteHoverEnd={onNoteHoverEnd}
        lastUpdated={lastUpdated}
      />
      <Legend eventTypes={eventTypes} />
    </>
  );
}
