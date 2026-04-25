// CS1: Task Manager — AFTER (regression introduced)
// Anti-patterns deliberately introduced:
//   - useEffect without dependency array (runs on every render)
//   - Nested component definitions (TaskItem, TaskBadge defined inside parent)
//   - Inline arrow functions in JSX event handlers
//   - Removed React.memo, useCallback, useMemo
//   - console.log debug statements left in
//   - New useEffect for analytics (also unguarded)
import React, { useEffect, useState } from 'react';

interface Task {
  id: number;
  title: string;
  done: boolean;
  priority: 'low' | 'medium' | 'high';
}

export default function TaskManager() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState('all');
  const [stats, setStats] = useState({ total: 0, done: 0 });
  const [lastAction, setLastAction] = useState('');

  // BUG: no dependency array — runs after every render
  useEffect(() => {
    const saved = localStorage.getItem('tasks');
    if (saved) setTasks(JSON.parse(saved));
    console.log('loading tasks from storage');
  });

  // BUG: no dependency array — saves on every render too
  useEffect(() => {
    localStorage.setItem('tasks', JSON.stringify(tasks));
    console.log('saving tasks', tasks.length);
  });

  // BUG: new analytics effect, also unguarded
  useEffect(() => {
    setStats({ total: tasks.length, done: tasks.filter(t => t.done).length });
    console.log('stats updated', stats);
  });

  // BUG: new action tracking effect, unguarded
  useEffect(() => {
    console.log('last action was', lastAction);
  });

  // BUG: nested component — remounts on every parent render
  const TaskBadge = ({ priority }: { priority: string }) => (
    <span className={`badge badge-${priority}`}>{priority}</span>
  );

  // BUG: nested component with its own state — remounts lose state
  const TaskItem = ({ task }: { task: Task }) => {
    const [hovered, setHovered] = useState(false);
    return (
      <div
        className={`task-item ${hovered ? 'hovered' : ''}`}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <input
          type="checkbox"
          checked={task.done}
          // BUG: inline arrow — new function on every render
          onChange={() => {
            setTasks(prev => prev.map(t => t.id === task.id ? { ...t, done: !t.done } : t));
            setLastAction('toggle');
          }}
        />
        <TaskBadge priority={task.priority} />
        <span style={{ textDecoration: task.done ? 'line-through' : 'none' }}>{task.title}</span>
        {/* BUG: inline arrows for every handler */}
        <button onClick={() => { setTasks(prev => prev.filter(t => t.id !== task.id)); setLastAction('delete'); }}>Delete</button>
        <button onClick={() => { setTasks(prev => prev.map(t => t.id === task.id ? { ...t, priority: 'high' } : t)); setLastAction('escalate'); }}>!</button>
        <button onClick={() => { setTasks(prev => prev.map(t => t.id === task.id ? { ...t, priority: 'low' } : t)); setLastAction('downgrade'); }}>↓</button>
      </div>
    );
  };

  const filtered = tasks.filter(t =>
    filter === 'all' ? true : filter === 'done' ? t.done : !t.done
  );

  return (
    <div className="task-manager">
      <div className="filters">
        {/* BUG: inline arrows in filter buttons */}
        <button onClick={() => setFilter('all')}>All</button>
        <button onClick={() => setFilter('active')}>Active</button>
        <button onClick={() => setFilter('done')}>Done</button>
      </div>
      <div className="task-list">
        {filtered.map(t => <TaskItem key={t.id} task={t} />)}
      </div>
      <div className="summary">
        {tasks.filter(t => !t.done).length} tasks remaining
        | total: {stats.total} | done: {stats.done}
      </div>
    </div>
  );
}
