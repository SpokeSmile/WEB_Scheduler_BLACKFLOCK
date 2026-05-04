import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, X } from 'lucide-react';

import { copyWeekSchedule } from '../../api.js';

function weekLabel(weeks, weekStart) {
  return weeks.find((week) => week.weekStart === weekStart)?.label || weekStart || '—';
}

export default function CopyScheduleModal({
  sourceWeeks,
  targetWeeks,
  selectedWeekStart,
  currentWeekStart,
  canEditSelectedWeek,
  onClose,
  onCopied,
}) {
  const defaultSourceWeekStart = useMemo(() => (
    sourceWeeks.find((week) => week.weekStart === selectedWeekStart)?.weekStart
    || sourceWeeks[0]?.weekStart
    || ''
  ), [sourceWeeks, selectedWeekStart]);
  const defaultTargetWeekStart = useMemo(() => {
    const preferredTarget = canEditSelectedWeek ? selectedWeekStart : currentWeekStart;
    return targetWeeks.find((week) => week.weekStart === preferredTarget)?.weekStart
      || targetWeeks[0]?.weekStart
      || '';
  }, [canEditSelectedWeek, currentWeekStart, selectedWeekStart, targetWeeks]);

  const [sourceWeekStart, setSourceWeekStart] = useState(defaultSourceWeekStart);
  const [targetWeekStart, setTargetWeekStart] = useState(defaultTargetWeekStart);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const isSameWeek = sourceWeekStart && targetWeekStart && sourceWeekStart === targetWeekStart;
  const canSubmit = sourceWeekStart && targetWeekStart && !isSameWeek && !isSaving;

  async function handleSubmit(submitEvent) {
    submitEvent.preventDefault();
    if (!canSubmit) return;

    setIsSaving(true);
    setError('');
    setSuccess('');

    try {
      const response = await copyWeekSchedule({
        sourceWeekStart,
        targetWeekStart,
      });
      setSuccess(`Скопировано записей: ${response.copiedCount}`);
      await onCopied(response.targetWeekStart);
    } catch (copyError) {
      setError(copyError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm">
      <motion.form
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="w-full max-w-xl rounded-xl border border-bf-cream/12 bg-[#0d1420] p-6 shadow-panel"
        onSubmit={handleSubmit}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm font-black uppercase text-bf-orange">Schedule copy</div>
            <h2 className="mt-1 text-2xl font-black uppercase text-slate-100">
              Скопировать расписание
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

        {sourceWeeks.length ? (
          <div className="mt-6 grid gap-5">
            <label className="grid gap-2 text-sm font-black text-bf-cream">
              С какой недели
              <select
                value={sourceWeekStart}
                onChange={(event) => {
                  setSourceWeekStart(event.target.value);
                  setSuccess('');
                  setError('');
                }}
              >
                {sourceWeeks.map((week) => (
                  <option key={week.weekStart} value={week.weekStart}>
                    {week.label} · записей: {week.slotCount}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-2 text-sm font-black text-bf-cream">
              На какую неделю
              <select
                value={targetWeekStart}
                onChange={(event) => {
                  setTargetWeekStart(event.target.value);
                  setSuccess('');
                  setError('');
                }}
              >
                {targetWeeks.map((week) => (
                  <option key={week.weekStart} value={week.weekStart}>
                    {week.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="rounded-xl border border-bf-cream/10 bg-black/20 p-3 text-sm text-bf-cream/62">
              Записи в неделе <span className="font-black text-bf-cream">{weekLabel(targetWeeks, targetWeekStart)}</span> будут заменены только у вашего профиля.
            </div>

            {isSameWeek ? (
              <div className="rounded-xl border border-orange-300/30 bg-orange-500/10 p-3 text-sm text-orange-100">
                Выберите разные недели для копирования.
              </div>
            ) : null}

            {error ? (
              <div className="rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
                {error}
              </div>
            ) : null}

            {success ? (
              <div className="rounded-xl border border-emerald-300/30 bg-emerald-500/10 p-3 text-sm font-bold text-emerald-100">
                {success}
              </div>
            ) : null}

            <div className="flex justify-end gap-3">
              <button
                className="rounded-xl border border-bf-cream/10 px-5 py-3 font-black text-bf-cream/70 transition hover:border-bf-cream/25 hover:text-bf-cream"
                type="button"
                onClick={onClose}
              >
                Закрыть
              </button>
              <button
                className="inline-flex items-center gap-2 rounded-xl bg-[#f4f7fb] px-5 py-3 font-black text-[#151b26] transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-45"
                type="submit"
                disabled={!canSubmit}
              >
                <Copy size={18} />
                {isSaving ? 'Копирую...' : 'Скопировать'}
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-6 rounded-xl border border-bf-cream/10 bg-black/20 p-4 text-sm text-bf-cream/65">
            Нет заполненных недель, которые можно скопировать.
          </div>
        )}
      </motion.form>
    </div>
  );
}
