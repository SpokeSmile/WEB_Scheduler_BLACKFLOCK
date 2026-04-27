import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  CalendarPlus,
  Clock3,
  Gamepad2,
  LogOut,
  MonitorPlay,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Search,
  Settings,
  Shield,
  Swords,
  Trash2,
  Trophy,
  Users,
  X,
} from 'lucide-react';

import { bootstrap, createSlot, deleteSlot, logout, updateSlot } from './api.js';

const EVENT_STYLES = {
  practice: {
    icon: Settings,
    border: 'border-orange-500/45',
    bg: 'bg-orange-500/10',
    text: 'text-orange-300',
    glow: 'shadow-[0_0_34px_rgba(255,122,0,0.16)]',
  },
  scrim: {
    icon: Swords,
    border: 'border-blue-400/45',
    bg: 'bg-blue-500/10',
    text: 'text-blue-300',
    glow: 'shadow-[0_0_34px_rgba(59,130,246,0.16)]',
  },
  vod_review: {
    icon: MonitorPlay,
    border: 'border-purple-400/45',
    bg: 'bg-purple-500/10',
    text: 'text-purple-300',
    glow: 'shadow-[0_0_34px_rgba(168,85,247,0.16)]',
  },
  match: {
    icon: Trophy,
    border: 'border-red-400/45',
    bg: 'bg-red-500/10',
    text: 'text-red-300',
    glow: 'shadow-[0_0_34px_rgba(239,68,68,0.16)]',
  },
  unavailable: {
    icon: AlertTriangle,
    border: 'border-red-300/45',
    bg: 'bg-red-500/20',
    text: 'text-red-200',
    glow: 'shadow-[0_0_34px_rgba(239,68,68,0.18)]',
  },
  fallback: {
    icon: Clock3,
    border: 'border-orange-500/35',
    bg: 'bg-orange-500/10',
    text: 'text-orange-200',
    glow: 'shadow-[0_0_28px_rgba(255,122,0,0.1)]',
  },
};

function formatClock(timeZone) {
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone,
  }).format(new Date());
}

