const clockFormatters = {
    utc: new Intl.DateTimeFormat('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: 'UTC',
    }),
    moscow: new Intl.DateTimeFormat('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: 'Europe/Moscow',
    }),
    cest: new Intl.DateTimeFormat('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: 'Etc/GMT-2',
    }),
};

function updateClocks() {
    const now = new Date();

    Object.entries(clockFormatters).forEach(([key, formatter]) => {
        document.querySelectorAll(`[data-clock="${key}"]`).forEach((node) => {
            node.textContent = formatter.format(now);
        });
    });
}

updateClocks();
setInterval(updateClocks, 1000);
