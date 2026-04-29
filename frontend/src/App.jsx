import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  CalendarPlus,
  Check,
  Clock3,
  Crosshair,
  LogOut,
  MonitorPlay,
  Pencil,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Save,
  Settings,
  Swords,
  Trash2,
  Trophy,
  Users,
  X,
} from 'lucide-react';

import {
  bootstrap,
  changePassword,
  createSlot,
  deleteSlot,
  disconnectDiscord,
  logout,
  updateProfile,
  updateSlot,
} from './api.js';

const SIDEBAR_STORAGE_KEY = 'bf-sidebar-collapsed';

const EVENT_STYLES = {
  scrim: {
    icon: Swords,
    border: 'border-blue-400/45',
    bg: 'bg-blue-500/10',
    text: 'text-blue-300',
    glow: 'shadow-[0_0_12px_rgba(59,130,246,0.08)]',
  },
  competitive: {
    icon: Crosshair,
    border: 'border-orange-500/45',
    bg: 'bg-orange-500/10',
    text: 'text-orange-300',
    glow: 'shadow-[0_0_12px_rgba(243,112,30,0.08)]',
  },
  review: {
    icon: MonitorPlay,
    border: 'border-purple-400/45',
    bg: 'bg-purple-500/10',
    text: 'text-purple-300',
    glow: 'shadow-[0_0_12px_rgba(168,85,247,0.08)]',
  },
  tournament: {
    icon: Trophy,
    border: 'border-red-400/45',
    bg: 'bg-red-500/10',
    text: 'text-red-300',
    glow: 'shadow-[0_0_12px_rgba(239,68,68,0.08)]',
  },
  unavailable: {
    icon: AlertTriangle,
    border: 'border-red-300/45',
    bg: 'bg-red-500/28',
    text: 'text-red-200',
    glow: 'shadow-[0_0_14px_rgba(239,68,68,0.14)]',
  },
  full_day_available: {
    icon: Check,
    border: 'border-emerald-300/45',
    bg: 'bg-emerald-500/18',
    text: 'text-emerald-200',
    glow: 'shadow-[0_0_12px_rgba(16,185,129,0.12)]',
  },
  tentative: {
    icon: AlertTriangle,
    border: 'border-orange-300/45',
    bg: 'bg-orange-500/22',
    text: 'text-orange-200',
    glow: 'shadow-[0_0_14px_rgba(243,112,30,0.14)]',
  },
  fallback: {
    icon: Clock3,
    border: 'border-bf-cream/15',
    bg: 'bg-bf-steel/10',
    text: 'text-bf-cream/72',
    glow: 'shadow-[0_0_10px_rgba(75,96,127,0.08)]',
  },
};

const AVAILABLE_CARD_STYLE = {
  border: 'border-bf-cream/12',
  bg: 'bg-bf-steel/10',
  text: 'text-bf-cream/82',
  glow: 'shadow-[0_0_10px_rgba(75,96,127,0.07)]',
};

function formatClock(timeZone) {
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone,
  }).format(new Date());
}

function Avatar({ src, alt, fallbackLabel, className = '' }) {
  if (src) {
    return <img className={`rounded-full border border-bf-cream/15 ${className}`} src={src} alt={alt} />;
  }

  return (
    <div className={`grid place-items-center rounded-full border border-bf-cream/15 bg-black/30 ${className}`}>
      <img
        className="h-[70%] w-[70%] object-contain opacity-95"
        src="/static/design_assets/Logo.png"
        alt={fallbackLabel || 'Black Flock'}
      />
    </div>
  );
}

