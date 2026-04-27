import type { FormEvent } from "react";

type AuthPanelProps = {
  authMode: "login" | "register";
  authEmail: string;
  authPassword: string;
  authLoading: boolean;
  authError: string;
  onSubmit: (e: FormEvent<HTMLFormElement>) => Promise<void>;
  onToggleMode: () => void;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
};

export function AuthPanel({
  authMode,
  authEmail,
  authPassword,
  authLoading,
  authError,
  onSubmit,
  onToggleMode,
  onEmailChange,
  onPasswordChange,
}: AuthPanelProps) {
  return (
    <section className="panel">
      <h2>{authMode === "login" ? "Login" : "Create account"}</h2>
      <form className="task-form" onSubmit={(e) => void onSubmit(e)}>
        <label>
          Email
          <input
            type="email"
            value={authEmail}
            onChange={(e) => onEmailChange(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={authPassword}
            onChange={(e) => onPasswordChange(e.target.value)}
            required
          />
        </label>
        <div className="task-actions">
          <button type="submit" disabled={authLoading}>
            {authLoading ? "Please wait..." : authMode === "login" ? "Login" : "Register"}
          </button>
          <button type="button" onClick={onToggleMode}>
            {authMode === "login" ? "Switch to register" : "Switch to login"}
          </button>
        </div>
      </form>
      {authError ? <p className="error">{authError}</p> : null}
      <p className="muted">Demo account: demo@smarttracker.local / demo1234</p>
    </section>
  );
}
