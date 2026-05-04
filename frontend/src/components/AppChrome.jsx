import { useEffect, useState } from 'react';
import { BarChart3, BookText, Clock3, LogOut, Settings, Users } from 'lucide-react';

import { logout } from '../api.js';
import { Avatar } from './common.jsx';

function formatClock(timeZone) {
  const options = {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  };

  if (timeZone) {
    options.timeZone = timeZone;
  }

  return new Intl.DateTimeFormat('ru-RU', options).format(new Date());
}

function useClocks() {
  const [clocks, setClocks] = useState({
    utc: '--:--',
    local: '--:--',
    cest: '--:--',
  });

  useEffect(() => {
    const update = () => {
      setClocks({
        utc: formatClock('UTC'),
        local: formatClock(),
        cest: formatClock('Etc/GMT-2'),
      });
    };

    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, []);

  return clocks;
}

export function Header({ user }) {
  const clocks = useClocks();
  const isProfilePage = window.location.pathname.startsWith('/profile');

  async function handleLogout() {
    const response = await logout();
    window.location.href = response.redirectUrl || '/login/';
  }

  return (
    <header className="top-header">
      <a className="top-header-brand" href="/">
        <img className="top-header-logo" src="/static/img/Logo.png" alt="" />
        <span>Black Flock</span>
      </a>

      <div className="top-header-clocks">
        {[
          ['UTC', clocks.utc, false],
          ['Your', clocks.local, true],
          ['CEST', clocks.cest, false],
        ].map(([label, value, isActive]) => (
          <div key={label} className={`top-header-clock ${isActive ? 'top-header-clock-active' : ''}`}>
            <div className="top-header-clock-label">{label}</div>
            <div className="top-header-clock-value">{value}</div>
          </div>
        ))}
      </div>

      <div className="top-header-actions">
        <a
          className={`top-header-user ${isProfilePage ? 'top-header-user-active' : ''}`}
          href="/profile/"
          aria-label="Открыть профиль"
        >
          <Avatar src={user.avatarUrl} alt={user.username} fallbackLabel={user.username} className="h-7 w-7 object-cover" />
          <span>{user.username}</span>
        </a>
        <button
          className="top-header-logout"
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

export function Sidebar({ pathname }) {
  const items = [
    {
      href: '/',
      label: 'Расписание',
      icon: Clock3,
      isActive: !pathname.startsWith('/main') && !pathname.startsWith('/team') && !pathname.startsWith('/profile') && !pathname.startsWith('/updates') && !pathname.startsWith('/stats'),
    },
    {
      href: '/team/',
      label: 'Состав',
      icon: Users,
      isActive: pathname.startsWith('/team'),
    },
    {
      href: '/updates/',
      label: 'Обновления',
      icon: BookText,
      isActive: pathname.startsWith('/updates'),
    },
    {
      href: '/stats/',
      label: 'Статистика',
      icon: BarChart3,
      isActive: pathname.startsWith('/stats'),
    },
    {
      href: '/profile/',
      label: 'Настройки',
      icon: Settings,
      isActive: pathname.startsWith('/profile'),
    },
  ];

  return (
    <aside className="app-sidebar glass-panel rounded-xl xl:sticky xl:top-4 xl:self-start">
      <div className="sidebar-shell">
        <div className="sidebar-head">
          <a className="sidebar-brand" href="/" aria-label="Black Flock">
            <img className="brand-logo" src="/static/img/Logo.png" alt="" />
          </a>
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
              >
                <Icon size={20} />
                <span className="sidebar-link-label">{item.label}</span>
              </a>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
