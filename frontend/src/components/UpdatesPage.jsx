import { BookText, ExternalLink } from 'lucide-react';

function formatPublishedDate(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(value));
}

const UPDATE_TYPE_STYLES = {
  Hotfix: 'border-amber-300/30 bg-amber-500/10 text-amber-100',
  'Bug Fix': 'border-rose-300/30 bg-rose-500/10 text-rose-100',
  'Season / Event': 'border-purple-300/30 bg-purple-500/10 text-purple-100',
  'Patch Notes': 'border-sky-300/30 bg-sky-500/10 text-sky-100',
  Update: 'border-bf-cream/10 bg-black/20 text-bf-cream/72',
};

function UpdateTypeBadge({ typeLabel, className = '' }) {
  const style = UPDATE_TYPE_STYLES[typeLabel] || UPDATE_TYPE_STYLES.Update;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${style} ${className}`}>
      {typeLabel}
    </span>
  );
}

function UpdatesBanner() {
  return (
    <section className="glass-panel hero-banner relative mt-4 overflow-hidden rounded-xl border-bf-orange/25 px-6 py-6 lg:px-8">
      <div className="relative z-10 grid gap-3 lg:max-w-[520px]">
        <div className="text-sm font-black uppercase text-bf-orange">Blizzard</div>
        <h1 className="text-4xl font-black uppercase leading-none text-slate-100 max-md:text-3xl">
          Обновления Overwatch
        </h1>
      </div>
    </section>
  );
}

function UpdateContentBlock({ block }) {
  if (block.type === 'heading') {
    if (block.level <= 4) {
      return <h3 className="mt-5 text-lg font-black uppercase text-slate-100 first:mt-0">{block.text}</h3>;
    }
    return <h4 className="mt-4 text-sm font-black uppercase text-bf-orange">{block.text}</h4>;
  }

  if (block.type === 'paragraph') {
    return <p className="text-sm leading-6 text-bf-cream/74">{block.text}</p>;
  }

  if (block.type === 'bullet_list') {
    return (
      <ul className="grid gap-2 pl-5 text-sm leading-6 text-bf-cream/78">
        {block.items.map((item) => (
          <li key={item} className="list-disc">
            {item}
          </li>
        ))}
      </ul>
    );
  }

  if (block.type === 'image') {
    return (
      <div className="mt-3 flex items-center gap-3 rounded-xl border border-bf-cream/10 bg-[#101620] p-3">
        <div className="relative h-14 w-14 overflow-hidden rounded-xl border border-bf-cream/10 bg-[#101620]">
          <img
            className="h-full w-full object-cover opacity-90"
            src={block.src}
            alt={block.alt || ''}
          />
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(16,22,32,0.12),rgba(16,22,32,0.42))]" />
        </div>
        <div className="text-sm font-bold text-bf-cream/72">{block.alt || 'Hero update'}</div>
      </div>
    );
  }

  return null;
}

export default function UpdatesPage({
  updates,
  selectedSlug,
  selectedUpdate,
  onSelect,
  isLoadingList,
  isLoadingDetail,
  error,
}) {
  const visibleUpdates = updates.slice(0, 10);
  const hasUpdates = visibleUpdates.length > 0;

  return (
    <>
      <UpdatesBanner />
      <section className="mt-4 grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="glass-panel rounded-xl p-4">
          <div className="mb-4 flex items-center gap-2 text-sm font-black uppercase text-slate-100">
            <BookText size={18} className="text-bf-orange" />
            Последние обновления
          </div>

          {isLoadingList ? (
            <div className="rounded-xl border border-bf-cream/10 bg-black/18 px-4 py-6 text-sm text-bf-cream/62">
              Загружаю список обновлений...
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-6 text-sm text-red-100">
              {error}
            </div>
          ) : hasUpdates ? (
            <div className="grid gap-3">
              {visibleUpdates.map((update) => {
                const isActive = update.slug === selectedSlug;
                return (
                  <button
                    key={update.slug}
                    type="button"
                    onClick={() => onSelect(update.slug)}
                    className={`grid gap-3 overflow-hidden rounded-xl border p-4 text-left transition ${
                      isActive
                        ? 'border-bf-orange/45 bg-bf-orange/10 shadow-[0_0_18px_rgba(216,109,56,0.10)]'
                        : 'border-bf-cream/10 bg-black/18 hover:border-bf-orange/25 hover:bg-bf-steel/10'
                    }`}
                  >
                    <div className="grid items-start gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                      <div className="min-w-0">
                        <div className="line-clamp-2 break-words text-base font-black uppercase leading-tight text-slate-100">
                          {update.title}
                        </div>
                        <div className="mt-1 text-xs font-semibold text-bf-cream/48">{formatPublishedDate(update.publishedAt)}</div>
                      </div>
                      <UpdateTypeBadge typeLabel={update.typeLabel} className="justify-self-start sm:justify-self-end" />
                    </div>
                    <p className="line-clamp-3 text-sm leading-5 text-bf-cream/64">{update.summary || 'Без краткого описания.'}</p>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl border border-bf-cream/10 bg-black/18 px-4 py-6 text-sm text-bf-cream/62">
              Обновления еще не синхронизированы.
            </div>
          )}
        </div>

        <div className="glass-panel rounded-xl p-4">
          {isLoadingDetail ? (
            <div className="rounded-xl border border-bf-cream/10 bg-black/18 px-4 py-6 text-sm text-bf-cream/62">
              Загружаю детали патча...
            </div>
          ) : selectedUpdate ? (
            <div className="grid gap-5">
              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <UpdateTypeBadge typeLabel={selectedUpdate.typeLabel} />
                    <span className="text-xs font-semibold uppercase tracking-wide text-bf-cream/44">
                      {formatPublishedDate(selectedUpdate.publishedAt)}
                    </span>
                  </div>
                  <h2 className="mt-3 break-words text-3xl font-black uppercase leading-tight text-slate-100">
                    {selectedUpdate.title}
                  </h2>
                  <p className="mt-3 max-w-[780px] text-sm leading-6 text-bf-cream/70">
                    {selectedUpdate.summary || 'Без краткого описания.'}
                  </p>
                </div>

                {selectedUpdate.heroImageUrl ? (
                  <div className="relative h-48 w-full overflow-hidden rounded-xl border border-bf-cream/10 bg-[#101620]">
                    <img
                      className="h-full w-full object-cover opacity-88"
                      src={selectedUpdate.heroImageUrl}
                      alt={selectedUpdate.title}
                    />
                    <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(16,22,32,0.18),rgba(16,22,32,0.5))]" />
                  </div>
                ) : null}
              </div>

              <div className="rounded-xl border border-bf-cream/10 bg-black/18 p-4">
                <div className="grid gap-4">
                  {selectedUpdate.contentJson.length ? (
                    selectedUpdate.contentJson.map((block, index) => (
                      <UpdateContentBlock key={`${block.type}-${index}-${block.text || block.src || 'block'}`} block={block} />
                    ))
                  ) : (
                    <div className="text-sm text-bf-cream/60">Контент патча не найден.</div>
                  )}
                </div>
              </div>

              <div className="flex justify-end">
                <a
                  className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-bf-cream/10 bg-black/18 px-4 font-black text-slate-100 transition hover:border-bf-orange/35 hover:text-bf-orange"
                  href={selectedUpdate.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink size={17} />
                  Открыть на Blizzard
                </a>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-bf-cream/10 bg-black/18 px-4 py-6 text-sm text-bf-cream/62">
              Выберите обновление из списка.
            </div>
          )}
        </div>
      </section>
    </>
  );
}
