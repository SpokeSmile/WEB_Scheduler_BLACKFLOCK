import { Avatar, DiscordClouds, RoleBadge } from './common.jsx';

function TeamBanner() {
  return (
    <section className="glass-panel hero-banner relative mt-4 overflow-hidden rounded-xl border-bf-orange/45 px-6 py-6 lg:px-8">
      <div className="relative z-10 grid gap-2 lg:max-w-[520px]">
        <div className="text-sm font-black uppercase text-bf-orange">Black Flock team</div>
        <h1 className="whitespace-nowrap text-4xl font-black uppercase leading-none text-slate-100 max-md:text-3xl">
          Состав команды
        </h1>
      </div>
    </section>
  );
}

function StaffDirectory({ staffMembers }) {
  return (
    <section className="glass-panel mt-4 rounded-xl p-4">
      <div className="mb-4">
        <div className="text-sm font-black uppercase text-bf-orange">Operations</div>
        <h2 className="mt-1 text-xl font-black uppercase text-slate-100">Организаторский состав</h2>
      </div>

      {staffMembers.length ? (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {staffMembers.map((staffMember) => (
            <article key={staffMember.id} className="rounded-xl border border-bf-cream/10 bg-black/24 p-4 shadow-[0_10px_24px_rgba(0,0,0,0.16)]">
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

              <div className="mt-4 rounded-xl border border-bf-cream/10 bg-black/28 px-4 py-3">
                <div className="text-[11px] font-black uppercase tracking-wide text-bf-cream/44">Discord</div>
                <DiscordClouds displayTag={staffMember.discordDisplayTag} />
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-bf-cream/12 bg-black/20 px-4 py-6 text-sm text-bf-cream/46">
          Организаторский состав пока не заполнен в админке.
        </div>
      )}
    </section>
  );
}

function PlayerProfiles({ players, showHeading = true }) {
  return (
    <section className="glass-panel mt-4 rounded-xl p-4">
      {showHeading ? (
        <div className="mb-4">
          <div className="text-sm font-black uppercase text-bf-orange">Player profiles</div>
          <h2 className="mt-1 text-xl font-black uppercase text-slate-100">Актуальные игровые профили</h2>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {players.map((player) => (
          <article key={player.id} className="rounded-xl border border-bf-cream/10 bg-black/24 p-4 shadow-[0_10px_24px_rgba(0,0,0,0.16)]">
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
              <div className="rounded-xl border border-bf-cream/10 bg-black/28 px-4 py-3">
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

              <div className="rounded-xl border border-bf-cream/10 bg-black/28 px-4 py-3">
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

export default function TeamPage({ players, staffMembers }) {
  return (
    <>
      <TeamBanner />
      <PlayerProfiles players={players} showHeading={false} />
      <StaffDirectory staffMembers={staffMembers} />
    </>
  );
}
