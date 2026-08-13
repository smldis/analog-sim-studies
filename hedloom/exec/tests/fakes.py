"""A fake batch substrate whose lifetime is independent of its caller.

This exists to reproduce the one property that makes direct batch execution
hard: work accepted by the substrate survives the process that submitted it.
The store below stands in for that independent lifetime, so the failure
injections can run locally with no scheduler installed.
"""

from __future__ import annotations

from typing import Any, Mapping

from hedloom_exec.transport import Observation, SubmissionRefused, TransportError


class FakeBatchStore:
    """External state that outlives any controller. Stands in for the farm."""

    def __init__(self) -> None:
        self.jobs: dict[str, dict[str, Any]] = {}
        self.next_job_id = 1000
        self.accepted = 0

    def accept(self, identity: str) -> dict[str, Any]:
        """Accept work, keeping any existing record for this identity.

        Reusing the entry is what lets a duplicate submission be *observed*.
        Replacing it — as this once did — reset the run counter, so the
        no-duplication assertions held whether one or five jobs had been
        created. A fake that cannot fail is not evidence.
        """

        self.accepted += 1
        job = self.jobs.get(identity)
        if job is None:
            self.next_job_id += 1
            job = {"job_id": str(self.next_job_id), "state": "pending", "runs": 0}
            self.jobs[identity] = job
        return job


class FakeBatchTransport:
    """One controller's view of the store, with injectable failures."""

    name = "fake-batch"

    def __init__(
        self,
        store: FakeBatchStore,
        *,
        discovery_is_authoritative: bool = True,
        can_discover: bool = True,
        drop_receipt: bool = False,
        refuse: bool = False,
    ) -> None:
        self.store = store
        self.discovery_is_authoritative = discovery_is_authoritative
        # A site with no lookup-by-name facility at all: it can neither confirm
        # nor deny, which is the case that must fail loudly.
        self.can_discover = can_discover
        self.drop_receipt = drop_receipt
        self.refuse = refuse

    def submit(self, identity: str, bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.refuse:
            raise SubmissionRefused("queue rejected the job script")
        job = self.store.accept(identity)
        job["runs"] += 1
        if self.drop_receipt:
            # Injection one: the substrate accepted, the caller never learned.
            raise TransportError("connection lost after submission")
        return {"transport": self.name, "identity": identity, "job_id": job["job_id"]}

    def discover(self, identity: str) -> Mapping[str, Any] | None:
        if not self.can_discover:
            return None
        job = self.store.jobs.get(identity)
        if job is None:
            return None
        return {
            "transport": self.name,
            "identity": identity,
            "job_id": job["job_id"],
        }

    def poll(self, handle: Mapping[str, Any]) -> Observation:
        job = self.store.jobs.get(handle.get("identity"))
        if job is None:
            return Observation("absent")
        return Observation(job["state"], {"job_id": job["job_id"]})

    def cancel(self, handle: Mapping[str, Any]) -> None:
        job = self.store.jobs.get(handle.get("identity"))
        if job is not None:
            job["state"] = "cancelled"
