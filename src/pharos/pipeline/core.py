"""PharosPipeline: per-tick orchestrator that combines all sensing and estimation modules."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from pharos.cogload.core import cognitive_load_index, extract_features, preprocess_pupil
from pharos.entropy.core import stationary_entropy, transition_entropy
from pharos.io.core import GazeSource, PupilSource
from pharos.priority.core import Hazard, PriorityQueueEngine, ScoringContext, ScoringWeights
from pharos.sensing.core import SensingSource, density_to_visibility, scattering_to_density

# ── HudState ──────────────────────────────────────────────────────────────────


@dataclass
class HudState:
    """Serialisable snapshot produced by PharosPipeline on every tick.

    This is the JSON contract between the pipeline and the HUD frontend.

    active_hazards  — top-k Hazard objects (already ranked by STOM score)
    ranked_scores   — [(score, hazard_id), ...] for the full queue
    cognitive_load  — [0, 1] pupil-based load index
    smoke_density   — [0, 1] from Tyndall scattering sensor
    visibility      — metres, Koschmieder estimate
    gaze_entropy_hs — stationary Shannon entropy (bits)
    gaze_entropy_ht — transition Shannon entropy (bits)
    """

    timestamp: float
    active_hazards: list[Hazard]
    ranked_scores: list[tuple[float, str]]
    cognitive_load: float
    smoke_density: float
    visibility: float
    gaze_entropy_hs: float
    gaze_entropy_ht: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict.

        Hazard objects are reduced to {id, kind, priority} to keep the payload
        minimal — the HUD only needs what it renders.
        """
        return {
            "timestamp": self.timestamp,
            "active_hazards": [
                {
                    "id": h.id,
                    "kind": h.kind.name,
                    "priority": h.priority,
                }
                for h in self.active_hazards
            ],
            "ranked_scores": [[s, hid] for s, hid in self.ranked_scores],
            "cognitive_load": self.cognitive_load,
            "smoke_density": self.smoke_density,
            "visibility": self.visibility,
            "gaze_entropy_hs": self.gaze_entropy_hs,
            "gaze_entropy_ht": self.gaze_entropy_ht,
        }


# ── PharosPipeline ────────────────────────────────────────────────────────────

# Minimum fixations required before entropy is meaningful
_MIN_FIXATIONS_FOR_ENTROPY: int = 2


@dataclass
class _PipelineConfig:
    """Internal configuration bundle for PharosPipeline."""

    screen_size: tuple[int, int]
    bin_size: int
    fixation_window: int
    pupil_window: int
    baseline_n: int
    top_k: int
    scoring_weights: ScoringWeights | None


class PharosPipeline:
    """Per-tick orchestrator: reads one sample from each source, updates buffers,
    and returns a HudState with entropy, cognitive load, and hazard rankings.

    Call can_tick() before tick() to check whether all three sources still have data.
    """

    def __init__(
        self,
        gaze_source: GazeSource,
        pupil_source: PupilSource,
        sensing_source: SensingSource,
        hazards: list[Hazard],
        *,
        screen_size: tuple[int, int] = (800, 600),
        bin_size: int = 100,
        fixation_window: int = 100,
        pupil_window: int = 100,
        baseline_n: int = 25,
        top_k: int = 2,
        scoring_weights: ScoringWeights | None = None,
    ) -> None:
        self._gaze = gaze_source
        self._pupil = pupil_source
        self._sensing = sensing_source
        self._hazards = hazards
        self._cfg = _PipelineConfig(
            screen_size=screen_size,
            bin_size=bin_size,
            fixation_window=fixation_window,
            pupil_window=pupil_window,
            baseline_n=baseline_n,
            top_k=top_k,
            scoring_weights=scoring_weights,
        )
        self._engine = PriorityQueueEngine(top_k=top_k, weights=scoring_weights)
        # buffers store plain tuples; converted to ndarray on demand
        self._fix_buf: deque[tuple[float, float]] = deque(maxlen=fixation_window)
        self._pupil_buf: deque[tuple[float, float]] = deque(maxlen=pupil_window)

    def can_tick(self) -> bool:
        """Return True when all three sources have at least one sample remaining."""
        return (
            self._gaze.has_data()
            and self._pupil.has_data()
            and self._sensing.has_data()
        )

    def tick(self) -> HudState:
        """Consume one sample from each source and return a fresh HudState.

        Entropy and cognitive load return 0.0 until enough samples accumulate
        (entropy: ≥ 2 fixations; cogload: ≥ baseline_n + 1 pupil samples).
        """
        gaze_s = self._gaze.read()
        pupil_s = self._pupil.read()
        scatter_s = self._sensing.read()

        self._fix_buf.append(gaze_s.fixation)
        self._pupil_buf.append((pupil_s.timestamp, pupil_s.diameter_mm))

        density = scattering_to_density(scatter_s.intensity)
        visibility = density_to_visibility(density)

        hs, ht = self._compute_entropy()
        cli = self._compute_cogload()

        ctx = ScoringContext(smoke_density=density, visibility=visibility)
        self._engine.update(self._hazards, ctx)

        ranked = self._engine.ranked_queue()
        return HudState(
            timestamp=gaze_s.timestamp,
            active_hazards=self._engine.active_items(),
            ranked_scores=[(s, h.id) for s, h in ranked],
            cognitive_load=cli,
            smoke_density=density,
            visibility=visibility,
            gaze_entropy_hs=hs,
            gaze_entropy_ht=ht,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    def _compute_entropy(self) -> tuple[float, float]:
        """Return (Hs, Ht) from fixation buffer; (0.0, 0.0) if too few samples."""
        if len(self._fix_buf) < _MIN_FIXATIONS_FOR_ENTROPY:
            return 0.0, 0.0
        fxy: npt.NDArray[np.float64] = np.array(list(self._fix_buf), dtype=np.float64)
        hs = stationary_entropy(fxy, self._cfg.bin_size, self._cfg.screen_size)
        ht = transition_entropy(fxy, self._cfg.bin_size, self._cfg.screen_size)
        return hs, ht

    def _compute_cogload(self) -> float:
        """Return cognitive_load_index from pupil buffer; 0.0 if baseline not yet full."""
        n = len(self._pupil_buf)
        if n < self._cfg.baseline_n + 1:
            return 0.0
        arr: npt.NDArray[np.float64] = np.array(list(self._pupil_buf), dtype=np.float64)
        timestamps = arr[:, 0]
        diameters = arr[:, 1]
        baseline_end = float(timestamps[self._cfg.baseline_n - 1])
        baseline_interval = (float(timestamps[0]), baseline_end)
        clean = preprocess_pupil(timestamps, diameters)
        feats = extract_features(timestamps, clean, baseline_interval)
        return cognitive_load_index(feats)
