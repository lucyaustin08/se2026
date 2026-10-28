/**
 * Who is using the app (the sprint 1 user picker).
 *
 * The choice lives in memory, mirrored to sessionStorage so a page reload keeps it. The API
 * client reads it on every request to send the X-Acting-Member-Id header. This is not
 * security: the server enforces every permission (see DECISIONS.md).
 */
import { createContext, use, useState, type ReactNode } from "react";

export interface ActingMember {
  id: number;
  name: string;
  isManager: boolean;
  isBandLeader: boolean;
}

/** The manager or the band leader: they see every gig in full. The server decides for real. */
export function runsTheBand(member: ActingMember): boolean {
  return member.isManager || member.isBandLeader;
}

const STORAGE_KEY = "roadhouse.actingMember";

function isActingMember(value: unknown): value is ActingMember {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "number" &&
    typeof record.name === "string" &&
    typeof record.isManager === "boolean" &&
    typeof record.isBandLeader === "boolean"
  );
}

function loadStoredMember(): ActingMember | null {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return isActingMember(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

let current: ActingMember | null = loadStoredMember();

export function getActingMember(): ActingMember | null {
  return current;
}

export function setActingMember(member: ActingMember | null): void {
  current = member;
  try {
    if (member) {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(member));
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // Storage can be unavailable (private browsing). The choice then lasts until reload.
  }
}

/** Re-read the stored choice. Used on startup and by tests. */
export function reloadActingMember(): ActingMember | null {
  current = loadStoredMember();
  return current;
}

interface SessionValue {
  member: ActingMember | null;
  signIn: (member: ActingMember) => void;
  signOut: () => void;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [member, setMember] = useState<ActingMember | null>(getActingMember);

  const value: SessionValue = {
    member,
    signIn: (next) => {
      setActingMember(next);
      setMember(next);
    },
    signOut: () => {
      setActingMember(null);
      setMember(null);
    },
  };
  return <SessionContext value={value}>{children}</SessionContext>;
}

export function useSession(): SessionValue {
  const value = use(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>");
  return value;
}

/** The acting member, for pages that only render once someone is chosen. */
export function useActingMember(): ActingMember {
  const { member } = useSession();
  if (!member) throw new Error("No acting member: this page must be inside <AppLayout>");
  return member;
}
