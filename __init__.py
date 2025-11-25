from typing import Optional, Dict
import json
import os

from anki.cards import Card
from aqt import mw, gui_hooks
from aqt.utils import showInfo, qconnect, getText
from aqt.qt import QAction, QTimer

# ===== Config =====
DEFAULT_SECONDS = 6.0

auto_answer_enabled: bool = True
_timer: Optional[QTimer] = None
_current_card_id: Optional[int] = None


ADDON_DIR = os.path.dirname(__file__)
USER_FILES_DIR = os.path.join(ADDON_DIR, "user_files")
TIMERS_PATH = os.path.join(USER_FILES_DIR, "timers.json")

_timers: Dict[str, float] = {}  # card_id (str) -> seconds


# ===== JSON load/save =====

def _load_timers() -> None:
    """Load timers.json into _timers dict."""
    global _timers
    if os.path.exists(TIMERS_PATH):
        try:
            with open(TIMERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            _timers = data.get("timers", {})
        except Exception as e:
            print("AutoAnswerTimer: failed to load timers.json:", e)
            _timers = {}
    else:
        _timers = {}


def _save_timers() -> None:
    """Persist _timers dict to timers.json."""
    data = {"timers": _timers}
    try:
        with open(TIMERS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("AutoAnswerTimer: failed to save timers.json:", e)


# Load once at import
_load_timers()


# ===== Core timer logic =====

def _cancel_timer() -> None:
    """Stop and dispose of any existing timer."""
    global _timer
    if _timer is not None:
        _timer.stop()
        _timer.deleteLater()
        _timer = None


def _get_seconds_for_card(card: Card) -> float:
    """Return delay (seconds) for this card, from JSON or default."""
    card_id = str(card.id)
    try:
        return float(_timers.get(card_id, DEFAULT_SECONDS))
    except (TypeError, ValueError):
        return DEFAULT_SECONDS


def _schedule_auto_answer(card: Card) -> None:
    """
    Called when the reviewer shows the QUESTION side.
    Schedules an automatic 'show answer' after N seconds.
    """
    global _timer, _current_card_id
    print("Auto answer starts")

    _cancel_timer()

    if not auto_answer_enabled:
        print("Auto answer is disabled")
        return

    if mw.reviewer.state != "question":
        print("Not in question state, skipping")
        return

    seconds = _get_seconds_for_card(card)
    _current_card_id = card.id

    _timer = QTimer(mw)
    _timer.setSingleShot(True)

    print(f"Auto answer will be shown in {seconds} seconds")

    def on_timeout() -> None:
        print("Auto answer timer fired")
        # Only act if:
        #  - reviewer still exists
        #  - we're still on the same card
        #  - still on question side (haven't shown answer yet)
        if (
            mw.reviewer is not None
            and mw.reviewer.card is not None
            and mw.reviewer.card.id == _current_card_id
            and mw.reviewer.state == "question"
        ):
            mw.reviewer.onEnterKey()  # simulate pressing space/enter

    _timer.timeout.connect(on_timeout)
    _timer.start(int(seconds * 1000))


def _on_show_answer(card: Card) -> None:
    """When the answer shows, we cancel the timer (nothing left to do)."""
    _cancel_timer()
    print("Answer shown, timer cancelled")


# ===== UI: toggles + per-card editing =====

def _toggle_auto_answer() -> None:
    """Menu action to turn the feature on/off."""
    global auto_answer_enabled
    auto_answer_enabled = not auto_answer_enabled
    status = "ON" if auto_answer_enabled else "OFF"
    showInfo(f"Per-card auto answer is now {status}.")


def _set_timer_for_current_card() -> None:
    """Ask user for seconds and store them for the current card in timers.json."""
    global _timers

    if mw.reviewer is None or mw.reviewer.card is None:
        showInfo("No card is currently being reviewed.")
        return

    card = mw.reviewer.card
    card_id = str(card.id)

    current = _timers.get(card_id)
    default_str = str(current if current is not None else DEFAULT_SECONDS)

    text, ok = getText(
        "Enter auto-answer delay in seconds for this card.\n"
        "(Leave empty to cancel, or set 0 to disable for this card.)",
        default=default_str,
        title="Set Auto-Answer Timer",
    )

    if not ok:
        return  # user cancelled dialog

    text = text.strip()
    if not text:
        # Empty -> do nothing
        return

    try:
        seconds = float(text)
    except ValueError:
        showInfo("Invalid number. Please enter a valid numeric value.")
        return

    
    if seconds <= 0:
        # interpret 0 or negative as "clear timer, use global default"
        if card_id in _timers:
            del _timers[card_id]
            _save_timers()
        showInfo("Custom timer cleared for this card. Default will be used.")
    else:
        _timers[card_id] = seconds
        _save_timers()
        showInfo(f"Auto-answer timer for this card set to {seconds} seconds.")


def _clear_timer_for_current_card() -> None:
    """Remove custom timer for current card (fallback to default)."""
    if mw.reviewer is None or mw.reviewer.card is None:
        showInfo("No card is currently being reviewed.")
        return

    card_id = str(mw.reviewer.card.id)
    global _timers

    if card_id in _timers:
        del _timers[card_id]
        _save_timers()
        showInfo("Custom timer cleared for this card. Default will be used.")
    else:
        showInfo("This card does not have a custom timer set.")


def _setup_menu() -> None:
    """Add menu items under Tools."""
    # Toggle global behaviour
    action_toggle = QAction("Toggle Per-Card Auto Answer", mw)
    qconnect(action_toggle.triggered, _toggle_auto_answer)
    mw.form.menuTools.addAction(action_toggle)

def _add_reviewer_more_menu_options(reviewer, menu):
    """Adds 'Set Timer' and 'Clear Timer' into the Reviewer's More menu."""
    action_set = QAction("Set Auto-Answer Timer for This Card", menu)
    qconnect(action_set.triggered, _set_timer_for_current_card)
    menu.addAction(action_set)


# ===== Hook registrations =====

gui_hooks.reviewer_did_show_question.append(_schedule_auto_answer)
gui_hooks.reviewer_did_show_answer.append(_on_show_answer)
gui_hooks.reviewer_will_show_context_menu.append(_add_reviewer_more_menu_options)
gui_hooks.main_window_did_init.append(lambda: _setup_menu())