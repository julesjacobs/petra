//! Opt-in bounded progress records; never part of a solver certificate.
use std::{
    cell::Cell,
    collections::{BTreeMap, BTreeSet},
    io::{self, Write},
    sync::atomic::{AtomicU64, AtomicUsize, Ordering},
    time::Instant,
};

const MAX_EVENTS: usize = 128;
const MAX_COUNTERS: usize = 64;
const MAX_RECORD_BYTES: usize = 16_384;
const PROGRESS_WORK: usize = 100_000;
static NEXT_OPERATION: AtomicU64 = AtomicU64::new(0);
static PROCESS_EVENTS: AtomicUsize = AtomicUsize::new(0);
thread_local! {
    static CURRENT_PHASE: Cell<Option<(u64, u64)>> = const { Cell::new(None) };
}

pub(crate) struct Diagnostics(Option<Box<Enabled>>);
struct Enabled {
    output: Box<dyn Write>,
    process_limit: bool,
    operation: &'static str,
    operation_id: u64,
    phase_id: u64,
    parent: Option<(u64, u64)>,
    phase: &'static str,
    activity: &'static str,
    started: Instant,
    phase_started: Instant,
    activity_started: Instant,
    activity_ns: BTreeMap<&'static str, u128>,
    seen_activities: BTreeSet<&'static str>,
    counters: BTreeMap<&'static str, usize>,
    controls: BTreeSet<Vec<u64>>,
    control_coordinates: usize,
    work: usize,
    next_progress: usize,
    events: usize,
    finished: bool,
}