function useClocks() {
  const [clocks, setClocks] = useState({
    utc: '--:--:--',
    gmt3: '--:--:--',
    cest: '--:--:--',
  });

  useEffect(() => {
    const update = () => {
      setClocks({
        utc: formatClock('UTC'),
        gmt3: formatClock('Europe/Moscow'),
        cest: formatClock('Etc/GMT-2'),
      });
    };

    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, []);

  return clocks;
}

function timeChoices(startHour, endHour) {
  return Array.from({ length: endHour - startHour + 1 }, (_, index) => {
    const hour = startHour + index;
    return {
      value: hour * 60,
      label: `${String(hour).padStart(2, '0')}:00`,
    };
  });
}

function Header({ user }) {
  const clocks = useClocks();

  async function handleLogout() {
    const response = await logout();
    window.location.href = response.redirectUrl || '/login/';
  }

  return (
    <header className="glass-panel grid min-h-20 grid-cols-[minmax(220px,1fr)_auto_minmax(220px,1fr)] items-center gap-5 rounded-[22px] px-5 py-3 max-lg:grid-cols-1">
      <a className="flex w-max items-center gap-3 font-black uppercase tracking-normal text-slate-100" href="/">
        <span className="brand-emblem" aria-hidden="true" />
        <span>Black Flock</span>
      </a>

      <div className="grid grid-cols-3 gap-4 max-sm:grid-cols-1">
        {[
          ['UTC', clocks.utc],
          ['GMT+3', clocks.gmt3],
          ['CEST', clocks.cest],
        ].map(([label, value]) => (
          <div key={label} className="min-w-32 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 py-2 shadow-inner">
            <div className="text-xs font-bold uppercase text-bf-cream/55">{label}</div>
            <div className="text-lg font-black text-slate-100">{value}</div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-end gap-3 max-lg:justify-between">
        <div className="flex items-center gap-2 rounded-full border border-bf-cream/10 bg-black/30 px-3 py-2">
          {user.avatarUrl ? (
            <img className="h-7 w-7 rounded-full object-cover" src={user.avatarUrl} alt={user.username} />
          ) : (
            <span className="grid h-7 w-7 place-items-center rounded-full bg-bf-steel/45 text-xs font-black">
              {user.username.slice(0, 1).toUpperCase()}
            </span>
          )}
          <span className="max-w-28 truncate font-semibold text-bf-cream/80">{user.username}</span>
        </div>
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-2xl border border-bf-orange px-4 font-black text-slate-100 transition hover:-translate-y-0.5 hover:shadow-[0_0_28px_rgba(255,122,0,0.25)]"
          type="button"
          onClick={handleLogout}
        >
          <LogOut size={18} />
          Выйти
        </button>
      </div>
    </header>
  );
}

function HeroBanner({ canAdd, onAdd }) {
  return (
    <section className="glass-panel relative mt-5 min-h-44 overflow-hidden rounded-[22px] border-bf-orange/50 px-9 py-8">
      <div className="hero-figure" aria-hidden="true" />
      <div className="relative z-10 flex items-center justify-between gap-6 max-md:flex-col max-md:items-start">
        <div>
          <div className="text-sm font-black uppercase text-bf-orange">Black Flock squad</div>
          <h1 className="mt-3 text-5xl font-black uppercase leading-none text-slate-100 max-md:text-4xl">
            Weekly roster
          </h1>
          <p className="mt-4 text-lg text-bf-cream/62">Расписание команды на неделю</p>
        </div>
        {canAdd ? (
          <button
            className="inline-flex min-h-12 items-center gap-3 rounded-2xl bg-gradient-to-b from-orange-400 to-bf-orange px-6 font-black text-black shadow-[0_16px_42px_rgba(255,122,0,0.28)] transition hover:-translate-y-0.5 hover:shadow-[0_20px_54px_rgba(255,122,0,0.38)]"
            type="button"
            onClick={() => onAdd(null)}
          >
            <CalendarPlus size={20} />
            Добавить время
          </button>
        ) : (
          <span className="rounded-full border border-bf-cream/10 bg-black/30 px-4 py-3 font-bold text-bf-cream/70">
            Аккаунт не привязан к игроку
          </span>
        )}
      </div>
    </section>
  );
}

function PlayerRow({ player }) {
  return (
    <div className="flex h-full min-w-0 items-center gap-3 px-5 py-3">
      {player.avatarUrl ? (
        <img className="h-12 w-12 rounded-full border border-bf-cream/15 object-cover" src={player.avatarUrl} alt={player.name} />
      ) : (
        <div className="grid h-12 w-12 place-items-center rounded-full border border-bf-cream/15 bg-gradient-to-br from-bf-orange/70 to-bf-steel/70 text-lg font-black text-bf-cream">
          {player.initial}
        </div>
      )}
      <div className="min-w-0">
        <div className="truncate font-black text-slate-100">{player.name}</div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {player.role ? (
            <span className="max-w-28 truncate rounded-full border border-bf-cream/10 bg-bf-steel/20 px-2 py-0.5 text-xs font-bold text-bf-cream/62">
              {player.role}
            </span>
          ) : null}
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

function EventCard({ event, onEdit }) {
  const style = EVENT_STYLES[event.slotType === 'unavailable' ? 'unavailable' : event.eventType] || EVENT_STYLES.fallback;
  const Icon = style.icon;
  const isUnavailable = event.slotType === 'unavailable';

  return (
    <motion.article
      whileHover={{ scale: 1.02 }}
      className={`group rounded-xl border ${style.border} ${style.bg} ${style.glow} p-3 transition`}
    >
      <div className="flex items-start gap-3">
        <Icon className={`${style.text} mt-1 shrink-0`} size={20} />
        <div className="min-w-0 flex-1">
          {isUnavailable ? (
            <div className={`text-sm font-black ${style.text}`}>Не могу в этот день</div>
          ) : (
            <div className={`text-sm font-black ${style.text}`}>{event.timeRange}</div>
          )}
          <div className="mt-1 truncate text-sm font-black text-slate-100">{event.label}</div>
          {event.note ? <p className="mt-1 line-clamp-2 text-xs font-medium text-bf-cream/60">{event.note}</p> : null}
        </div>
        {event.canEdit ? (
          <button
            className="rounded-lg border border-bf-cream/10 p-1.5 text-bf-cream/55 opacity-0 transition hover:border-bf-orange/40 hover:text-bf-orange group-hover:opacity-100"
            type="button"
            onClick={() => onEdit(event)}
            aria-label="Редактировать событие"
          >
            <Pencil size={15} />
          </button>
        ) : null}
      </div>
    </motion.article>
  );
}

function RosterTable({ days, players, slots, eventTypes, filter, onFilterChange, onAdd, onEdit, lastUpdated }) {
  const filteredPlayers = useMemo(() => {
    const query = filter.trim().toLowerCase();
    if (!query) return players;
    return players.filter((player) => `${player.name} ${player.role}`.toLowerCase().includes(query));
  }, [filter, players]);

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
    <section className="glass-panel mt-5 rounded-[22px] p-5">
      <div className="mb-4 flex items-center justify-between gap-4 max-md:flex-col max-md:items-stretch">
        <div className="flex items-center gap-3 text-lg font-black uppercase text-slate-100">
          <Users className="text-bf-orange" size={22} />
          Игроки
        </div>
        <label className="relative w-full max-w-xs max-md:max-w-none">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-bf-cream/42" size={18} />
          <input
            className="h-11 w-full rounded-2xl border border-bf-cream/10 bg-black/30 pl-10 pr-4 text-sm font-semibold text-slate-100 outline-none transition placeholder:text-bf-cream/35 focus:border-bf-orange/50 focus:shadow-[0_0_0_4px_rgba(255,122,0,0.12)]"
            value={filter}
            onChange={(event) => onFilterChange(event.target.value)}
            placeholder="Фильтр по нику или роли"
          />
        </label>
      </div>

      <div className="roster-scroll overflow-x-auto">
        <div className="grid min-w-[1240px] grid-cols-[194px_repeat(7,minmax(150px,1fr))] overflow-hidden rounded-2xl border border-bf-cream/10 bg-black/20">
          <div className="grid min-h-20 content-center border-b border-r border-bf-cream/10 bg-black/20 px-5">
            <div className="flex items-center gap-2 font-black uppercase text-slate-100">
              <Users size={19} className="text-bf-orange" />
              Игроки
            </div>
          </div>
          {days.map((day) => (
            <div key={day.value} className="grid min-h-20 place-items-center border-b border-r border-bf-cream/10 bg-black/20 px-3 text-center last:border-r-0">
              <div>
                <div className="text-sm font-black text-slate-100">{day.label}</div>
                <div className="mt-1 text-xs font-semibold text-bf-cream/52">{day.date}</div>
              </div>
            </div>
          ))}

          {filteredPlayers.map((player) => (
            <div key={player.id} className="contents">
              <div className="min-h-[76px] border-b border-r border-bf-cream/10 bg-black/20">
                <PlayerRow player={player} />
              </div>
              {days.map((day) => {
                const cellSlots = slotsByCell.get(`${player.id}:${day.value}`) || [];
                const isUnavailable = cellSlots.some((slot) => slot.slotType === 'unavailable');
                return (
                  <div
                    key={`${player.id}-${day.value}`}
                    className={`relative flex min-h-[76px] items-center border-b border-r border-bf-cream/10 p-2 last:border-r-0 ${
                      isUnavailable
                        ? 'bg-red-950/45 shadow-[inset_0_0_0_1px_rgba(239,68,68,0.28)]'
                        : 'bg-slate-950/42'
                    }`}
                  >
                    {cellSlots.length ? (
                      <div className="grid w-full gap-2">
                        {cellSlots.map((slot) => (
                          <EventCard key={slot.id} event={slot} onEdit={onEdit} />
                        ))}
                        {player.canEdit ? (
                          <button
                            className="justify-self-end text-xs font-black text-bf-cream/45 transition hover:text-bf-orange"
                            type="button"
                            onClick={() => onAdd(day.value)}
                          >
                            + запись
                          </button>
                        ) : null}
                      </div>
                    ) : player.canEdit ? (
                      <button
                        className="grid min-h-12 w-full place-items-center text-3xl font-light text-bf-cream/28 transition hover:scale-105 hover:text-bf-orange"
                        type="button"
                        onClick={() => onAdd(day.value)}
                        aria-label={`Добавить запись на ${day.label}`}
                      >
                        +
                      </button>
                    ) : (
                      <span className="grid min-h-12 w-full place-items-center text-3xl font-light text-bf-cream/18">+</span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <Legend eventTypes={eventTypes} />

      <footer className="mt-5 flex justify-between gap-4 border-t border-bf-cream/10 pt-5 text-sm text-bf-cream/48 max-md:flex-col">
        <span>Все время указано по часовому поясу UTC+3</span>
        <span>Последнее обновление: {lastUpdated}</span>
      </footer>
    </section>
  );
}

function Legend({ eventTypes }) {
  return (
    <div className="mt-5 grid grid-cols-4 gap-4 border-t border-bf-cream/10 pt-5 max-lg:grid-cols-2 max-sm:grid-cols-1">
      {eventTypes.map((eventType) => {
        const style = EVENT_STYLES[eventType.value] || EVENT_STYLES.fallback;
        const Icon = style.icon;
        return (
          <div key={eventType.value} className="flex items-center gap-3 border-r border-bf-cream/10 last:border-r-0 max-sm:border-r-0">
            <div className={`grid h-11 w-11 place-items-center rounded-xl border ${style.border} ${style.bg}`}>
              <Icon className={style.text} size={20} />
            </div>
            <div>
              <div className={`text-sm font-black ${style.text}`}>{eventType.label}</div>
              <div className="text-xs text-bf-cream/52">{eventType.description}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function EventModal({ event, day, days, eventTypes, onClose, onSaved, onDeleted }) {
  const isEditing = Boolean(event);
  const [slotType, setSlotType] = useState(event?.slotType || 'available');
  const [eventType, setEventType] = useState(event?.eventType || eventTypes[0]?.value || 'practice');
  const [dayOfWeek, setDayOfWeek] = useState(event?.dayOfWeek ?? day ?? days[0]?.value ?? 0);
  const [startTimeMinutes, setStartTimeMinutes] = useState(event?.startTimeMinutes ?? 1140);
  const [endTimeMinutes, setEndTimeMinutes] = useState(event?.endTimeMinutes ?? 1260);
  const [note, setNote] = useState(event?.note || '');
  const [errors, setErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault();
    setIsSaving(true);
    setErrors({});

    const payload = {
      slotType,
      eventType,
      dayOfWeek,
      startTimeMinutes,
      endTimeMinutes,
      note,
    };

    if (slotType === 'unavailable') {
      payload.eventType = '';
      payload.startTimeMinutes = null;
      payload.endTimeMinutes = null;
    }

    try {
      const response = isEditing ? await updateSlot(event.id, payload) : await createSlot(payload);
      onSaved(response.slot);
    } catch (error) {
      setErrors(error.payload?.errors || { __all__: [error.message] });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (!isEditing) return;
    setIsSaving(true);
    try {
      await deleteSlot(event.id);
      onDeleted(event.id);
    } catch (error) {
      setErrors(error.payload?.errors || { __all__: [error.message] });
    } finally {
      setIsSaving(false);
    }
  }

  const startChoices = timeChoices(0, 23);
  const endChoices = timeChoices(1, 24);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm">
      <motion.form
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="w-full max-w-2xl rounded-[24px] border border-bf-cream/12 bg-[#0d1420] p-6 shadow-panel"
        onSubmit={handleSubmit}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm font-black uppercase text-bf-orange">Event editor</div>
            <h2 className="mt-1 text-2xl font-black uppercase text-slate-100">
              {isEditing ? 'Редактировать событие' : 'Добавить событие'}
            </h2>
          </div>
          <button
            className="rounded-xl border border-bf-cream/10 p-2 text-bf-cream/60 transition hover:border-bf-orange/40 hover:text-bf-orange"
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
          >
            <X size={20} />
          </button>
        </div>

        {errors.__all__ ? <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">{errors.__all__.join(', ')}</div> : null}

        <div className="mt-6 grid gap-5">
          <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
            <button
              className={`rounded-2xl border px-4 py-3 font-black transition ${
                slotType === 'available'
                  ? 'border-bf-orange bg-bf-orange/15 text-bf-orange'
                  : 'border-bf-cream/10 bg-black/20 text-bf-cream/62'
              }`}
              type="button"
              onClick={() => setSlotType('available')}
            >
              Диапазон времени
            </button>
            <button
              className={`rounded-2xl border px-4 py-3 font-black transition ${
                slotType === 'unavailable'
                  ? 'border-red-300/50 bg-red-500/15 text-red-100'
                  : 'border-bf-cream/10 bg-black/20 text-bf-cream/62'
              }`}
              type="button"
              onClick={() => setSlotType('unavailable')}
            >
              Не могу в этот день
            </button>
          </div>

          <label className="grid gap-2 text-sm font-black text-bf-cream/70">
            День
            <select
              className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none focus:border-bf-orange/50"
              value={dayOfWeek}
              onChange={(inputEvent) => setDayOfWeek(Number(inputEvent.target.value))}
            >
              {days.map((dayOption) => (
                <option key={dayOption.value} value={dayOption.value}>
                  {dayOption.label} - {dayOption.date}
                </option>
              ))}
            </select>
          </label>

          {slotType === 'available' ? (
            <>
              <div>
                <div className="mb-2 text-sm font-black text-bf-cream/70">Тип события</div>
                <div className="grid grid-cols-4 gap-3 max-md:grid-cols-2">
                  {eventTypes.map((type) => {
                    const style = EVENT_STYLES[type.value] || EVENT_STYLES.fallback;
                    const Icon = style.icon;
                    const selected = eventType === type.value;
                    return (
                      <button
                        key={type.value}
                        className={`rounded-2xl border p-3 text-left transition ${
                          selected ? `${style.border} ${style.bg} ${style.glow}` : 'border-bf-cream/10 bg-black/20'
                        }`}
                        type="button"
                        onClick={() => setEventType(type.value)}
                      >
                        <Icon className={selected ? style.text : 'text-bf-cream/45'} size={20} />
                        <div className={`mt-2 text-sm font-black ${selected ? style.text : 'text-bf-cream/62'}`}>
                          {type.label}
                        </div>
                      </button>
                    );
                  })}
                </div>
                {errors.event_type ? <div className="mt-2 text-sm text-red-200">{errors.event_type.join(', ')}</div> : null}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <label className="grid gap-2 text-sm font-black text-bf-cream/70">
                  С
                  <select
                    className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none focus:border-bf-orange/50"
                    value={startTimeMinutes}
                    onChange={(inputEvent) => setStartTimeMinutes(Number(inputEvent.target.value))}
                  >
                    {startChoices.map((choice) => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </select>
                  {errors.start_time_minutes ? <span className="text-red-200">{errors.start_time_minutes.join(', ')}</span> : null}
                </label>
                <label className="grid gap-2 text-sm font-black text-bf-cream/70">
                  До
                  <select
                    className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none focus:border-bf-orange/50"
                    value={endTimeMinutes}
                    onChange={(inputEvent) => setEndTimeMinutes(Number(inputEvent.target.value))}
                  >
                    {endChoices.map((choice) => (
                      <option key={choice.value} value={choice.value}>
                        {choice.label}
                      </option>
                    ))}
                  </select>
                  {errors.end_time_minutes ? <span className="text-red-200">{errors.end_time_minutes.join(', ')}</span> : null}
                </label>
              </div>
            </>
          ) : null}

          <label className="grid gap-2 text-sm font-black text-bf-cream/70">
            Комментарий
            <input
              className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none placeholder:text-bf-cream/35 focus:border-bf-orange/50"
              value={note}
              onChange={(inputEvent) => setNote(inputEvent.target.value)}
              placeholder="Дополнительная информация"
            />
          </label>
        </div>

        <div className="mt-6 flex flex-wrap justify-between gap-3">
          <div>
            {isEditing ? (
              <button
                className="inline-flex min-h-11 items-center gap-2 rounded-2xl border border-red-300/30 px-4 font-black text-red-100 transition hover:bg-red-500/10"
                type="button"
                disabled={isSaving}
                onClick={handleDelete}
              >
                <Trash2 size={18} />
                Удалить
              </button>
            ) : null}
          </div>
          <div className="flex gap-3">
            <button
              className="min-h-11 rounded-2xl border border-bf-cream/10 px-4 font-black text-bf-cream/70 transition hover:border-bf-orange/40"
              type="button"
              onClick={onClose}
            >
              Отмена
            </button>
            <button
              className="inline-flex min-h-11 items-center gap-2 rounded-2xl bg-gradient-to-b from-orange-400 to-bf-orange px-5 font-black text-black transition hover:-translate-y-0.5"
              type="submit"
              disabled={isSaving}
            >
              <Save size={18} />
              Сохранить
            </button>
          </div>
        </div>
      </motion.form>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('');
  const [modal, setModal] = useState(null);

  async function loadData() {
    setIsLoading(true);
    try {
      const response = await bootstrap();
      setData(response);
      setError('');
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function upsertSlot(slot) {
    setData((current) => ({
      ...current,
      slots: current.slots.some((existing) => existing.id === slot.id)
        ? current.slots.map((existing) => (existing.id === slot.id ? slot : existing))
        : [...current.slots, slot],
      lastUpdated: new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date()),
    }));
    setModal(null);
  }

  function removeSlot(id) {
    setData((current) => ({
      ...current,
      slots: current.slots.filter((slot) => slot.id !== id),
      lastUpdated: new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(new Date()),
    }));
    setModal(null);
  }

  if (isLoading) {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="glass-panel rounded-[22px] px-8 py-6 text-center">
          <RefreshCw className="mx-auto animate-spin text-bf-orange" />
          <div className="mt-3 font-black uppercase">Загрузка расписания</div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="glass-panel max-w-md rounded-[22px] px-8 py-6 text-center">
          <AlertTriangle className="mx-auto text-red-300" />
          <div className="mt-3 font-black uppercase">Не удалось загрузить расписание</div>
          <p className="mt-2 text-bf-cream/60">{error}</p>
          <button className="mt-5 rounded-2xl bg-bf-orange px-5 py-3 font-black text-black" type="button" onClick={loadData}>
            Повторить
          </button>
        </div>
      </main>
    );
  }

  const canAdd = Boolean(data.user.playerId);

  return (
    <main className="mx-auto min-h-screen w-[min(1500px,calc(100%_-_48px))] py-4 max-sm:w-[min(100%_-_20px,760px)]">
      <Header user={data.user} />
      <HeroBanner canAdd={canAdd} onAdd={(day) => setModal({ day })} />
      <RosterTable
        days={data.days}
        players={data.players}
        slots={data.slots}
        eventTypes={data.eventTypes}
        filter={filter}
        onFilterChange={setFilter}
        onAdd={(day) => setModal({ day })}
        onEdit={(event) => setModal({ event })}
        lastUpdated={data.lastUpdated}
      />
      {modal ? (
        <EventModal
          event={modal.event}
          day={modal.day}
          days={data.days}
          eventTypes={data.eventTypes}
          onClose={() => setModal(null)}
          onSaved={upsertSlot}
          onDeleted={removeSlot}
        />
      ) : null}
    </main>
  );
}
