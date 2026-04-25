// CS1: Task Manager — BEFORE (clean, optimized)
import React, { useEffect, useState, useCallback, useMemo } from 'react';

interface Task {
  id: number;
  title: string;
  done: boolean;
  priority: 'low' | 'medium' | 'high';
}

interface TaskItemProps {
  task: Task;
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
}

const TaskItem = React.memo(function TaskItem({ task, onToggle, onDelete }: TaskItemProps) {
  return (
    <div className={`task-item priority-${task.priority}`}>
      <input type="checkbox" checked={task.done} onChange={() => onToggle(task.id)} />
      <span style={{ textDecoration: task.done ? 'line-through' : 'none' }}>{task.title}</span>
      <button onClick={() => onDelete(task.id)}>Delete</button>
    </div>
  );
});

export default function TaskManager() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<'all' | 'active' | 'done'>('all');

  useEffect(() => {
    const saved = localStorage.getItem('tasks');
    if (saved) setTasks(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem('tasks', JSON.stringify(tasks));
  }, [tasks]);

  const handleToggle = useCallback((id: number) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t));
  }, []);

  const handleDelete = useCallback((id: number) => {
    setTasks(prev => prev.filter(t => t.id !== id));
  }, []);

  const filtered = useMemo(() =>
    tasks.filter(t => filter === 'all' ? true : filter === 'done' ? t.done : !t.done),
    [tasks, filter]
  );

  return (
    <div className="task-manager">
      <div className="filters">
        {(['all', 'active', 'done'] as const).map(f => (
          <button key={f} className={filter === f ? 'active' : ''} onClick={() => setFilter(f)}>{f}</button>
        ))}
      </div>
      <div className="task-list">
        {filtered.map(t => (
          <TaskItem key={t.id} task={t} onToggle={handleToggle} onDelete={handleDelete} />
        ))}
      </div>
      <div className="summary">
        {useMemo(() => `${tasks.filter(t => !t.done).length} tasks remaining`, [tasks])}
      </div>
    </div>
  );
}
