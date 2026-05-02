export function Avatar({ src, alt, fallbackLabel, className = '' }) {
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

function hexToRgba(hexColor, alpha) {
  if (!hexColor || !/^#[0-9A-Fa-f]{6}$/.test(hexColor)) {
    return `rgba(232, 237, 245, ${alpha})`;
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

export function RoleBadge({ role, color, className = '' }) {
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

export function DiscordClouds({ displayTag }) {
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
