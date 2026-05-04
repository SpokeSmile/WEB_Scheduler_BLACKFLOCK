import { useEffect, useState } from 'react';

import {
  bootstrap,
  fetchGameUpdateDetail,
  fetchGameUpdates,
  fetchOverwatchStats,
  refreshOverwatchStats,
} from './api.js';
import { Header, Sidebar } from './components/AppChrome.jsx';
import { ErrorView, LoadingView } from './components/AppStateViews.jsx';
import MainPage from './components/MainPage.jsx';
import EventModal from './components/modals/EventModal.jsx';
import OverwatchStatsPage from './components/OverwatchStatsPage.jsx';
import ProfilePage from './components/profile/ProfilePage.jsx';
import CommentTooltip from './components/schedule/CommentTooltip.jsx';
import RosterPage from './components/schedule/RosterPage.jsx';
import TeamPage from './components/TeamPage.jsx';
import UpdatesPage from './components/UpdatesPage.jsx';

function getScheduleWeekParam() {
  return new URLSearchParams(window.location.search).get('week') || '';
}

function setScheduleWeekParam(weekStart) {
  const params = new URLSearchParams(window.location.search);
  if (weekStart) {
    params.set('week', weekStart);
  } else {
    params.delete('week');
  }
  const query = params.toString();
  window.history.replaceState({}, document.title, `${window.location.pathname}${query ? `?${query}` : ''}`);
}

