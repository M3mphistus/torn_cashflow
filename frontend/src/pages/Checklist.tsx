import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getChecklist, createTask, updateTask, deleteTask, setTaskDone, type ChecklistTaskInput } from '../api/checklist';
import { getWarMode } from '../api/settings';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import type { ChecklistTaskDTO, RepeatType } from '../types/api';

const REPEAT_TYPE_LABELS: Record<RepeatType, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  every_x_days: 'Every X Days',
  once: 'One-off',
  war_day: 'On War Days',
};

const REPEAT_TYPE_ORDER: RepeatType[] = ['daily', 'weekly', 'every_x_days', 'war_day', 'once'];

export default function ChecklistPage() {
  const { premium } = useAuth();
  const queryClient = useQueryClient();

  const tasksQuery = useQuery({ queryKey: ['checklist'], queryFn: getChecklist });
  const warModeQuery = useQuery({ queryKey: ['warMode'], queryFn: getWarMode });

  const invalidateTasks = () => queryClient.invalidateQueries({ queryKey: ['checklist'] });

  const createMutation = useMutation({ mutationFn: createTask, onSuccess: invalidateTasks });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: ChecklistTaskInput }) => updateTask(id, input),
    onSuccess: invalidateTasks,
  });
  const deleteMutation = useMutation({ mutationFn: deleteTask, onSuccess: invalidateTasks });
  const doneMutation = useMutation({
    mutationFn: ({ id, done }: { id: number; done: boolean }) => setTaskDone(id, done),
    onSuccess: invalidateTasks,
  });

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [repeatType, setRepeatType] = useState<RepeatType>('daily');
  const [intervalDays, setIntervalDays] = useState(2);
  const [editingId, setEditingId] = useState<number | null>(null);

  function handleAddTask(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    createMutation.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        repeatType,
        repeatIntervalDays: repeatType === 'every_x_days' ? intervalDays : null,
      },
      { onSuccess: () => { setTitle(''); setDescription(''); setRepeatType('daily'); } },
    );
  }

  const warModeActive = warModeQuery.data?.active ?? false;
  const allTasks = tasksQuery.data?.tasks ?? [];
  const visibleTasks = allTasks.filter((t) => t.repeatType !== 'war_day' || warModeActive);
  const openTasks = visibleTasks.filter((t) => !t.isDoneCurrentCycle);
  const doneTasks = visibleTasks.filter((t) => t.isDoneCurrentCycle);

  const grouped = new Map<RepeatType, ChecklistTaskDTO[]>();
  for (const rt of REPEAT_TYPE_ORDER) {
    const group = openTasks.filter((t) => t.repeatType === rt);
    if (group.length > 0) grouped.set(rt, group);
  }

  return (
    <div className="page">
      <h1>Checklist</h1>

      {!premium?.isPremium && (
        <AlertBanner kind="info">
          Recurring tasks reset automatically with Premium. On the free tier, check tasks off and
          un-check them yourself when a new cycle starts.
        </AlertBanner>
      )}

      <SectionHeading>Add a task</SectionHeading>
      <Card>
        <form onSubmit={handleAddTask}>
          <label htmlFor="task-title">Title</label>
          <input id="task-title" value={title} onChange={(e) => setTitle(e.target.value)} />

          <label htmlFor="task-description" style={{ marginTop: 8 }}>
            Description (optional)
          </label>
          <textarea id="task-description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />

          <label htmlFor="task-repeat" style={{ marginTop: 8 }}>
            Repeat type
          </label>
          <select id="task-repeat" value={repeatType} onChange={(e) => setRepeatType(e.target.value as RepeatType)}>
            {REPEAT_TYPE_ORDER.map((rt) => (
              <option key={rt} value={rt}>
                {REPEAT_TYPE_LABELS[rt]}
              </option>
            ))}
          </select>

          {repeatType === 'every_x_days' && (
            <>
              <label htmlFor="task-interval" style={{ marginTop: 8 }}>
                Every X days
              </label>
              <input id="task-interval" type="number" min={1} value={intervalDays} onChange={(e) => setIntervalDays(Number(e.target.value))} />
            </>
          )}

          <div style={{ marginTop: 12 }}>
            <Button type="submit" variant="primary" disabled={createMutation.isPending || !title.trim()}>
              Add task
            </Button>
          </div>
        </form>
      </Card>

      <hr />
      <SectionHeading>Open Tasks</SectionHeading>
      {openTasks.length === 0 ? (
        <AlertBanner kind="info">Nothing open right now.</AlertBanner>
      ) : (
        [...grouped.entries()].map(([rt, group]) => (
          <div key={rt}>
            <p style={{ fontFamily: 'var(--label)', textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 12, color: 'var(--text-mute)' }}>
              {REPEAT_TYPE_LABELS[rt]}
            </p>
            {group.map((task) =>
              editingId === task.id ? (
                <EditTaskForm
                  key={task.id}
                  task={task}
                  onCancel={() => setEditingId(null)}
                  onSave={(input) => {
                    updateMutation.mutate({ id: task.id, input });
                    setEditingId(null);
                  }}
                />
              ) : (
                <TaskRow
                  key={task.id}
                  task={task}
                  onToggleDone={() => doneMutation.mutate({ id: task.id, done: true })}
                  onEdit={() => setEditingId(task.id)}
                  onDelete={() => deleteMutation.mutate(task.id)}
                />
              ),
            )}
          </div>
        ))
      )}

      <hr />
      <SectionHeading>Completed</SectionHeading>
      {doneTasks.length === 0 ? (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Nothing completed for the current cycle.</p>
      ) : (
        <details>
          <summary>{doneTasks.length} completed task(s)</summary>
          {doneTasks.map((task) => (
            <div key={task.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0' }}>
              <input type="checkbox" style={{ width: 'auto' }} checked onChange={() => doneMutation.mutate({ id: task.id, done: false })} />
              <span style={{ textDecoration: 'line-through' }}>{task.title}</span>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}

function TaskRow({
  task,
  onToggleDone,
  onEdit,
  onDelete,
}: {
  task: ChecklistTaskDTO;
  onToggleDone: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <input type="checkbox" style={{ width: 'auto', marginTop: 4 }} checked={false} onChange={onToggleDone} />
        <div style={{ flex: 1 }}>
          <strong>{task.title}</strong>
          {task.description && <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>{task.description}</p>}
        </div>
        <Button onClick={onEdit}>Edit</Button>
        <Button variant="danger" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </Card>
  );
}

function EditTaskForm({
  task,
  onCancel,
  onSave,
}: {
  task: ChecklistTaskDTO;
  onCancel: () => void;
  onSave: (input: ChecklistTaskInput) => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description ?? '');
  const [repeatType, setRepeatType] = useState<RepeatType>(task.repeatType);
  const [intervalDays, setIntervalDays] = useState(task.repeatIntervalDays ?? 2);

  return (
    <Card>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSave({
            title: title.trim(),
            description: description.trim(),
            repeatType,
            repeatIntervalDays: repeatType === 'every_x_days' ? intervalDays : null,
          });
        }}
      >
        <label htmlFor={`edit-title-${task.id}`}>Title</label>
        <input id={`edit-title-${task.id}`} value={title} onChange={(e) => setTitle(e.target.value)} />

        <label htmlFor={`edit-desc-${task.id}`} style={{ marginTop: 8 }}>
          Description
        </label>
        <textarea id={`edit-desc-${task.id}`} value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />

        <label htmlFor={`edit-repeat-${task.id}`} style={{ marginTop: 8 }}>
          Repeat type
        </label>
        <select id={`edit-repeat-${task.id}`} value={repeatType} onChange={(e) => setRepeatType(e.target.value as RepeatType)}>
          {REPEAT_TYPE_ORDER.map((rt) => (
            <option key={rt} value={rt}>
              {REPEAT_TYPE_LABELS[rt]}
            </option>
          ))}
        </select>

        {repeatType === 'every_x_days' && (
          <>
            <label htmlFor={`edit-interval-${task.id}`} style={{ marginTop: 8 }}>
              Every X days
            </label>
            <input
              id={`edit-interval-${task.id}`}
              type="number"
              min={1}
              value={intervalDays}
              onChange={(e) => setIntervalDays(Number(e.target.value))}
            />
          </>
        )}

        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <Button type="submit" variant="primary">
            Save changes
          </Button>
          <Button type="button" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}
