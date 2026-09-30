"""Every operational value, set from the environment (see ``.env.example``).

Nothing that sizes, times or paces the hub is fixed in the code: the
defaults below are the values it always had; each one is overridden by
the environment variable of the same name in capitals (``DB_POOL_SIZE``,
``MEAL_AI_TIME_LIMIT_S``…). Documented in docs/guides/configuration.md.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode

#: A list set as ``1,2,3`` in the environment.
Numbers = Annotated[list[float], NoDecode]


class Tuning(BaseSettings):
    """Processes, time limits, sizes, batches, schedules and rules."""

    # --- Database connections (per API or worker process) ---------------
    db_pool_size: int = Field(5, ge=1)
    db_max_overflow: int = Field(5, ge=0)
    db_pool_timeout_s: float = Field(30.0, gt=0)

    # --- Worker (background jobs) ----------------------------------------
    worker_max_jobs: int = Field(10, ge=1)
    worker_job_timeout_s: int = Field(7200, ge=1)
    worker_max_tries: int = Field(1, ge=1)
    worker_keep_result_s: int = Field(3600, ge=0)

    # --- AI (Ollama) --------------------------------------------------------
    ollama_timeout_s: float = Field(600.0, gt=0)
    #: Model calls at once, per process (Ollama queues the rest anyway).
    ollama_concurrency: int = Field(1, ge=1)
    meal_ai_time_limit_s: float = Field(900.0, gt=0)
    meal_ai_max_tokens: int = Field(1500, ge=100)
    meal_ai_judge_tokens: int = Field(700, ge=100)
    document_ai_time_limit_s: float = Field(1800.0, gt=0)
    document_ai_chunk_chars: int = Field(5000, ge=500)
    document_ai_max_chunks: int = Field(8, ge=1)
    label_ai_time_limit_s: float = Field(100.0, gt=0)
    ocr_max_pages: int = Field(12, ge=1)
    #: Resolution a scanned page is read at (OCR, model).
    ocr_dpi: int = Field(200, ge=72)
    #: Words the model may write: a document's values, then its summary.
    document_ai_values_tokens: int = Field(1024, ge=100)
    document_ai_summary_tokens: int = Field(900, ge=100)
    #: Characters of a document given to the model for its summary.
    document_ai_summary_chars: int = Field(12_000, ge=1000)
    #: Values the model gave that the text does not bear, kept to show.
    document_ai_rejected_max: int = Field(30, ge=0)
    #: A remark of the model longer than this is cut at a sentence.
    meal_remark_max_chars: int = Field(300, ge=40)
    #: A product's ingredients longer than this are not given to it.
    meal_ingredients_max_chars: int = Field(400, ge=0)
    #: Longest side (pixels) of a picture read: label, extra photo…
    image_read_side: int = Field(2048, ge=320)
    #: …a barcode (larger: thin bars)…
    barcode_read_side: int = Field(2400, ge=320)
    #: …and two photos compared side by side.
    photo_compare_side: int = Field(640, ge=64)

    # --- Sizes and limits ---------------------------------------------------
    evidence_max_mb: int = Field(30, ge=1)
    medical_max_mb: int = Field(25, ge=1)
    #: Longest side of a photo kept after normalising (pixels).
    image_max_side: int = Field(1280, ge=320)
    meal_max_photos: int = Field(6, ge=0)
    meal_max_foods: int = Field(20, ge=1)
    meal_description_max: int = Field(2000, ge=100)
    #: A meal line above this is refused as impossible (grams).
    meal_line_max_g: float = Field(1500.0, gt=0)
    ecg_max_points: int = Field(5000, ge=100)
    route_max_points: int = Field(3000, ge=100)
    document_text_max: int = Field(200_000, ge=1000)

    # --- Open Food Facts ----------------------------------------------------
    openfoodfacts_timeout_s: float = Field(10.0, gt=0)
    #: Nightly re-reading, UTC.
    food_refresh_hour: int = Field(4, ge=0, le=23)
    food_refresh_minute: int = Field(40, ge=0, le=59)
    food_refresh_per_night: int = Field(50, ge=1)
    food_refresh_pause_s: float = Field(1.0, ge=0)
    #: « Tout relire » answers within this; the rest waits for the night.
    food_refresh_budget_s: float = Field(60.0, gt=0)

    # --- Batches (imports, syncs, rebuilds) ---------------------------------
    import_batch: int = Field(5000, ge=100)
    import_commit_every: int = Field(50_000, ge=1000)
    import_rollup_batch: int = Field(500, ge=10)
    import_obs_batch: int = Field(1000, ge=10)
    rollup_read_block: int = Field(20_000, ge=100)
    sync_chunk: int = Field(2000, ge=10)
    sync_rollup_chunk: int = Field(400, ge=10)
    catalog_sync_batch: int = Field(5000, ge=100)
    delete_chunk: int = Field(500, ge=10)
    #: Ids per ``IN (…)`` (SQLite allows 999 bound values at most).
    sql_in_chunk: int = Field(500, ge=10, le=900)
    upload_chunk_kb: int = Field(1024, ge=16)
    #: Lines of an import report listed (skipped lines, periods…).
    import_report_lines: int = Field(50, ge=1)
    #: One message trace of a chat holds this many characters at most.
    chat_trace_max_chars: int = Field(8000, ge=500)
    #: A trace this close to one already kept is the same (seconds).
    trace_same_time_s: float = Field(60.0, ge=0)

    # --- Logs ---------------------------------------------------------------
    #: An API request this long or longer ends with ``slow`` in the log.
    log_slow_ms: int = Field(1000, ge=1)

    # --- Updates (run/ files shared with ./update.sh) -----------------------
    update_fresh_s: int = Field(180, ge=10)
    update_taken_s: int = Field(180, ge=10)
    update_running_s: int = Field(1200, ge=60)

    # --- Work and sleep rules -----------------------------------------------
    #: Legal maxima (Code du travail): a day, a week, a day's spread.
    work_max_day_hours: float = Field(10.0, gt=0)
    work_max_week_hours: float = Field(48.0, gt=0)
    work_max_spread_hours: float = Field(13.0, gt=0)
    #: A session longer than this is refused as a typing error.
    work_max_session_hours: float = Field(72.0, gt=0)
    #: A clock-in without clock-out is « at work now » this long.
    work_open_session_hours: float = Field(16.0, gt=0)
    #: A clock-in and a clock-out further apart are not paired (imports).
    work_pair_max_hours: float = Field(20.0, gt=0)
    #: A ticket's worked time above this is not believed (hours).
    work_ticket_max_hours: float = Field(12.0, gt=0)
    #: Landmarks: daily rest, a long session, a 12-week average.
    work_min_rest_hours: float = Field(11.0, gt=0)
    work_long_session_hours: float = Field(12.0, gt=0)
    work_max_avg_hours: float = Field(44.0, gt=0)
    work_avg_weeks: int = Field(12, ge=1)
    #: Night hours (local, HH:MM).
    work_night_start: str = Field("21:00", pattern=r"^\d{2}:\d{2}$")
    work_night_end: str = Field("06:00", pattern=r"^\d{2}:\d{2}$")
    sleep_manual_max_hours: float = Field(20.0, gt=0)
    #: Weeks drawn in the work report's chart.
    work_chart_weeks: int = Field(52, ge=4)
    #: « Journées les plus significatives »: how many, and a session this
    #: long is « through the night ».
    work_highlight_days: int = Field(20, ge=1)
    work_continuous_hours: float = Field(24.0, gt=0)
    #: A trace this long (a parking, a hotel) also marks the next days.
    work_stay_hours: float = Field(6.0, gt=0)
    #: A night whose end falls before this hour counts for the day before.
    work_morning_hour: int = Field(12, ge=0, le=23)
    #: A session's other end is looked for this far (hours).
    work_pair_search_hours: float = Field(20.0, gt=0)
    #: A correlation needs this many days (work ↔ health file).
    work_corr_min_pairs: int = Field(5, ge=3)
    #: A pause in the night this long is an awakening; a gap this long
    #: starts a new sleep block (minutes).
    sleep_awakening_min: float = Field(5.0, gt=0)
    sleep_block_gap_min: float = Field(60.0, gt=0)
    #: The longest a sleep sample may be (hours; a query bound).
    sleep_sample_max_hours: float = Field(48.0, gt=0)
    #: A dose may be logged this far in the future (clock drift, minutes).
    medication_future_min: float = Field(10.0, ge=0)
    #: A dose logged this long after it was taken is « saisie tardive ».
    medication_late_entry_min: float = Field(60.0, gt=0)
    #: Days an adherence covers when none is asked.
    adherence_days: int = Field(30, ge=1)
    #: A photo is refused under this size, too dark, too bright or blurry.
    photo_min_side: int = Field(300, ge=32)
    photo_dark: float = Field(35.0, ge=0, le=255)
    photo_bright: float = Field(235.0, ge=0, le=255)
    photo_blurry: float = Field(12.0, ge=0)
    #: A photo trend needs this many days over this span (days); its
    #: slope is read over the last window; a smoothing of this many days;
    #: under this slope (points per 30 days) it is « stable ».
    photo_trend_min_days: int = Field(8, ge=2)
    photo_trend_min_span_days: int = Field(21, ge=1)
    photo_trend_window_days: int = Field(90, ge=7)
    photo_trend_smooth_days: int = Field(7, ge=1)
    photo_trend_stable: float = Field(0.5, ge=0)
    #: Restaurants listed in « Dépenses ».
    spending_top: int = Field(10, ge=1)
    #: Late orders (Dépenses): from this hour to that one, local time.
    spending_late_from_hour: int = Field(21, ge=0, le=23)
    spending_late_until_hour: int = Field(5, ge=0, le=23)

    # --- Web page (sent by GET /system/settings; seconds) -------------------
    #: A hub that does not answer (restarting) is asked again this often.
    web_retry_s: float = Field(5.0, gt=0)
    #: The session is renewed this long before its access token ends.
    web_renew_margin_s: int = Field(180, ge=0)
    #: A session renewal waits this long for the hub.
    web_refresh_timeout_s: float = Field(15.0, gt=0)
    #: A new version installed is looked for this often (and on focus)…
    web_update_check_s: float = Field(300.0, gt=0)
    #: …this often while the host updates…
    web_update_look_s: float = Field(20.0, gt=0)
    #: …and the update's state (administrator) this often meanwhile.
    web_update_state_s: float = Field(15.0, gt=0)
    #: An update finished this recently is confirmed on the page.
    web_update_recent_s: float = Field(1800.0, gt=0)
    #: An AI reading under way (meal, document) is looked for this often.
    web_poll_s: float = Field(5.0, gt=0)
    #: After « Réconcilier » (Données), the pages are refreshed this
    #: often, this many times (about 3 minutes).
    web_reconcile_refresh_s: float = Field(10.0, gt=0)
    web_reconcile_refresh_steps: int = Field(18, ge=0)
    #: After « Réanalyser tout l'historique » (photos), likewise.
    web_reanalysis_refresh_s: float = Field(10.0, gt=0)
    web_reanalysis_refresh_steps: int = Field(12, ge=0)
    #: After a photo reading is asked, the photo is read again after these.
    web_photo_refresh_s: Numbers = Field(default=[1.5, 4.0, 8.0, 13.0])
    #: A page missing after an update reloads once in this time at most.
    web_reload_guard_s: float = Field(60.0, gt=0)
    #: The « Par page » choices of the lists.
    web_page_sizes: Numbers = Field(default=[10, 25, 50, 100, 200])

    @field_validator("web_photo_refresh_s", "web_page_sizes", mode="before")
    @classmethod
    def _numbers(cls, value: object) -> object:
        """``1.5,4,8`` (a list given as is is kept)."""
        if isinstance(value, str):
            return [float(x) for x in value.split(",") if x.strip()]
        return value
