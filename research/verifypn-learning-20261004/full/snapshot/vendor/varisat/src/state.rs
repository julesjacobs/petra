//! Miscellaneous solver state.
use crate::solver::SolverError;

/// Satisfiability state.
#[derive(Copy, Clone, Eq, PartialEq, Debug)]
pub enum SatState {
    Unknown,
    Sat,
    Unsat,
    UnsatUnderAssumptions,
}

impl Default for SatState {
    fn default() -> SatState {
        SatState::Unknown
    }
}

/// Miscellaneous solver state.
///
/// Anything larger or any larger group of related state variables should be moved into a separate
/// part of [`Context`](crate::context::Context).
pub struct SolverState {
    pub sat_state: SatState,
    pub formula_is_empty: bool,
    /// Whether solve was called at least once.
    pub solver_invoked: bool,
    pub state_is_invalid: bool,
    pub solver_error: Option<SolverError>,
    pub interrupt: Option<Box<dyn FnMut() -> bool>>,
}

impl Default for SolverState {
    fn default() -> SolverState {
        SolverState {
            sat_state: SatState::Unknown,
            formula_is_empty: true,
            solver_invoked: false,
            state_is_invalid: false,
            solver_error: None,
            interrupt: None,
        }
    }
}

impl SolverState {
    pub fn poll_interrupt(&mut self) -> bool {
        if self.solver_error.is_some() {
            return true;
        }
        if self.interrupt.as_mut().map_or(false, |callback| callback()) {
            self.solver_error = Some(SolverError::Interrupted);
            return true;
        }
        false
    }
}
