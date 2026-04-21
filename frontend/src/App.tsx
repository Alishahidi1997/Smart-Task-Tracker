import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

type TaskStatus = "todo" | "in_progress" | "done";
type TaskCategory = "today" | "this_week" | "routine" | "backlog";

type Task = {
  id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  due_date: string | null;
  category: TaskCategory | null;
};

type DailySummaryResponse = {
  summary: string;
  task_count: number;
  mode: string;
};

type ProductivityBucket = {
  category: string;
  tasks_completed: number;
  avg_hours_to_complete: number;
};

type ProductivityResponse = {
  buckets: ProductivityBucket[];
  narrative: string;
};

type PriorityTask = {
  id: number;
  title: string;
  status: TaskStatus;
  due_date: string;
  category: string;
  hours_overdue: number;
  priority: "low" | "medium" | "high";
};

type PriorityResponse = {
  generated_at: string;
  total_overdue: number;
  suggestion: string;
  tasks: PriorityTask[];
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [creating, setCreating] = useState(false);
  const [updatingTaskId, setUpdatingTaskId] = useState<number | null>(null);
  const [deletingTaskId, setDeletingTaskId] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState<"" | TaskStatus>("");
  const [filterDueBefore, setFilterDueBefore] = useState("");
  const [filterDueAfter, setFilterDueAfter] = useState("");
  const [dailySummary, setDailySummary] = useState<DailySummaryResponse | null>(null);
  const [productivity, setProductivity] = useState<ProductivityResponse | null>(null);
  const [priority, setPriority] = useState<PriorityResponse | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState("");

  const statusCount = useMemo(() => {
    return tasks.reduce(
      (acc, task) => {
        acc[task.status] += 1;
        return acc;
      },
      { todo: 0, in_progress: 0, done: 0 },
    );
  }, [tasks]);

  async function loadTasks() {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (filterStatus) {
        params.set("status", filterStatus);
      }
      if (filterDueBefore) {
        params.set("due_before", new Date(filterDueBefore).toISOString());
      }
      if (filterDueAfter) {
        params.set("due_after", new Date(filterDueAfter).toISOString());
      }
      const query = params.toString();
      const response = await fetch(`${API_BASE_URL}/tasks${query ? `?${query}` : ""}`);
      if (!response.ok) {
        throw new Error(`Failed to load tasks (${response.status})`);
      }
      const data = (await response.json()) as Task[];
      setTasks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusChange(taskId: number, nextStatus: TaskStatus) {
    setUpdatingTaskId(taskId);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!response.ok) {
        throw new Error(`Failed to update task (${response.status})`);
      }
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update task");
    } finally {
      setUpdatingTaskId(null);
    }
  }

  async function handleDeleteTask(taskId: number) {
    setDeletingTaskId(taskId);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(`Failed to delete task (${response.status})`);
      }
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete task");
    } finally {
      setDeletingTaskId(null);
    }
  }

  async function handleCreateTask(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!title.trim()) {
      return;
    }

    setCreating(true);
    setError("");
    try {
      const payload = {
        title: title.trim(),
        description: description.trim() || null,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
      };
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Failed to create task (${response.status})`);
      }
      setTitle("");
      setDescription("");
      setDueDate("");
      await loadTasks();
      await loadInsights();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create task");
    } finally {
      setCreating(false);
    }
  }

  async function loadInsights() {
    setInsightsLoading(true);
    setInsightsError("");
    try {
      const [summaryRes, productivityRes, priorityRes] = await Promise.all([
        fetch(`${API_BASE_URL}/summary/daily`),
        fetch(`${API_BASE_URL}/insights/productivity`),
        fetch(`${API_BASE_URL}/insights/priority`),
      ]);

      if (!summaryRes.ok) {
        throw new Error(`Daily summary failed (${summaryRes.status})`);
      }
      if (!productivityRes.ok) {
        throw new Error(`Productivity insights failed (${productivityRes.status})`);
      }
      if (!priorityRes.ok) {
        throw new Error(`Priority insights failed (${priorityRes.status})`);
      }

      setDailySummary((await summaryRes.json()) as DailySummaryResponse);
      setProductivity((await productivityRes.json()) as ProductivityResponse);
      setPriority((await priorityRes.json()) as PriorityResponse);
    } catch (err) {
      setInsightsError(err instanceof Error ? err.message : "Could not load insights");
    } finally {
      setInsightsLoading(false);
    }
  }

  useEffect(() => {
    void loadTasks();
  }, [filterStatus, filterDueBefore, filterDueAfter]);

  useEffect(() => {
    void loadInsights();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <h1>Smart Task Tracker</h1>
        <p>FastAPI + React task dashboard</p>
      </header>

      <section className="panel stats">
        <div><strong>{tasks.length}</strong> total</div>
        <div><strong>{statusCount.todo}</strong> todo</div>
        <div><strong>{statusCount.in_progress}</strong> in progress</div>
        <div><strong>{statusCount.done}</strong> done</div>
      </section>

      <section className="panel">
        <h2>Filters</h2>
        <div className="filters">
          <label>
            Status
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as "" | TaskStatus)}
            >
              <option value="">All</option>
              <option value="todo">todo</option>
              <option value="in_progress">in_progress</option>
              <option value="done">done</option>
            </select>
          </label>
          <label>
            Due before
            <input
              type="datetime-local"
              value={filterDueBefore}
              onChange={(e) => setFilterDueBefore(e.target.value)}
            />
          </label>
          <label>
            Due after
            <input
              type="datetime-local"
              value={filterDueAfter}
              onChange={(e) => setFilterDueAfter(e.target.value)}
            />
          </label>
          <button
            type="button"
            onClick={() => {
              setFilterStatus("");
              setFilterDueBefore("");
              setFilterDueAfter("");
            }}
          >
            Clear filters
          </button>
        </div>
      </section>

      <section className="panel">
        <h2>Create task</h2>
        <form onSubmit={handleCreateTask} className="task-form">
          <label>
            Title
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Finish API docs"
              required
            />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional details"
            />
          </label>
          <label>
            Due date
            <input
              type="datetime-local"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </label>
          <button type="submit" disabled={creating}>
            {creating ? "Creating..." : "Add task"}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="list-head">
          <h2>Tasks</h2>
          <button type="button" onClick={() => void loadTasks()} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {error ? <p className="error">{error}</p> : null}
        {!loading && tasks.length === 0 ? <p>No tasks yet.</p> : null}
        <ul className="task-list">
          {tasks.map((task) => (
            <li key={task.id}>
              <div className="row">
                <strong>{task.title}</strong>
                <span className={`badge ${task.status}`}>{task.status}</span>
              </div>
              {task.description ? <p>{task.description}</p> : null}
              <small>
                category: {task.category ?? "n/a"} | due: {task.due_date ?? "n/a"}
              </small>
              <div className="task-actions">
                <select
                  value={task.status}
                  onChange={(e) => void handleStatusChange(task.id, e.target.value as TaskStatus)}
                  disabled={updatingTaskId === task.id}
                >
                  <option value="todo">todo</option>
                  <option value="in_progress">in_progress</option>
                  <option value="done">done</option>
                </select>
                <button
                  type="button"
                  className="danger"
                  onClick={() => void handleDeleteTask(task.id)}
                  disabled={deletingTaskId === task.id}
                >
                  {deletingTaskId === task.id ? "Deleting..." : "Delete"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <div className="list-head">
          <h2>Daily summary</h2>
          <button type="button" onClick={() => void loadInsights()} disabled={insightsLoading}>
            {insightsLoading ? "Refreshing..." : "Refresh insights"}
          </button>
        </div>
        {insightsError ? <p className="error">{insightsError}</p> : null}
        {dailySummary ? (
          <div className="insight-block">
            <p>{dailySummary.summary}</p>
            <small>
              mode: {dailySummary.mode} | based on {dailySummary.task_count} completed tasks
            </small>
          </div>
        ) : (
          <p>No summary yet.</p>
        )}
      </section>

      <section className="panel">
        <h2>Productivity insights</h2>
        {productivity ? (
          <div className="insight-block">
            <p>{productivity.narrative}</p>
            <ul className="simple-list">
              {productivity.buckets.map((bucket) => (
                <li key={bucket.category}>
                  <strong>{bucket.category}</strong>: {bucket.tasks_completed} tasks, avg{" "}
                  {bucket.avg_hours_to_complete}h
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p>No productivity data yet.</p>
        )}
      </section>

      <section className="panel">
        <h2>Priority suggestions</h2>
        {priority ? (
          <div className="insight-block">
            <p>{priority.suggestion}</p>
            <small>total overdue: {priority.total_overdue}</small>
            <ul className="simple-list">
              {priority.tasks.slice(0, 8).map((item) => (
                <li key={item.id}>
                  <strong>{item.title}</strong> ({item.priority}) - {item.hours_overdue}h overdue
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p>No overdue tasks right now.</p>
        )}
      </section>
    </main>
  );
}

export default App;
