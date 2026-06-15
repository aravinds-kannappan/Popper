"use client";

import { useState } from "react";
import Chat, { Interaction } from "./Chat";
import LiveBenchmark from "./LiveBenchmark";

const GATE = 10;

export default function AgentLab() {
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [show, setShow] = useState(false);

  const count = interactions.length;
  const ready = count >= GATE;

  return (
    <div>
      <p className="note">
        This is Popper in action. Ask it any math or coding claim. For anything it can check, it
        tries to <b>break</b> the claim through AXLE and shows the real result. Send {GATE} messages
        and a live benchmark unlocks below, built from your own conversation.
      </p>

      <div className="gate">
        <div className="gate-bar">
          <div className="gate-fill" style={{ width: `${Math.min(100, (count / GATE) * 100)}%` }} />
        </div>
        <span className="gate-label">
          {ready ? `${count} messages, benchmark unlocked` : `${count} / ${GATE} messages to unlock the live benchmark`}
        </span>
      </div>

      <Chat onTurn={(i) => setInteractions((prev) => [...prev, i])} />

      {ready && !show && (
        <button className="btn" style={{ marginTop: 16 }} onClick={() => setShow(true)}>
          Show the live benchmark from these {count} messages
        </button>
      )}

      {ready && show && <LiveBenchmark interactions={interactions} />}
    </div>
  );
}