function useClocks() {
  const [clocks, setClocks] = useState({
    utc: '--:--',
    moscow: '--:--',
    cest: '--:--',
  });

  useEffect(() => {
    const update = () => {
      setClocks({
        utc: formatClock('UTC'),
        moscow: formatClock('Europe/Moscow'),
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

function discordFeedbackFromUrl(search) {
  const params = new URLSearchParams(search);
  const status = params.get('discord');
  const reason = params.get('reason');
  if (!status) return null;

  if (status === 'connected') {
    return { tone: 'success', text: 'Discord успешно подключен.' };
  }

  if (status === 'disconnected') {
    return { tone: 'success', text: 'Discord отвязан.' };
  }

  if (status === 'error') {
    const messages = {
      'already-linked': 'Этот Discord-аккаунт уже привязан к другому пользователю.',
      'invalid-state': 'Не удалось подтвердить запрос подключения Discord.',
      'missing-code': 'Discord не вернул код подключения.',
      'oauth-failed': 'Не удалось получить данные Discord. Повторите попытку.',
      'not-configured': 'Discord временно недоступен. Обратитесь к администратору.',
      'access_denied': 'Подключение Discord было отменено.',
    };
    return { tone: 'error', text: messages[reason] || 'Не удалось подключить Discord.' };
  }

  return null;
}

function buildDayEventMap(dayEventTypes = []) {
  const map = new Map();
  dayEventTypes.forEach((dayEvent) => {
    map.set(Number(dayEvent.dayOfWeek), dayEvent);
  });
  return map;
}

function hexToRgba(hexColor, alpha) {
  if (!hexColor || !/^#[0-9A-Fa-f]{6}$/.test(hexColor)) {
    return `rgba(232, 216, 201, ${alpha})`;
  }

  const red = Number.parseInt(hexColor.slice(1, 3), 16);
  const green = Number.parseInt(hexColor.slice(3, 5), 16);
  const blue = Number.parseInt(hexColor.slice(5, 7), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function roleBadgeStyle(color) {
  return {
    borderColor: hexToRgba(color, 0.35),
    backgroundColor: hexToRgba(color, 0.12),
    color,
  };
}

function RoleBadge({ role, color, className = '' }) {
  if (!role) return null;

  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[11px] font-bold ${className}`}
      style={roleBadgeStyle(color)}
    >
      {role}
    </span>
  );
}

function DiscordClouds({ displayTag }) {
  if (!displayTag) {
    return <div className="mt-2 text-bf-cream/42">Не подключен</div>;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      <span className="rounded-full border border-bf-cream/10 bg-bf-steel/18 px-3 py-1 text-sm font-semibold text-slate-100">
        {displayTag}
      </span>
    </div>
  );
}

function Header({ user }) {
  const clocks = useClocks();
  const isProfilePage = window.location.pathname.startsWith('/profile');

  async function handleLogout() {
    const response = await logout();
    window.location.href = response.redirectUrl || '/login/';
  }

  return (
    <header className="glass-panel grid min-h-16 grid-cols-[minmax(220px,1fr)_auto_minmax(220px,1fr)] items-center gap-5 rounded-[20px] px-5 py-2 max-lg:grid-cols-1">
      <a className="flex w-max items-center gap-3 font-black uppercase tracking-normal text-slate-100" href="/">
        <img className="brand-logo" src="/static/design_assets/Logo.png" alt="" />
        <span>Black Flock</span>
      </a>

      <div className="grid grid-cols-3 gap-3 max-sm:grid-cols-1">
        {[
          ['UTC', clocks.utc],
          ['Moscow', clocks.moscow],
          ['CEST', clocks.cest],
        ].map(([label, value]) => (
          <div key={label} className="min-w-28 rounded-xl border border-bf-cream/10 bg-black/30 px-4 py-2">
            <div className="text-xs font-bold uppercase text-bf-cream/55">{label}</div>
            <div className="text-base font-black text-slate-100">{value}</div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-end gap-3 max-lg:justify-between">
        <a
          className={`flex items-center gap-2 rounded-full border px-3 py-2 transition ${
            isProfilePage
              ? 'border-bf-orange/40 bg-bf-orange/10'
              : 'border-bf-cream/10 bg-black/30 hover:border-bf-orange/35 hover:bg-bf-orange/5'
          }`}
          href="/profile/"
          aria-label="Открыть профиль"
        >
          <Avatar src={user.avatarUrl} alt={user.username} fallbackLabel={user.username} className="h-7 w-7 object-cover" />
          <span className="max-w-28 truncate font-semibold text-bf-cream/80">{user.username}</span>
        </a>
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-bf-orange px-4 font-black text-slate-100 transition hover:-translate-y-0.5 hover:shadow-[0_0_14px_rgba(243,112,30,0.16)]"
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

function Sidebar({ pathname, collapsed, onToggle }) {
  const items = [
    {
      href: '/',
      label: 'Расписание',
      icon: Clock3,
      isActive: !pathname.startsWith('/team') && !pathname.startsWith('/profile'),
    },
    {
      href: '/team/',
      label: 'Состав',
      icon: Users,
      isActive: pathname.startsWith('/team'),
    },
    {
      href: '/profile/',
      label: 'Настройки',
      icon: Settings,
      isActive: pathname.startsWith('/profile'),
    },
  ];

  return (
    <aside className={`app-sidebar glass-panel xl:sticky xl:top-4 xl:self-start ${collapsed ? 'app-sidebar-collapsed' : ''}`}>
      <div className="sidebar-head">
        <a className="sidebar-brand" href="/" aria-label="Black Flock">
          <img className="brand-logo" src="/static/design_assets/Logo.png" alt="" />
          <div className={`sidebar-brand-meta ${collapsed ? 'xl:w-0 xl:opacity-0' : 'xl:w-auto xl:opacity-100'}`}>
            <div className="truncate text-sm font-black uppercase tracking-[0.18em] text-slate-100">Black Flock</div>
            <div className="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-bf-orange/85">Overwatch Team</div>
          </div>
        </a>
        <button
          className="sidebar-toggle hidden xl:inline-flex"
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? 'Развернуть меню' : 'Свернуть меню'}
          aria-pressed={collapsed}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Основная навигация">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <a
              key={item.href}
              className={`sidebar-nav-link ${item.isActive ? 'sidebar-nav-link-active' : ''}`}
              href={item.href}
              aria-current={item.isActive ? 'page' : undefined}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={18} />
              <span className={`sidebar-link-label ${collapsed ? 'xl:w-0 xl:opacity-0' : 'xl:w-auto xl:opacity-100'}`}>
                {item.label}
              </span>
              {collapsed ? <span className="sidebar-link-tooltip">{item.label}</span> : null}
            </a>
          );
        })}
      </nav>

      <div className={`sidebar-footer ${collapsed ? 'xl:items-center' : ''}`}>
        <div className="sidebar-footer-mark">
          <img src="/static/design_assets/Logo.png" alt="" />
        </div>
        <div className={`text-sm font-black uppercase text-bf-orange ${collapsed ? 'xl:hidden' : ''}`}>Black Flock</div>
        <div className={`text-[11px] font-bold uppercase tracking-[0.18em] text-bf-cream/36 ${collapsed ? 'xl:hidden' : ''}`}>Together we strike</div>
      </div>
    </aside>
  );
}

function HeroBanner({ canAdd, onAdd }) {
  return (
    <section className="glass-panel hero-banner relative mt-4 overflow-hidden rounded-[22px] border-bf-orange/45 px-6 py-6 lg:px-8">
      <div className="relative z-10 grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="grid gap-3 lg:max-w-[440px]">
          <div className="text-sm font-black uppercase text-bf-orange">Black Flock team</div>
          <h1 className="text-5xl font-black uppercase leading-none text-slate-100 max-md:text-4xl">
            Weekly roster
          </h1>
        </div>

        <div className="relative z-10 justify-self-start lg:justify-self-end">
          {canAdd ? (
            <button
              className="inline-flex min-h-11 items-center gap-3 rounded-xl bg-bf-orange px-6 font-black text-black shadow-[0_8px_18px_rgba(243,112,30,0.16)] transition hover:-translate-y-0.5 hover:shadow-[0_10px_22px_rgba(243,112,30,0.2)]"
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
      </div>
    </section>
  );
}

function TeamBanner() {
  return (
    <section className="glass-panel hero-banner relative mt-4 overflow-hidden rounded-[22px] border-bf-orange/45 px-6 py-6 lg:px-8">
      <div className="relative z-10 grid gap-2 lg:max-w-[520px]">
        <div className="text-sm font-black uppercase text-bf-orange">Black Flock team</div>
        <h1 className="whitespace-nowrap text-4xl font-black uppercase leading-none text-slate-100 max-md:text-3xl">
          Состав команды
        </h1>
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

function EventCard({ event, onEdit }) {
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

  return (
    <motion.article
      whileHover={{ scale: 1.015 }}
      className={`group relative max-w-full rounded-lg border ${style.border} ${style.bg} ${style.glow} p-2 transition`}
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
                  <p className="line-clamp-1 text-[11px] font-medium leading-tight text-bf-cream/60" title={event.note}>
                    {event.note}
                  </p>
                  <div
                    className="pointer-events-none absolute left-0 top-full z-[90] mt-2 hidden min-w-[180px] max-w-[260px] rounded-xl border border-white/10 px-3 py-2 text-[12px] font-medium leading-relaxed text-white shadow-[0_18px_40px_rgba(0,0,0,0.72)] group-hover:block"
                    style={{ backgroundColor: '#000000', opacity: 1 }}
                  >
                    {event.note}
                  </div>
                </div>
              ) : null}
            </>
          ) : (
            <>
              <div className={`text-[11px] font-black leading-tight ${style.text}`}>{event.timeRange}</div>
              {event.note ? (
                <div className="relative mt-1">
                  <p className="line-clamp-1 text-[11px] font-medium leading-tight text-bf-cream/60" title={event.note}>
                    {event.note}
                  </p>
                  <div
                    className="pointer-events-none absolute left-0 top-full z-[90] mt-2 hidden min-w-[180px] max-w-[260px] rounded-xl border border-white/10 px-3 py-2 text-[12px] font-medium leading-relaxed text-white shadow-[0_18px_40px_rgba(0,0,0,0.72)] group-hover:block"
                    style={{ backgroundColor: '#000000', opacity: 1 }}
                  >
                    {event.note}
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>
        {event.canEdit ? (
          <button
            className="absolute right-1 top-1 rounded-md border border-bf-cream/10 bg-black/40 p-1 text-bf-cream/55 opacity-0 transition hover:border-bf-orange/40 hover:text-bf-orange group-hover:opacity-100"
            type="button"
            onClick={() => onEdit(event)}
            aria-label="Редактировать событие"
          >
            <Pencil size={13} />
          </button>
        ) : null}
      </div>
    </motion.article>
  );
}

function Legend({ eventTypes }) {
  return (
    <section className="glass-panel mt-4 rounded-[20px] p-4">
      <div className="mb-4 text-sm font-black uppercase text-bf-orange">Event legend</div>
      <div className="grid grid-cols-4 gap-3 border-t border-bf-cream/10 pt-4 max-lg:grid-cols-2 max-sm:grid-cols-1">
      {eventTypes.map((eventType) => {
        const style = EVENT_STYLES[eventType.value] || EVENT_STYLES.fallback;
        const Icon = style.icon;
        return (
          <div key={eventType.value} className="flex items-center gap-3 border-r border-bf-cream/10 pr-3 last:border-r-0 last:pr-0 max-sm:border-r-0 max-sm:pr-0">
            <div className={`grid h-9 w-9 place-items-center rounded-lg border ${style.border} ${style.bg}`}>
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
  onAdd,
  onEdit,
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
    <section className="glass-panel mt-4 rounded-[20px] p-4">
      <div className="mb-3 flex items-center justify-between gap-4 max-md:flex-col max-md:items-stretch">
        <div className="flex items-center gap-3 text-lg font-black uppercase text-slate-100">
          <Users className="text-bf-orange" size={22} />
          Игроки
        </div>
      </div>

      <div className="roster-scroll overflow-x-auto">
        <div className="grid min-w-[1180px] grid-cols-[180px_repeat(7,minmax(134px,1fr))] overflow-visible rounded-2xl border border-bf-cream/10 bg-black/20">
          <div className="grid min-h-[84px] content-center border-b border-r border-bf-cream/10 bg-black/20 px-4 py-4">
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
                className="grid min-h-[84px] place-items-center border-b border-r border-bf-cream/10 bg-black/20 px-2.5 pt-4 pb-3 text-center last:border-r-0"
              >
                <div className="grid justify-items-center gap-1.5">
                  <div className="text-sm font-black text-slate-100">{day.label}</div>
                  <div className="text-xs font-semibold text-bf-cream/52">{day.date}</div>
                  <div
                    className={`mt-1 inline-flex max-w-full items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-black ${
                      hasDayType
                        ? `${style.border} ${style.bg} ${style.text}`
                        : 'border-bf-cream/10 bg-black/30 text-bf-cream/35'
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
              <div className="min-h-[60px] border-b border-r border-bf-cream/10 bg-black/20">
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
                      isUnavailable ? 'bg-red-900/50' : isFullDayAvailable ? 'bg-emerald-950/30' : isTentative ? 'bg-orange-950/40' : 'bg-slate-950/36'
                    }`}
                  >
                    {cellSlots.length ? (
                      <div className="grid w-full gap-1.5">
                        {cellSlots.map((slot) => (
                          <EventCard key={slot.id} event={slot} onEdit={onEdit} />
                        ))}
                        {player.canEdit ? (
                          <button
                            className="justify-self-end text-[11px] font-black text-bf-cream/45 transition hover:text-bf-orange"
                            type="button"
                            onClick={() => onAdd(day.value)}
                          >
                            + запись
                          </button>
                        ) : null}
                      </div>
                    ) : player.canEdit ? (
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

      <footer className="mt-4 flex justify-end gap-4 border-t border-bf-cream/10 pt-4 text-sm text-bf-cream/48">
        <span>Дата последнего обновления: {lastUpdated}</span>
      </footer>
    </section>
  );
}

function StaffDirectory({ staffMembers }) {
  return (
    <section className="glass-panel mt-4 rounded-[20px] p-4">
      <div className="mb-4">
        <div className="text-sm font-black uppercase text-bf-orange">Operations</div>
        <h2 className="mt-1 text-xl font-black uppercase text-slate-100">Организаторский состав</h2>
      </div>

      {staffMembers.length ? (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {staffMembers.map((staffMember) => (
            <article key={staffMember.id} className="rounded-[18px] border border-bf-cream/10 bg-black/24 p-4 shadow-[0_10px_24px_rgba(0,0,0,0.16)]">
              <div className="flex items-start gap-3">
                <Avatar src={staffMember.avatarUrl} alt={staffMember.name} fallbackLabel={staffMember.name} className="h-12 w-12 object-cover" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-base font-black text-slate-100">{staffMember.name}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <RoleBadge role={staffMember.role} color={staffMember.roleColor} />
                    {staffMember.canEdit ? (
                      <span className="rounded-full border border-bf-orange/30 bg-bf-orange/10 px-2 py-0.5 text-[11px] font-bold text-bf-orange">
                        Ваш профиль
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-bf-cream/10 bg-black/28 px-4 py-3">
                <div className="text-[11px] font-black uppercase tracking-wide text-bf-cream/44">Discord</div>
                <DiscordClouds displayTag={staffMember.discordDisplayTag} />
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-[18px] border border-dashed border-bf-cream/12 bg-black/20 px-4 py-6 text-sm text-bf-cream/46">
          Организаторский состав пока не заполнен в админке.
        </div>
      )}
    </section>
  );
}

function PlayerProfiles({ players, showHeading = true }) {
  return (
    <section className="glass-panel mt-4 rounded-[20px] p-4">
      {showHeading ? (
        <div className="mb-4">
          <div className="text-sm font-black uppercase text-bf-orange">Player profiles</div>
          <h2 className="mt-1 text-xl font-black uppercase text-slate-100">Актуальные игровые профили</h2>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {players.map((player) => (
          <article key={player.id} className="rounded-[18px] border border-bf-cream/10 bg-black/24 p-4 shadow-[0_10px_24px_rgba(0,0,0,0.16)]">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <Avatar src={player.avatarUrl} alt={player.name} fallbackLabel={player.name} className="h-12 w-12 object-cover" />
                <div className="min-w-0">
                  <div className="truncate text-base font-black text-slate-100">{player.name}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <RoleBadge role={player.role} color={player.roleColor} />
                    {player.canEdit ? (
                      <span className="rounded-full border border-bf-orange/30 bg-bf-orange/10 px-2 py-0.5 text-[11px] font-bold text-bf-orange">
                        Ваш профиль
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 grid gap-3 text-sm">
              <div className="rounded-2xl border border-bf-cream/10 bg-black/28 px-4 py-3">
                <div className="text-[11px] font-black uppercase tracking-wide text-bf-cream/44">Battle.net</div>
                {player.battleTags.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {player.battleTags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-bf-cream/10 bg-bf-steel/18 px-3 py-1 text-sm font-semibold text-slate-100"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="mt-2 text-bf-cream/42">Не указано</div>
                )}
              </div>

              <div className="rounded-2xl border border-bf-cream/10 bg-black/28 px-4 py-3">
                <div className="text-[11px] font-black uppercase tracking-wide text-bf-cream/44">Discord</div>
                <DiscordClouds displayTag={player.discordDisplayTag} />
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function TeamPage({ players, staffMembers }) {
  return (
    <>
      <TeamBanner />
      <PlayerProfiles players={players} showHeading={false} />
      <StaffDirectory staffMembers={staffMembers} />
    </>
  );
}

function ProfilePage({ user, profile, profileType, onSaved }) {
  const isPlayerProfile = profileType === 'player';
  const isStaffProfile = profileType === 'staff';
  const [name, setName] = useState(profile?.name || '');
  const [battleTagsText, setBattleTagsText] = useState(profile?.battleTagsText || '');
  const [profileErrors, setProfileErrors] = useState({});
  const [profileSuccess, setProfileSuccess] = useState('');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [discordFeedback, setDiscordFeedback] = useState(() => discordFeedbackFromUrl(window.location.search));
  const [isDisconnectingDiscord, setIsDisconnectingDiscord] = useState(false);

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [passwordErrors, setPasswordErrors] = useState({});
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [isSavingPassword, setIsSavingPassword] = useState(false);

  useEffect(() => {
    setName(profile?.name || '');
    setBattleTagsText(profile?.battleTagsText || '');
  }, [profile]);

  useEffect(() => {
    if (!discordFeedbackFromUrl(window.location.search)) return;
    window.history.replaceState({}, document.title, window.location.pathname);
  }, []);

  async function handleProfileSubmit(submitEvent) {
    submitEvent.preventDefault();
    setIsSavingProfile(true);
    setProfileErrors({});
    setProfileSuccess('');
    try {
      const payload = { name };
      if (isPlayerProfile) {
        payload.battleTagsText = battleTagsText;
      }
      const response = await updateProfile(payload);
      await onSaved(response.profile || response.player);
      setProfileSuccess('Профиль сохранен.');
    } catch (saveError) {
      setProfileErrors(saveError.payload?.errors || { __all__: [saveError.message] });
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleDiscordDisconnect() {
    setIsDisconnectingDiscord(true);
    setDiscordFeedback(null);
    try {
      await disconnectDiscord();
      await onSaved(null, { reload: true });
      setDiscordFeedback({ tone: 'success', text: 'Discord отвязан.' });
    } catch (disconnectError) {
      setDiscordFeedback({ tone: 'error', text: disconnectError.message });
    } finally {
      setIsDisconnectingDiscord(false);
    }
  }

  async function handlePasswordSubmit(submitEvent) {
    submitEvent.preventDefault();
    setIsSavingPassword(true);
    setPasswordErrors({});
    setPasswordSuccess('');
    try {
      await changePassword({ oldPassword, newPassword, newPasswordConfirm });
      setOldPassword('');
      setNewPassword('');
      setNewPasswordConfirm('');
      setPasswordSuccess('Пароль обновлен.')
    } catch (saveError) {
      setPasswordErrors(saveError.payload?.errors || { __all__: [saveError.message] });
    } finally {
      setIsSavingPassword(false);
    }
  }

  if (!profile) {
    return (
      <section className="glass-panel mt-4 rounded-[20px] p-6">
        <div className="text-sm font-black uppercase text-bf-orange">Profile</div>
        <h1 className="mt-1 text-3xl font-black uppercase text-slate-100">Профиль</h1>
        <p className="mt-4 text-bf-cream/62">Аккаунт не привязан ни к игроку, ни к организаторскому составу. Обратитесь к администратору.</p>
      </section>
    );
  }

  return (
    <section className="glass-panel mt-4 rounded-[20px] p-5">
      <div className="mb-5">
        <div>
          <div className="text-sm font-black uppercase text-bf-orange">Profile</div>
          <h1 className="mt-1 text-3xl font-black uppercase text-slate-100">
            {isStaffProfile ? 'Профиль организатора' : 'Профиль игрока'}
          </h1>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <form className="rounded-[18px] border border-bf-cream/10 bg-black/24 p-5" onSubmit={handleProfileSubmit}>
          <div className="text-sm font-black uppercase text-bf-orange">
            {isStaffProfile ? 'Контактные данные' : 'Игровые данные'}
          </div>
          {profileErrors.__all__ ? (
            <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
              {profileErrors.__all__.join(', ')}
            </div>
          ) : null}
          {profileSuccess ? (
            <div className="mt-4 rounded-xl border border-emerald-400/25 bg-emerald-500/10 p-3 text-sm text-emerald-100">
              {profileSuccess}
            </div>
          ) : null}
          {discordFeedback ? (
            <div
              className={`mt-4 rounded-xl p-3 text-sm ${
                discordFeedback.tone === 'success'
                  ? 'border border-emerald-400/25 bg-emerald-500/10 text-emerald-100'
                  : 'border border-red-400/30 bg-red-500/10 text-red-100'
              }`}
            >
              {discordFeedback.text}
            </div>
          ) : null}
          <div className="mt-5 grid gap-4">
            <label className="grid gap-2 text-sm font-black text-bf-cream/70">
              Логин
              <input
                className="h-12 rounded-2xl border border-bf-cream/10 bg-black/20 px-4 text-bf-cream/52 outline-none"
                value={user.username}
                readOnly
              />
            </label>
            <label className="grid gap-2 text-sm font-black text-bf-cream/70">
              {isStaffProfile ? 'Имя' : 'Имя игрока'}
              <input
                className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none focus:border-bf-orange/45"
                value={name}
                onChange={(inputEvent) => setName(inputEvent.target.value)}
              />
              {profileErrors.name ? <span className="text-red-200">{profileErrors.name.join(', ')}</span> : null}
            </label>
            {isPlayerProfile ? (
              <label className="grid gap-2 text-sm font-black text-bf-cream/70">
                BattleTag&apos;и
                <textarea
                  className="min-h-36 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 py-3 text-slate-100 outline-none placeholder:text-bf-cream/35 focus:border-bf-orange/45"
                  value={battleTagsText}
                  onChange={(inputEvent) => setBattleTagsText(inputEvent.target.value)}
                  placeholder={'По одному на строку\nBlackFlock#21234\nBlackFlockAlt#19876'}
                />
              </label>
            ) : null}
            <div className="rounded-2xl border border-bf-cream/10 bg-black/28 px-4 py-4">
              <div className="text-sm font-black uppercase text-bf-orange">Discord</div>
              {profile.discordConnected ? (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <Avatar src={profile.avatarUrl} alt={profile.discordDisplayTag} fallbackLabel={profile.name || profile.discordDisplayTag} className="h-12 w-12 object-cover" />
                    <div>
                      <div className="text-sm font-black text-slate-100">{profile.discordDisplayTag || '@unknown'}</div>
                      <div className="mt-1 text-xs text-bf-cream/50">
                        {profile.discordGlobalName || 'Подключенный аккаунт Discord'}
                      </div>
                    </div>
                  </div>
                  <button
                    className="inline-flex min-h-10 items-center rounded-xl border border-red-300/30 px-4 font-black text-red-100 transition hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-45"
                    type="button"
                    onClick={handleDiscordDisconnect}
                    disabled={isDisconnectingDiscord}
                  >
                    Отвязать Discord
                  </button>
                </div>
              ) : (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="text-sm font-semibold text-slate-100">Не подключен</div>
                    <div className="mt-1 text-xs text-bf-cream/50">Аватар и Discord handle подтянутся автоматически после подключения.</div>
                  </div>
                  <button
                    className="inline-flex min-h-10 items-center rounded-xl bg-bf-orange px-4 font-black text-black transition hover:-translate-y-0.5 hover:shadow-[0_10px_22px_rgba(243,112,30,0.18)]"
                    type="button"
                    onClick={() => {
                      window.location.href = '/api/discord/connect/';
                    }}
                  >
                    Подключить Discord
                  </button>
                </div>
              )}
            </div>
          </div>
          <div className="mt-5 flex justify-end">
            <button
              className="inline-flex min-h-11 items-center gap-2 rounded-2xl bg-gradient-to-b from-orange-400 to-bf-orange px-5 font-black text-black transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:translate-y-0"
              type="submit"
              disabled={isSavingProfile}
            >
              <Save size={18} />
              Сохранить профиль
            </button>
          </div>
        </form>

        <form className="rounded-[18px] border border-bf-cream/10 bg-black/24 p-5" onSubmit={handlePasswordSubmit}>
          <div className="text-sm font-black uppercase text-bf-orange">Безопасность</div>
          {passwordErrors.__all__ ? (
            <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
              {passwordErrors.__all__.join(', ')}
            </div>
          ) : null}
          {passwordSuccess ? (
            <div className="mt-4 rounded-xl border border-emerald-400/25 bg-emerald-500/10 p-3 text-sm text-emerald-100">
              {passwordSuccess}
            </div>
          ) : null}
          <div className="mt-5 grid gap-4">
            <label className="grid gap-2 text-sm font-black text-bf-cream/70">
              Старый пароль
              <input
                type="password"
                className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none focus:border-bf-orange/45"
                value={oldPassword}
                onChange={(inputEvent) => setOldPassword(inputEvent.target.value)}
              />
              {passwordErrors.oldPassword ? <span className="text-red-200">{passwordErrors.oldPassword.join(', ')}</span> : null}
            </label>
            <label className="grid gap-2 text-sm font-black text-bf-cream/70">
              Новый пароль
              <input
                type="password"
                className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none focus:border-bf-orange/45"
                value={newPassword}
                onChange={(inputEvent) => setNewPassword(inputEvent.target.value)}
              />
              {passwordErrors.newPassword ? <span className="text-red-200">{passwordErrors.newPassword.join(', ')}</span> : null}
            </label>
            <label className="grid gap-2 text-sm font-black text-bf-cream/70">
              Повторите новый пароль
              <input
                type="password"
                className="h-12 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 text-slate-100 outline-none focus:border-bf-orange/45"
                value={newPasswordConfirm}
                onChange={(inputEvent) => setNewPasswordConfirm(inputEvent.target.value)}
              />
              {passwordErrors.newPasswordConfirm ? <span className="text-red-200">{passwordErrors.newPasswordConfirm.join(', ')}</span> : null}
            </label>
          </div>
          <div className="mt-5 flex justify-end">
            <button
              className="inline-flex min-h-11 items-center gap-2 rounded-2xl border border-bf-orange/45 px-5 font-black text-bf-orange transition hover:bg-bf-orange/10 disabled:cursor-not-allowed disabled:opacity-45"
              type="submit"
              disabled={isSavingPassword}
            >
              <Save size={18} />
              Сменить пароль
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

function EventModal({ event, day, days, onClose, onSaved, onDeleted }) {
  const isEditing = Boolean(event);
  const [slotType, setSlotType] = useState(event?.slotType || 'available');
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
      dayOfWeek,
      startTimeMinutes,
      endTimeMinutes,
      note,
    };

    if (slotType === 'unavailable' || slotType === 'full_day_available' || slotType === 'tentative') {
      payload.startTimeMinutes = null;
      payload.endTimeMinutes = null;
    }

    try {
      const response = isEditing ? await updateSlot(event.id, payload) : await createSlot(payload);
      onSaved(response.slot);
    } catch (saveError) {
      setErrors(saveError.payload?.errors || { __all__: [saveError.message] });
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
    } catch (deleteError) {
      setErrors(deleteError.payload?.errors || { __all__: [deleteError.message] });
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
            <div className="text-sm font-black uppercase text-bf-orange">Availability editor</div>
            <h2 className="mt-1 text-2xl font-black uppercase text-slate-100">
              {isEditing ? 'Редактировать время' : 'Добавить время'}
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

        {errors.__all__ ? (
          <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
            {errors.__all__.join(', ')}
          </div>
        ) : null}

        <div className="mt-6 grid gap-5">
          <div className="grid grid-cols-4 gap-3 max-lg:grid-cols-2 max-md:grid-cols-1">
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
                slotType === 'full_day_available'
                  ? 'border-emerald-300/50 bg-emerald-500/15 text-emerald-100'
                  : 'border-bf-cream/10 bg-black/20 text-bf-cream/62'
              }`}
              type="button"
              onClick={() => setSlotType('full_day_available')}
            >
              Свободен весь день
            </button>
            <button
              className={`rounded-2xl border px-4 py-3 font-black transition ${
                slotType === 'tentative'
                  ? 'border-orange-300/50 bg-orange-500/15 text-orange-100'
                  : 'border-bf-cream/10 bg-black/20 text-bf-cream/62'
              }`}
              type="button"
              onClick={() => setSlotType('tentative')}
            >
              Не уверен
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
            {errors.day_of_week ? <span className="text-red-200">{errors.day_of_week.join(', ')}</span> : null}
          </label>

          {slotType === 'available' ? (
            <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
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
              className="inline-flex min-h-11 items-center gap-2 rounded-2xl bg-gradient-to-b from-orange-400 to-bf-orange px-5 font-black text-black transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:translate-y-0"
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

function ProfileModal({ player, onClose, onSaved }) {
  const [battleTagsText, setBattleTagsText] = useState(player.battleTagsText || '');
  const [error, setError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault();
    setIsSaving(true);
    setError('');
    try {
      const response = await updateProfile({ battleTagsText });
      await onSaved(response.profile || response.player);
    } catch (saveError) {
      setError(saveError.payload?.error || saveError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm">
      <motion.form
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="w-full max-w-xl rounded-[24px] border border-bf-cream/12 bg-[#0d1420] p-6 shadow-panel"
        onSubmit={handleSubmit}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm font-black uppercase text-bf-orange">Profile editor</div>
            <h2 className="mt-1 text-2xl font-black uppercase text-slate-100">Игровые профили</h2>
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

        {error ? (
          <div className="mt-4 rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">{error}</div>
        ) : null}

        <div className="mt-6 grid gap-5">
          <label className="grid gap-2 text-sm font-black text-bf-cream/70">
            BattleTag&apos;и
            <textarea
              className="min-h-32 rounded-2xl border border-bf-cream/10 bg-black/30 px-4 py-3 text-slate-100 outline-none placeholder:text-bf-cream/35 focus:border-bf-orange/50"
              value={battleTagsText}
              onChange={(inputEvent) => setBattleTagsText(inputEvent.target.value)}
              placeholder={'По одному на строку\nBlackFlock#21234\nBlackFlockAlt#19876'}
            />
            <span className="text-xs font-medium text-bf-cream/45">Если аккаунтов несколько, указывай каждый BattleTag с новой строки.</span>
          </label>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            className="min-h-11 rounded-2xl border border-bf-cream/10 px-4 font-black text-bf-cream/70 transition hover:border-bf-orange/40"
            type="button"
            onClick={onClose}
          >
            Отмена
          </button>
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-2xl bg-gradient-to-b from-orange-400 to-bf-orange px-5 font-black text-black transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:translate-y-0"
            type="submit"
            disabled={isSaving}
          >
            <Save size={18} />
            Сохранить
          </button>
        </div>
      </motion.form>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [slotModal, setSlotModal] = useState(null);
  const [profileModalPlayer, setProfileModalPlayer] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true';
  });

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

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  function upsertSlot(slot) {
    setData((current) => ({
      ...current,
      slots: current.slots.some((existing) => existing.id === slot.id)
        ? current.slots.map((existing) => (existing.id === slot.id ? slot : existing))
        : [...current.slots, slot],
    }));
    setSlotModal(null);
  }

  function removeSlot(id) {
    setData((current) => ({
      ...current,
      slots: current.slots.filter((slot) => slot.id !== id),
    }));
    setSlotModal(null);
  }

  async function updatePlayerProfile(player, options = {}) {
    if (options.reload) {
      await loadData();
      setProfileModalPlayer(null);
      return;
    }
    setData((current) => ({
      ...current,
      players: current.players.map((existing) => (existing.id === player.id ? player : existing)),
    }));
    setProfileModalPlayer(null);
  }

  async function updateStaffProfile(staffMember, options = {}) {
    if (options.reload) {
      await loadData();
      return;
    }
    setData((current) => ({
      ...current,
      staffMembers: current.staffMembers.map((existing) => (existing.id === staffMember.id ? staffMember : existing)),
    }));
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
  const pathname = window.location.pathname;
  const isProfilePage = pathname.startsWith('/profile');
  const isTeamPage = pathname.startsWith('/team');
  const currentPlayer = data.players.find((player) => player.id === data.user.playerId) || null;
  const currentStaffMember = data.staffMembers.find((staffMember) => staffMember.id === data.user.staffMemberId) || null;
  const currentProfile = data.user.profileType === 'staff' ? currentStaffMember : currentPlayer;
  const handleProfileSaved = data.user.profileType === 'staff' ? updateStaffProfile : updatePlayerProfile;

  return (
    <main className="mx-auto min-h-screen w-[min(1500px,calc(100%_-_48px))] py-4 max-sm:w-[min(100%_-_20px,760px)]">
      <div className={`app-shell ${sidebarCollapsed ? 'app-shell-collapsed' : ''}`}>
        <Sidebar pathname={pathname} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((current) => !current)} />
        <div className="min-w-0">
          <Header user={data.user} />
          {isProfilePage ? (
            <ProfilePage
              user={data.user}
              profile={currentProfile}
              profileType={data.user.profileType}
              onSaved={handleProfileSaved}
            />
          ) : isTeamPage ? (
            <TeamPage players={data.players} staffMembers={data.staffMembers} />
          ) : (
            <>
              <HeroBanner canAdd={canAdd} onAdd={(day) => setSlotModal({ day })} />
              <RosterTable
                days={data.days}
                players={data.players}
                slots={data.slots}
                dayEventTypes={data.dayEventTypes}
                onAdd={(day) => setSlotModal({ day })}
                onEdit={(event) => setSlotModal({ event })}
                lastUpdated={data.lastUpdated}
              />
              <Legend eventTypes={data.eventTypes} />
            </>
          )}
        </div>
      </div>
      {slotModal ? (
        <EventModal
          event={slotModal.event}
          day={slotModal.day}
          days={data.days}
          onClose={() => setSlotModal(null)}
          onSaved={upsertSlot}
          onDeleted={removeSlot}
        />
      ) : null}
      {profileModalPlayer ? (
        <ProfileModal
          player={profileModalPlayer}
          onClose={() => setProfileModalPlayer(null)}
          onSaved={updatePlayerProfile}
        />
      ) : null}
    </main>
  );
}
