// Non-negotiable provenance labelling: any panel whose data carries
// data_provenance === "SYNTHETIC_DEMONSTRATION" must show this badge.

export function ProvenanceBadge({ provenance }: { provenance?: string }) {
  if (provenance !== "SYNTHETIC_DEMONSTRATION") return null;
  return (
    <span className="badge badge-synthetic" title="Process and economic data is simulated, not measured from the plant.">
      Synthetic Demonstration Data
    </span>
  );
}

export function StubModeBadge({ stubMode }: { stubMode?: boolean }) {
  if (!stubMode) return null;
  return (
    <span className="badge badge-stub" title="Backend is running in stub mode (no live model weights).">
      Stub Mode
    </span>
  );
}

export function MockDataBadge({ isMock }: { isMock: boolean }) {
  if (!isMock) return null;
  return (
    <span className="badge badge-stub" title="Backend unreachable — showing local mock data.">
      Offline · Mock Data
    </span>
  );
}
