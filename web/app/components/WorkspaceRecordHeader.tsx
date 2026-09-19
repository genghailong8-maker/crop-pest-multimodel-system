import type { ReactNode } from "react";
import Link from "next/link";

type WorkspaceRecordHeaderProps = {
  eyebrow: string;
  title: string;
  description?: string;
  recordId?: string;
  backHref?: string;
  backLabel?: string;
  badge?: string;
  action?: ReactNode;
};

export default function WorkspaceRecordHeader({
  eyebrow,
  title,
  description,
  recordId,
  backHref,
  backLabel = "返回",
  badge,
  action,
}: WorkspaceRecordHeaderProps) {
  return (
    <header className="workspace-v4-record-header">
      <div className="workspace-v4-record-heading">
        {backHref && <Link className="workspace-v4-back" href={backHref}><span aria-hidden="true">←</span>{backLabel}</Link>}
        <div>
          <div className="workspace-v4-record-line"><span className="workspace-v4-eyebrow">{eyebrow}</span>{recordId && <span className="workspace-v4-record-id">{recordId}</span>}{badge && <span className="workspace-v4-badge">{badge}</span>}</div>
          <h1>{title}</h1>
          {description && <p>{description}</p>}
        </div>
      </div>
      {action && <div className="workspace-v4-record-action">{action}</div>}
    </header>
  );
}
