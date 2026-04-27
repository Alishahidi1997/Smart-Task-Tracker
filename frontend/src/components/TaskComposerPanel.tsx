import type { FormEvent } from "react";

type TaskComposerPanelProps = {
  aiInput: string;
  aiLoading: boolean;
  aiNote: string;
  title: string;
  description: string;
  dueDate: string;
  creating: boolean;
  onAiInputChange: (value: string) => void;
  onAiParse: () => Promise<void>;
  onSubmit: (e: FormEvent<HTMLFormElement>) => Promise<void>;
  onTitleChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onDueDateChange: (value: string) => void;
};

export function TaskComposerPanel({
  aiInput,
  aiLoading,
  aiNote,
  title,
  description,
  dueDate,
  creating,
  onAiInputChange,
  onAiParse,
  onSubmit,
  onTitleChange,
  onDescriptionChange,
  onDueDateChange,
}: TaskComposerPanelProps) {
  return (
    <>
      <section className="panel">
        <h2>AI task parser</h2>
        <p className="muted">Write a natural sentence and auto-fill the form below.</p>
        <div className="task-form">
          <textarea
            value={aiInput}
            onChange={(e) => onAiInputChange(e.target.value)}
            placeholder='Example: "Finish auth docs tomorrow at 5pm and prepare release notes"'
          />
          <button type="button" onClick={() => void onAiParse()} disabled={aiLoading}>
            {aiLoading ? "Parsing..." : "Parse with AI"}
          </button>
          {aiNote ? <p className="muted">{aiNote}</p> : null}
        </div>
      </section>

      <section className="panel">
        <h2>Create task</h2>
        <form onSubmit={(e) => void onSubmit(e)} className="task-form">
          <label>
            Title
            <input
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              placeholder="Finish API docs"
              required
            />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => onDescriptionChange(e.target.value)}
              placeholder="Optional details"
            />
          </label>
          <label>
            Due date
            <input
              type="datetime-local"
              value={dueDate}
              onChange={(e) => onDueDateChange(e.target.value)}
            />
          </label>
          <button type="submit" disabled={creating}>
            {creating ? "Creating..." : "Add task"}
          </button>
        </form>
      </section>
    </>
  );
}