impl Diagnostics {
    pub(crate) fn new(operation: &'static str) -> Self {
        if std::env::var_os("VASS_RAW_PHASE_DIAGNOSTICS").is_none() {
            return Self(None);
        }
        Self::with_writer(operation, Box::new(io::stderr()), true)
    }
    fn with_writer(operation: &'static str, output: Box<dyn Write>, process_limit: bool) -> Self {
        let now = Instant::now();
        let operation_id = NEXT_OPERATION.fetch_add(1, Ordering::Relaxed);
        let parent = CURRENT_PHASE.with(|current| current.replace(Some((operation_id, 0))));
        let mut enabled = Enabled {
            output,
            process_limit,
            operation,
            operation_id,
            phase_id: 0,
            parent,
            phase: "setup",
            activity: "setup",
            started: now,
            phase_started: now,
            activity_started: now,
            activity_ns: BTreeMap::new(),
            seen_activities: BTreeSet::from(["setup"]),
            counters: BTreeMap::new(),
            controls: BTreeSet::new(),
            control_coordinates: 0,
            work: 0,
            next_progress: PROGRESS_WORK,
            events: 0,
            finished: false,
        };
        enabled.emit("phase-start", None);
        Self(Some(Box::new(enabled)))
    }
    #[cfg(test)]
    pub(crate) fn disabled() -> Self {
        Self(None)
    }
    pub(crate) fn enabled(&self) -> bool {
        self.0.is_some()
    }
    pub(crate) fn phase(&mut self, phase: &'static str) {
        if let Some(inner) = &mut self.0 {
            inner.emit("phase-end", Some("complete"));
            inner.set_activity(phase);
            inner.phase_id += 1;
            CURRENT_PHASE.with(|current| current.set(Some((inner.operation_id, inner.phase_id))));
            inner.phase = phase;
            inner.phase_started = Instant::now();
            inner.emit("phase-start", None);
        }
    }
    pub(crate) fn activity(&mut self, activity: &'static str) -> Option<&'static str> {
        self.0.as_mut().map(|inner| {
            let previous = inner.activity;
            inner.set_activity(activity);
            if inner.seen_activities.insert(activity) {
                inner.emit("activity-start", None);
            }
            previous
        })
    }
    pub(crate) fn restore_activity(&mut self, previous: Option<&'static str>) {
        if let (Some(inner), Some(previous)) = (&mut self.0, previous) {
            inner.set_activity(previous);
        }
    }
    pub(crate) fn add(&mut self, name: &'static str, amount: usize) {
        if let Some(inner) = &mut self.0
            && (inner.counters.len() < MAX_COUNTERS || inner.counters.contains_key(name))
        {
            let value = inner.counters.entry(name).or_default();
            *value = value.saturating_add(amount);
        }
    }
    pub(crate) fn maximum(&mut self, name: &'static str, value: usize) {
        if let Some(inner) = &mut self.0
            && (inner.counters.len() < MAX_COUNTERS || inner.counters.contains_key(name))
        {
            let old = inner.counters.entry(name).or_default();
            *old = (*old).max(value);
        }
    }
    pub(crate) fn work(&mut self, amount: usize) {
        if let Some(inner) = &mut self.0 {
            inner.work = inner.work.saturating_add(amount);
            if inner.work >= inner.next_progress {
                inner.next_progress = inner.work.saturating_mul(2);
                inner.emit("progress", None);
            }
        }
    }
    pub(crate) fn observe_control(&mut self, control: &[u64]) {
        if let Some(inner) = &mut self.0 {
            if inner.controls.contains(control) {
                return;
            }
            if inner.controls.len() >= 1024
                || control.len() > 65_536usize.saturating_sub(inner.control_coordinates)
            {
                inner.counters.insert("projected_markings_capped", 1);
                return;
            }
            inner.control_coordinates += control.len();
            inner.controls.insert(control.to_vec());
            inner
                .counters
                .insert("projected_markings_observed", inner.controls.len());
        }
    }
    pub(crate) fn finish(&mut self, status: &'static str) {
        if let Some(inner) = &mut self.0
            && !inner.finished
        {
            inner.emit("phase-end", Some(status));
            inner.finished = true;
            CURRENT_PHASE.with(|current| {
                if current.get() == Some((inner.operation_id, inner.phase_id)) {
                    current.set(inner.parent);
                }
            });
        }
    }
    pub(crate) fn finish_result<T>(&mut self, result: &anyhow::Result<T>) {
        if self.0.is_none() {
            return;
        }
        let status = match result {
            Ok(_) => "complete",
            Err(error) => {
                let message = error.to_string();
                if message.contains("deadline") {
                    "deadline"
                } else if message.contains("work limit") {
                    "work-limit"
                } else if message.contains("dimension limit") {
                    "dimension-limit"
                } else if message.contains("overflow") || message.contains("exceeds u64") {
                    "arithmetic-limit"
                } else {
                    "error"
                }
            }
        };
        self.finish(status);
    }
}
impl Enabled {
    fn set_activity(&mut self, activity: &'static str) {
        let now = Instant::now();
        let elapsed = now.duration_since(self.activity_started).as_nanos();
        let total = self.activity_ns.entry(self.activity).or_default();
        *total = total.saturating_add(elapsed);
        self.activity_started = now;
        self.activity = activity;
    }
    fn emit(&mut self, event: &'static str, status: Option<&'static str>) {
        if self.events >= MAX_EVENTS {
            return;
        }
        let slot = if self.process_limit {
            let Ok(slot) =
                PROCESS_EVENTS.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |count| {
                    (count < MAX_EVENTS).then_some(count + 1)
                })
            else {
                return;
            };
            slot
        } else {
            self.events
        };
        self.set_activity(self.activity);
        let event = if slot == MAX_EVENTS - 1 {
            "diagnostics-truncated"
        } else {
            event
        };
        let mut record = serde_json::json!({
            "raw_phase_diagnostic":"v1", "operation":self.operation,
            "pid":std::process::id(), "operation_id":self.operation_id,
            "phase_id":self.phase_id, "parent":self.parent.map(|(operation_id,phase_id)|
                serde_json::json!({"operation_id":operation_id,"phase_id":phase_id})),
            "event":event, "sequence":self.events, "phase":self.phase,
            "activity":self.activity, "status":status,
            "elapsed_seconds":self.started.elapsed().as_secs_f64(),
            "phase_seconds":self.phase_started.elapsed().as_secs_f64(),
            "charged_work":self.work, "counters":self.counters,
            "exclusive_activity_nanoseconds":self.activity_ns,
        });
        self.events += 1;
        let encoded = record.to_string();
        if encoded.len() + 1 > MAX_RECORD_BYTES {
            if self.process_limit {
                PROCESS_EVENTS.store(MAX_EVENTS, Ordering::Relaxed);
            }
            self.events = MAX_EVENTS;
            record["event"] = "diagnostics-truncated".into();
            record["reason"] = "record-byte-limit".into();
            record["counters"] = serde_json::json!({});
            record["exclusive_activity_nanoseconds"] = serde_json::json!({});
            let _ = writeln!(self.output, "{record}");
        } else {
            let _ = writeln!(self.output, "{encoded}");
        }
        let _ = self.output.flush();
    }
}
impl Drop for Diagnostics {
    fn drop(&mut self) {
        self.finish("aborted");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{cell::RefCell, rc::Rc};
    #[derive(Clone, Default)]
    struct Output(Rc<RefCell<(Vec<u8>, usize)>>);
    impl Write for Output {
        fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
            self.0.borrow_mut().0.extend_from_slice(bytes);
            Ok(bytes.len())
        }
        fn flush(&mut self) -> io::Result<()> {
            self.0.borrow_mut().1 += 1;
            Ok(())
        }
    }
    fn records(output: &Output) -> Vec<serde_json::Value> {
        String::from_utf8(output.0.borrow().0.clone())
            .unwrap()
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect()
    }
    #[test]
    fn bounded_records_are_flushed_and_end_with_truncation() {
        let output = Output::default();
        let mut d = Diagnostics::with_writer("test", Box::new(output.clone()), false);
        for _ in 0..1000 {
            d.add("nodes", 1);
            d.phase("next");
        }
        d.finish("complete");
        let rows = records(&output);
        assert_eq!(rows.len(), MAX_EVENTS);
        assert_eq!(output.0.borrow().1, MAX_EVENTS);
        assert_eq!(rows.last().unwrap()["event"], "diagnostics-truncated");
        assert!(rows.iter().enumerate().all(|(i, row)| row["sequence"] == i));
    }
    #[test]
    fn progress_leaves_room_for_phase_completion_at_large_work_budgets() {
        let output = Output::default();
        let mut d = Diagnostics::with_writer("test", Box::new(output.clone()), false);
        for _ in 0..1000 {
            d.work(PROGRESS_WORK);
        }
        d.finish("work-limit");
        let rows = records(&output);
        assert!(rows.len() < 20);
        let last = rows.last().unwrap();
        assert_eq!(last["event"], "phase-end");
        assert_eq!(last["status"], "work-limit");
        assert_eq!(last["charged_work"], 1000 * PROGRESS_WORK);
    }
    #[test]
    fn early_drop_retains_active_phase_and_exclusive_activity() {
        let output = Output::default();
        {
            let mut d = Diagnostics::with_writer("test", Box::new(output.clone()), false);
            d.phase("game-expansion");
            let prior = d.activity("transfer-search");
            d.add("transfer_calls", 1);
            d.work(PROGRESS_WORK);
            d.restore_activity(prior);
            d.activity("checking");
        }
        let rows = records(&output);
        assert!(
            rows.iter()
                .any(|r| r["event"] == "progress" && r["activity"] == "transfer-search")
        );
        let last = rows.last().unwrap();
        assert_eq!(last["status"], "aborted");
        assert_eq!(last["activity"], "checking");
        assert_eq!(last["counters"]["transfer_calls"], 1);
        assert!(
            last["exclusive_activity_nanoseconds"]
                .get("transfer-search")
                .is_some()
        );
    }
    #[test]
    fn disabled_recorder_has_no_state_and_output_errors_are_ignored() {
        let mut disabled = Diagnostics::disabled();
        disabled.phase("test");
        disabled.work(usize::MAX);
        disabled.add("nodes", 1);
        assert!(!disabled.enabled());
        assert!(disabled.activity("test").is_none());
        struct Broken;
        impl Write for Broken {
            fn write(&mut self, _: &[u8]) -> io::Result<usize> {
                Err(io::Error::other("closed"))
            }
            fn flush(&mut self) -> io::Result<()> {
                Err(io::Error::other("closed"))
            }
        }
        let mut broken = Diagnostics::with_writer("test", Box::new(Broken), false);
        broken.phase("checking");
        broken.finish("complete");
    }
}