export default function App() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [slotModal, setSlotModal] = useState(null);
  const [commentTooltip, setCommentTooltip] = useState(null);
  const [updatesList, setUpdatesList] = useState([]);
  const [updatesBySlug, setUpdatesBySlug] = useState({});
  const [isLoadingUpdatesList, setIsLoadingUpdatesList] = useState(false);
  const [isLoadingUpdateDetail, setIsLoadingUpdateDetail] = useState(false);
  const [updatesError, setUpdatesError] = useState('');
  const [selectedUpdateSlug, setSelectedUpdateSlug] = useState(() => new URLSearchParams(window.location.search).get('patch') || '');
  const statsMode = 'competitive';
  const [statsByMode, setStatsByMode] = useState({});
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [isRefreshingStats, setIsRefreshingStats] = useState(false);
  const [statsError, setStatsError] = useState('');

  async function loadData(weekStart = getScheduleWeekParam()) {
    setIsLoading(true);
    try {
      const response = await bootstrap(weekStart);
      setData(response);
      if (window.location.pathname === '/' && response.selectedWeekStart) {
        setScheduleWeekParam(response.selectedWeekStart);
      }
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

  async function loadUpdatesList() {
    setIsLoadingUpdatesList(true);
    setUpdatesError('');
    try {
      const response = await fetchGameUpdates();
      setUpdatesList(response.updates || []);
      return response.updates || [];
    } catch (loadError) {
      setUpdatesError(loadError.message);
      return [];
    } finally {
      setIsLoadingUpdatesList(false);
    }
  }

  async function loadUpdateDetail(slug) {
    if (!slug || updatesBySlug[slug]) {
      return updatesBySlug[slug] || null;
    }

    setIsLoadingUpdateDetail(true);
    setUpdatesError('');
    try {
      const response = await fetchGameUpdateDetail(slug);
      setUpdatesBySlug((current) => ({
        ...current,
        [slug]: response.update,
      }));
      return response.update;
    } catch (loadError) {
      setUpdatesError(loadError.message);
      return null;
    } finally {
      setIsLoadingUpdateDetail(false);
    }
  }

  function selectUpdate(slug) {
    setSelectedUpdateSlug(slug);
    const params = new URLSearchParams(window.location.search);
    if (slug) {
      params.set('patch', slug);
    } else {
      params.delete('patch');
    }
    const query = params.toString();
    window.history.replaceState({}, document.title, `${window.location.pathname}${query ? `?${query}` : ''}`);
  }

  async function loadOverwatchStats(mode) {
    setIsLoadingStats(true);
    setStatsError('');
    try {
      const response = await fetchOverwatchStats(mode);
      setStatsByMode((current) => ({
        ...current,
        [response.stats.mode]: response.stats,
      }));
      return response.stats;
    } catch (loadError) {
      setStatsError(loadError.message);
      return null;
    } finally {
      setIsLoadingStats(false);
    }
  }

  async function handleOverwatchStatsRefresh() {
    setIsRefreshingStats(true);
    setStatsError('');
    try {
      const response = await refreshOverwatchStats(statsMode);
      setStatsByMode((current) => ({
        ...current,
        [response.stats.mode]: response.stats,
      }));
    } catch (refreshError) {
      setStatsError(refreshError.message);
    } finally {
      setIsRefreshingStats(false);
    }
  }

  useEffect(() => {
    if (!commentTooltip) return;

    const handleViewportChange = () => setCommentTooltip(null);
    window.addEventListener('scroll', handleViewportChange, true);
    window.addEventListener('resize', handleViewportChange);

    return () => {
      window.removeEventListener('scroll', handleViewportChange, true);
      window.removeEventListener('resize', handleViewportChange);
    };
  }, [commentTooltip]);

  const pathname = window.location.pathname;
  const isMainPage = pathname.startsWith('/main');
  const isUpdatesPage = pathname.startsWith('/updates');
  const isStatsPage = pathname.startsWith('/stats');

  useEffect(() => {
    if (!isUpdatesPage) return;

    let isMounted = true;

    loadUpdatesList().then((updates) => {
      if (!isMounted) return;
      const requestedSlug = new URLSearchParams(window.location.search).get('patch') || '';
      const initialSlug = updates.some((item) => item.slug === requestedSlug)
        ? requestedSlug
        : updates[0]?.slug || '';

      if (initialSlug) {
        setSelectedUpdateSlug(initialSlug);
        const params = new URLSearchParams(window.location.search);
        if (params.get('patch') !== initialSlug) {
          params.set('patch', initialSlug);
          window.history.replaceState({}, document.title, `${window.location.pathname}?${params.toString()}`);
        }
      } else {
        setSelectedUpdateSlug('');
      }
    });

    return () => {
      isMounted = false;
    };
  }, [isUpdatesPage]);

  useEffect(() => {
    if (!isUpdatesPage || !selectedUpdateSlug) return;
    loadUpdateDetail(selectedUpdateSlug);
  }, [isUpdatesPage, selectedUpdateSlug]);

  useEffect(() => {
    if (!isStatsPage) return;
    loadOverwatchStats(statsMode);
  }, [isStatsPage, statsMode]);

  function handleNoteHoverStart(text, anchorRect) {
    setCommentTooltip({
      text,
      anchorRect,
      placement: 'bottom',
      visible: true,
    });
  }

  function handleNoteHoverEnd() {
    setCommentTooltip(null);
  }

  function upsertSlot(slot) {
    setData((current) => {
      if (slot.weekStart !== current.selectedWeekStart) {
        return current;
      }
      return {
        ...current,
        slots: current.slots.some((existing) => existing.id === slot.id)
          ? current.slots.map((existing) => (existing.id === slot.id ? slot : existing))
          : [...current.slots, slot],
      };
    });
    setSlotModal(null);
  }

  function removeSlot(id) {
    setData((current) => ({
      ...current,
      slots: current.slots.filter((slot) => slot.id !== id),
    }));
    setSlotModal(null);
  }

  async function handleWeekChange(weekStart) {
    setScheduleWeekParam(weekStart);
    await loadData(weekStart);
  }

  async function updatePlayerProfile(player, options = {}) {
    if (options.reload) {
      await loadData();
      return;
    }
    setData((current) => ({
      ...current,
      players: current.players.map((existing) => (existing.id === player.id ? player : existing)),
    }));
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
    return <LoadingView />;
  }

  if (error) {
    return <ErrorView error={error} onRetry={loadData} />;
  }

  const hasPlayerProfile = Boolean(data.user.playerId);
  const canAdd = hasPlayerProfile && data.canEditSelectedWeek;
  const isProfilePage = pathname.startsWith('/profile');
  const isTeamPage = pathname.startsWith('/team');
  const currentPlayer = data.players.find((player) => player.id === data.user.playerId) || null;
  const currentStaffMember = data.staffMembers.find((staffMember) => staffMember.id === data.user.staffMemberId) || null;
  const currentProfile = data.user.profileType === 'staff' ? currentStaffMember : currentPlayer;
  const handleProfileSaved = data.user.profileType === 'staff' ? updateStaffProfile : updatePlayerProfile;
  const selectedUpdate = selectedUpdateSlug ? updatesBySlug[selectedUpdateSlug] || null : null;
  const selectedStats = statsByMode[statsMode] || null;

  return (
    <main className="mx-auto min-h-screen w-[min(1500px,calc(100%_-_48px))] py-4 xl:w-[min(1700px,calc(100%_-_32px))] 2xl:w-[min(1820px,calc(100%_-_28px))] max-sm:w-[min(100%_-_20px,760px)]">
      <div className="app-shell">
        <Sidebar pathname={pathname} />
        <div className="min-w-0">
          <Header user={data.user} />
          {isMainPage ? (
            <MainPage
              players={data.players}
              staffMembers={data.staffMembers}
              slots={data.slots}
              weekRangeLabel={data.weekRangeLabel}
              user={data.user}
            />
          ) : isProfilePage ? (
            <ProfilePage
              user={data.user}
              profile={currentProfile}
              profileType={data.user.profileType}
              onSaved={handleProfileSaved}
            />
          ) : isTeamPage ? (
            <TeamPage players={data.players} staffMembers={data.staffMembers} />
          ) : isUpdatesPage ? (
            <UpdatesPage
              updates={updatesList}
              selectedSlug={selectedUpdateSlug}
              selectedUpdate={selectedUpdate}
              onSelect={selectUpdate}
              isLoadingList={isLoadingUpdatesList}
              isLoadingDetail={isLoadingUpdateDetail}
              error={updatesError}
            />
          ) : isStatsPage ? (
            <OverwatchStatsPage
              stats={selectedStats}
              isLoading={isLoadingStats}
              isRefreshing={isRefreshingStats}
              error={statsError}
              onRefresh={handleOverwatchStatsRefresh}
            />
          ) : (
            <>
              <RosterPage
                hasPlayerProfile={hasPlayerProfile}
                canAdd={canAdd}
                canEditSelectedWeek={data.canEditSelectedWeek}
                selectedWeekStart={data.selectedWeekStart}
                weekRangeLabel={data.weekRangeLabel}
                days={data.days}
                players={data.players}
                slots={data.slots}
                dayEventTypes={data.dayEventTypes}
                eventTypes={data.eventTypes}
                lastUpdated={data.lastUpdated}
                onAdd={(day) => setSlotModal({ day })}
                onEdit={(event) => setSlotModal({ event })}
                onWeekChange={handleWeekChange}
                onNoteHoverStart={handleNoteHoverStart}
                onNoteHoverEnd={handleNoteHoverEnd}
              />
            </>
          )}
        </div>
      </div>
      {slotModal ? (
        <EventModal
          event={slotModal.event}
          day={slotModal.day}
          days={data.days}
          weekStart={data.selectedWeekStart}
          onClose={() => setSlotModal(null)}
          onSaved={upsertSlot}
          onDeleted={removeSlot}
        />
      ) : null}
      {commentTooltip?.visible ? (
        <CommentTooltip
          key={`${commentTooltip.anchorRect.left}-${commentTooltip.anchorRect.top}-${commentTooltip.text}`}
          tooltip={commentTooltip}
        />
      ) : null}
    </main>
  );
}
