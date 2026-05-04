import { useMemo, useState } from 'react';
import {
  BarChart3,
  CalendarDays,
  Clock3,
  Plus,
  Settings,
  ShieldCheck,
  UserPlus,
  Users,
} from 'lucide-react';

function HubButton({ as = 'button', href = '', icon: Icon, label, caption, variant = 'secondary', onClick }) {
  const className = {
    primary: 'border-bf-orange/55 bg-bf-orange text-white shadow-[0_14px_30px_rgba(243,112,30,0.18)] hover:bg-[#ff812e]',
    secondary: 'border-bf-cream/10 bg-black/24 text-slate-100 hover:border-bf-orange/35 hover:bg-bf-orange/10',
  }[variant];
  const content = (
    <>
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-current/20 bg-black/18">
        <Icon size={19} />
      </span>
      <span className="min-w-0 text-left">
        <span className="block text-sm font-black uppercase leading-tight">{label}</span>
        <span className="mt-0.5 block text-xs font-semibold opacity-58">{caption}</span>
      </span>
    </>
  );

  if (as === 'a') {
    return (
      <a className={`inline-flex min-h-14 items-center gap-3 rounded-xl border px-4 transition ${className}`} href={href}>
        {content}
      </a>
    );
  }

  return (
    <button className={`inline-flex min-h-14 items-center gap-3 rounded-xl border px-4 transition ${className}`} type="button" onClick={onClick}>
      {content}
    </button>
  );
}

function SummaryTile({ icon: Icon, label, value, caption }) {
  return (
    <div className="rounded-xl border border-bf-cream/10 bg-black/22 p-4">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl border border-bf-orange/20 bg-bf-orange/10 text-bf-orange">
          <Icon size={19} />
        </div>
        <div>
          <div className="text-[11px] font-black uppercase tracking-wide text-bf-cream/42">{label}</div>
          <div className="mt-1 text-2xl font-black text-slate-100">{value}</div>
        </div>
      </div>
      <div className="mt-2 text-xs font-semibold text-bf-cream/44">{caption}</div>
    </div>
  );
}

function QuickCard({ href, icon: Icon, label, caption }) {
  return (
    <a
      className="group rounded-xl border border-bf-cream/10 bg-black/18 p-4 text-decoration-none transition hover:-translate-y-0.5 hover:border-bf-orange/35 hover:bg-bf-orange/10"
      href={href}
    >
      <div className="flex items-start gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl border border-bf-cream/10 bg-black/24 text-bf-orange transition group-hover:border-bf-orange/35">
          <Icon size={18} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-black uppercase text-slate-100">{label}</div>
          <div className="mt-1 text-xs font-semibold leading-relaxed text-bf-cream/48">{caption}</div>
        </div>
      </div>
    </a>
  );
}

export default function MainPage({ players, staffMembers, slots, weekRangeLabel, user }) {
  const [notice, setNotice] = useState('Функции создания и присоединения к командам скоро будут доступны.');
  const summary = useMemo(() => {
    const filledPlayers = new Set((slots || []).map((slot) => slot.playerId)).size;
    const connectedProfiles = [...(players || []), ...(staffMembers || [])].filter((profile) => profile.discordConnected).length;
    return {
      players: players?.length || 0,
      staff: staffMembers?.length || 0,
      filledPlayers,
      connectedProfiles,
    };
  }, [players, staffMembers, slots]);

  function showComingSoon(action) {
    setNotice(`${action} пока в подготовке. Сейчас можно пользоваться расписанием, составом, статистикой и профилем.`);
  }

  return (
    <>
      <section className="glass-panel hero-banner relative mt-4 overflow-hidden rounded-xl border-bf-orange/35 px-6 py-7 lg:px-8">
        <div className="relative z-10 grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px] xl:items-center">
          <div className="grid gap-5">
            <div>
              <div className="text-sm font-black uppercase text-bf-orange">Black Flock</div>
              <h1 className="mt-2 text-5xl font-black uppercase leading-none text-slate-100 max-md:text-4xl">
                Team Hub
              </h1>
              <p className="mt-4 max-w-2xl text-sm font-semibold leading-relaxed text-bf-cream/62">
                Центр управления командой: расписание, состав, статистика, профили игроков и будущие командные инструменты в одном месте.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:max-w-[720px]">
              <HubButton
                icon={Plus}
                label="Создать новую команду"
                caption="Настройка состава и доступа"
                variant="primary"
                onClick={() => showComingSoon('Создание команды')}
              />
              <HubButton
                icon={UserPlus}
                label="Присоединиться"
                caption="Вход по приглашению"
                onClick={() => showComingSoon('Присоединение к команде')}
              />
            </div>

            <div className="rounded-xl border border-bf-orange/18 bg-bf-orange/10 px-4 py-3 text-sm font-semibold text-bf-cream/72">
              {notice}
            </div>
          </div>

          <div className="rounded-xl border border-bf-cream/10 bg-black/24 p-4">
            <div className="mb-4 flex items-center gap-3">
              <img className="h-12 w-12 rounded-full border border-bf-cream/10 object-contain" src="/static/img/Logo.png" alt="" />
              <div>
                <div className="text-sm font-black uppercase text-slate-100">Black Flock Team</div>
                <div className="text-xs font-semibold text-bf-cream/48">Аккаунт: {user.username}</div>
              </div>
            </div>
            <div className="grid gap-3">
              <SummaryTile icon={Users} label="Игроки" value={summary.players} caption={`${summary.staff} в организаторском составе`} />
              <SummaryTile icon={CalendarDays} label="Неделя" value={weekRangeLabel || '—'} caption={`${summary.filledPlayers} игроков уже заполнили время`} />
              <SummaryTile icon={ShieldCheck} label="Discord" value={summary.connectedProfiles} caption="Профилей подключено через Discord" />
            </div>
          </div>
        </div>
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="glass-panel rounded-xl p-4">
          <div className="mb-4 text-sm font-black uppercase text-slate-100">Быстрые действия</div>
          <div className="grid gap-3 md:grid-cols-2">
            <QuickCard href="/" icon={Clock3} label="Открыть расписание" caption="Неделя, время игроков и типы активностей." />
            <QuickCard href="/team/" icon={Users} label="Посмотреть состав" caption="Игровые профили, BattleTag, Discord и роли." />
            <QuickCard href="/stats/" icon={BarChart3} label="Статистика команды" caption="OverFast данные по BattleTag игроков." />
            <QuickCard href="/profile/" icon={Settings} label="Настройки профиля" caption="Имя, BattleTag, пароль и Discord Connect." />
          </div>
        </div>

        <div className="glass-panel rounded-xl p-4">
          <div className="mb-4 text-sm font-black uppercase text-slate-100">Следующие функции</div>
          <div className="grid gap-3 text-sm font-semibold text-bf-cream/58">
            <div className="rounded-xl border border-bf-cream/10 bg-black/18 p-3">Создание нескольких команд и переключение между ними.</div>
            <div className="rounded-xl border border-bf-cream/10 bg-black/18 p-3">Приглашения игроков по ссылке или коду доступа.</div>
            <div className="rounded-xl border border-bf-cream/10 bg-black/18 p-3">Роли доступа для владельца, менеджера, тренера и игроков.</div>
          </div>
        </div>
      </section>
    </>
  );
}
