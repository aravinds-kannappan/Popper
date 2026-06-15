"use client";

import Markdown from "./Markdown";
import { research } from "../content/research";

export default function Research() {
  return (
    <div className="panel" style={{ padding: "8px 28px 24px" }}>
      <Markdown>{research}</Markdown>
      <p className="note" style={{ marginTop: 20 }}>
        The full write-up, including reproduction commands, lives in{" "}
        <a href="https://github.com/aravinds-kannappan/Popper/blob/main/reports/research.md">
          reports/research.md
        </a>
        .
      </p>
    </div>
  );
}
